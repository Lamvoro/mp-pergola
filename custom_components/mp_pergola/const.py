"""Constants for the MP-Pergola integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "mp_pergola"

# Manufacturer / default device metadata shown in the HA device registry.
MANUFACTURER: Final = "MP-Pergola"
MODEL: Final = "ESP32-S3 Pergola Controller"

# Config entry keys.
CONF_HOST: Final = "host"
CONF_PASSWORD: Final = "password"
CONF_SCAN_INTERVAL: Final = "scan_interval"

# Defaults.
DEFAULT_PASSWORD: Final = "pergola-admin"
DEFAULT_SCAN_INTERVAL: Final = 5  # seconds
MIN_SCAN_INTERVAL: Final = 2
MAX_SCAN_INTERVAL: Final = 120
DEFAULT_TIMEOUT: Final = 10  # seconds for a single HTTP request

# Endpoint types as reported by GET /api/state -> endpoints[].type
EP_TYPE_SHADE: Final = "shade"
EP_TYPE_ROOF: Final = "roof"
EP_TYPE_LED: Final = "led"

# Controller actions sent to GET /cmd?u=<uid>&a=<action>
ACTION_UP: Final = "up"
ACTION_DOWN: Final = "down"
ACTION_STOP: Final = "stop"
ACTION_POS: Final = "pos"
ACTION_ON: Final = "on"
ACTION_OFF: Final = "off"
ACTION_DIMUP: Final = "dimup"
ACTION_DIMDOWN: Final = "dimdown"
ACTION_PAIR: Final = "pair"

# zeroconf service type advertised by the controller (MDNS.addService("pergola","tcp",80)).
ZEROCONF_TYPE: Final = "_pergola._tcp.local."

# Entity service exposed for the motor "learn" frame.
SERVICE_PAIR: Final = "pair"

MIN_UPDATE_INTERVAL: Final = timedelta(seconds=MIN_SCAN_INTERVAL)
