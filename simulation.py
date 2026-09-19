

import random
from datetime import datetime

ZONE_DEFS = [
    # id,   name,                 x,   y,   elev, slope
    ("z1",  "North Ridge",        120, 90,  0.80, 0.70),
    ("z2",  "Deer Creek Canyon",  280, 70,  0.50, 0.50),
    ("z3",  "Saddle Basin",       460, 110, 0.65, 0.40),
    ("z4",  "Pine Hollow",        560, 190, 0.40, 0.30),
    ("z5",  "West Mesa",          90,  220, 0.55, 0.60),
    ("z6",  "Coldwater Flats",    230, 230, 0.30, 0.20),
    ("z7",  "Chaparral Bench",    370, 250, 0.60, 0.55),
    ("z8",  "Oak Draw",           500, 300, 0.35, 0.35),
    ("z9",  "Sundance Slope",     150, 340, 0.75, 0.80),
    ("z10", "Lower Basin",        310, 370, 0.20, 0.15),
    ("z11", "Timberline East",    450, 400, 0.70, 0.65),
    ("z12", "Redrock Spur",       580, 340, 0.50, 0.45),
]

MAX_HISTORY = 60
MAX_FEED = 60
TICK_SECONDS = 2.2


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


class Simulation:
    def __init__(self):
        self.zones = []
        for zid, name, x, y, elev, slope in ZONE_DEFS:
            self.zones.append({
                "id": zid, "name": name, "x": x, "y": y,
                "elev": elev, "slope": slope,
                "temp": 78 + random.random() * 10,
                "humidity": 25 + random.random() * 20,
                "moisture": 8 + random.random() * 10,
                "risk": 0.0, "risk_level": "low", "on_fire": False,
            })
        self.wind_speed = 12 + random.random() * 8
        self.wind_dir = random.random() * 360
        self.wind_history = []
        self.moist_history = []
        self.fires = []
        self.feed = []
        self.tick_count = 0
        self.fire_id_seq = 1

        # seed some history so the first snapshot isn't empty
        for _ in range(20):
            self._step_environment()
        self._log("info", "System",
                  "Sensor network initialized — 12 nodes online across the Sierra Foothills region.")

    # -- risk model ---------------------------------------------------
    def _compute_risk(self, z):
        wind_term = min(self.wind_speed / 35, 1)
        moist_term = 1 - min(z["moisture"] / 20, 1)
        temp_term = min((z["temp"] - 60) / 40, 1)
        slope_term = z["slope"]
        score = wind_term * 0.28 + moist_term * 0.34 + temp_term * 0.2 + slope_term * 0.18
        return clamp(score, 0, 1)

    @staticmethod
    def _risk_level(score):
        if score > 0.72:
            return "extreme"
        if score > 0.52:
            return "high"
        if score > 0.32:
            return "moderate"
        return "low"

    def _log(self, cls, tag, text):
        """cls: 'extreme' | 'high' | 'info' | 'contained'. Use [b]..[/b] for emphasis."""
        ts = datetime.now().strftime("%H:%M:%S")
        self.feed.append({"cls": cls, "tag": tag, "text": text, "ts": ts})
        if len(self.feed) > MAX_FEED:
            self.feed.pop(0)

    # -- simulation steps ----------------------------------------------
    def _step_environment(self):
        self.wind_speed = clamp(self.wind_speed + (random.random() - 0.5) * 2.2, 4, 42)
        self.wind_dir = (self.wind_dir + (random.random() - 0.5) * 10 + 360) % 360

        for z in self.zones:
            z["temp"] = clamp(z["temp"] + (random.random() - 0.5) * 1.4, 55, 108)
            z["humidity"] = clamp(z["humidity"] + (random.random() - 0.5) * 2, 5, 70)
            dry_pull = -0.15 if z["on_fire"] else -0.02
            z["moisture"] = clamp(z["moisture"] + (random.random() - 0.5) * 0.6 + dry_pull, 2, 26)
            z["risk"] = self._compute_risk(z)
            z["risk_level"] = self._risk_level(z["risk"])

        avg_moist = sum(z["moisture"] for z in self.zones) / len(self.zones)
        self.wind_history.append(self.wind_speed)
        if len(self.wind_history) > MAX_HISTORY:
            self.wind_history.pop(0)
        self.moist_history.append(avg_moist)
        if len(self.moist_history) > MAX_HISTORY:
            self.moist_history.pop(0)

    def _maybe_ignite(self):
        for z in self.zones:
            if z["on_fire"]:
                continue
            chance = (z["risk"] ** 3) * 0.05
            if random.random() < chance:
                self._ignite(z)

    def _ignite(self, z):
        z["on_fire"] = True
        self.fires.append({
            "id": self.fire_id_seq, "zone_id": z["id"], "zone_name": z["name"],
            "x": z["x"], "y": z["y"], "start_tick": self.tick_count,
            "radius": 6.0, "max_radius": 30 + z["risk"] * 70,
            "wind_dir_at_start": self.wind_dir, "severity": z["risk_level"],
            "contained": False, "contain_tick": None,
        })
        self.fire_id_seq += 1
        self._log(
            "extreme" if z["risk_level"] == "extreme" else "high",
            "Detection",
            f"New smoke/heat signature confirmed at [b]{z['name']}[/b] — "
            f"risk level {z['risk_level'].upper()}.",
        )

    def _step_fires(self):
        for f in self.fires:
            if f["contained"]:
                continue
            age = self.tick_count - f["start_tick"]
            growth = f["max_radius"] / 22
            f["radius"] = min(f["max_radius"], f["radius"] + growth)
            f["wind_dir_at_start"] = self.wind_dir  # spread axis follows current wind

            if f["radius"] >= f["max_radius"] and random.random() < 0.35:
                f["contained"] = True
                f["contain_tick"] = self.tick_count
                zone = next((zz for zz in self.zones if zz["id"] == f["zone_id"]), None)
                if zone:
                    zone["on_fire"] = False
                self._log("contained", "Containment",
                          f"Fire at [b]{f['zone_name']}[/b] reported contained by ground crews.")
            elif age > 0 and age % 6 == 0:
                self._log("info", "Update",
                          f"Fire at [b]{f['zone_name']}[/b] spreading — radius {round(f['radius'])} units, "
                          f"wind {round(self.wind_speed)} mph.")

        self.fires = [
            f for f in self.fires
            if not f["contained"] or (self.tick_count - f["contain_tick"]) < 40
        ]

    def tick(self):
        self.tick_count += 1
        self._step_environment()
        self._maybe_ignite()
        self._step_fires()

    def snapshot(self):
        top_zone = max(self.zones, key=lambda z: z["risk"])
        return {
            "tick": self.tick_count,
            "server_time": datetime.now().strftime("%H:%M:%S"),
            "zones": self.zones,
            "wind": {"speed": self.wind_speed, "dir": self.wind_dir},
            "wind_history": self.wind_history,
            "moist_history": self.moist_history,
            "fires": self.fires,
            "feed": list(reversed(self.feed[-25:])),
            "top_zone_id": top_zone["id"],
        }
