import os
import time
import uuid
import asyncio
from dataclasses import dataclass

import httpx


OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
API_BASE = "https://gigachat.devices.sberbank.ru"
CHAT_COMPLETIONS_URL = f"{API_BASE}/api/v1/chat/completions"

async def _post_with_retries(
    client: httpx.AsyncClient,
    url: str,
    *,
    headers: dict | None = None,
    data: dict | None = None,
    json: dict | None = None,
    retries: int = 3,
) -> httpx.Response:
    delay = 0.25
    last_exc: Exception | None = None

    for attempt in range(retries):
        try:
            r = await client.post(url, headers=headers, data=data, json=json)

            if r.status_code in (429, 500, 502, 503, 504):
                await asyncio.sleep(delay)
                delay *= 2
                continue

            r.raise_for_status()
            return r

        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as e:
            last_exc = e

            if isinstance(e, httpx.HTTPStatusError) and e.response is not None:
                sc = e.response.status_code
                if sc < 500 and sc != 429:
                    raise

            await asyncio.sleep(delay)
            delay *= 2

    raise last_exc or RuntimeError("HTTP request failed after retries")

@dataclass
class _Token:
    access_token: str
    expires_at_unix: int


class GigaChatLLM:
    """
    Async REST client for GigaChat:
    - Gets OAuth access token (valid ~30 minutes) and caches it
    - Calls /api/v1/chat/completions and returns assistant content
    """

    def __init__(
        self,
        auth_key: str,
        scope: str = "GIGACHAT_API_PERS",
        model: str = "GigaChat-Pro",
        verify_ssl: bool = False,
        timeout_s: float = 30.0,
    ):
        self.auth_key = auth_key
        self.scope = scope
        self.model = model
        self.verify_ssl = verify_ssl
        self.timeout_s = timeout_s
        self._token: _Token | None = None
        self._token_lock = asyncio.Lock()

    async def _get_access_token(self) -> str:
        if self._token and (self._token.expires_at_unix - int(time.time()) > 30):
            return self._token.access_token

        async with self._token_lock:
            if self._token and (self._token.expires_at_unix - int(time.time()) > 30):
                return self._token.access_token

            headers = {
                "RqUID": str(uuid.uuid4()),
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {self.auth_key}",
            }
            data = {"scope": self.scope}

            async with httpx.AsyncClient(timeout=self.timeout_s, verify=self.verify_ssl) as client:
                r = await _post_with_retries(client, OAUTH_URL, headers=headers, data=data, retries=3)
                payload = r.json()

            access_token = payload["access_token"]
            expires_at = int(payload["expires_at"])
            self._token = _Token(access_token=access_token, expires_at_unix=expires_at)
            return access_token

    async def to_sql(self, system_prompt: str, user_text: str) -> str:
        token = await self._get_access_token()

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }

        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            "temperature": 0.0,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=self.timeout_s, verify=self.verify_ssl) as client:
            r = await _post_with_retries(client, CHAT_COMPLETIONS_URL, headers=headers, json=body, retries=3)
            data = r.json()

        return (data["choices"][0]["message"]["content"] or "").strip()


def from_env() -> GigaChatLLM:
    auth_key = os.environ["GIGACHAT_AUTH_KEY"].strip()
    if auth_key.lower().startswith("basic "):
        auth_key = auth_key.split(" ", 1)[1].strip()

    scope = os.environ.get("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
    model = os.environ.get("GIGACHAT_MODEL", "GigaChat-Pro")
    verify_ssl = os.environ.get("GIGACHAT_VERIFY_SSL", "false").lower() in ("1", "true", "yes")

    return GigaChatLLM(auth_key=auth_key, scope=scope, model=model, verify_ssl=verify_ssl)