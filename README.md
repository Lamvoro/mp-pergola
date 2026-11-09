# MP-Pergola — Home Assistant integration

A HACS-installable **custom integration** that controls the **MP-Pergola**
controller over your **local network** (no cloud account required).

MP-Pergola is an ESP32-S3 controller that drives a motorised pergola — a roof
louvre + an LED strip (868 MHz) and up to three fabric shades (433 MHz). It is
**paired with the motors as an additional remote** (the original remote keeps
working) and exposes a small local HTTP API; this integration polls `/api/state`
and sends `/cmd` actions.

MP-Pergola is a branded edition of the **Lamvoro** smart pergola module —
see [lamvoro.com](https://lamvoro.com/) for the hardware, and
[mp-pergola.lamvoro.com](https://mp-pergola.lamvoro.com/) for the Android app,
quick-start guide and support.

> This folder (`product/ha-integration/`) is the **root of the public GitHub
> repo** `Lamvoro/mp-pergola`. HACS installs the component from
> `custom_components/mp_pergola/`.

---

## Entity model

| Controller endpoint | HA platform | Device class | Notes |
|---|---|---|---|
| `type: shade` (433 MHz) | `cover` | `shade` | open / close / stop / set position |
| `type: roof` (868 MHz louvre) | `cover` | `awning` | overhead louvre; `shutter` would also fit |
| `type: led` (868 MHz) | `light` | — (`onoff`) | on / off only |
| `type: led` | `button` ×2 | — | **Brighten** (`dimup`) / **Dim** (`dimdown`) — one ramp step each |
| every endpoint | `button` | config | **Pair** (`pair`) — pairs the controller with the motor as an additional remote |
| controller (hub) | `sensor` ×6 | diagnostic | Wi-Fi signal (RSSI), Wi-Fi network, IP, firmware, uptime, free memory |

Each endpoint is its **own HA device** (named from the controller) linked to the
controller **hub** device via `via_device`, so every shade/roof/LED groups its
own controls and pair button.

### Why brightness is buttons, not a slider
The controller sends the same commands as the original remote, which has only **ON/OFF** buttons;
brightness is a *relative* ramp done by **holding** a button, and the controller
reports **no brightness value** (only `led_on`). A faked absolute slider would
never reflect reality, so the `light` entity is **on/off only** and relative
brightness is exposed honestly as **Brighten / Dim** buttons.

### Pairing
`Pair` sends the signal to pair the controller as an additional remote. The
integration cannot confirm whether the motor accepted it:

- **Shades:** select the shade’s channel on the original remote. Remove the
  battery cover, press **P2**, wait **2 seconds**, press **P2** again, then
  promptly press **Pair** in Home Assistant. Watch for a brief jog and test control.
- **Roof + light:** power-cycle the roof motor, then press **Pair** within
  **10 seconds**. The controller sends the code-key signal for about **5 seconds**,
  then **STOP** for about **5 seconds**. Test the roof and light; one pairing
  covers both. You do not press buttons on the roof remote.

The same procedure applies to the `mp_pergola.pair` service (target a cover or
light entity). In the Android app the roof action is **Start**. If pairing fails,
repeat the complete preparation for that motor, then send the signal again.
Full procedure: [quick-start guide](https://lamvoro.com/manual/Lamvoro-Quick-Start.pdf).

### Positions are estimates
`pos` is a **time-based, open-loop estimate** (the motors have no feedback). Moves
are reported optimistically and reconciled on the next poll; `dir` (−1/0/+1)
drives `is_closing` / `is_opening`.

---

## Install

### Option A — HACS (recommended)
1. HACS → **⋮** → **Custom repositories**.
2. Add the repo URL `https://github.com/Lamvoro/mp-pergola`, category
   **Integration**, click **Add**.
3. Find **MP-Pergola** in HACS → **Download**.
4. **Restart Home Assistant.**
5. **Settings → Devices & Services → Add Integration → MP-Pergola.**

### Option B — Manual
1. Download [`mp_pergola.zip`](https://github.com/Lamvoro/mp-pergola/raw/main/mp_pergola.zip).
2. Extract so you have `config/custom_components/mp_pergola/…` on your HA host.
3. **Restart Home Assistant**, then add the integration as above.

### Configuration
Enter the controller **host** (IP or `name.local`) and its **current admin password**
(from your installer or device setup), plus an optional **poll interval** (default 5 s,
changeable later under the integration's **Configure**). Controllers advertised
over mDNS (`_pergola._tcp`) are auto-discovered.

## Slovenščina — namestitev in seznanitev

MP-Pergola je izvedba krmilnika Lamvoro za prodajalca MP-Pergola. Integracija
upravlja krmilnik neposredno v lokalnem omrežju; račun v oblaku ni potreben.

1. V HACS odprite **⋮ → Custom repositories** in dodajte
   `https://github.com/Lamvoro/mp-pergola`, kategorija **Integration**.
2. Prenesite **MP-Pergola** in znova zaženite Home Assistant.
3. Odprite **Nastavitve → Naprave in storitve → Dodaj integracijo → MP-Pergola**.
4. Vnesite naslov IP krmilnika (ali `ime.local`) in njegovo trenutno skrbniško
   geslo, ki ste ga nastavili ali prejeli od monterja.

**Senčila:** na izvirnem daljincu izberite kanal senčila. Pod pokrovčkom baterije
pritisnite **P2**, počakajte **2 sekundi**, znova pritisnite **P2**, nato takoj
**Poveži** v Home Assistant. Opazujte kratek premik senčila in preizkusite upravljanje.

**Streha in luč:** izklopite in znova vklopite napajanje motorja ter v **10 sekundah**
pritisnite **Poveži**. Krmilnik sam pošilja kodirni signal približno **5 sekund**,
nato **STOP** približno **5 sekund**. Ena seznanitev velja za oboje. V aplikaciji
za Android postopek sprožite z gumbom **Začni**. Če ni uspelo, ponovite celoten
postopek. Aplikacija ne more potrditi odziva motorja; preizkusite streho in luč.

Položaji so časovne ocene. Gumba **Posvetli / Zatemni** spreminjata svetlost
postopoma; integracija ne prikazuje izmerjene svetlosti.

---

## Links
- Hardware and resellers: [lamvoro.com](https://lamvoro.com/) · [lamvoro.com/en](https://lamvoro.com/en/)
- MP-Pergola app, guide and support: [mp-pergola.lamvoro.com](https://mp-pergola.lamvoro.com/)

## License
MIT — see [LICENSE](LICENSE).
