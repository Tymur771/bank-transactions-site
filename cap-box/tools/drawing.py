"""Technical die-line drawing for MFC cap box Rev I (step at the back of the side split)."""
import math

from shapely.geometry import Polygon
from shapely.ops import unary_union

from dieline import FOLD180

RED, BLUE, PURPLE, MAG, GREY, INK = "#e0102f", "#0a6fd6", "#5b2bd6", "#c03cc0", "#555555", "#111111"
LINER_FILL, EAR_FILL, CHANGE = "#f3edf9", "#e8f0fb", "#e85d1a"
CHANGED_J = {"bodytop", "lidtop", "toplockL", "toplockR"}
CHANGED = {"sideL", "sideR", "sidelinerL", "sidelinerR", "lidsideL", "lidsideR", "lidlinerL", "lidlinerR", "lidearL", "lidearR"}

LABELS = {
    "bottom": "BOTTOM", "back": "BACK", "lidtop": "LID TOP", "lidfront": "LID FRONT", "lip": "FRONT LIP",
    "innerlip": "INNER LIP (180 in, tabs)", "lidinner": "LID INNER FRONT (180 up)", "tuck": "TUCK FLAP (180 down)",
    "sideL": "SIDE WALL", "sideR": "SIDE WALL", "sidelinerL": "SIDE LINER (180 in, tabs lock in slots)",
    "sidelinerR": "SIDE LINER (180 in, tabs lock in slots)", "lidsideL": "LID SIDE", "lidsideR": "LID SIDE",
    "lidlinerL": "LID LINER (180)", "lidlinerR": "LID LINER (180)", "lidearL": "EAR", "lidearR": "EAR",
    "backearL": "EAR", "backearR": "EAR", "frontearL": "EAR", "frontearR": "EAR",
    "bodytop": "FIXED TOP", "toplockL": "TOP LOCK", "toplockR": "TOP LOCK",
}


def f1(v):
    return ("%.1f" % v).rstrip("0").rstrip(".")


def d_path(pts, close=False):
    return "M" + " L".join("%.2f %.2f" % (x, y) for x, y in pts) + (" Z" if close else "")


def text(x, y, s, size=4.2, color=INK, anchor="middle", rot=0, weight=400, spacing=0.0):
    return ('<text x="0" y="0" transform="translate(%.2f %.2f) rotate(%.2f)" font-family="Helvetica, Arial, sans-serif" '
            'font-size="%.2f" font-weight="%d" fill="%s" text-anchor="%s" letter-spacing="%.2f">%s</text>'
            % (x, y, rot, size, weight, color, anchor, spacing, s))


def dim_v(x, y0, y1, label, tick=4):
    return ('<path d="M%.2f %.2f V%.2f M%.2f %.2f h%.2f M%.2f %.2f h%.2f" stroke="%s" stroke-width="0.35" fill="none"/>'
            % (x, y0, y1, x - tick / 2, y0, tick, x - tick / 2, y1, tick, GREY)
            + text(x + 3, (y0 + y1) / 2 + 1.4, label, 3.6, GREY, "start"))


def dim_h(y, x0, x1, label, tick=4):
    return ('<path d="M%.2f %.2f H%.2f M%.2f %.2f v%.2f M%.2f %.2f v%.2f" stroke="%s" stroke-width="0.35" fill="none"/>'
            % (x0, y, x1, x0, y - tick / 2, tick, x1, y - tick / 2, tick, GREY)
            + text((x0 + x1) / 2, y + 6, label, 3.6, GREY))


def dim_aligned(a, b, off, label, color=CHANGE):
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy)
    nx, ny = -dy / n * off, dx / n * off
    A, B = (a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny)
    ang = math.degrees(math.atan2(dy, dx))
    if ang > 90 or ang < -90:
        ang += 180
    mx, my = (A[0] + B[0]) / 2 + nx / abs(off) * 3, (A[1] + B[1]) / 2 + ny / abs(off) * 3
    return ('<path d="M%.2f %.2f L%.2f %.2f M%.2f %.2f L%.2f %.2f M%.2f %.2f L%.2f %.2f" stroke="%s" stroke-width="0.35" fill="none"/>'
            % (A[0], A[1], B[0], B[1], a[0], a[1], A[0], A[1], b[0], b[1], B[0], B[1], color)
            + text(mx, my + 1.3, label, 3.8, color, rot=ang, weight=700))


