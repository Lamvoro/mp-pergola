"""Diagnostic sensors for the MP-Pergola controller."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfInformation,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import MpPergolaConfigEntry, MpPergolaCoordinator, PergolaData
from .entity import MpPergolaEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class MpPergolaSensorDescription(SensorEntityDescription):
    """Describes an MP-Pergola diagnostic sensor."""

    value_fn: Callable[[PergolaData], Any]


def _rssi(data: PergolaData) -> int | None:
    if not data.wifi.get("up"):
        return None
    return data.wifi.get("rssi")


SENSORS: tuple[MpPergolaSensorDescription, ...] = (
    MpPergolaSensorDescription(
        key="rssi",
        translation_key="rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
        value_fn=_rssi,
    ),
    MpPergolaSensorDescription(
        key="ssid",
        translation_key="ssid",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.wifi.get("ssid") or None,
    ),
    MpPergolaSensorDescription(
        key="ip",
        translation_key="ip",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.dev.get("ip") or None,
    ),
    MpPergolaSensorDescription(
        key="firmware",
        translation_key="firmware",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.dev.get("fw") or None,
    ),
    MpPergolaSensorDescription(
        key="uptime",
        translation_key="uptime",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.dev.get("uptime"),
    ),
    MpPergolaSensorDescription(
        key="free_heap",
        translation_key="free_heap",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.dev.get("heap"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MpPergolaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up controller diagnostic sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        MpPergolaSensor(coordinator, description) for description in SENSORS
    )


class MpPergolaSensor(MpPergolaEntity, SensorEntity):
    """A controller-level diagnostic sensor."""

    entity_description: MpPergolaSensorDescription

    def __init__(
        self,
        coordinator: MpPergolaCoordinator,
        description: MpPergolaSensorDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{self._controller_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return the current sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)
