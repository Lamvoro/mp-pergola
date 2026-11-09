# MP-Pergola

Local-network Home Assistant integration for the **MP-Pergola** controller — an
ESP32-S3 that drives a motorised pergola (roof louvre + LED strip on 868 MHz and
up to three fabric shades on 433 MHz) by pairing with the motors as an additional remote. The original remote keeps
working. MP-Pergola is a branded edition of Lamvoro.

Talks **directly to the controller on your LAN** (`http://<ip>/`). No cloud
account required.

## What you get

- **Covers** — each shade and the roof louvre (open / close / stop / set position).
- **Lights** — each LED strip (on / off).
- **Buttons** — *Brighten* / *Dim* (relative ramp steps) for each LED, and a
  *Pair* button per device.
- **Diagnostics** — Wi-Fi signal & network, firmware, uptime, free memory.

## Setup

1. In Home Assistant go to **Settings → Devices & Services → Add Integration**.
2. Search for **MP-Pergola**.
3. Enter the controller's IP (or `name.local`) and admin password
   (use the current password from your installer or device setup).

Discovered controllers (mDNS `_pergola._tcp`) appear automatically; enter the admin password to add them.

## Notes

- Position is an **open-loop estimate** — the pergola motors give no feedback.
- LED brightness is **relative only** (the real remote has just ON/OFF + a hold
  gesture), so brightness is offered as *Brighten* / *Dim* buttons instead of a
  fake absolute slider.

## Pairing / Seznanitev

Shades: **P2 → wait 2 s → P2 → Pair** (P2 is under the original remote’s battery
cover). Roof + light: power-cycle the motor, then **Pair** within 10 s; the
controller sends the code-key signal for about 5 s, then STOP for about 5 s.
Test the controls: sending a signal does not confirm pairing. See the
[installation guide](README.md) for the full English and Slovenian instructions.

Senčila: **P2 → počakajte 2 s → P2 → Poveži** (P2 je pod pokrovčkom baterije
izvirnega daljinca). Streha in luč: izklopite in znova vklopite napajanje motorja,
nato v 10 s pritisnite **Poveži**; krmilnik pošilja kodirni signal približno 5 s,
nato STOP približno 5 s. Preizkusite upravljanje — poslan signal ne potrjuje seznanitve.
