"""MFC box designs.  Every design is a Variant (colours + a few layout switches)
rendered by one set of layout functions, so all variants share the same, checked
text orientation per panel (see geometry.py for `rot`).

Coordinates are die-line (sheet) mm.  Key panel spans (Rev H and Rev I alike):
  lid front  y 135.08 (free edge, bottom when closed) .. 296.74 (hinge, top)   rot 180
  lid top    y 296.74 (front) .. 528.82 (back hinge)                           rot 180
  back       y 528.82 (top) .. 726.32 (floor fold)                             rot 0
  bottom     y 726.32 (back) .. 958.39 (front), x 295.73 .. 512.39             rot 0
  front lip  y 958.39 (floor fold) .. 987.14 (top, thumb notch)                rot 180
  inside of the lid top: read from inside -> mirrored glyphs, up = toward y 296.74
"""
import math

from shapely.geometry import box as sbox
from shapely.ops import unary_union

from build import text_el, geom_d, layer, fmt, Font
from design_v1 import logo, rule, T, S

CX = 404.06
LID = ["lidtop", "lidfront", "lidsideL", "lidsideR", "lidinner", "tuck", "lidearL", "lidearR"]
LINERS = ["sidelinerL", "sidelinerR", "lidlinerL", "lidlinerR", "innerlip"]


class Variant:
    def __init__(self, key, name, **kw):
        self.key, self.name = key, name
        d = dict(board="#d8d1c6", lid=None, liner=None, inside="#dcd6cc", insert="#dcd6cc",
                 ink="#4c4640", txt="#6a625b", rule="#8b827a", logo="#4a3a2f",
                 lid_ink=None, lid_txt=None, lid_logo=None,
                 in_ink=None, in_txt=None, in_logo=None,
                 ins_ink=None, ins_txt=None, ins_logo=None,
                 top="center", top_logo=None, top_size=110,
                 front="stack", front_logo=40, horizon=None, mark_inside=60)
        d.update(kw)
        for k, v in d.items():
            setattr(self, k, v)
        self.lid = self.lid or self.board
        self.liner = self.liner or self.board
        self.lid_ink = self.lid_ink or self.ink
        self.lid_txt = self.lid_txt or self.txt
        self.lid_logo = self.lid_logo or self.logo
        self.in_ink, self.in_txt, self.in_logo = self.in_ink or self.ink, self.in_txt or self.txt, self.in_logo or self.logo
        self.ins_ink, self.ins_txt, self.ins_logo = self.ins_ink or self.ink, self.ins_txt or self.txt, self.ins_logo or self.logo


VARIANTS = [
    Variant("stone", "Stone", top_logo="#c6bdb0"),
    Variant("noir", "Noir", board="#2b2623", liner="#cdbfa8", inside="#cdbfa8", insert="#d6cab6",
            ink="#ece3d4", txt="#cfc4b3", rule="#8d8174", logo="#ece3d4",
            in_ink="#2b2623", in_txt="#5c524a", in_logo="#2b2623",
            ins_ink="#2b2623", ins_txt="#5c524a", ins_logo="#2b2623", top_logo="#38312d", top_size=150),
    Variant("coast", "Coastline", board="#eeeae2", liner="#e2dcd1", inside="#e9e4db", insert="#e9e4db",
            ink="#2e3a45", txt="#55606a", rule="#7d8790", logo="#2e3a45", front="script",
            top_logo="#2e3a45", top_size=56, horizon=(58, "#2e3a45")),
    Variant("mark", "Big Mark", board="#cbbda4", liner="#ece4d6", inside="#ece4d6", insert="#ece4d6",
            ink="#4b4034", txt="#6d604f", rule="#8f8170", logo="#4b4034", top="wrap", top_logo="#b8a98d",
            front="corner", in_logo="#cbbda4", mark_inside=120),
    Variant("sun", "Sun-faded", board="#efe6d6", lid="#b8704f", liner="#b8704f", inside="#b8704f", insert="#efe6d6",
            ink="#8a4a31", txt="#9a6a55", rule="#b98f7c", logo="#8a4a31",
            lid_ink="#f4ebdc", lid_txt="#f0dfcc", lid_logo="#f4ebdc",
            in_ink="#f4ebdc", in_txt="#f0dfcc", in_logo="#f4ebdc", top_logo="#c98564", top_size=120),
]
BY_KEY = {v.key: v for v in VARIANTS}


