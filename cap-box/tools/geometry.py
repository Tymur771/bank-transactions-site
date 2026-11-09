"""Panel geometry for the MFC cap box (Rev H) and cap insert (Rev C).

All coordinates are in millimetres, in the coordinate system of the source
PDF drawings (x to the right, y down, viewed from the PRINT side).
Every number below was read from the vector paths of the source PDFs
(see extract_pdf.py); nothing is eyeballed from the picture.

Each panel:
  id      unique id
  name    human name (RU)
  sheet   'box' | 'insert'
  parent  parent panel id (None for the root)
  poly    outline polygon (list of [x, y])
  holes   list of hole polygons
  hinge   [[x1, y1], [x2, y2]] fold line shared with the parent
  lift    only for folds that land on / behind other board (None otherwise):
          for 180-degree folds, the number of board layers the panel has to
          clear (0 = lands straight on the inside of its parent, 1 = over an
          ear, 2 = folds toward the print side); -1 = 90-degree ear that has to
          sit one board thickness inside the neighbouring wall
  face    what the PRINT side of this panel is when the box is assembled:
          'out' (seen from outside), 'in' (seen inside when opened), 'hidden'
  rot     rotation (deg, SVG convention) that makes artwork read upright on
          the assembled box; None = no fixed orientation
"""
import json
import math
import pymupdf
from shapely.geometry import LineString, Polygon, MultiPoint, Point
from shapely.ops import unary_union, polygonize, snap

K = 25.4 / 72.0
CUT = (0.878, 0.063, 0.184)
CREASE = (0.039, 0.435, 0.839)
DBL = (0.357, 0.169, 0.839)
BLEED = (0.753, 0.235, 0.753)


def _same(c, ref):
    return c is not None and all(abs(a - b) < 0.01 for a, b in zip(c, ref))


def read_pdf(path):
    """Return dict kind -> list of polylines (each a list of [x, y] in mm)."""
    page = pymupdf.open(path)[0]
    out = {"cut": [], "crease": [], "dbl": [], "bleed": []}
    for d in page.get_drawings():
        col = d.get("color")
        kind = None
        for k, ref in (("cut", CUT), ("crease", CREASE), ("dbl", DBL), ("bleed", BLEED)):
            if _same(col, ref):
                kind = k
        if kind is None:
            continue
        for it in d["items"]:
            if it[0] == "l":
                out[kind].append([[it[1].x * K, it[1].y * K], [it[2].x * K, it[2].y * K]])
            elif it[0] == "c":
                pts = []
                p0, p1, p2, p3 = it[1:5]
                for i in range(9):
                    t = i / 8
                    x = (1-t)**3*p0.x + 3*(1-t)**2*t*p1.x + 3*(1-t)*t**2*p2.x + t**3*p3.x
                    y = (1-t)**3*p0.y + 3*(1-t)**2*t*p1.y + 3*(1-t)*t**2*p2.y + t**3*p3.y
                    pts.append([x * K, y * K])
                out[kind].append(pts)
            elif it[0] == "re":
                r = it[1]
                x0, y0, x1, y1 = r.x0 * K, r.y0 * K, r.x1 * K, r.y1 * K
                out[kind].append([[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]])
    return out


def mirror(poly, axis):
    return [[2 * axis - x, y] for x, y in poly]


def arc(cx, cy, r, a0, a1, n=12):
    return [[cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))] for i in range(n + 1)]


# --------------------------------------------------------------------------
# BOX  (Rev H, glueless, E-flute).  Bottom panel x 295.73..512.39
# --------------------------------------------------------------------------
BX = 404.06            # centre line of the box sheet
BXM = 808.12           # mirror sum (295.73 + 512.39)


