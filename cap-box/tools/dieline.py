"""Die-line (cut / crease / double crease) generated from panel polygons, and the
technical drawing for a box revision that has no source PDF (Rev I)."""
import math

from shapely.geometry import LineString, Polygon, MultiLineString
from shapely.ops import unary_union, linemerge

FOLD180 = {"innerlip", "sidelinerL", "sidelinerR", "lidinner", "tuck", "lidlinerL", "lidlinerR", "tab1", "tab2", "tophemL", "tophemR"}


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
        # a crease only exists where BOTH panels have material along the hinge
        par = next((q for q in panels if q["id"] == p["parent"]), None)
        if par is not None:
            shared = h.intersection(Polygon(p["poly"]).buffer(0.06)).intersection(Polygon(par["poly"], par["holes"]).buffer(0.06))
            pieces = [list(g.coords) for g in getattr(shared, "geoms", [shared]) if isinstance(g, LineString) and g.length > 0.5]
        else:
            pieces = [[list(a), list(b)]]
        for pa, pb in ((pc[0], pc[-1]) for pc in pieces):
            if p["id"] in FOLD180:
                dx, dy = pb[0] - pa[0], pb[1] - pa[1]
                n = math.hypot(dx, dy)
                nx, ny = -dy / n, dx / n
                for s in (-1, 1):
                    dbl.append([[pa[0] + s * nx, pa[1] + s * ny], [pb[0] + s * nx, pb[1] + s * ny]])
            else:
                crease.append([list(pa), list(pb)])
    cut = edges.difference(unary_union(hinge_zone))
    cut = linemerge(cut) if not cut.is_empty else cut
    cut_lines = [pl for pl in _lines(cut) if LineString(pl).length > 0.2]
    return {"cut": cut_lines, "crease": crease, "dbl": dbl, "bleed": []}
