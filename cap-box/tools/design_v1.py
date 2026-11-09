"""MFC design v1 (after the client's mood shots): warm stone board, wide-tracked
Montserrat caps, MFC logo silhouette.

Three artwork layers, all in die-line (sheet) coordinates, mm:
  box_outside   printed outside of the box
  box_inside    inside of the lid top (needs printing on the reverse side!)
  insert        printed face of the insert

`rot` conventions per panel are explained in geometry.py.  Text placement
was checked on the 3D model.
"""
import re
import os

from build import text_el, geom_d, layer, fmt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

BOARD = "#d8d1c6"        # stone board (box)
BOARD_IN = "#dcd6cc"     # insert / inside print
INK = "#4c4640"          # headings
TXT = "#6a625b"          # body text
LOGO = "#4a3a2f"         # logo brown
RULE = "#8b827a"

_logo = open(os.path.join(ROOT, "source", "MFC-logo-silhouette.svg")).read()
LOGO_D = re.search(r' d="([^"]+)"', _logo).group(1)
LOGO_VB = (1620.0, 1290.0)
# visual bounds of the silhouette inside its viewBox
LOGO_BOX = (65.0, 69.8, 1546.0, 1227.0)


def logo(cx, cy, width, rot=0, fill=LOGO, mirror=False, opacity=None):
    x0, y0, x1, y1 = LOGO_BOX
    s = width / (x1 - x0)
    mx = -1 if mirror else 1
    op = ' opacity="%s"' % opacity if opacity is not None else ""
    return ('<path transform="translate(%s %s) rotate(%s) scale(%s %s) translate(%s %s)" fill="%s" fill-rule="evenodd"%s d="%s"/>'
            % (fmt(cx), fmt(cy), fmt(rot), fmt(s * mx), fmt(s), fmt(-(x0 + x1) / 2), fmt(-(y0 + y1) / 2), fill, op, LOGO_D))


def rule(cx, cy, length, rot=0, color=RULE, w=0.35):
    return ('<rect transform="translate(%s %s) rotate(%s)" x="%s" y="%s" width="%s" height="%s" fill="%s"/>'
            % (fmt(cx), fmt(cy), fmt(rot), fmt(-length / 2), fmt(-w / 2), fmt(length), fmt(w), color))


def T(outlined, txt, x, y, size, weight="Regular", color=TXT, rot=0, track=0.0, anchor="middle", mirror=False):
    el = text_el(txt, x, y, size, "Montserrat-%s.ttf" % weight, color, rot, track, anchor, outlined=outlined)
    if mirror:
        # mirror the glyphs in place (for artwork that is read from the inside of the board)
        el = el.replace('transform="translate(%s %s) rotate(%s)' % (fmt(x), fmt(y), fmt(rot)),
                        'transform="translate(%s %s) rotate(%s) scale(-1 1)' % (fmt(x), fmt(y), fmt(rot)), 1)
    return el


def S(outlined, txt, x, y, size, color=TXT, rot=0, anchor="middle", mirror=False):
    """Serif italic for the descriptive lines (Cormorant Garamond Medium Italic)."""
    el = text_el(txt, x, y, size, "CormorantGaramond-MediumItalic.ttf", color, rot, 0.0, anchor, outlined=outlined)
    if mirror:
        el = el.replace('transform="translate(%s %s) rotate(%s)' % (fmt(x), fmt(y), fmt(rot)),
                        'transform="translate(%s %s) rotate(%s) scale(-1 1)' % (fmt(x), fmt(y), fmt(rot)), 1)
    return el


def backgrounds(info, color):
    """Flood the whole bleed area: one colour, so every panel (petals too) gets ink to the bleed."""
    return ['<path d="%s" fill="%s"/>' % (geom_d(info["bleed"]), color)]


# ------------------------------------------------------------------ box, outside

