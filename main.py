

import math
from datetime import datetime

import flet as ft

from simulation import MAX_HISTORY, TICK_SECONDS, Simulation


# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------

BG = "#F5F6F7"
PANEL = "#FFFFFF"
LINE = "#E2E5E8"
LINE_SOFT = "#EDEFF1"
TEXT = "#15181B"
DIM = "#5B636B"
FAINT = "#87909A"

RISK = {
    "low": "#3F9560",
    "moderate": "#C99A1E",
    "high": "#DB7423",
    "extreme": "#D13B2E",
}
CONTAINED = "#A3ABB2"
WIND = "#3B84A0"
MOIST = "#4F9A5B"
MAP_BG = "#F4F6F7"
MAP_LINE = "#E3E7EA"

FEED_COLOR = {
    "extreme": RISK["extreme"],
    "high": RISK["high"],
    "info": WIND,
    "contained": "#7C848C",
}

COMPASS = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
]


def compass_dir(deg):
    return COMPASS[int(round(deg / 22.5)) % 16]


def txt(value, size=13, color=DIM, bold=False, font_family=None):
    return ft.Text(
        str(value),
        size=size,
        color=color,
        weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL,
        font_family=font_family,
    )



def card(content, padding=14, expand=False, width=None, height=None):
    return ft.Container(
        content=content,
        bgcolor=PANEL,
        border=ft.Border.all(1, LINE),
        border_radius=8,
        padding=padding,
        expand=expand,
        width=width,
        height=height,
    )


def chip(label, color):
    return ft.Container(
        content=txt(label.capitalize(), 11, color, bold=True),
        border=ft.Border.all(1, color),
        border_radius=6,
        padding=ft.Padding.symmetric(horizontal=9, vertical=4),
    )


def dot(color, size=8):
    return ft.Container(
        width=size,
        height=size,
        bgcolor=color,
        border_radius=size / 2,
    )


# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------

