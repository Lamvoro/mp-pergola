"""Diagnostics support for MP-Pergola."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_PASSWORD
from .coordinator import MpPergolaConfigEntry

TO_REDACT = {CONF_PASSWORD, "ssid", "ip"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: MpPergolaConfigEntry
) -> dict[str, Any]:
    """Return redacted diagnostics for a config entry."""
    coordinator = entry.runtime_data
    data = coordinator.data

    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
            "unique_id": entry.unique_id,
        },
        "state": async_redact_data(
            {
                "dev": data.dev,
                "wifi": data.wifi,
                "radios": data.radios,
                "diag": data.diag,
                "endpoints": data.endpoints,
            },
            TO_REDACT,
        ),
    }
