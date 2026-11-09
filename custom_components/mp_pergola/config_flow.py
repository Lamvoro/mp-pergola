"""Config flow for the MP-Pergola integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .api import PergolaAuthError, PergolaClient, PergolaConnectionError
from .const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    DEFAULT_PASSWORD,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .coordinator import MpPergolaConfigEntry

_LOGGER = logging.getLogger(__name__)


def _slug(name: str) -> str:
    """Slugify a controller name into a stable unique id."""
    slug = "".join(c if c.isalnum() else "_" for c in (name or "").lower()).strip("_")
    return slug


async def _async_try_connect(
    hass: Any, host: str, password: str
) -> dict[str, Any]:
    """Validate credentials; return the controller state or raise."""
    session = async_get_clientsession(hass)
    client = PergolaClient(session, host, password)
    return await client.async_validate()


class MpPergolaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MP-Pergola."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise flow state."""
        self._host: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the manual (user) step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            password = user_input[CONF_PASSWORD]
            try:
                state = await _async_try_connect(self.hass, host, password)
            except PergolaAuthError:
                errors["base"] = "invalid_auth"
            except PergolaConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 - surface anything unexpected
                _LOGGER.exception("Unexpected error validating MP-Pergola")
                errors["base"] = "unknown"
            else:
                name = (state.get("dev") or {}).get("name") or host
                await self.async_set_unique_id(_slug(name))
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})
                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_HOST: host,
                        CONF_PASSWORD: password,
                    },
                    options={
                        CONF_SCAN_INTERVAL: user_input.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST, default=(user_input or {}).get(CONF_HOST, "")
                    ): str,
                    vol.Required(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
                    vol.Optional(
                        CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                    ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)),
                }
            ),
            errors=errors,
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle discovery via mDNS (_pergola._tcp)."""
        host = discovery_info.host
        hostname = (discovery_info.hostname or "").removesuffix(".local.").removesuffix(".local")
        # Prefer the advertised instance name, fall back to the hostname/host.
        name = discovery_info.name.split(".")[0] if discovery_info.name else hostname
        await self.async_set_unique_id(_slug(name or host))
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        self._host = host
        self.context["title_placeholders"] = {"name": name or host}
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm a discovered controller and collect its password."""
        errors: dict[str, str] = {}
        assert self._host is not None
        if user_input is not None:
            password = user_input[CONF_PASSWORD]
            try:
                state = await _async_try_connect(self.hass, self._host, password)
            except PergolaAuthError:
                errors["base"] = "invalid_auth"
            except PergolaConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating MP-Pergola")
                errors["base"] = "unknown"
            else:
                name = (state.get("dev") or {}).get("name") or self._host
                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_HOST: self._host,
                        CONF_PASSWORD: password,
                    },
                    options={CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL},
                )

        return self.async_show_form(
            step_id="zeroconf_confirm",
            data_schema=vol.Schema(
                {vol.Required(CONF_PASSWORD, default=DEFAULT_PASSWORD): str}
            ),
            description_placeholders={"host": self._host},
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauth when the password is rejected during operation."""
        self._host = entry_data[CONF_HOST]
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect a fresh password for the existing entry."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()
        host = reauth_entry.data[CONF_HOST]
        if user_input is not None:
            password = user_input[CONF_PASSWORD]
            try:
                await _async_try_connect(self.hass, host, password)
            except PergolaAuthError:
                errors["base"] = "invalid_auth"
            except PergolaConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating MP-Pergola")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={CONF_PASSWORD: password},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {vol.Required(CONF_PASSWORD, default=DEFAULT_PASSWORD): str}
            ),
            description_placeholders={"host": host},
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: MpPergolaConfigEntry,
    ) -> MpPergolaOptionsFlow:
        """Return the options flow handler."""
        return MpPergolaOptionsFlow()


class MpPergolaOptionsFlow(OptionsFlow):
    """Handle MP-Pergola options (poll interval)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the poll-interval option."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_SCAN_INTERVAL, default=current): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    )
                }
            ),
        )