def box_panels():
    P = []

    def add(**kw):
        kw.setdefault("holes", [])
        kw.setdefault("lift", None)
        kw.setdefault("rot", None)
        kw["sheet"] = "box"
        P.append(kw)

    slots = [[[299.06, 775.30], [301.56, 775.30], [301.56, 807.29], [299.06, 807.29]],
             [[299.06, 863.48], [301.56, 863.48], [301.56, 895.48], [299.06, 895.48]],
             [[506.56, 775.30], [509.06, 775.30], [509.06, 807.29], [506.56, 807.29]],
             [[506.56, 863.48], [509.06, 863.48], [509.06, 895.48], [506.56, 895.48]],
             [[333.89, 952.56], [365.89, 952.56], [365.89, 955.06], [333.89, 955.06]],
             [[442.22, 952.56], [474.22, 952.56], [474.22, 955.06], [442.22, 955.06]]]
    add(id="bottom", name="Дно", parent=None,
        poly=[[295.73, 726.32], [512.39, 726.32], [512.39, 958.39], [295.73, 958.39]],
        holes=slots, hinge=None, face="out", rot=0)

    # ---- front lip + inner lip (thumb notch r=12 at 404.06, 987.14)
    notch_top = arc(404.06, 987.14, 12, 0, -180, 16)          # from right, over the top, to left
    add(id="lip", name="Передний борт", parent="bottom",
        poly=[[294.98, 958.39], [513.13, 958.39], [513.13, 987.14]] + notch_top + [[294.98, 987.14]],
        hinge=[[294.98, 958.39], [513.13, 958.39]], face="out", rot=180)
    notch_bot = arc(404.06, 987.14, 12, 180, 0, 16)            # from left, under, to right
    add(id="innerlip", name="Внутренний борт (180°)", parent="lip",
        poly=[[294.98, 987.14]] + notch_bot + [[513.13, 987.14], [513.13, 990.97], [510.85, 990.97],
              [510.85, 1014.35], [473.22, 1014.35], [471.72, 1017.60], [444.72, 1017.60],
              [443.22, 1014.35], [364.89, 1014.35], [363.39, 1017.60], [336.39, 1017.60],
              [334.89, 1014.35], [297.27, 1014.35], [297.27, 990.97], [294.98, 990.97]],
        hinge=[[294.98, 987.14], [513.13, 987.14]], lift=1, face="in", rot=None)

    # ---- side walls, their liners and front ears (left; right mirrored)
    side = [[295.73, 726.32], [103.02, 726.32], [104.10, 727.86], [262.10, 952.27],
            [270.81, 952.27], [270.81, 956.10], [295.73, 956.10]]
    liner = [[104.10, 727.86], [262.10, 952.27], [251.27, 982.48], [196.87, 962.99],
             [194.36, 965.55], [168.95, 956.44], [168.63, 952.88], [113.85, 933.25],
             [111.34, 935.81], [85.92, 926.70], [85.60, 923.14], [40.00, 906.80]]
    fear = [[293.99, 956.10], [271.60, 956.10], [271.60, 983.10], [274.60, 986.10],
            [290.99, 986.10], [293.99, 983.10]]
    bear = [[295.73, 724.03], [259.73, 724.03], [255.73, 720.03], [255.73, 569.60],
            [259.73, 562.78], [295.73, 538.52]]
    for s, m in (("L", lambda p: p), ("R", lambda p: mirror(p, BXM / 2))):
        sgn = 1 if s == "L" else -1
        add(id="side" + s, name="Боковая стенка " + ("левая" if s == "L" else "правая"), parent="bottom",
            poly=m(side), hinge=m([[295.73, 726.32], [295.73, 956.10]]), face="out", rot=-90 * sgn)
        add(id="sideliner" + s, name="Вкладыш стенки (180°)", parent="side" + s,
            poly=m(liner), hinge=m([[104.10, 727.86], [262.10, 952.27]]), lift=1, face="in")
        add(id="frontear" + s, name="Ушко стенки", parent="side" + s,
            poly=m(fear), hinge=m([[293.99, 956.10], [271.60, 956.10]]), lift=0, face="hidden")

    # ---- back + back ears
    add(id="back", name="Задняя стенка", parent="bottom",
        poly=[[295.73, 528.82], [512.39, 528.82], [512.39, 726.32], [295.73, 726.32]],
        hinge=[[295.73, 726.32], [512.39, 726.32]], face="out", rot=0)
    for s, m in (("L", lambda p: p), ("R", lambda p: mirror(p, BXM / 2))):
        add(id="backear" + s, name="Ушко задней стенки", parent="back",
            poly=m(bear), hinge=m([[295.73, 538.52], [295.73, 724.03]]), lift=-1, face="hidden")

    # ---- lid
    add(id="lidtop", name="Крышка — верх", parent="back",
        poly=[[295.73, 296.74], [512.39, 296.74], [512.39, 528.82], [295.73, 528.82]],
        hinge=[[295.73, 528.82], [512.39, 528.82]], face="out", rot=180)
    add(id="lidfront", name="Крышка — перед", parent="lidtop",
        poly=[[294.98, 135.08], [513.13, 135.08], [513.13, 296.74], [294.98, 296.74]],
        hinge=[[294.98, 296.74], [513.13, 296.74]], face="out", rot=180)
    add(id="lidinner", name="Внутренний перед крышки (180°)", parent="lidfront",
        poly=[[294.98, 135.08], [513.13, 135.08], [513.13, 131.25], [508.56, 131.25],
              [508.56, 113.08], [299.56, 113.08], [299.56, 131.25], [294.98, 131.25]],
        hinge=[[294.98, 135.08], [513.13, 135.08]], lift=1, face="in")
    tuck = ([[506.27, 113.08], [506.27, 75.0]] + arc(501.27, 75.0, 5, 0, -90, 6)[1:] +
            arc(306.85, 75.0, 5, -90, -180, 6) + [[301.85, 113.08]])
    add(id="tuck", name="Язычок (180°)", parent="lidinner",
        poly=tuck, hinge=[[301.85, 113.08], [506.27, 113.08]], lift=2, face="hidden")

    lside = [[295.73, 299.03], [137.89, 299.03], [137.89, 302.86], [138.15, 303.36],
             [293.44, 523.94], [295.73, 527.19]]
    lliner = [[293.44, 523.94], [81.70, 448.10], [134.16, 301.66], [138.15, 303.36]]
    lear = [[81.87, 447.62], [133.89, 302.40], [104.71, 291.95], [100.87, 293.76],
            [50.87, 433.33], [52.69, 437.17]]
    for s, m in (("L", lambda p: p), ("R", lambda p: mirror(p, BXM / 2))):
        sgn = 1 if s == "L" else -1
        add(id="lidside" + s, name="Крышка — бок", parent="lidtop",
            poly=m(lside), hinge=m([[295.73, 299.03], [295.73, 527.19]]), face="out", rot=90 * sgn)
        add(id="lidliner" + s, name="Вкладыш крышки (180°)", parent="lidside" + s,
            poly=m(lliner), hinge=m([[138.15, 303.36], [293.44, 523.94]]), lift=0, face="in")
        add(id="lidear" + s, name="Ушко крышки", parent="lidliner" + s,
            poly=m(lear), hinge=m([[81.87, 447.62], [133.89, 302.40]]), lift=0, face="hidden")
    return P


