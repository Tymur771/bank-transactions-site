"""Box Rev E (folder 5, 2026-10-09) rebuilt from its own DXF + PDF labels.

Faces come from the DXF cut/crease network (each 180 double crease is replaced
by its mid line = the hinge); panel names come from the labels in the PDF;
parents, lifts and faces follow Rev H (same construction).  The sheet is moved
so its bottom panel sits where Rev H's bottom sits, so the 3D viewer can use
the same origin.
"""
import math
import os

import ezdxf
import pymupdf
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import polygonize, unary_union

from geometry import box_panels

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DXF = os.path.join(HERE, "..", "source", "MFC-box-RevE-glueless-Eflute.dxf")
SRC_PDF = os.path.join(HERE, "..", "source", "MFC-box-RevE-glueless-Eflute.pdf")

LABELS = {"BOTTOM": "bottom", "BACK": "back", "LIDTOP": "lidtop", "LIDFRONT": "lidfront",
          "LIDINNERFRONT": "lidinner", "TUCKFLAP": "tuck", "FRONTLIP": "lip", "INNERLIP": "innerlip",
          "SIDEWALL": "side", "SIDELINER": "sideliner", "LIDSIDE": "lidside", "LIDLINER": "lidliner",
          "EAR": "ear"}


def _dxf_lines(path):
    doc = ezdxf.readfile(path)
    out = {"CUT": [], "CREASE": [], "CREASE_DOUBLE": []}
    for e in doc.modelspace():
        lay = e.dxf.layer
        if lay not in out:
            continue
        if e.dxftype() == "LINE":
            out[lay].append([(e.dxf.start.x, -e.dxf.start.y), (e.dxf.end.x, -e.dxf.end.y)])
        elif e.dxftype() == "LWPOLYLINE":
            pts = [(x, -y) for x, y in e.get_points("xy")]
            if e.closed:
                pts.append(pts[0])
            out[lay].append(pts)
    return out


def _pair_doubles(lines):
    """Replace each pair of parallel lines 2 mm apart by their mid line."""
    segs = [LineString(l) for l in lines]
    used, mids = set(), []
    for i, a in enumerate(segs):
        if i in used:
            continue
        best = None
        for j, b in enumerate(segs):
            if j <= i or j in used:
                continue
            d = a.distance(b)
            if 1.5 < d < 2.5 and abs(a.length - b.length) < 3:
                best = j
                break
        if best is None:
            mids.append(lines[i])
            continue
        used.update((i, best))
        (ax, ay), (bx, by) = lines[i][0], lines[i][-1]
        (cx, cy), (dx, dy) = lines[best][0], lines[best][-1]
        if math.hypot(ax - cx, ay - cy) > math.hypot(ax - dx, ay - dy):
            cx, cy, dx, dy = dx, dy, cx, cy
        mids.append([((ax + cx) / 2, (ay + cy) / 2), ((bx + dx) / 2, (by + dy) / 2)])
    return mids


def _pdf_labels(path, cut_bbox_dxf):
    """Label texts with their centres mapped into DXF sheet coordinates."""
    page = pymupdf.open(path)[0]
    reds = []
    for d in page.get_drawings():
        c = d.get("color")
        if c and c[0] > 0.7 and c[1] < 0.4 and c[2] < 0.5:
            r = d["rect"]
            if r.x1 < page.rect.width * 0.8:
                reds.append(r)
    x0 = min(r.x0 for r in reds); x1 = max(r.x1 for r in reds)
    y0 = min(r.y0 for r in reds); y1 = max(r.y1 for r in reds)
    X0, Y0, X1, Y1 = cut_bbox_dxf
    sx, sy = (X1 - X0) / (x1 - x0), (Y1 - Y0) / (y1 - y0)
    out = []
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            txt = "".join(s["text"] for s in ln["spans"])
            key = "".join(ch for ch in txt.upper() if ch.isalpha())
            for k in LABELS:
                if key.startswith(k) and (k != "LIDSIDE" or key == "LIDSIDE") and (k != "INNERLIP" or "LIDINNER" not in key):
                    if k in ("LIDINNERFRONT",) or key.startswith(k):
                        bx = (ln["bbox"][0] + ln["bbox"][2]) / 2
                        by = (ln["bbox"][1] + ln["bbox"][3]) / 2
                        if bx > x1 + 5:
                            continue
                        out.append((LABELS[k], X0 + (bx - x0) * sx, Y0 + (by - y0) * sy, key))
                    break
    return out


