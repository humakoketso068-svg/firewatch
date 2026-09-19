# Firewatch — Wildfire Early-Warning Console (Flet)

A cross-platform dashboard for a simulated wildfire sensor network, written
entirely in Python. One codebase runs on Windows, macOS, Linux, Android, iOS
and the web.

## What's simulated

- 12 sensor nodes with temperature, humidity and fuel-moisture readings that drift over time
- A risk score per zone from wind speed, fuel moisture, temperature and slope
- Random ignitions weighted toward high-risk zones, with a spread ellipse oriented by
  wind direction and a dashed evacuation-advisory ring on extreme fires
- Containment over time, a live event feed, and wind / fuel-moisture trends
- A public alert view: the same data as a plain-language advisory

## Files

| File | Role |
|------|------|
| `simulation.py` | The engine. Plain Python, no UI. `tick()` advances it, `snapshot()` returns the state. |
| `main.py` | The Flet interface. Builds every screen in Python from Flet controls and redraws from `snapshot()` via `page.update()`. |
| `requirements.txt` | `flet` |

The UI only ever reads `snapshot()`, so real sensor / weather / satellite data can replace
`Simulation._step_environment` without touching `main.py`.

## Run it
```bash
pip install -r requirements.txt
python main.py
```

The layout is responsive: three columns on wide windows, a single scrolling column on
tablets and phones.

## Package it

Install Flet, then build for your target platform:

- **Windows / macOS / Linux:** `flet build windows` (or `macos`, `linux`)
- **Android:** `flet build apk` (or `flet build aab` for the Play Store)
- **iOS:** `flet build ipa` (requires a Mac with Xcode)
- **Web:** `flet build web`

Run these from the project root. Build settings such as the app name, version,
and dependencies go in `pyproject.toml` (or via flags like `--project` and
`--product`).

## Notes

- The simulation runs in-process on Flet's clock (every 2.2 s). There is no server, so the app
  works offline and on mobile.
- To go beyond a prototype, swap the toy risk formula for a validated fire-danger index (e.g., NFDRS)
  and the spread model for a physics-based one (e.g., Rothermel).