# ------------------------------------------------------------------ small graphics

def us_flag(cx, cy, w, ink, bg, rot=0):
    """Monochrome US flag: ink stripes and canton, stars knocked out in the background colour."""
    h = w * 10 / 19
    sh = h / 13
    o = ['<g transform="translate(%s %s) rotate(%s) translate(%s %s)">' % (fmt(cx), fmt(cy), fmt(rot), fmt(-w / 2), fmt(-h / 2))]
    for i in range(0, 13, 2):
        o.append('<rect x="0" y="%s" width="%s" height="%s" fill="%s"/>' % (fmt(i * sh), fmt(w), fmt(sh), ink))
    cw, ch = w * 0.4, sh * 7
    o.append('<rect x="0" y="0" width="%s" height="%s" fill="%s"/>' % (fmt(cw), fmt(ch), ink))
    r = ch / 9 * 0.32
    for row in range(9):
        n, off = (6, 0) if row % 2 == 0 else (5, 1)
        for c in range(n):
            x = cw / 12 * (2 * c + 1 + off)
            y = ch / 10 * (row + 1)
            o.append(star(x, y, r, bg))
    o.append('<rect x="0" y="0" width="%s" height="%s" fill="none" stroke="%s" stroke-width="0.2"/>' % (fmt(w), fmt(h), ink))
    o.append("</g>")
    return "".join(o)


def star(x, y, r, fill):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.42
        pts.append("%s,%s" % (fmt(x + rr * math.cos(a)), fmt(y + rr * math.sin(a))))
    return '<polygon points="%s" fill="%s"/>' % (" ".join(pts), fill)


def icon_sun(cx, cy, s, ink):
    o = ['<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="0.35"/>' % (fmt(cx), fmt(cy), fmt(s * 0.24), ink)]
    for i in range(8):
        a = i * math.pi / 4
        o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="0.35" stroke-linecap="round"/>'
                 % (fmt(cx + math.cos(a) * s * 0.34), fmt(cy + math.sin(a) * s * 0.34),
                    fmt(cx + math.cos(a) * s * 0.48), fmt(cy + math.sin(a) * s * 0.48), ink))
    return "".join(o)


def icon_recycle(cx, cy, s, ink):
    r = s * 0.38
    o = []
    for k in range(3):
        a0 = math.radians(k * 120 + 20)
        a1 = math.radians(k * 120 + 110)
        x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
        x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        o.append('<path d="M%s %s A%s %s 0 0 1 %s %s" fill="none" stroke="%s" stroke-width="0.35" stroke-linecap="round"/>'
                 % (fmt(x0), fmt(y0), fmt(r), fmt(r), fmt(x1), fmt(y1), ink))
        # arrow head at the end, along the tangent
        tx, ty = -math.sin(a1), math.cos(a1)
        nx, ny = math.cos(a1), math.sin(a1)
        hs = s * 0.12
        o.append('<path d="M%s %s L%s %s L%s %s Z" fill="%s"/>'
                 % (fmt(x1 + tx * hs), fmt(y1 + ty * hs), fmt(x1 - nx * hs * 0.7), fmt(y1 - ny * hs * 0.7),
                    fmt(x1 + nx * hs * 0.7), fmt(y1 + ny * hs * 0.7), ink))
    return "".join(o)


