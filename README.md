# Rain Forecast & History for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/jacobbjerregaard/homeassistant-rain-forecast/actions/workflows/validate.yml/badge.svg)](https://github.com/jacobbjerregaard/homeassistant-rain-forecast/actions/workflows/validate.yml)
[![Tests](https://github.com/jacobbjerregaard/homeassistant-rain-forecast/actions/workflows/tests.yml/badge.svg)](https://github.com/jacobbjerregaard/homeassistant-rain-forecast/actions/workflows/tests.yml)

A Home Assistant custom integration that gives you **rain forecast** sensors and
**historical rainfall** sensors for any location on Earth — powered by the free
[Open-Meteo](https://open-meteo.com/) API.

- 🌍 **Global & free** — no API key, no account, no rate-limit headaches.
- 🌦️ **Forecast** — how much rain is coming today, tomorrow, in the next hour and
  next 24 hours, plus rain probability and a "rain soon" binary sensor.
- 📈 **History** — how much rain actually fell today, yesterday, in the last 7 and
  30 days, backed by Open-Meteo's historical archive **and** a locally-accumulated
  lifetime total that survives restarts and API outages.

Unlike most existing rain integrations, this one needs no paid API key
(OpenWeatherMap), no physical rain gauge, and isn't locked to a single country
(Buienradar/Antistorm).

## Entities

All entities are grouped under one device per configured location.

### Sensors

| Entity | Description | Unit |
| --- | --- | --- |
| Rain forecast today | Forecast precipitation total for today | mm |
| Rain forecast tomorrow | Forecast precipitation total for tomorrow | mm |
| Rain probability today | Max chance of precipitation today | % |
| Rain probability tomorrow | Max chance of precipitation tomorrow | % |
| Rain next hour | Forecast precipitation in the next hour | mm |
| Rain next 24 hours | Forecast precipitation over the next 24 hours | mm |
| Minutes until rain | Minutes until the next rain in the look-ahead window | min |
| Current precipitation | Precipitation reported for the current period | mm |
| Rain today | Actual rainfall so far today | mm |
| Rain yesterday | Actual rainfall yesterday | mm |
| Rain last 7 days | Rolling 7-day actual rainfall | mm |
| Rain last 30 days | Rolling 30-day actual rainfall (archive-backed) | mm |
| Rain accumulated total | Lifetime rainfall accumulated locally since install | mm |

The **Rain forecast today** sensor also exposes the full multi-day daily forecast
as a `daily_forecast` attribute, handy for charts and templates.

### Binary sensor

| Entity | Description |
| --- | --- |
| Rain soon | `on` when rain above the threshold is expected within the look-ahead window. Attributes: `minutes_until_rain`, `expected_amount`, `look_ahead_hours`. |

## Installation

### HACS (recommended)

1. In HACS, open the three-dot menu → **Custom repositories**.
2. Add `https://github.com/jacobbjerregaard/homeassistant-rain-forecast` with
   category **Integration**.
3. Search for **Rain Forecast & History**, install it, and restart Home Assistant.

### Manual

Copy `custom_components/rain_forecast` into your Home Assistant
`config/custom_components/` directory and restart.

## Configuration

After installing, add the integration from the UI:

**Settings → Devices & Services → Add Integration → Rain Forecast & History**

You'll be asked for:

- **Name** — a label for this location (e.g. `Home`, `Cabin`).
- **Latitude / Longitude** — pre-filled from your Home Assistant location; change
  it to monitor anywhere.

You can add the integration multiple times to track several locations.

### Options

Open the integration's **Configure** dialog to tune:

| Option | Default | Range |
| --- | --- | --- |
| Update interval (minutes) | 30 | 5–360 |
| Forecast days | 7 | 1–16 |
| History days | 30 | 7–92 |
| "Rain soon" look-ahead (hours) | 2 | 1–12 |
| "Rain soon" threshold (mm/hour) | 0.1 | 0–10 |

## How the history works

- **Recent days** come from the live forecast endpoint (`past_days`), which is the
  freshest source for the last week.
- **Older days** (up to *History days*) come from Open-Meteo's
  [historical archive API](https://open-meteo.com/en/docs/historical-weather-api)
  (ERA5). The archive lags real time by a few days, so the integration merges it
  with the recent forecast data, letting the fresher source win on overlap.
- **Rain accumulated total** is computed locally on every update and persisted via
  Home Assistant's restore state, so it keeps counting even if the archive is
  temporarily unavailable.

The rainfall total sensors use the `total`/`total_increasing` state class, so they
can be added to the **Energy / utility** style dashboards and `utility_meter`
helpers.

## Data source & attribution

Weather data by [Open-Meteo.com](https://open-meteo.com/) under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Open-Meteo is free for
non-commercial use; review their [terms](https://open-meteo.com/en/terms) before
commercial use.

## License

[Apache License 2.0](LICENSE).