class FireMap(ft.Container):
    VIEW_W = 640
    VIEW_H = 460

    def __init__(self):
        self.state = None
        self.avail_w = self.VIEW_W
        self.avail_h = self.VIEW_H
        self.map_stack = ft.Stack(
            width=self.VIEW_W,
            height=self.VIEW_H,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )
        super().__init__(
            content=self.map_stack,
            bgcolor=MAP_BG,
            border=ft.Border.all(1, LINE_SOFT),
            border_radius=6,
            expand=True,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            on_size_change=self._on_size_change,
        )

    def _on_size_change(self, e):
        # Flet reports the real rendered size; redraw the map to fit it.
        if e.width < 20 or e.height < 20:
            return
        if abs(e.width - self.avail_w) < 1 and abs(e.height - self.avail_h) < 1:
            return
        self.avail_w, self.avail_h = e.width, e.height
        if self.state is not None:
            self.render(self.state)
            self.update()

    def _pos(self, x, y, scale, ox, oy):
        return ox + x * scale, oy + (self.VIEW_H - y) * scale

    def _terrain_controls(self, scale, ox, oy):
        controls = []
        # Lightweight terrain bands. They are decorative and intentionally
        # kept as thin containers so the map stays fast in Flet.
        for i in range(6):
            y0 = 20 + i * 75
            points = [
                (x, y0 + math.sin(x / 90 + i) * (18 + (i % 3) * 6) * 0.4)
                for x in range(0, 641, 80)
            ]
            for (x1, y1), (x2, y2) in zip(points, points[1:]):
                sx1, sy1 = self._pos(x1, y1, scale, ox, oy)
                sx2, sy2 = self._pos(x2, y2, scale, ox, oy)
                length = max(1, math.hypot(sx2 - sx1, sy2 - sy1))
                angle = math.degrees(math.atan2(sy2 - sy1, sx2 - sx1))
                controls.append(
                    ft.Container(
                        left=sx1,
                        top=sy1,
                        width=length,
                        height=1,
                        bgcolor=MAP_LINE,
                        rotate=ft.Rotate(angle * math.pi / 180),
                    )
                )
        return controls

    def render(self, state):
        self.state = state

        # Keep the map centered in its available space.
        available_w = self.avail_w
        available_h = self.avail_h
        scale = min(available_w / self.VIEW_W, available_h / self.VIEW_H)
        scale = max(0.35, min(scale, 1.5))
        ox = max(0, (available_w - self.VIEW_W * scale) / 2)
        oy = max(0, (available_h - self.VIEW_H * scale) / 2)

        controls = self._terrain_controls(scale, ox, oy)

        # Wind indicator
        wx, wy = self._pos(590, 40, scale, ox, oy)
        controls.append(
            ft.Container(
                left=wx - 24 * scale,
                top=wy - 24 * scale,
                width=48 * scale,
                height=48 * scale,
                border=ft.Border.all(1, LINE),
                border_radius=24 * scale,
            )
        )
        wind_angle = (state["wind"]["dir"] - 90) * math.pi / 180
        arrow = ft.Text(
            "➤",
            size=max(12, 18 * scale),
            color=WIND,
        )
        controls.append(
            ft.Container(
                content=arrow,
                left=wx - 9 * scale,
                top=wy - 9 * scale,
                rotate=ft.Rotate(wind_angle),
            )
        )
        controls.append(
            ft.Container(
                content=txt("Wind", 10, FAINT),
                left=wx - 20,
                top=wy + 28 * scale,
            )
        )

        # Fires
        for fire in state["fires"]:
            fx, fy = self._pos(fire["x"], fire["y"], scale, ox, oy)
            radius = fire["radius"] * scale
            size = max(8, radius * 1.4)
            color = CONTAINED if fire["contained"] else RISK[fire["severity"]]

            if not fire["contained"] and fire["severity"] == "extreme":
                ring = max(20, radius * 2.1)
                controls.append(
                    ft.Container(
                        left=fx - ring,
                        top=fy - ring,
                        width=ring * 2,
                        height=ring * 2,
                        border=ft.Border.all(1, RISK["extreme"]),
                        border_radius=ring,
                        opacity=0.55,
                    )
                )

            controls.append(
                ft.Container(
                    left=fx - size / 2,
                    top=fy - size / 2,
                    width=size,
                    height=size,
                    bgcolor=color,
                    opacity=0.22,
                    border_radius=size / 2,
                )
            )
            controls.append(
                ft.Container(
                    left=fx - max(4, 5 * scale),
                    top=fy - max(4, 5 * scale),
                    width=max(8, 10 * scale),
                    height=max(8, 10 * scale),
                    bgcolor=color,
                    border_radius=max(4, 5 * scale),
                )
            )

        # Sensor nodes
        show_labels = self.VIEW_W * scale >= 480
        for zone in state["zones"]:
            zx, zy = self._pos(zone["x"], zone["y"], scale, ox, oy)
            nr = max(4.5, 5.5 * scale)
            controls.append(
                ft.Container(
                    left=zx - nr,
                    top=zy - nr,
                    width=nr * 2,
                    height=nr * 2,
                    bgcolor=PANEL,
                    border=ft.Border.all(1.6, RISK[zone["risk_level"]]),
                    border_radius=nr,
                )
            )
            if show_labels:
                controls.append(
                    ft.Container(
                        content=txt(zone["name"], 9, DIM),
                        left=zx - 45,
                        top=zy + nr + 5,
                        width=90,
                        alignment=ft.Alignment.CENTER,
                    )
                )

        self.map_stack.width = available_w
        self.map_stack.height = available_h
        self.map_stack.controls = controls


# ---------------------------------------------------------------------------
# Reusable UI components
# ---------------------------------------------------------------------------

class StatTile(ft.Container):
    def __init__(self, label, sub="", value_size=24):
        self.value = txt("—", value_size, TEXT, font_family="monospace")
        self.sub = txt(sub, 11, DIM)
        super().__init__(
            content=ft.Column(
                [
                    txt(label, 12, FAINT),
                    self.value,
                    self.sub,
                ],
                spacing=3,
                tight=True,
            ),
            padding=ft.Padding.symmetric(vertical=4),
        )

    def set(self, value, sub=None, color=TEXT):
        self.value.value = str(value)
        self.value.color = color
        if sub is not None:
            self.sub.value = sub


