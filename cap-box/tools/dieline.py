"""Die-line (cut / crease / double crease) generated from panel polygons, and the
technical drawing for a box revision that has no source PDF (Rev I)."""
import math

from shapely.geometry import LineString, Polygon, MultiLineString
from shapely.ops import unary_union, linemerge

FOLD180 = {"innerlip", "sidelinerL", "sidelinerR", "lidinner", "tuck", "lidlinerL", "lidlinerR", "tab1", "tab2"}


def _lines(g):
    if g.is_empty:
        return []
    if isinstance(g, LineString):
        return [list(g.coords)]
    if hasattr(g, "geoms"):
        out = []
        for x in g.geoms:
            out.extend(_lines(x))
        return out
    return []


def dieline_from_panels(panels):
    """Return {'cut','crease','dbl','bleed'} polylines (sheet mm), like read_pdf()."""
    rings = []
    for p in panels:
        rings.append(LineString(list(p["poly"]) + [p["poly"][0]]))
        for h in p["holes"]:
            rings.append(LineString(list(h) + [h[0]]))
    edges = unary_union(rings)
    crease, dbl, hinge_zone = [], [], []
    for p in panels:
        if not p["hinge"]:
            continue
        a, b = p["hinge"]
        h = LineString([a, b])
        hinge_zone.append(h.buffer(0.08, cap_style=2))
        if p["id"] in FOLD180:
            dx, dy = b[0] - a[0], b[1] - a[1]
            n = math.hypot(dx, dy)
            nx, ny = -dy / n, dx / n
            for s in (-1, 1):
                dbl.append([[a[0] + s * nx, a[1] + s * ny], [b[0] + s * nx, b[1] + s * ny]])
        else:
            crease.append([list(a), list(b)])
    cut = edges.difference(unary_union(hinge_zone))
    cut = linemerge(cut) if not cut.is_empty else cut
    cut_lines = [pl for pl in _lines(cut) if LineString(pl).length > 0.2]
    return {"cut": cut_lines, "crease": crease, "dbl": dbl, "bleed": []}