def icon_noglue(cx, cy, s, ink):
    h = s * 0.42
    d = "M%s %s C%s %s %s %s %s %s A%s %s 0 1 1 %s %s C%s %s %s %s %s %s Z" % (
        fmt(cx), fmt(cy - h), fmt(cx + h * 0.2), fmt(cy - h * 0.55), fmt(cx + h * 0.55), fmt(cy - h * 0.1),
        fmt(cx + h * 0.55), fmt(cy + h * 0.25), fmt(h * 0.55), fmt(h * 0.55), fmt(cx - h * 0.55), fmt(cy + h * 0.25),
        fmt(cx - h * 0.55), fmt(cy - h * 0.1), fmt(cx - h * 0.2), fmt(cy - h * 0.55), fmt(cx), fmt(cy - h))
    return ('<path d="%s" fill="none" stroke="%s" stroke-width="0.35"/>'
            '<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="0.35" stroke-linecap="round"/>'
            % (d, ink, fmt(cx - s * 0.4), fmt(cy + s * 0.4), fmt(cx + s * 0.4), fmt(cy - s * 0.4), ink))


def circle_text(outlined, txt, cx, cy, r, size, color, weight="Medium", track=None, start=-90.0, mirror=False):
    """Text set on a circle, reading clockwise from `start` degrees (0 = 3 o'clock).
    track=None spreads the letters to close the full circle."""
    F = Font.get("Montserrat-%s.ttf" % weight)
    if track is None:
        track = (2 * math.pi * r - F.width(txt, size)) / (len(txt) * size)
    o, ang = [], math.radians(start)
    for ch in txt:
        adv = F.width(ch, size) + track * size
        mid = ang + adv / 2 / r
        x, y = cx + r * math.cos(mid), cy + r * math.sin(mid)
        if ch != " ":
            o.append(T(outlined, ch, x, y, size, weight, color, math.degrees(mid) + 90, 0.0, mirror=mirror))
        ang += adv / r
    return "".join(o)


def seal(outlined, cx, cy, v, ink, logo_fill, mirror=False):
    o = ['<circle cx="%s" cy="%s" r="24" fill="none" stroke="%s" stroke-width="0.35"/>' % (fmt(cx), fmt(cy), ink),
         '<circle cx="%s" cy="%s" r="17.2" fill="none" stroke="%s" stroke-width="0.25"/>' % (fmt(cx), fmt(cy), ink)]
    o.append(circle_text(outlined, "MFC · THE CATCH CAP · GOOD MOMENTS AHEAD · ", cx, cy, 19.6, 2.25, ink))
    o.append(logo(cx, cy, 24, 0, logo_fill))
    return "".join(o)


# ------------------------------------------------------------------ layouts

def _bg(info, color, ids=None):
    if ids is None:
        return '<path d="%s" fill="%s"/>' % (geom_d(info["bleed"]), color)
    regs = [info["regions"][i] for i in ids if i in info["regions"]]
    return '<path d="%s" fill="%s"/>' % (geom_d(unary_union(regs)), color) if regs else ""


def _clip(cid, info, ids):
    regs = unary_union([info["regions"][i] for i in ids if i in info["regions"]])
    return '<clipPath id="%s"><path d="%s"/></clipPath>' % (cid, geom_d(regs))


def bottom_block(v, outlined, cx=CX):
    """Brand block on the box bottom (rot 0, up = toward the back)."""
    o, ink, txt = [], v.ink, v.txt
    t = lambda *a, **k: o.append(T(outlined, *a, **k))
    o.append(seal(outlined, cx, 778, v, ink, v.logo))
    o.append(us_flag(cx, 822, 19, ink, v.board))
    t("DESIGNED IN CALIFORNIA", cx, 839, 3.0, "SemiBold", ink, 0, 0.36)
    o.append(S(outlined, "for those who chase the good moments", cx, 845.5, 3.4, txt))
    for x, fn, cap in ((cx - 32, icon_sun, "MORE SUNNY DAYS"), (cx, icon_recycle, "PLEASE RECYCLE"),
                       (cx + 32, icon_noglue, "GLUE-FREE BOX")):
        o.append(fn(x, 870, 10, ink))
        t(cap, x, 881, 1.7, "SemiBold", ink, 0, 0.3)
    o.append(rule(cx, 893, 60, 0, v.rule, 0.25))
    t("COLLECTIBLE EDITION", cx - 9, 905, 2.2, "SemiBold", ink, 0, 0.32, "end")
    t("No.", cx - 3, 905, 2.2, "SemiBold", ink, 0, 0.1, "start")
    o.append('<rect x="%s" y="905.3" width="22" height="0.25" fill="%s"/>' % (fmt(cx + 3), ink))
    t("© 2026 MFC. ALL RIGHTS RESERVED.", cx, 922, 1.6, "Medium", txt, 0, 0.3)
    return o