def box_panels_rev_e():
    L = _dxf_lines(SRC_DXF)
    cut = L["CUT"]
    allpts = [p for l in cut for p in l]
    bbox = (min(p[0] for p in allpts), min(p[1] for p in allpts), max(p[0] for p in allpts), max(p[1] for p in allpts))
    mids = _pair_doubles(L["CREASE_DOUBLE"])
    net = unary_union([LineString(l) for l in cut + L["CREASE"] + mids])
    faces = [f for f in polygonize(net)]
    # closed cut loops inside a panel (slots, thumb hole) are holes, not panels
    loops = [Polygon(l) for l in cut if len(l) > 3 and l[0] == l[-1]]
    small = [f for f in faces if f.area < 600]
    big = [f for f in faces if f.area >= 600]
    labels = _pdf_labels(SRC_PDF, bbox)
    named = {}
    for f in big:
        hits = [lb for lb in labels if f.contains(Point(lb[1], lb[2]))]
        if not hits:
            raise RuntimeError("unlabelled face at %s" % (f.centroid,))
        named.setdefault(hits[0][0], []).append(f)
    bottom = named["bottom"][0]
    cx = bottom.centroid.x
    by_id = {}
    for base, fs in named.items():
        if base in ("side", "sideliner", "lidside", "lidliner"):
            for f in fs:
                by_id[base + ("L" if f.centroid.x < cx else "R")] = f
        elif base == "ear":
            back = named["back"][0]
            lip = named["lip"][0]
            for f in fs:
                s = "L" if f.centroid.x < cx else "R"
                if f.distance(back) < 0.5:
                    by_id["backear" + s] = f
                elif f.distance(lip) < 3 and f.centroid.y > bottom.bounds[3] - 5:
                    by_id["frontear" + s] = f
                else:
                    by_id["lidear" + s] = f
        else:
            by_id[base] = fs[0]
    # holes: slots in the bottom; the thumb hole cuts lip + inner lip
    holes = {k: [] for k in by_id}
    for f in small:
        for k, g in by_id.items():
            if k == "bottom" and Polygon(bottom.exterior).contains(f.centroid):
                holes[k].append(f)
    thumb = [lp for lp in loops if 300 < lp.area < 600]
    for k in ("lip", "innerlip"):
        if thumb:
            by_id[k] = by_id[k].difference(thumb[0].buffer(0.01))
    # move the sheet so the bottom centre sits on Rev H's bottom centre
    href = {p["id"]: p for p in box_panels()}
    hb = Polygon(href["bottom"]["poly"]).centroid
    dx, dy = hb.x - bottom.centroid.x, hb.y - bottom.centroid.y
    mv = lambda pts: [[round(x + dx, 2), round(y + dy, 2)] for x, y in pts]
    P = []
    for ref in box_panels():
        k = ref["id"]
        if k not in by_id:
            raise RuntimeError("Rev E has no panel " + k)
        g = by_id[k]
        if g.geom_type != "Polygon":
            g = max(g.geoms, key=lambda q: q.area)
        hinge = None
        if ref["parent"]:
            par = by_id[ref["parent"]]
            shared = g.buffer(0.05).intersection(par.buffer(0.05).exterior if hasattr(par, "exterior") else par.boundary)
            ls = [l for l in getattr(shared, "geoms", [shared]) if l.length > 1]
            ls = [l for l in ls if l.geom_type in ("LineString", "MultiLineString")]
            cs = [c for l in ls for q in getattr(l, "geoms", [l]) for c in q.coords]
            # straight hinge between the two farthest points
            a, b = max(((p, q) for p in cs for q in cs), key=lambda pq: math.dist(*pq))
            hinge = mv([a, b])
        P.append(dict(ref, poly=mv(list(g.simplify(0.02).exterior.coords)[:-1]),
                      holes=[mv(list(h.exterior.coords)[:-1]) for h in holes.get(k, [])],
                      hinge=hinge))
    return P, dict(bbox=bbox, shift=(dx, dy))


if __name__ == "__main__":
    P, info = box_panels_rev_e()
    for p in P:
        print(p["id"], p["parent"], p["hinge"], len(p["poly"]), len(p["holes"]))