# --------------------------------------------------------------------------
# INSERT (Rev C).  Main panel x 411.77..613.78, centre 512.775
# --------------------------------------------------------------------------
IXM = 1025.55


def insert_petals(raw):
    """Arch petals: polygonize the cut/crease network inside the arch."""
    lines = []
    for kind in ("cut", "crease"):
        for pl in raw[kind]:
            ls = LineString(pl)
            lines.append(ls)
    area = Polygon([(425, 130), (600, 130), (600, 290), (425, 290)])
    sel = [l for l in lines if l.within(area)]
    pts = MultiPoint([c for l in sel for c in l.coords])
    sel = [snap(l, pts, 0.35) for l in sel]
    faces = list(polygonize(unary_union(sel)))
    circle = [f for f in faces if f.centroid.distance(Point(512.78, 211.08)) < 1 and 250 < f.area < 400]
    petals = [f for f in faces if 150 < f.area < 400 and f not in circle]
    band = unary_union([f for f in faces if f.area > 0 and f not in circle]).buffer(0.05).buffer(-0.05)
    crease_r = [[512.78, 155.02], [520.16, 155.02], [533.37, 159.66], [546.01, 167.73], [556.47, 178.60],
                [563.55, 191.82], [568.18, 211.28], [570.11, 233.19], [569.48, 260.19]]
    crease_l = mirror(crease_r, IXM / 2)
    segs = []
    for c in (crease_r, crease_l):
        for a, b in zip(c[:-1], c[1:]):
            segs.append((a, b))
    out = []
    for i, f in enumerate(sorted(petals, key=lambda f: (f.centroid.x - 512.78) * 1000 + f.centroid.y)):
        f = f.simplify(0.08)
        hs = [s for s in segs if f.exterior.distance(Point((s[0][0] + s[1][0]) / 2, (s[0][1] + s[1][1]) / 2)) < 0.3]
        if len(hs) == 2:   # centre petal: two collinear halves
            xs = sorted([hs[0][0][0], hs[0][1][0], hs[1][0][0], hs[1][1][0]])
            hinge = [[xs[0], 155.02], [xs[-1], 155.02]]
        else:
            hinge = [list(hs[0][0]), list(hs[0][1])]
        out.append(dict(poly=[list(map(lambda v: round(v, 2), c)) for c in list(f.exterior.coords)[:-1]], hinge=hinge))
    circ = [list(map(lambda v: round(v, 2), c)) for c in list(circle[0].simplify(0.05).exterior.coords)[:-1]]
    bandpoly = [list(map(lambda v: round(v, 2), c)) for c in list(band.simplify(0.05).exterior.coords)[:-1]]
    return out, circ, bandpoly


