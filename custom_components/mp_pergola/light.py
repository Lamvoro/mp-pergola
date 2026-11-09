"""Light platform for MP-Pergola LED strips.

Design note on brightness
--------------------------
The controller impersonates the original Dooya remote, which only has ON / OFF
buttons; brightness is a *relative* ramp triggered by holding a button. The
controller therefore has **no absolute brightness value and no brightness
readback** -- ``/api/state`` only reports ``led_on`` (bool).

Faking an absolute brightness slider here would lie to the user (the slider
would never reflect the real strip and could not be set to an absolute level),
so this light exposes **on/off only** (``ColorMode.ONOFF``). Relative brightness
is offered honestly as "Brighten" / "Dim" buttons in ``button.py`` (one ramp
step each), matching how the physical remote behaves.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ACTION_OFF, ACTION_ON, ACTION_PAIR, EP_TYPE_LED, SERVICE_PAIR
from .coordinator import MpPergolaConfigEntry, MpPergolaCoordinator
from .entity import MpPergolaEndpointEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MpPergolaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one light per LED endpoint."""
    coordinator = entry.runtime_data
    entities = [
        MpPergolaLight(coordinator, int(ep["uid"]))
        for ep in coordinator.data.endpoints
        if ep.get("type") == EP_TYPE_LED
    ]
    async_add_entities(entities)

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(SERVICE_PAIR, {}, "async_pair")


class MpPergolaLight(MpPergolaEndpointEntity, LightEntity):
    """An LED strip driven over 868 MHz (on/off only)."""

    _attr_name = None
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    def __init__(self, coordinator: MpPergolaCoordinator, uid: int) -> None:
        """Initialise the light."""
        super().__init__(coordinator, uid, "light")

    @property
    def is_on(self) -> bool | None:
        """Return the LED on/off state."""
        ep = self.endpoint
        if ep is None:
            return None
        return bool(ep.get("led_on", False))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the LED on."""
        await self._command(ACTION_ON)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the LED off."""
        await self._command(ACTION_OFF)

    async def async_pair(self) -> None:
        """Send the motor learn / pair frame."""
        await self.coordinator.client.async_send(self._uid, ACTION_PAIR)

    async def _command(self, action: str) -> None:
        await self.coordinator.client.async_send(self._uid, action)
        await self.coordinator.async_request_refresh()