def horizon(v, info, outlined):
    if not v.horizon:
        return []
    h, col = v.horizon
    ids = ["lidfront", "back", "sideL", "sideR", "lidsideL", "lidsideR"]
    # the line is cut to the panels geometrically (no clip path), so every renderer gets the same result
    w = 1.0
    regs = unary_union([info["regions"][i] for i in ids if i in info["regions"]])
    bars = [sbox(250, 97.74 + h - w / 2, 570, 97.74 + h + w / 2),            # lid front
            sbox(250, 726.32 - h - w / 2, 570, 726.32 - h + w / 2)]          # back
    for x in (295.73 - h, 512.39 + h):                                       # side walls
        bars.append(sbox(x - w / 2, 700, x + w / 2, 1000))
    for x in (295.73 - (197.5 - h), 512.39 + (197.5 - h)):                   # lid sides (closed)
        bars.append(sbox(x - w / 2, 280, x + w / 2, 540))
    return ['<path d="%s" fill="%s"/>' % (geom_d(unary_union(bars).intersection(regs)), col)]


def box_outside(v, panels, info, outlined):
    o = [_bg(info, v.board), _bg(info, v.lid, LID), _bg(info, v.liner, LINERS)]
    t = lambda *a, **k: o.append(T(outlined, *a, **k))
    y = lambda h: 135.08 + h                          # lid front, h above its free edge
    o += horizon(v, info, outlined)
    # ---- lid top
    if v.top == "wrap":
        # oversized mark cropped by the lid: runs from the lid top over the front edge
        o.append(_clip("lidwrap", info, ["lidtop", "lidfront"]))
        o.append('<g clip-path="url(#lidwrap)">%s</g>' % logo(CX + 40, 330, 300, 180, v.top_logo))
    else:
        o.append(logo(CX, 420, v.top_size, 180, v.top_logo))
        t("MFC", CX, 352, 6.5, "Regular", v.lid_ink, 180, 0.62)
    # ---- lid front
    if v.front == "stack":
        o.append(logo(CX, y(112), v.front_logo, 180, v.lid_logo))
        t("MFC", CX, y(79), 10.5, "Regular", v.lid_ink, 180, 0.62)
        o.append(rule(CX, y(73.5), 9, 180, v.rule))
        t("FOR THOSE WHO CHASE", CX, y(66), 2.7, "Medium", v.lid_txt, 180, 0.42)
        t("THE GOOD MOMENTS.", CX, y(61.2), 2.7, "Medium", v.lid_txt, 180, 0.42)
    elif v.front == "script":
        o.append(S(outlined, "the catch", CX, y(84), 34, v.lid_ink, 180))
        o.append(logo(CX, y(124), 26, 180, v.lid_logo))
        t("MFC", CX, y(64), 5.5, "Regular", v.lid_ink, 180, 0.62)
        t("FOR THOSE WHO CHASE THE GOOD MOMENTS.", CX, y(42), 2.3, "Medium", v.lid_txt, 180, 0.42)
    elif v.front == "corner":
        t("MFC", 512.39 - 14, y(14), 6, "Regular", v.lid_ink, 180, 0.62, "start")
        t("THE CATCH CAP", 295.73 + 14, y(14), 2.4, "SemiBold", v.lid_ink, 180, 0.36, "start")
    # ---- front lip
    t("GOOD MOMENTS AHEAD", CX, 958.39 + 6.5, 2.5, "Medium", v.txt, 180, 0.48)
    # ---- back
    o.append(logo(CX, 600, 52, 0, v.logo))
    t("MFC", CX, 652, 7, "Regular", v.ink, 0, 0.62)
    o.append(rule(CX, 658, 7, 0, v.rule))
    t("THE CATCH CAP", CX, 667, 2.5, "SemiBold", v.ink, 0, 0.32)
    o.append(S(outlined, "Made for sunny days and bigger stories.", CX, 673.5, 3.4, v.txt))
    # ---- side walls: small mark near the floor
    for x, r in ((295.73 - 9, -90), (512.39 + 9, 90)):
        t("MFC", x, 842.4, 3.4, "Regular", v.ink, r, 0.62)
    # ---- bottom
    o += bottom_block(v, outlined)
    return layer("ARTWORK", "ARTWORK - outside print (%s)" % v.name, "\n".join(o))


