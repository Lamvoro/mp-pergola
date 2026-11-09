"""Button platform for MP-Pergola.

* Per LED: "Brighten" (``dimup``) and "Dim" (``dimdown``) -- one relative ramp
  step each. These replace an absolute brightness slider (see ``light.py``).
* Per endpoint (shade / roof / led): "Pair / learn" (``pair``) -- sends a single
  motor learn frame. This is honest: the user must put the motor into learn
  mode and watch it react; there is no feedback.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import (
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ACTION_DIMDOWN,
    ACTION_DIMUP,
    ACTION_PAIR,
    EP_TYPE_LED,
)
from .coordinator import MpPergolaConfigEntry, MpPergolaCoordinator
from .entity import MpPergolaEndpointEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class MpPergolaButtonDescription(ButtonEntityDescription):
    """Describes an MP-Pergola button."""

    action: str


BRIGHTEN = MpPergolaButtonDescription(
    key="brighten",
    translation_key="brighten",
    icon="mdi:brightness-7",
    action=ACTION_DIMUP,
)
DIM = MpPergolaButtonDescription(
    key="dim",
    translation_key="dim",
    icon="mdi:brightness-5",
    action=ACTION_DIMDOWN,
)
PAIR = MpPergolaButtonDescription(
    key="pair",
    translation_key="pair",
    icon="mdi:link-variant",
    entity_category=EntityCategory.CONFIG,
    action=ACTION_PAIR,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MpPergolaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities."""
    coordinator = entry.runtime_data
    entities: list[MpPergolaButton] = []
    for ep in coordinator.data.endpoints:
        uid = int(ep["uid"])
        if ep.get("type") == EP_TYPE_LED:
            entities.append(MpPergolaButton(coordinator, uid, BRIGHTEN))
            entities.append(MpPergolaButton(coordinator, uid, DIM))
        # Every endpoint can be (re)paired to its motor/receiver.
        entities.append(MpPergolaButton(coordinator, uid, PAIR))
    async_add_entities(entities)


class MpPergolaButton(MpPergolaEndpointEntity, ButtonEntity):
    """A stateless action button bound to an endpoint."""

    entity_description: MpPergolaButtonDescription

    def __init__(
        self,
        coordinator: MpPergolaCoordinator,
        uid: int,
        description: MpPergolaButtonDescription,
    ) -> None:
        """Initialise the button."""
        super().__init__(coordinator, uid, f"button_{description.key}")
        self.entity_description = description

    async def async_press(self) -> None:
        """Send the button's action to the controller."""
        await self.coordinator.client.async_send(self._uid, self.entity_description.action)
        await self.coordinator.async_request_refresh()
