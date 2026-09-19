# Firewatch — Wildfire Early-Warning Console (Kivy)

A cross-platform dashboard for a simulated wildfire sensor network, written
entirely in Python. One codebase runs on Windows, macOS, Linux, Android and iOS.

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
| `main.py` | The Kivy interface. Builds every screen in Python (no `.kv` files) and redraws from `snapshot()`. |
| `requirements.txt` | `kivy` |

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

- **Windows / macOS / Linux:** `pip install pyinstaller` then `pyinstaller --windowed main.py`
- **Android:** `pip install buildozer`, run `buildozer init`, set `requirements = python3,kivy`
  in `buildozer.spec`, then `buildozer android debug` (Linux or WSL)
- **iOS:** build with [kivy-ios](https://github.com/kivy/kivy-ios) on a Mac with Xcode

## Notes

- The simulation runs in-process on Kivy's clock (every 2.2 s). There is no server, so the app
  works offline and on mobile.
- To go beyond a prototype, swap the toy risk formula for a validated fire-danger index (e.g. NFDRS)
  and the spread model for a physics-based one (e.g. Rothermel).
