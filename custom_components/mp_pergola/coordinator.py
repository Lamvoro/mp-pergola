"""DataUpdateCoordinator for the MP-Pergola controller."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PergolaAuthError, PergolaClient, PergolaConnectionError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

type MpPergolaConfigEntry = ConfigEntry[MpPergolaCoordinator]


@dataclass(slots=True)
class PergolaData:
    """Parsed snapshot of a single ``/api/state`` poll."""

    dev: dict[str, Any] = field(default_factory=dict)
    wifi: dict[str, Any] = field(default_factory=dict)
    radios: dict[str, Any] = field(default_factory=dict)
    diag: dict[str, Any] = field(default_factory=dict)
    endpoints: list[dict[str, Any]] = field(default_factory=list)
    endpoints_by_uid: dict[int, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_state(cls, state: dict[str, Any]) -> "PergolaData":
        """Build from the raw state dict returned by the controller."""
        endpoints = state.get("endpoints") or []
        by_uid = {int(e["uid"]): e for e in endpoints if "uid" in e}
        return cls(
            dev=state.get("dev") or {},
            wifi=state.get("wifi") or {},
            radios=state.get("radios") or {},
            diag=state.get("diag") or {},
            endpoints=endpoints,
            endpoints_by_uid=by_uid,
        )


class MpPergolaCoordinator(DataUpdateCoordinator[PergolaData]):
    """Polls the controller's local ``/api/state`` endpoint."""

    config_entry: MpPergolaConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: MpPergolaConfigEntry,
        client: PergolaClient,
        scan_interval: int,
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client

    async def _async_update_data(self) -> PergolaData:
        """Fetch the latest controller state."""
        try:
            state = await self.client.async_get_state()
        except PergolaAuthError as err:
            # Surfaces as the reauth flow in the UI.
            raise ConfigEntryAuthFailed(str(err)) from err
        except PergolaConnectionError as err:
            raise UpdateFailed(str(err)) from err
        return PergolaData.from_state(state)

    # -- convenience accessors --------------------------------------------

    @property
    def controller_id(self) -> str:
        """Return a stable id for the controller device.

        The controller does not expose a serial/MAC in ``/api/state``, so we
        derive the id from its (user-settable) name. The config flow pins this
        as the config entry ``unique_id`` at setup time so later name edits do
        not spawn a duplicate device.
        """
        name = (self.data.dev.get("name") if self.data else "") or ""
        slug = "".join(c if c.isalnum() else "_" for c in name.lower()).strip("_")
        return slug or self.client.host.replace(".", "_")

    def endpoint(self, uid: int) -> dict[str, Any] | None:
        """Return the endpoint dict for ``uid`` from the latest poll."""
        if self.data is None:
            return None
        return self.data.endpoints_by_uid.get(uid)
