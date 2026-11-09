"""Cover platform for MP-Pergola shades and the roof louvre."""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ACTION_DOWN,
    ACTION_PAIR,
    ACTION_POS,
    ACTION_STOP,
    ACTION_UP,
    EP_TYPE_ROOF,
    EP_TYPE_SHADE,
    SERVICE_PAIR,
)
from .coordinator import MpPergolaConfigEntry, MpPergolaCoordinator
from .entity import MpPergolaEndpointEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MpPergolaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up cover entities (one per shade and the roof)."""
    coordinator = entry.runtime_data
    entities = [
        MpPergolaCover(coordinator, int(ep["uid"]), ep["type"])
        for ep in coordinator.data.endpoints
        if ep.get("type") in (EP_TYPE_SHADE, EP_TYPE_ROOF)
    ]
    async_add_entities(entities)

    # Expose mp_pergola.pair as an entity service on covers (buttons also exist).
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(SERVICE_PAIR, {}, "async_pair")


class MpPergolaCover(MpPergolaEndpointEntity, CoverEntity):
    """A single shade (433 MHz) or the roof louvre (868 MHz).

    Position is an OPEN-LOOP, time-based estimate from the controller: there is
    no true position feedback, so moves are reported optimistically and
    reconciled on the next poll.
    """

    _attr_name = None  # the device/endpoint name is the entity name
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

    def __init__(
        self,
        coordinator: MpPergolaCoordinator,
        uid: int,
        ep_type: str,
    ) -> None:
        """Initialise the cover."""
        super().__init__(coordinator, uid, "cover")
        self._ep_type = ep_type
        # Shades are fabric blinds -> SHADE. The roof is a motorised louvre that
        # opens/retracts overhead; AWNING is the closest HA class (SHUTTER would
        # also be defensible, but AWNING better matches an overhead sun cover).
        self._attr_device_class = (
            CoverDeviceClass.SHADE if ep_type == EP_TYPE_SHADE else CoverDeviceClass.AWNING
        )
        # Optimistic movement hint, cleared on the next successful poll.
        self._optimistic_dir: int | None = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Drop the optimistic hint once fresh state arrives."""
        self._optimistic_dir = None
        super()._handle_coordinator_update()

    @property
    def _pos(self) -> int | None:
        ep = self.endpoint
        if ep is None:
            return None
        pos = ep.get("pos")
        return int(pos) if pos is not None else None

    @property
    def _dir(self) -> int:
        if self._optimistic_dir is not None:
            return self._optimistic_dir
        ep = self.endpoint
        return int(ep.get("dir", 0)) if ep else 0

    @property
    def current_cover_position(self) -> int | None:
        """Return the estimated position (0 closed .. 100 open)."""
        return self._pos

    @property
    def is_closed(self) -> bool | None:
        """Return True when fully closed (position 0)."""
        pos = self._pos
        if pos is None:
            return None
        return pos == 0

    @property
    def is_opening(self) -> bool:
        """Return True while opening (dir == +1)."""
        return self._dir == 1

    @property
    def is_closing(self) -> bool:
        """Return True while closing (dir == -1)."""
        return self._dir == -1

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        await self._command(ACTION_UP, optimistic_dir=1)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        await self._command(ACTION_DOWN, optimistic_dir=-1)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        await self._command(ACTION_STOP, optimistic_dir=0)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a target position."""
        position = int(kwargs[ATTR_POSITION])
        current = self._pos
        hint = None
        if current is not None:
            hint = 1 if position > current else -1 if position < current else 0
        await self._command(ACTION_POS, pos=position, optimistic_dir=hint)

    async def async_pair(self) -> None:
        """Send the motor learn / pair frame (user must watch the motor)."""
        await self.coordinator.client.async_send(self._uid, ACTION_PAIR)

    async def _command(
        self,
        action: str,
        *,
        pos: int | None = None,
        optimistic_dir: int | None = None,
    ) -> None:
        await self.coordinator.client.async_send(self._uid, action, pos=pos)
        if optimistic_dir is not None:
            self._optimistic_dir = optimistic_dir
            self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