class RiskBar(ft.Container):
    def __init__(self):
        self.bar = ft.ProgressBar(value=0, color=RISK["low"], bgcolor=LINE_SOFT, height=4)
        super().__init__(content=self.bar, padding=0)

    def set(self, fraction, color):
        self.bar.value = max(0, min(1, fraction))
        self.bar.color = color


class ZoneRow(ft.Container):
    def __init__(self):
        self.name = txt("", 13, TEXT, bold=False)
        self.flag = txt("", 11, RISK["extreme"])
        self.meta = txt("", 11, DIM)
        self.bar = RiskBar()

        super().__init__(
            content=ft.Column(
                [
                    ft.Row([self.name, self.flag], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    self.meta,
                    self.bar,
                ],
                spacing=3,
            ),
            padding=ft.Padding.symmetric(vertical=8),
            border=ft.Border.only(bottom=ft.BorderSide(1, LINE_SOFT)),
        )

    def render(self, zone, wind_speed):
        self.name.value = zone["name"]
        self.flag.value = "Burning" if zone["on_fire"] else ""
        self.meta.value = (
            f'{round(zone["temp"])}°F, {round(zone["moisture"])}% moisture, '
            f'wind {round(wind_speed)} mph'
        )
        self.bar.set(zone["risk"], RISK[zone["risk_level"]])


class ZoneList(ft.ListView):
    def __init__(self):
        super().__init__(expand=True, spacing=0, auto_scroll=False)
        self.rows = {}
        self.order = []

    def render(self, zones, wind_speed):
        ranked = sorted(zones, key=lambda z: -z["risk"])
        ids = [z["id"] for z in ranked]

        if ids != self.order:
            self.controls = []
            for zone in ranked:
                row = self.rows.setdefault(zone["id"], ZoneRow())
                self.controls.append(row)
            self.order = ids

        for zone in ranked:
            self.rows[zone["id"]].render(zone, wind_speed)


class FeedItem(ft.Container):
    def __init__(self, entry):
        color = FEED_COLOR.get(entry["cls"], DIM)
        top = txt(f'{entry["ts"]}   {entry["tag"]}', 11, color)
        body = txt(entry["text"].replace("[b]", "").replace("[/b]", ""), 12.5, TEXT)
        body.color = TEXT
        super().__init__(
            content=ft.Column([top, body], spacing=2, tight=True),
            padding=ft.Padding.symmetric(vertical=9),
            border=ft.Border.only(bottom=ft.BorderSide(1, LINE_SOFT)),
        )


class FeedList(ft.ListView):
    def __init__(self):
        super().__init__(expand=True, spacing=0, auto_scroll=False)
        self.signature = None

    def render(self, feed):
        sig = tuple((e["ts"], e["tag"], e["text"]) for e in feed)
        if sig == self.signature:
            return
        self.signature = sig
        self.controls = [FeedItem(e) for e in feed]


class Trend(ft.Container):
    def __init__(self, title, color, lo, hi):
        self.title = txt(title, 12, DIM)
        self.value = txt("—", 14, TEXT, font_family="monospace")
        self.color = color
        self.lo = lo
        self.hi = hi
        self.bars = ft.Row(spacing=2, vertical_alignment=ft.CrossAxisAlignment.END)
        super().__init__(
            content=ft.Column(
                [
                    ft.Row(
                        [self.title, ft.Container(expand=True), self.value],
                        tight=True,
                    ),
                    ft.Container(content=self.bars, height=65),
                ],
                spacing=6,
            ),
            expand=True,
        )

    def set_data(self, data):
        values = list(data)[-30:]
        if not values:
            return
        self.bars.controls = []
        span = max(self.hi - self.lo, 1)
        for value in values:
            frac = max(0.08, min(1, (value - self.lo) / span))
            self.bars.controls.append(
                ft.Container(
                    width=7,
                    height=round(55 * frac),
                    bgcolor=self.color,
                    border_radius=2,
                )
            )


class StatusPill(ft.Container):
    def __init__(self):
        self.dot_control = dot(RISK["low"], 7)
        self.label = txt("Connecting…", 12, TEXT)
        super().__init__(
            content=ft.Row(
                [self.dot_control, self.label],
                spacing=8,
                tight=True,
            ),
            border=ft.Border.all(1, LINE),
            border_radius=15,
            padding=ft.Padding.symmetric(horizontal=12, vertical=6),
        )

    def set_state(self, alert, label):
        self.label.value = label
        self.dot_control.bgcolor = RISK["extreme"] if alert else RISK["low"]
        self.label.color = RISK["extreme"] if alert else TEXT
        self.border = ft.Border.all(1, RISK["extreme"] if alert else LINE)


class Header(ft.Container):
    def __init__(self, on_reset, on_toggle):
        self.clock = txt("--:--:--", 12, DIM, font_family="monospace")
        self.pill = StatusPill()
        self.toggle_button = ft.OutlinedButton("Public view", on_click=on_toggle)
        self.reset_button = ft.OutlinedButton("Reset", on_click=on_reset)

        super().__init__(
            content=ft.ResponsiveRow(
                [
                    ft.Container(
                        col={"xs": 12, "md": 7},
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        dot(TEXT, 9),
                                        txt("Firewatch", 19, TEXT, bold=True),
                                    ],
                                    spacing=8,
                                    tight=True,
                                ),
                                txt(
                                    "Live sensor fusion and fire-spread projection, "
                                    "Sierra Foothills",
                                    12,
                                    DIM,
                                ),
                            ],
                            spacing=2,
                            tight=True,
                        ),
                    ),
                    ft.Container(
                        col={"xs": 12, "md": 5},
                        content=ft.Row(
                            [
                                self.clock,
                                self.pill,
                                self.reset_button,
                                self.toggle_button,
                            ],
                            alignment=ft.MainAxisAlignment.END,
                            wrap=True,
                        ),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=PANEL,
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            border=ft.Border.only(bottom=ft.BorderSide(1, LINE)),
        )