def box_inside(v, panels, info, outlined):
    o = [_bg(info, v.inside)]
    t = lambda *a, **k: o.append(T(outlined, *a, mirror=True, **k))
    # composition sits toward the hinge: with the lid open, the lid front (161.7 mm, at right angles)
    # hides the first ~60 mm of the lid top from a viewer in front of the box
    f = 296.74
    if v.top == "wrap":
        o.append(logo(CX + 30, f + 150, v.mark_inside * 1.6, 0, "#e0d6c5", mirror=True))
        o.append(logo(CX, f + 92, 40, 0, v.in_ink, mirror=True))
    else:
        o.append(logo(CX, f + 92, v.mark_inside, 0, v.in_logo, mirror=True))
    t("MFC", CX, f + 140, 9, "Regular", v.in_ink, 0, 0.62)
    o.append(rule(CX, f + 146, 9, 0, v.rule))
    t("FOR THOSE WHO CHASE", CX, f + 155, 2.7, "Medium", v.in_txt, 0, 0.42)
    t("THE GOOD MOMENTS.", CX, f + 160, 2.7, "Medium", v.in_txt, 0, 0.42)
    xl = 512.39 - 22
    t("PREMIUM CAP", xl, f + 196, 2.5, "SemiBold", v.in_ink, 0, 0.32, "start")
    o.append('<rect x="%s" y="%s" width="6" height="0.35" fill="%s"/>' % (fmt(xl - 6), fmt(f + 199), v.rule))
    o.append(S(outlined, "Made for sunny days", xl, f + 205.5, 3.2, v.in_txt, 0, "start", mirror=True))
    o.append(S(outlined, "and bigger stories.", xl, f + 209.8, 3.2, v.in_txt, 0, "start", mirror=True))
    return layer("ARTWORK", "ARTWORK - inside print, lid (%s)" % v.name, "\n".join(o))


def insert_art(v, panels, info, outlined):
    o = [_bg(info, v.insert)]
    t = lambda *a, **k: o.append(T(outlined, *a, **k))
    ink, txt, xl = v.ins_ink, v.ins_txt, 419.0
    t("THE CATCH CAP", xl, 133, 2.4, "SemiBold", ink, 0, 0.3, "start")
    o.append('<rect x="%s" y="135.6" width="5" height="0.35" fill="%s"/>' % (fmt(xl), v.rule))
    o.append(S(outlined, "For those who chase", xl, 140.6, 2.9, txt, 0, "start"))
    o.append(S(outlined, "the good moments.", xl, 144.3, 2.9, txt, 0, "start"))
    o.append(logo(594.5, 139, 26, 0, v.ins_logo))
    for i, w in enumerate(("MORE", "SUNNY", "DAYS")):
        t(w, 424.5, 252 + i * 3.6, 1.9, "SemiBold", ink, 0, 0.32)
    o.append(rule(424.5, 264.5, 4, 0, v.rule))
    t("COLLECTIBLE CAP", xl, 304, 2.4, "SemiBold", ink, 0, 0.3, "start")
    o.append('<rect x="%s" y="306.6" width="5" height="0.35" fill="%s"/>' % (fmt(xl), v.rule))
    o.append(S(outlined, "Made for sunny days", xl, 311.6, 2.9, txt, 0, "start"))
    o.append(S(outlined, "and bigger stories.", xl, 315.3, 2.9, txt, 0, "start"))
    return layer("ARTWORK", "ARTWORK - insert print (%s)" % v.name, "\n".join(o))
