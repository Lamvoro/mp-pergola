"""Base entities for the MP-Pergola integration.

Device model
------------
* The controller itself is one "hub" device (diagnostic sensors attach here).
* Each endpoint (shade / roof / LED) is its own device linked to the hub via
  ``via_device``. This gives every shade/roof/light its own name and groups its
  control + pair buttons together, instead of colliding under a single device.
"""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    EP_TYPE_LED,
    EP_TYPE_ROOF,
    MANUFACTURER,
    MODEL,
)
from .coordinator import MpPergolaCoordinator

_EP_MODEL = {
    EP_TYPE_ROOF: "Roof louvre (868 MHz)",
    EP_TYPE_LED: "LED strip (868 MHz)",
}


class MpPergolaEntity(CoordinatorEntity[MpPergolaCoordinator]):
    """Base entity attached to the controller (hub) device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: MpPergolaCoordinator) -> None:
        """Initialise the base entity."""
        super().__init__(coordinator)
        # The config entry's unique_id is pinned at flow time and stays stable
        # even if the controller is later renamed, so it anchors the HA device.
        self._controller_id = coordinator.config_entry.unique_id or coordinator.controller_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for the controller (hub)."""
        dev = self.coordinator.data.dev
        return DeviceInfo(
            identifiers={(DOMAIN, self._controller_id)},
            name=dev.get("name") or "MP-Pergola",
            manufacturer=MANUFACTURER,
            model=MODEL,
            sw_version=self._sw_version(dev),
            configuration_url=self.coordinator.client.base_url,
        )

    @staticmethod
    def _sw_version(dev: dict[str, Any]) -> str | None:
        fw = dev.get("fw")
        build = dev.get("build")
        if fw and build:
            return f"{fw} ({build})"
        return fw or None

    @property
    def available(self) -> bool:
        """Available while the last coordinator refresh succeeded."""
        return super().available and self.coordinator.last_update_success


class MpPergolaEndpointEntity(MpPergolaEntity):
    """Base entity bound to one controller endpoint (its own sub-device)."""

    def __init__(self, coordinator: MpPergolaCoordinator, uid: int, platform: str) -> None:
        """Initialise an endpoint-bound entity."""
        super().__init__(coordinator)
        self._uid = uid
        # <controller-id>_<uid>_<platform>
        self._attr_unique_id = f"{self._controller_id}_{uid}_{platform}"

    @property
    def endpoint(self) -> dict[str, Any] | None:
        """Return this entity's endpoint dict from the latest poll."""
        return self.coordinator.endpoint(self._uid)

    @property
    def device_info(self) -> DeviceInfo:
        """Return a per-endpoint device, linked to the controller hub."""
        ep = self.endpoint or {}
        ep_type = ep.get("type", "")
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._controller_id}_{self._uid}")},
            name=ep.get("name") or f"Pergola {self._uid}",
            manufacturer=MANUFACTURER,
            model=_EP_MODEL.get(ep_type, "Shade (433 MHz)"),
            via_device=(DOMAIN, self._controller_id),
        )

    @property
    def available(self) -> bool:
        """Unavailable if the endpoint disappeared from the controller."""
        return super().available and self.endpoint is not None