# ---------------------------------------------------------------------------
# Public view
# ---------------------------------------------------------------------------

class PublicView(ft.Column):
    def __init__(self):
        self.banner = ft.Container()
        self.advisories = ft.Column(spacing=0)
        super().__init__(
            [self.banner, card(self.advisories, padding=0)],
            spacing=14,
        )

    def render(self, state):
        active = [f for f in state["fires"] if not f["contained"]]
        extreme = [f for f in active if f["severity"] == "extreme"]

        if extreme:
            title = "Evacuation advisory in effect"
            body = (
                f"Active fire detections with rapid spread potential are affecting "
                f"{len(extreme)} zone(s). Follow instructions from local emergency "
                "services and be ready to leave immediately if directed."
            )
            color = RISK["extreme"]
        elif active:
            title = "Active fire activity nearby"
            body = (
                f"Fire crews are responding to {len(active)} detection(s) in the region. "
                "Monitor conditions and prepare an evacuation kit."
            )
            color = RISK["high"]
        else:
            hot = [z for z in state["zones"] if z["risk_level"] in ("high", "extreme")]
            if hot:
                title = "Elevated fire danger"
                body = (
                    f"Wind, low fuel moisture and temperature are raising fire risk in "
                    f"{len(hot)} zone(s). No active fires detected at this time."
                )
                color = RISK["moderate"]
            else:
                title = "No active fire danger reported"
                body = (
                    "The sensor network reports normal conditions region-wide. "
                    "This page updates automatically as conditions change."
                )
                color = RISK["low"]

        self.banner.content = ft.Container(
            content=ft.Column(
                [
                    txt("Regional fire status", 12.5, DIM),
                    txt(title, 24, TEXT, bold=True),
                    txt(body, 14, DIM),
                ],
                spacing=6,
            ),
            border=ft.Border(
                left=ft.BorderSide(4, color),
                top=ft.BorderSide(1, LINE),
                right=ft.BorderSide(1, LINE),
                bottom=ft.BorderSide(1, LINE),
            ),
            padding=ft.Padding.symmetric(horizontal=24, vertical=20),
            bgcolor=PANEL,
            border_radius=8,
        )

        rows = [
            ft.Container(
                content=txt("Zones with active advisories", 14, TEXT, bold=True),
                padding=ft.Padding.symmetric(horizontal=14, vertical=11),
                border=ft.Border.only(bottom=ft.BorderSide(1, LINE_SOFT)),
            )
        ]
        if active:
            for fire in active:
                rows.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                txt(fire["zone_name"], 14, TEXT),
                                chip(fire["severity"], RISK[fire["severity"]]),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        padding=ft.Padding.symmetric(horizontal=14, vertical=11),
                        border=ft.Border.only(bottom=ft.BorderSide(1, LINE_SOFT)),
                    )
                )
        else:
            rows.append(
                ft.Container(
                    content=txt("No zones are currently under advisory.", 13.5, DIM),
                    padding=14,
                )
            )

        self.advisories.controls = rows


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

class FirewatchApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.sim = Simulation()
        self.showing_public = False

        page.title = "Firewatch — Live Detection Console"
        page.bgcolor = BG
        page.padding = 0
        page.theme_mode = ft.ThemeMode.LIGHT
        page.scroll = ft.ScrollMode.AUTO
        page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH

        self.header = Header(self.reset, self.toggle_view)
        self.ops = self.build_ops()
        self.public = PublicView()

        self.holder = ft.Container(content=self.ops, padding=16)

        page.add(
            self.header,
            self.holder,
            ft.Container(
                content=txt(
                    "Simulated demo. Data is generated by a built-in Python simulation "
                    "for illustration and does not reflect real conditions.",
                    11,
                    FAINT,
                ),
                alignment=ft.Alignment.CENTER,
                padding=ft.Padding.only(bottom=10),
            ),
        )

        self.refresh()
        page.run_task(self.timer_loop)

    def build_ops(self):
        self.t_sensors = StatTile("Sensors online", "Smoke and weather nodes")
        self.t_fires = StatTile("Active detections", "No active ignitions")
        self.t_top = StatTile("Highest-risk zone", value_size=17)
        self.t_wind = StatTile("Wind")
        self.t_moist = StatTile("Avg. fuel moisture", "10-hr fuel class")

        stats = ft.ResponsiveRow(
            [
                ft.Container(content=x, col={"xs": 6, "sm": 4, "md": 2.4})
                for x in [
                    self.t_sensors,
                    self.t_fires,
                    self.t_top,
                    self.t_wind,
                    self.t_moist,
                ]
            ],
            spacing=16,
        )

        self.zone_list = ZoneList()
        zones_panel = card(
            ft.Column(
                [
                    txt("Zones by risk", 13, TEXT, bold=True),
                    ft.Divider(height=1, color=LINE_SOFT),
                    self.zone_list,
                ],
                spacing=8,
            ),
            padding=14,
            height=480,
        )

        self.map = FireMap()
        self.map_panel_meta = txt("", 11, FAINT)
        map_panel = card(
            ft.Column(
                [
                    ft.Row(
                        [txt("Terrain and sensor map", 13, TEXT, bold=True),
                         ft.Container(expand=True), self.map_panel_meta]
                    ),
                    self.map,
                    ft.Row(
                        [
                            ft.Row([dot(RISK["low"]), txt("Low", 11.5, DIM)], spacing=5),
                            ft.Row([dot(RISK["moderate"]), txt("Moderate", 11.5, DIM)], spacing=5),
                            ft.Row([dot(RISK["high"]), txt("High", 11.5, DIM)], spacing=5),
                            ft.Row([dot(RISK["extreme"]), txt("Extreme", 11.5, DIM)], spacing=5),
                            ft.Row([dot(CONTAINED), txt("Contained", 11.5, DIM)], spacing=5),
                        ],
                        wrap=True,
                    ),
                    txt(
                        "Rings show the simulated evacuation advisory radius.",
                        11,
                        FAINT,
                    ),
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            padding=10,
            height=480,
            expand=True,
        )

        self.feed_list = FeedList()
        feed_panel = card(
            ft.Column(
                [
                    txt("Event feed", 13, TEXT, bold=True),
                    ft.Divider(height=1, color=LINE_SOFT),
                    self.feed_list,
                ],
                spacing=8,
            ),
            padding=14,
            height=480,
        )

        main_grid = ft.ResponsiveRow(
            [
                ft.Container(content=zones_panel, col={"xs": 12, "lg": 3}),
                ft.Container(content=map_panel, col={"xs": 12, "lg": 6}),
                ft.Container(content=feed_panel, col={"xs": 12, "lg": 3}),
            ],
            spacing=12,
        )

        self.tr_wind = Trend("Wind speed (mph)", WIND, 0, 45)
        self.tr_moist = Trend("Fuel moisture (%)", MOIST, 0, 26)

        trends = card(
            ft.Column(
                [
                    txt(f"Environmental trends, last {MAX_HISTORY} readings", 13, TEXT, bold=True),
                    ft.Row([self.tr_wind, self.tr_moist], spacing=24),
                ],
                spacing=10,
            ),
            padding=14,
        )

        return ft.Column(
            [stats, main_grid, trends],
            spacing=14,
        )

    async def timer_loop(self):
        while True:
            await self._sleep(TICK_SECONDS)
            self.sim.tick()
            self.refresh()

    async def _sleep(self, seconds):
        import asyncio
        await asyncio.sleep(seconds)

    def refresh(self):
        state = self.sim.snapshot()

        self.update_stats(state)
        self.zone_list.render(state["zones"], state["wind"]["speed"])
        self.map.render(state)
        self.map_panel_meta.value = f'tick {state["tick"]}, {state["server_time"]}'
        self.feed_list.render(state["feed"])
        self.tr_wind.set_data(state["wind_history"])
        self.tr_moist.set_data(state["moist_history"])

        if state["wind_history"]:
            self.tr_wind.value.value = f'{round(state["wind_history"][-1])} mph'
            self.tr_moist.value.value = f'{state["moist_history"][-1]:.1f}%'

        self.public.render(state)
        self.page.update()

    def update_stats(self, state):
        zones = state["zones"]
        active = [f for f in state["fires"] if not f["contained"]]
        severe = any(f["severity"] == "extreme" for f in active)

        self.t_sensors.set(len(zones))

        names = [f["zone_name"] for f in active]
        if not names:
            sub = "No active ignitions"
        elif len(names) <= 2:
            sub = ", ".join(names)
        else:
            sub = f"{names[0]}, {names[1]} +{len(names)-2} more"

        self.t_fires.set(
            len(active),
            sub,
            RISK["extreme"] if severe else RISK["high"] if active else TEXT,
        )

        top = max(zones, key=lambda z: z["risk"])
        top_color = (
            RISK["extreme"] if top["risk_level"] == "extreme"
            else RISK["high"] if top["risk_level"] == "high"
            else TEXT
        )
        self.t_top.set(
            top["name"],
            f'{top["risk_level"].capitalize()}, score {top["risk"]:.2f}',
            top_color,
        )

        self.t_wind.set(
            f'{round(state["wind"]["speed"])} mph',
            "from " + compass_dir(state["wind"]["dir"]),
        )

        avg = sum(z["moisture"] for z in zones) / len(zones)
        self.t_moist.set(f"{avg:.1f}%")

        if active:
            n = len(active)
            self.header.pill.set_state(True, f"{n} active detection{'s' if n != 1 else ''}")
        else:
            self.header.pill.set_state(False, "All systems nominal")

        self.header.clock.value = datetime.now().strftime("%H:%M:%S") + " local"

    def reset(self, e=None):
        self.sim = Simulation()
        self.refresh()

    def toggle_view(self, e=None):
        self.showing_public = not self.showing_public
        self.holder.content = self.public if self.showing_public else self.ops
        self.header.toggle_button.content = (
            "Console view" if self.showing_public else "Public view"
        )
        self.page.update()


def main(page: ft.Page):
    FirewatchApp(page)


if __name__ == "__main__":
    ft.run(main)