def box_outside(panels, info, outlined):
    o = backgrounds(info, BOARD)
    t = lambda *a, **k: o.append(T(outlined, *a, **k))
    cx = 404.06
    # LID FRONT (rot 180): assembled height h above its free edge -> sheet y = 135.08 + h
    y = lambda h: 135.08 + h
    o.append(logo(cx, y(116), 20, rot=180))
    t("MFC", cx, y(86), 10.5, "Regular", INK, 180, 0.62)
    o.append(rule(cx, y(80.5), 9, 180))
    t("FOR THOSE WHO CHASE", cx, y(73), 2.7, "Medium", TXT, 180, 0.42)
    t("THE GOOD MOMENTS.", cx, y(68.2), 2.7, "Medium", TXT, 180, 0.42)
    # LID TOP (rot 180, read from the front): front edge y=296.74, back edge y=528.82
    o.append(logo(cx, 430, 46, rot=180, fill="#c9c1b5"))
    t("MFC", cx, 384, 6.5, "Regular", INK, 180, 0.62)
    # FRONT LIP (rot 180): fold at y=958.39 is the bottom; thumb notch at the top centre
    t("GOOD MOMENTS AHEAD", cx, 958.39 + 6.5, 2.5, "Medium", TXT, 180, 0.48)
    # BACK (rot 0): top at y=528.82, floor fold at y=726.32
    t("MFC", cx, 645, 7, "Regular", INK, 0, 0.62)
    o.append(rule(cx, 651, 7))
    t("THE CATCH CAP", cx, 660, 2.5, "SemiBold", INK, 0, 0.32)
    o.append(S(outlined, "Made for sunny days and bigger stories.", cx, 666.5, 3.4, TXT, 0))
    o.append(logo(cx, 690, 11, 0))
    # SIDE WALLS: small mark near the floor, centred on the depth
    for side, x, r in (("L", 295.73 - 9, -90), ("R", 512.39 + 9, 90)):
        t("MFC", x, 842.4, 3.4, "Regular", INK, r, 0.62)
    # BOTTOM
    t("MFC", cx, 836, 5, "Regular", INK, 0, 0.62)
    o.append(S(outlined, "the catch cap – collectible edition", cx, 845, 3.4, TXT, 0))
    return layer("ARTWORK", "ARTWORK - outside print", "\n".join(o))


# ------------------------------------------------------------------ box, inside of the lid (reverse print)

def box_inside(panels, info, outlined):
    """Seen from inside: up = toward the lid front edge (-y), reading direction = -x."""
    o = backgrounds(info, BOARD_IN)
    t = lambda *a, **k: o.append(T(outlined, *a, mirror=True, **k))
    cx = 404.06
    f = 296.74                                   # lid front edge = top when the lid is open
    t("MFC", cx, f + 72, 9, "Regular", INK, 0, 0.62)
    o.append(rule(cx, f + 78, 9))
    t("FOR THOSE WHO CHASE", cx, f + 88, 2.7, "Medium", TXT, 0, 0.42)
    t("THE GOOD MOMENTS.", cx, f + 93, 2.7, "Medium", TXT, 0, 0.42)
    xl = 512.39 - 22                             # viewer's left on the inside = +x
    t("PREMIUM CAP", xl, f + 168, 2.5, "SemiBold", INK, 0, 0.32, "start")
    o.append('<rect x="%s" y="%s" width="6" height="0.35" fill="%s"/>' % (fmt(xl - 6), fmt(f + 171), RULE))
    o.append(S(outlined, "Made for sunny days", xl, f + 177.5, 3.2, TXT, 0, "start", mirror=True))
    o.append(S(outlined, "and bigger stories.", xl, f + 181.8, 3.2, TXT, 0, "start", mirror=True))
    return layer("ARTWORK", "ARTWORK - inside print (lid)", "\n".join(o))


# ------------------------------------------------------------------ insert

def insert_art(panels, info, outlined):
    o = backgrounds(info, BOARD_IN)
    t = lambda *a, **k: o.append(T(outlined, *a, **k))
    xl = 419.0
    t("THE CATCH CAP", xl, 133, 2.4, "SemiBold", INK, 0, 0.3, "start")
    o.append('<rect x="%s" y="135.6" width="5" height="0.35" fill="%s"/>' % (fmt(xl), RULE))
    o.append(S(outlined, "For those who chase", xl, 140.6, 2.9, TXT, 0, "start"))
    o.append(S(outlined, "the good moments.", xl, 144.3, 2.9, TXT, 0, "start"))
    o.append(logo(599.5, 136.5, 15, 0))
    for i, w in enumerate(("MORE", "SUNNY", "DAYS")):
        t(w, 424.5, 252 + i * 3.6, 1.9, "SemiBold", INK, 0, 0.32)
    o.append(rule(424.5, 264.5, 4))
    t("COLLECTIBLE CAP", xl, 304, 2.4, "SemiBold", INK, 0, 0.3, "start")
    o.append('<rect x="%s" y="306.6" width="5" height="0.35" fill="%s"/>' % (fmt(xl), RULE))
    o.append(S(outlined, "Made for sunny days", xl, 311.6, 2.9, TXT, 0, "start"))
    o.append(S(outlined, "and bigger stories.", xl, 315.3, 2.9, TXT, 0, "start"))
    return layer("ARTWORK", "ARTWORK - insert print", "\n".join(o))