def side_view(ox, oy, sc, rev_i, rev_h_line):
    """Closed box seen from the left, scale sc (mm per mm). Front at the left."""
    W, H = 233.6, 199.0

    def P(d_back, h):          # d from the back outside face, h from the floor
        return (ox + (W - d_back) * sc, oy + (H - h) * sc)
    s = rev_i
    out = []
    out.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="none" stroke="%s" stroke-width="0.3"/>'
               % (ox, oy, W * sc, H * sc, "#999"))
    # base side wall (Rev I)
    base = [P(0, 0), P(0, s["wall_top"]), P(s["step"], s["wall_top"]), P(225.95, s["base_front"]), P(225.95, 24.92),
            P(W, 24.92), P(W, 0)]
    out.append('<path d="%s" fill="#efe9de" stroke="%s" stroke-width="0.5"/>' % (d_path(base, True), INK))
    lid_front_h = 39.92
    lid = [P(0, 199), P(W, 199), P(W, lid_front_h), P(225.46, lid_front_h), P(s["lid_end"], 197.5), P(0, 197.5)]
    out.append('<path d="%s" fill="#2a2d31" fill-opacity="0.85" stroke="%s" stroke-width="0.5"/>' % (d_path(lid, True), INK))
    # insert profile (Rev C) inside: tray, 65 deg panel, top flap, tube back wall
    T = 1.5
    foot = W - T - 2 * T - 0.3 - 83.6           # depth from back of the panel foot (approx.)
    top_d = foot - 217 * math.cos(math.radians(65))
    ins = [P(W - T - 3.3, T), P(foot, T), P(top_d, T + 196.7), P(top_d - 48, T + 196.7), P(top_d - 48, T)]
    out.append('<path d="%s" fill="none" stroke="%s" stroke-width="0.6" stroke-dasharray="2 1.2"/>' % (d_path(ins), BLUE))
    # Rev H split for comparison
    out.append('<path d="%s" fill="none" stroke="%s" stroke-width="0.5" stroke-dasharray="1.5 1.5"/>'
               % (d_path([P(*rev_h_line[0]), P(*rev_h_line[1])]), "#999"))
    out.append(text(ox + W * sc / 2, oy - 6, "SIDE VIEW, CLOSED (scale 1:%d) - front at left" % round(1 / sc), 4.2, INK, weight=700))
    out.append(text(*P(s["step"] / 2, s["wall_top"] - 9), "STEP %s" % f1(s["step"]), 3.2, CHANGE, weight=700))
    out.append(text(*P(150, 120), "insert", 3.2, BLUE))
    out.append(text(*P(115, 70), "Rev H split", 2.8, "#888", rot=-35))
    return "\n".join(out)


