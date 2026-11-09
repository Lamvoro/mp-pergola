"""Async HTTP client for the MP-Pergola local controller API.

The controller exposes a small local HTTP API on the home LAN:

* ``POST /api/login``  form body ``pw=<admin password>``  -> 200 + ``Set-Cookie: sid=<32 hex>``
* ``GET  /api/state``  -> JSON (requires the ``sid`` cookie)
* ``GET  /cmd?u=<uid>&a=<action>[&p=<pos>]`` -> 204 (requires the ``sid`` cookie)

All authenticated requests carry the ``sid`` cookie explicitly (we do NOT rely on
the shared aiohttp cookie jar, so sessions can never collide with other
integrations talking to the same host). On HTTP 401 we transparently re-login
once and retry the request.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import DEFAULT_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class PergolaError(Exception):
    """Base error for the MP-Pergola client."""


class PergolaConnectionError(PergolaError):
    """Raised when the controller cannot be reached (network/timeout/5xx)."""


class PergolaAuthError(PergolaError):
    """Raised when the admin password is rejected or the session is invalid."""


class PergolaClient:
    """Thin async client around the controller's local HTTP API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        password: str,
        *,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialise the client.

        ``host`` may be a bare IP (``192.168.1.50``) or an mDNS name
        (``pergola.local``); we normalise it into an ``http://`` base URL.
        """
        self._session = session
        self._host = _normalise_host(host)
        self._password = password
        self._timeout = timeout
        self._sid: str | None = None

    @property
    def host(self) -> str:
        """Return the normalised host (no scheme)."""
        return self._host

    @property
    def base_url(self) -> str:
        """Return the base URL used for requests."""
        return f"http://{self._host}"

    async def async_login(self) -> None:
        """Authenticate and capture the ``sid`` session cookie.

        Raises :class:`PergolaAuthError` on a bad password / lockout and
        :class:`PergolaConnectionError` on any transport problem.
        """
        url = f"{self.base_url}/api/login"
        try:
            async with asyncio.timeout(self._timeout):
                resp = await self._session.post(
                    url,
                    data={"pw": self._password},
                )
                # Drain the body so the connection can be reused.
                await resp.read()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise PergolaConnectionError(f"Cannot reach controller at {url}: {err}") from err

        if resp.status == 429:
            # Per-IP login lockout after repeated bad passwords (firmware).
            raise PergolaAuthError("Controller is temporarily locked out (too many bad logins)")
        if resp.status in (401, 403):
            raise PergolaAuthError("Controller rejected the admin password")
        if resp.status != 200:
            raise PergolaConnectionError(f"Unexpected login status {resp.status}")

        sid = _extract_sid(resp)
        if not sid:
            raise PergolaAuthError("Controller did not return a session cookie")
        self._sid = sid
        _LOGGER.debug("Logged in to %s", self._host)

    async def async_get_state(self) -> dict[str, Any]:
        """Return the parsed ``/api/state`` JSON, re-logging in once on 401."""
        resp = await self._request("get", "/api/state", retry_on_auth=True)
        try:
            return await resp.json(content_type=None)
        except (aiohttp.ClientError, ValueError) as err:
            raise PergolaConnectionError(f"Invalid state JSON from controller: {err}") from err

    async def async_send(
        self,
        uid: int,
        action: str,
        pos: int | None = None,
    ) -> None:
        """Send a control command (``/cmd``), re-logging in once on 401."""
        params: dict[str, Any] = {"u": uid, "a": action}
        if pos is not None:
            params["p"] = int(pos)
        await self._request("get", "/cmd", params=params, retry_on_auth=True)

    async def async_validate(self) -> dict[str, Any]:
        """Log in and fetch state once; used by the config flow.

        Returns the parsed state dict so the flow can read the device name/id.
        """
        await self.async_login()
        return await self.async_get_state()

    # -- internals ---------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        retry_on_auth: bool = True,
    ) -> aiohttp.ClientResponse:
        """Perform one authenticated request, re-login + retry once on 401."""
        if self._sid is None:
            await self.async_login()

        try:
            resp = await self._raw_request(method, path, params=params)
        except PergolaConnectionError:
            raise

        if resp.status == 401 and retry_on_auth:
            _LOGGER.debug("Session expired, re-authenticating to %s", self._host)
            self._sid = None
            await self.async_login()
            resp = await self._raw_request(method, path, params=params)

        if resp.status == 401:
            self._sid = None
            raise PergolaAuthError("Controller rejected the session cookie")
        if resp.status >= 400:
            raise PergolaConnectionError(f"Controller returned HTTP {resp.status} for {path}")
        return resp

    async def _raw_request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> aiohttp.ClientResponse:
        """Issue a single request carrying the sid cookie explicitly."""
        url = f"{self.base_url}{path}"
        cookies = {"sid": self._sid} if self._sid else None
        try:
            async with asyncio.timeout(self._timeout):
                resp = await self._session.request(
                    method,
                    url,
                    params=params,
                    cookies=cookies,
                )
                # Fully read the body so the connection is released even when a
                # caller does not consume it (e.g. 204 responses).
                await resp.read()
                return resp
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise PergolaConnectionError(f"Request to {url} failed: {err}") from err


def _normalise_host(host: str) -> str:
    """Strip any scheme / trailing slash from a user-entered host."""
    host = host.strip()
    for prefix in ("http://", "https://"):
        if host.lower().startswith(prefix):
            host = host[len(prefix):]
    return host.rstrip("/")


def _extract_sid(resp: aiohttp.ClientResponse) -> str | None:
    """Pull the ``sid`` value out of the login response's Set-Cookie."""
    cookie = resp.cookies.get("sid")
    if cookie is not None and cookie.value:
        return cookie.value
    return None