def insert_panels(raw):
    P = []

    def add(**kw):
        kw.setdefault("holes", [])
        kw.setdefault("lift", None)
        kw.setdefault("rot", None)
        kw["sheet"] = "insert"
        P.append(kw)

    petals, circle, band = insert_petals(raw)
    add(id="main", name="Основная панель", parent=None,
        poly=[[411.77, 120.18], [613.78, 120.18], [613.78, 337.19], [411.77, 337.19]],
        holes=[band, circle], hinge=None, face="out", rot=0)
    add(id="topflap", name="Верхний клапан (к задней стенке)", parent="main",
        poly=[[411.77, 72.18], [613.78, 72.18], [613.78, 120.18], [411.77, 120.18]],
        hinge=[[411.77, 120.18], [613.78, 120.18]], face="out", rot=0)
    add(id="tray", name="Нижний клапан (на дно)", parent="main",
        poly=[[411.77, 337.19], [613.78, 337.19], [613.78, 420.79], [411.77, 420.79]],
        hinge=[[411.77, 337.19], [613.78, 337.19]], face="out", rot=0)
    for i, p in enumerate(petals):
        add(id="petal%d" % i, name="Лепесток арки", parent="main", poly=p["poly"], hinge=p["hinge"], face="out")

    w1 = [[613.78, 121.29], [613.78, 337.19], [740.40, 278.15], [682.64, 154.28], [657.70, 100.81]]
    f1 = [[613.78, 121.29], [657.70, 100.81], [643.82, 73.03], [613.78, 72.18]]
    w2 = [[740.40, 278.15], [832.40, 235.24], [773.28, 112.01], [682.64, 154.28]]
    w3r = [[832.40, 235.24], [876.38, 214.74], [870.35, 189.97], [897.54, 177.29], [912.63, 197.83],
           [956.16, 177.54], [840.64, 80.60], [825.99, 87.43], [832.03, 112.21], [804.84, 124.88],
           [789.74, 104.34], [773.28, 112.01]]
    tab1 = [[804.84, 124.88], [789.74, 104.34], [825.99, 87.43], [832.03, 112.21]]
    tab2 = [[870.35, 189.97], [876.38, 214.74], [912.63, 197.83], [897.54, 177.29]]
    tip = find_curve(raw, [877.23, 52.56], [863.14, 53.79])
    w4r = [[956.16, 177.54], [985.09, 143.06]] + tip + [[840.64, 80.60]]
    w3l = [[192.69, 235.03], [148.71, 214.52], [154.75, 189.75], [127.55, 177.07], [112.45, 197.61],
           [68.93, 177.32], [184.45, 80.39], [199.10, 87.22], [193.07, 111.99], [220.26, 124.67],
           [235.35, 104.12], [250.45, 111.16]]
    # the left wing is NOT an exact mirror of the right one (W2/W3/W4 differ by
    # up to ~1.8 mm in the drawing), so its own coordinates are used
    w2l = [[285.15, 278.15], [192.69, 235.03], [250.45, 111.16], [342.91, 154.28]]
    tipl = find_curve(raw, [147.87, 52.34], [161.96, 53.57])
    w4l = [[68.93, 177.32], [40.00, 142.84]] + tipl + [[184.45, 80.39]]
    m = lambda p: mirror(p, IXM / 2)
    for s in ("R", "L"):
        mm = (lambda p: p) if s == "R" else m
        add(id="w1" + s, name="Крыло — боковая стенка", parent="main", poly=mm(w1),
            hinge=mm([[613.78, 121.29], [613.78, 337.19]]), face="hidden")
        add(id="f1" + s, name="Клапан крыла", parent="w1" + s, poly=mm(f1),
            hinge=mm([[613.78, 121.29], [657.70, 100.81]]), face="hidden")
        add(id="w2" + s, name="Крыло — задняя стенка трубы", parent="w1" + s, poly=(w2 if s == "R" else w2l),
            hinge=mm([[740.40, 278.15], [682.64, 154.28]]), face="hidden")
        add(id="w3" + s, name="Крыло — внутренняя стенка", parent="w2" + s,
            poly=(w3r if s == "R" else w3l),
            hinge=([[832.40, 235.24], [773.28, 112.01]] if s == "R" else [[192.69, 235.03], [250.45, 111.16]]),
            face="hidden")
        add(id="w4" + s, name="Крыло — замок", parent="w3" + s, poly=(w4r if s == "R" else w4l),
            hinge=([[956.16, 177.54], [840.64, 80.60]] if s == "R" else [[68.93, 177.32], [184.45, 80.39]]),
            face="hidden")
    add(id="tab1", name="Замковый язычок", parent="w3R", poly=tab1,
        hinge=[[804.84, 124.88], [832.03, 112.21]], lift=2, face="hidden")
    add(id="tab2", name="Замковый язычок", parent="w3R", poly=tab2,
        hinge=[[870.35, 189.97], [897.54, 177.29]], lift=2, face="hidden")
    return P


def find_curve(raw, a, b, tol=0.05):
    """Chain cut segments into the curve running from point a to point b."""
    segs = [pl for pl in raw["cut"]]
    path = [list(a)]
    cur = a
    used = set()
    for _ in range(400):
        if math.dist(cur, b) < tol:
            return [[round(x, 2), round(y, 2)] for x, y in path]
        for i, pl in enumerate(segs):
            if i in used:
                continue
            if math.dist(pl[0], cur) < tol:
                seq = pl
            elif math.dist(pl[-1], cur) < tol:
                seq = pl[::-1]
            else:
                continue
            used.add(i)
            path.extend(seq[1:])
            cur = seq[-1]
            break
        else:
            break
    raise ValueError("curve not found %r %r" % (a, b))


def r2(v):
    if isinstance(v, float):
        return round(v, 2)
    if isinstance(v, list):
        return [r2(x) for x in v]
    if isinstance(v, dict):
        return {k: r2(x) for k, x in v.items()}
    return v