def write_drawing(panels, raw, info, path_svg, sheet_poly, bleed_poly, rev="I"):
    minx, miny, maxx, maxy = sheet_poly.bounds
    page_w, page_h = 1140.0, 1080.0
    ox, oy = 40 - minx, 70 - miny          # place the sheet like the original drawing
    body = []
    # fills for liners and ears
    for p in panels:
        if p["id"] in FOLD180 and p["id"] not in ("tuck",):
            body.append('<path d="%s" fill="%s"/>' % (d_path(p["poly"], True), LINER_FILL))
        if p["id"].startswith(("backear", "frontear", "lidear", "toplock")):
            body.append('<path d="%s" fill="%s"/>' % (d_path(p["poly"], True), EAR_FILL))
    # changed panels outline
    changed = CHANGED | (CHANGED_J if rev == "J" else set())
    ch = unary_union([Polygon(p["poly"]) for p in panels if p["id"] in changed]).buffer(5, join_style=2)
    for g in getattr(ch, "geoms", [ch]):
        body.append('<path d="%s" fill="none" stroke="%s" stroke-width="0.5" stroke-dasharray="4 2" opacity="0.7"/>'
                    % (d_path(list(g.exterior.coords), True), CHANGE))
    bl = bleed_poly
    for g in getattr(bl, "geoms", [bl]):
        body.append('<path d="%s" fill="none" stroke="%s" stroke-width="0.3" stroke-dasharray="1 1.2"/>'
                    % (d_path(list(g.exterior.coords), True), MAG))
    body.append('<path d="%s" fill="none" stroke="%s" stroke-width="0.4" stroke-dasharray="5 2.5"/>'
                % (" ".join(d_path(pl) for pl in raw["crease"]), BLUE))
    body.append('<path d="%s" fill="none" stroke="%s" stroke-width="0.4" stroke-dasharray="5 2.5"/>'
                % (" ".join(d_path(pl) for pl in raw["dbl"]), PURPLE))
    body.append('<path d="%s" fill="none" stroke="%s" stroke-width="0.45" stroke-linejoin="round"/>'
                % (" ".join(d_path(pl) for pl in raw["cut"]), RED))
    # labels
    rot = {"sideL": -90, "sideR": -90, "lidsideL": -90, "lidsideR": -90}
    for p in panels:
        if p["id"] not in LABELS:
            continue
        poly = Polygon(p["poly"])
        c = poly.representative_point() if p["id"] != "lip" else type(poly.centroid)(350, 973)
        big = poly.area > 15000
        r = rot.get(p["id"], 0)
        if p["id"].startswith(("sideliner", "lidliner", "lidear", "backear", "frontear")):
            r = -90 if p["id"].endswith("L") else 90
            if p["id"].startswith("sideliner") or p["id"].startswith("lidliner"):
                a, b = p["hinge"]
                r = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
                r = r - 180 if r > 90 else r + 180 if r < -90 else r
        col = PURPLE if p["id"] in FOLD180 else BLUE if "ear" in p["id"] else INK
        body.append(text(c.x, c.y, LABELS[p["id"]], 7 if big else 3.6, col, rot=r, spacing=0.6 if big else 0.2))
    # Rev I dimensions
    L = {p["id"]: p for p in panels}
    bl_a, bl_b = info["base_line"]
    body.append(dim_v(bl_a[0] - 14, 726.32, bl_a[1], "%s STEP" % f1(info["step"])))
    body.append(dim_h(712, bl_a[0], 295.73, "%s wall at step" % f1(info["wall_top"])))
    body.append(text(bl_a[0] + 26, bl_a[1] + 40, "slope %s deg" % f1(info["slope_deg"]), 3.8, CHANGE, rot=info["slope_deg"] + 0.0, weight=700))
    la, lb = info["lid_line"]
    body.append(dim_v(306, la[1], 528.82, f1(528.82 - la[1])))
    # right-hand vertical dims (unchanged)
    x = maxx + 40
    ys = [70.0, 113.08, 135.08, 296.74, 528.82, 726.32, 958.39, 987.14, 1017.6]
    names = ["43.1", "22", "161.7", "232.1", "197.5", "232.1", "28.8", "27.2"]
    for (y0, y1), nm in zip(zip(ys[:-1], ys[1:]), names):
        body.append(dim_v(x, y0, y1, nm))
    body.append(dim_v(x + 30, miny, maxy, "%s overall" % f1(maxy - miny)))
    body.append(dim_h(maxy + 18, 295.73, 512.39, "216.7"))
    body.append(dim_h(maxy + 30, minx, maxx, "%s overall" % f1(maxx - minx)))
    sheet = "".join(body)
    # title block
    tx = page_w - 262
    t = []
    t.append(text(tx, 72, "MFC - CAP BOX", 11, INK, "start", weight=400))
    t.append(text(tx, 84, ("Rev J - GLUELESS, STEP %s mm, LID HINGE AT THE END OF THE STEP" if rev == "J" else
                           "Rev I - GLUELESS, short tuck, STEP %s mm at the back of the side split") % f1(info["step"]), 4.6, CHANGE, "start"))
    lines = [
        "Material: E-flute litho-laminated board, caliper ~1.5 mm",
        "Scale 1:1 - units mm - view from OUTSIDE (print side)",
        "All creases fold away from viewer", "",
        "Closed box (outside approx.): 218.2 W x 233.6 D x 199 H  (same as Rev H)",
        "Clear inside (between liners): 206 W x 226 D x 196 H (Rev C insert fits)",
        "Sheet size: %s x %s" % (f1(maxx - minx), f1(maxy - miny)),
        "Side seam gap: %s mm square to the seam (as Rev H)" % f1(4.87), "",
        "CHANGE vs Rev H (orange dashed outline):",
        "10. The side split no longer starts in the back top corner.",
        "    Base side wall keeps full height %s for %s mm from the back," % (f1(info["wall_top"]), f1(info["step"])),
        "    then slopes %s deg down to the front (front lip unchanged)." % f1(info["slope_deg"]),
        "    The base now hides the Rev C insert (top front corner ~53 mm",
        "    from the back at ~197 mm) when the lid is open.",
        "11. Lid side ends %s mm from the hinge; lid top is cut free" % f1(info["lid_end"]),
        "    over the step. Lid front, lid ears unchanged.",
        "12. Side liners, lid liners and lid ears re-mirrored about the",
        "    new 180 fold lines; liner tabs still land in the same 6 slots.",
        "13. Base front height at the seam %s (was 33.6)." % f1(info["base_front"]),
    ] + ([
        "14. Rev J: the top is split by a crease %s mm from the back (where" % f1(info.get("fixed_top", 0)),
        "    the lid side starts). The back part is a FIXED TOP over the step;",
        "    the lid hinges on that crease, so the lid side turns about its",
        "    own tip and stays on the base step when the lid opens.",
        "15. Fixed top has 2 side lock flaps (%s mm) that drop inside the" % f1(info.get("toplock", 0)),
        "    side walls over the step and hold it without glue.",
    ] if rev == "J" else []) + ["",
        "NOTES - NO GLUE ANYWHERE (as Rev H)",
        "1. Back and front lip fold up from BOTTOM.",
        "2. Side-wall ears fold in; side walls go up, ears sit BEHIND the",
        "   front lip. Inner lip folds 180 down over them, tabs into slots.",
        "3. Back ears fold in; side LINER folds 180 over the slope edge,",
        "   covers them, 2 tabs push into the bottom slots.",
        ("4. Fixed top folds over the step, its 2 lock flaps drop inside the side walls;"
         if rev == "J" else "4. Lid hinges on the back top edge: the top is one panel."),
    ] + (["   the lid hinges on the crease at the front edge of the fixed top."] if rev == "J" else []) + [
        "5. Lid front down, lid sides down, lid liners 180 over the slope",
        "   edge; their ears go in BEHIND the lid front.",
        "6. Lid inner front folds 180 up and traps those ears; the tuck",
        "   folds 180 down and goes in behind the inner lip.",
        "7. Draft for white sample - printer to confirm crease and slot",
        "   allowances for their board before die.",
        "8. E-flute: run flutes parallel to the long side folds.", "",
        "Rev %s - glueless - generated from Rev H geometry" % rev,
    ]
    for i, ln in enumerate(lines):
        col = CHANGE if ln.startswith(("CHANGE", "10.", "11.", "12.", "13.", "14.", "15.", "    ")) and 9 <= i <= 28 else INK
        t.append(text(tx, 98 + i * 6.2, ln, 3.7, col, "start"))
    ly = 98 + len(lines) * 6.2 + 8
    t.append(text(tx, ly, "LEGEND", 4.4, INK, "start", weight=700))
    leg = [(RED, "", "Cut (incl. 6 lock slots in bottom)"), (BLUE, "5 2.5", "Crease / fold"),
           (PURPLE, "5 2.5", "Double crease 2 mm apart (180 folds)"), (MAG, "1 1.2", "Bleed +3 mm for artwork"),
           (CHANGE, "4 2", "Changed vs Rev H")]
    for i, (c, da, nm) in enumerate(leg):
        y = ly + 8 + i * 7
        t.append('<path d="M%.1f %.1f h16" stroke="%s" stroke-width="0.6" stroke-dasharray="%s"/>' % (tx, y - 1.2, c, da or "none"))
        t.append(text(tx + 22, y, nm, 3.7, INK, "start"))
    t.append(side_view(tx, ly + 60, 0.5, info, [(1.54 + 1.5, 191.63 + 1.5), (225.95 + 1.5, 33.63 + 1.5)]))
    svg = ('<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="%dmm" height="%dmm" viewBox="0 0 %d %d">\n'
           '<rect width="100%%" height="100%%" fill="#ffffff"/>\n<g transform="translate(%.2f %.2f)">%s</g>\n%s\n</svg>\n'
           % (page_w, page_h, page_w, page_h, ox, oy, sheet, "\n".join(t)))
    open(path_svg, "w").write(svg)
    return svg
