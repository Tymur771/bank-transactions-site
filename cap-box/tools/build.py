"""Build everything for the MFC cap box from the two source PDFs.

    python3 cap-box/tools/build.py

Outputs (all in cap-box/):
  data/geometry.json                    panel geometry used by the 3D viewer
  print/MFC-box-RevH_design-template.svg|pdf     artwork template for the box
  print/MFC-insert-RevC_design-template.svg|pdf  artwork template for the insert
  design/MFC-box_concept.svg, design/MFC-insert_concept.svg   draft concept (editable text)
  index.html                            3D assembly viewer (built from tools/viewer.src.html)
"""
import json
import math
import os
import sys

import pymupdf
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from geometry import read_pdf, box_panels, box_panels_rev_i, box_panels_rev_j, box_panels_rev_k, box_panels_rev_l, box_panels_rev_m, insert_panels, r2  # noqa: E402
from dieline import dieline_from_panels  # noqa: E402
from drawing import write_drawing  # noqa: E402

SRC_BOX = os.path.join(ROOT, "source", "MFC-box-RevH-glueless-Eflute.pdf")
SRC_INS = os.path.join(ROOT, "source", "MFC-insert-RevC.pdf")
FONT_DIR = "/usr/share/fonts/opentype/inter"

MARGIN = 10.0   # mm of empty artboard around the bleed
BLEED = 3.0
SAFE = 3.0

# ---------------------------------------------------------------- helpers


def fmt(v):
    return ("%.2f" % v).rstrip("0").rstrip(".")


def pts_d(pts, close=True):
    d = "M" + " L".join("%s %s" % (fmt(x), fmt(y)) for x, y in pts)
    return d + (" Z" if close else "")


def geom_d(g):
    """SVG path data for a shapely (Multi)Polygon."""
    if g.is_empty:
        return ""
    polys = g.geoms if isinstance(g, MultiPolygon) else [g]
    out = []
    for p in polys:
        if p.area < 0.5:
            continue
        out.append(pts_d(list(p.exterior.coords)[:-1]))
        for h in p.interiors:
            out.append(pts_d(list(h.coords)[:-1]))
    return " ".join(out)


def poly_of(p):
    return Polygon(p["poly"], p["holes"]).buffer(0)


class Font:
    cache = {}

    def __init__(self, name):
        local = os.path.join(ROOT, "fonts", name)
        self.f = TTFont(local if os.path.exists(local) else os.path.join(FONT_DIR, name))
        self.gs = self.f.getGlyphSet()
        self.cmap = self.f.getBestCmap()
        self.upm = self.f["head"].unitsPerEm
        self.family = ("Montserrat" if name.startswith("Montserrat") else
                       "Cormorant Garamond" if name.startswith("Cormorant") else
                       "Inter Display" if name.startswith("InterDisplay") else "Inter")
        self.italic = "Italic" in name
        self.weight = {"Black": 900, "ExtraBold": 800, "Bold": 700, "SemiBold": 600, "Medium": 500,
                       "Regular": 400, "Light": 300}.get(name.split("-")[1].split(".")[0].replace("Italic", "") or "Regular", 400)

    @classmethod
    def get(cls, name):
        if name not in cls.cache:
            cls.cache[name] = Font(name)
        return cls.cache[name]

    def width(self, text, size, track=0.0):
        s = size / self.upm
        w = 0
        for ch in text:
            g = self.cmap.get(ord(ch))
            w += self.f["hmtx"][g][0] * s if g else size * 0.3
        return w + track * size * max(len(text) - 1, 0)

    def outline(self, text, size, track=0.0):
        """Path data for text with its baseline-left at (0,0)."""
        s = size / self.upm
        x = 0
        pen = SVGPathPen(self.gs, ntos=lambda v: fmt(v))
        for ch in text:
            g = self.cmap.get(ord(ch))
            if g is None:
                x += size * 0.3
                continue
            tp = TransformPen(pen, (s, 0, 0, -s, x, 0))
            self.gs[g].draw(tp)
            x += self.f["hmtx"][g][0] * s + track * size
        return pen.getCommands()


def text_el(text, x, y, size, font="Inter-Bold.otf", fill="#000", rot=0, track=0.0, anchor="middle",
            outlined=False, opacity=None):
    """Text centred (anchor) at x, y (baseline), rotated by rot around (x, y)."""
    F = Font.get(font)
    op = ' opacity="%s"' % opacity if opacity is not None else ""
    tr = "translate(%s %s) rotate(%s)" % (fmt(x), fmt(y), fmt(rot))
    if outlined:
        w = F.width(text, size, track)
        dx = {"middle": -w / 2, "start": 0, "end": -w}[anchor]
        return '<path transform="%s translate(%s 0)" fill="%s"%s d="%s"/>' % (tr, fmt(dx), fill, op, F.outline(text, size, track))
    ls = ' letter-spacing="%s"' % fmt(track * size) if track else ""
    style = ' font-style="italic"' if F.italic else ""
    return ('<text transform="%s" font-family="%s, Inter, Arial, sans-serif" font-weight="%d"%s font-size="%s"'
            ' text-anchor="%s" fill="%s"%s%s>%s</text>') % (tr, F.family, F.weight, style, fmt(size), anchor, fill, ls, op,
                                                            text.replace("&", "&amp;").replace("<", "&lt;"))


def layer(lid, label, body, locked=False, hidden=False):
    extra = ' sodipodi:insensitive="true"' if locked else ""
    style = ' style="display:none"' if hidden else ""
    return ('<g id="%s" inkscape:groupmode="layer" inkscape:label="%s"%s%s>\n%s\n</g>\n'
            % (lid, label, extra, style, body))


def svg_doc(art, body, title):
    w, h = art["w"], art["h"]
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"'
            ' xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"'
            ' width="%smm" height="%smm" viewBox="0 0 %s %s">\n<title>%s</title>\n'
            '<g transform="translate(%s %s)">\n%s</g>\n</svg>\n') % (
        fmt(w), fmt(h), fmt(w), fmt(h), title, fmt(-art["x"]), fmt(-art["y"]), body)


# ---------------------------------------------------------------- sheets


def sheet_info(panels, raw):
    polys = {p["id"]: poly_of(p) for p in panels}
    allp = unary_union([Polygon(p["poly"]) for p in panels])
    if raw["bleed"]:
        # the box drawing carries its own bleed outline
        bl = []
        for pl in raw["bleed"]:
            bl.extend(pl)
        bleed = Polygon(bl).buffer(0)
        if bleed.area < allp.area:
            bleed = allp.buffer(BLEED, join_style=2)
    else:
        bleed = allp.buffer(BLEED, join_style=2)
    minx, miny, maxx, maxy = bleed.bounds
    art = dict(x=round(minx - MARGIN, 2), y=round(miny - MARGIN, 2),
               w=round(maxx - minx + 2 * MARGIN, 2), h=round(maxy - miny + 2 * MARGIN, 2))
    # artwork region of each panel: the panel itself + bleed on its free (cut) edges
    regions = {}
    for p in panels:
        own = polys[p["id"]]
        others = unary_union([Polygon(q["poly"]) for q in panels if q["id"] != p["id"] and q["parent"] != p["id"]
                              and p["parent"] != q["id"]] + [Polygon(q["poly"]) for q in panels
                                                              if q["parent"] == p["id"] or p["parent"] == q["id"]])
        grown = Polygon(p["poly"]).buffer(BLEED, join_style=2).intersection(bleed)
        reg = grown.difference(others)
        for h in p["holes"]:
            reg = reg.difference(Polygon(h))
        regions[p["id"]] = reg.buffer(0)
    return dict(polys=polys, bleed=bleed, art=art, regions=regions, outline=allp)


def dieline_layers(raw, panels, info, labels=True):
    cut = " ".join(pts_d(pl, close=False) for pl in raw["cut"])
    crease = " ".join(pts_d(pl, close=False) for pl in raw["crease"])
    dbl = " ".join(pts_d(pl, close=False) for pl in raw["dbl"])
    safe = []
    for p in panels:
        if p.get("face") == "hidden":
            continue
        s = info["polys"][p["id"]].buffer(-SAFE, join_style=2)
        safe.append(geom_d(s))
    out = ""
    out += layer("BLEED", "Bleed 3 mm (не печатать)",
                 '<path d="%s" fill="none" stroke="#c03cc0" stroke-width="0.3" stroke-dasharray="1 1.2"/>'
                 % geom_d(info["bleed"]), locked=True)
    out += layer("SAFE", "Safe zone 3 mm — текст внутри (не печатать)",
                 '<path d="%s" fill="none" stroke="#00a6c8" stroke-width="0.25" stroke-dasharray="0.6 0.9"/>'
                 % " ".join(safe), locked=True)
    out += layer("CREASE", "CREASE — биговка (не печатать)",
                 '<path d="%s" fill="none" stroke="#0a6fd6" stroke-width="0.35" stroke-dasharray="5 2.5"/>\n'
                 '<path d="%s" fill="none" stroke="#5b2bd6" stroke-width="0.35" stroke-dasharray="5 2.5"/>'
                 % (crease, dbl), locked=True)
    out += layer("CUT", "CUT — высечка (не печатать)",
                 '<path d="%s" fill="none" stroke="#e0102f" stroke-width="0.35" stroke-linejoin="round"/>' % cut,
                 locked=True)
    return out


# label anchors for panels whose middle is taken by a cut-out (thumb notch)
LABEL_AT = {"lip": (350.0, 973.0), "innerlip": (350.0, 1003.0)}
ARROW = "M0 -9 L5 -2 L1.6 -2 L1.6 6 L-1.6 6 L-1.6 -2 L-5 -2 Z"
FACE_RU = {"out": "СНАРУЖИ", "in": "ВНУТРИ (видно при открытии)", "hidden": "скрыто — печать не видна"}


def guide_layer(panels, info, title_lines):
    body = []
    for p in panels:
        if p["id"].startswith("petal"):
            continue
        c = info["polys"][p["id"]].representative_point()
        cx, cy = LABEL_AT.get(p["id"], (c.x, c.y))
        big = info["polys"][p["id"]].area > 9000
        col = {"out": "#1b6e3a", "in": "#9a5a00", "hidden": "#8a8a8a"}[p["face"]]
        if p["rot"] is not None:
            body.append('<path transform="translate(%s %s) rotate(%s) scale(%s)" d="%s" fill="%s" opacity="0.85"/>'
                        % (fmt(cx), fmt(cy), fmt(p["rot"]), "1.6" if big else "0.9", ARROW, col))
            body.append(text_el("ВЕРХ", cx, cy, 4.2 if big else 2.6, "Inter-Bold.otf", col, p["rot"], 0.08,
                                outlined=False).replace('transform="', 'transform="translate(0 0) ', 1)
                        .replace("rotate(%s)" % fmt(p["rot"]), "rotate(%s) translate(0 %s)" % (fmt(p["rot"]), "-17" if big else "-9")))
        rot = p["rot"] if p["rot"] is not None else 0
        off = 18 if big else 9
        body.append(text_el(p["name"].upper(), cx, cy, 4.5 if big else 2.4, "Inter-SemiBold.otf", col, rot, 0.06)
                    .replace("rotate(%s)" % fmt(rot), "rotate(%s) translate(0 %s)" % (fmt(rot), off), 1))
        body.append(text_el(FACE_RU[p["face"]], cx, cy, 3.0 if big else 1.8, "Inter-Regular.otf", col, rot, 0.04)
                    .replace("rotate(%s)" % fmt(rot), "rotate(%s) translate(0 %s)" % (fmt(rot), off + (6 if big else 3.5)), 1))
    a = info["art"]
    y = a["y"] + MARGIN + 4
    x = a["x"] + MARGIN
    for i, ln in enumerate(title_lines):
        body.append(text_el(ln, x, y + i * 6, 5.5 if i == 0 else 3.4,
                            "Inter-Bold.otf" if i == 0 else "Inter-Regular.otf", "#333", 0, 0, "start"))
    return layer("GUIDES", "Подсказки — не печатать", "\n".join(body), locked=True)


def artwork_placeholder_layer(panels, info):
    """White-board base inside the bleed so the designer sees the printable area."""
    return layer("ARTWORK", "ARTWORK — дизайн сюда",
                 '<path d="%s" fill="#ffffff" stroke="none"/>' % geom_d(info["bleed"]))


def write_template(name, raw, panels, info, title_lines, outdir):
    body = artwork_placeholder_layer(panels, info)
    body += dieline_layers(raw, panels, info)
    body += guide_layer(panels, info, title_lines)
    svg = svg_doc(info["art"], body, name)
    path = os.path.join(outdir, name + ".svg")
    open(path, "w").write(svg)
    to_pdf(path, path[:-4] + ".pdf")
    return svg


def to_pdf(svg_path, pdf_path):
    # Chromium first (honours clip paths, e.g. the cropped logo in "Big Mark"); PyMuPDF as a fallback
    import subprocess
    try:
        env = dict(os.environ, NODE_PATH=subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip())
        subprocess.run(["node", os.path.join(HERE, "svg2pdf.js"), svg_path, pdf_path], check=True, env=env,
                       capture_output=True, timeout=120)
        # Chromium rounds the page to whole CSS pixels: crop back to the exact artboard size
        import re as _re
        head = open(svg_path).read(2000)
        w = float(_re.search(r'width="([\d.]+)mm"', head).group(1)) * 72 / 25.4
        h = float(_re.search(r'height="([\d.]+)mm"', head).group(1)) * 72 / 25.4
        d = pymupdf.open(pdf_path)
        d[0].set_cropbox(pymupdf.Rect(0, 0, w, h))
        d.save(pdf_path + ".tmp", garbage=3, deflate=True)
        os.replace(pdf_path + ".tmp", pdf_path)
        return
    except Exception as e:  # noqa: BLE001
        print("chromium pdf failed, using pymupdf:", os.path.basename(svg_path), e)
    doc = pymupdf.open(svg_path)
    pdf = pymupdf.open("pdf", doc.convert_to_pdf())
    pdf.set_metadata({"title": os.path.basename(pdf_path), "creator": "cap-box/tools/build.py"})
    pdf.save(pdf_path, garbage=3, deflate=True)

# ---------------------------------------------------------------- concept design (placeholder)


PAL = dict(ink="#15171a", bone="#efe9de", accent="#e4572e", mute="#8c8577", line="#2a2d31")


def concept_box(panels, info, outlined):
    R = info["regions"]
    P = {p["id"]: p for p in panels}
    lid = ["lidtop", "lidfront", "lidsideL", "lidsideR", "lidinner", "tuck", "lidearL", "lidearR"]
    acc = ["sidelinerL", "sidelinerR", "lidlinerL", "lidlinerR", "innerlip"]
    out = []
    for pid, reg in R.items():
        col = PAL["ink"] if pid in lid else PAL["accent"] if pid in acc else PAL["bone"]
        out.append('<path id="bg-%s" d="%s" fill="%s"/>' % (pid, geom_d(reg), col))
    T = lambda *a, **k: text_el(*a, outlined=outlined, **k)

    def ctr(pid):
        b = info["polys"][pid].bounds
        return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    # lid top (rot 180): wordmark
    x, y = ctr("lidtop")
    out.append(T("MFC", x, y - 18, 64, "InterDisplay-Black.otf", PAL["bone"], 180, -0.02))
    out.append(T("ЛОГОТИП / ТЕКСТ", x, y - 40, 6, "Inter-SemiBold.otf", PAL["accent"], 180, 0.32))
    out.append('<rect x="%s" y="%s" width="60" height="0.8" fill="%s" transform="rotate(180 %s %s)"/>'
               % (fmt(x - 30), fmt(y + 30), PAL["accent"], fmt(x), fmt(y + 30.4)))
    # lid front (rot 180)
    x, y = ctr("lidfront")
    out.append(T("MFC", x, y - 4, 38, "InterDisplay-Black.otf", PAL["bone"], 180, -0.02))
    out.append(T("ВАШ СЛОГАН ЗДЕСЬ", x, y - 26, 5, "Inter-Medium.otf", PAL["mute"], 180, 0.3))
    # lid sides: small mark near the wide (front) end
    for s, sg in (("L", 1), ("R", -1)):
        b = info["polys"]["lidside" + s].bounds
        xx = 295.73 - sg * 22 if s == "L" else 512.39 + 22
        out.append(T("MFC", xx, 345, 14, "InterDisplay-Black.otf", PAL["bone"], 90 * sg))
    # side walls (base): text along the floor edge
    for s, sg in (("L", 1), ("R", -1)):
        xx = 295.73 - 16 if s == "L" else 512.39 + 16
        out.append(T("ТЕКСТ НА ОСНОВЕ", xx, 860, 9, "InterDisplay-Bold.otf", PAL["ink"], -90 * sg, 0.12))
        out.append(T("вторая строка текста", xx + (7 if s == "L" else -7), 860, 4.2, "Inter-Medium.otf",
                     PAL["mute"], -90 * sg, 0.05)
                   .replace("translate(%s 860)" % fmt(xx + (7 if s == "L" else -7)), "translate(%s 860)" % fmt(xx + (9 if s == "L" else -9))))
    # back (rot 0)
    x, y = ctr("back")
    out.append(T("MFC", x, y - 30, 30, "InterDisplay-Black.otf", PAL["ink"], 0))
    for i, ln in enumerate(["Текст на задней стенке:", "состав, контакты, сайт,", "соцсети или QR-код"]):
        out.append(T(ln, x, y + 2 + i * 7, 4.6, "Inter-Medium.otf", PAL["line"], 0))
    out.append('<rect x="%s" y="%s" width="26" height="26" fill="none" stroke="%s" stroke-width="0.6" stroke-dasharray="2 1.5"/>'
               % (fmt(x - 13), fmt(y + 30), PAL["mute"]))
    out.append(T("QR", x, y + 45, 5, "Inter-Bold.otf", PAL["mute"], 0))
    # front lip (rot 180)
    x, y = ctr("lip")
    out.append(T("MFC  ·  ТЕКСТ НА БОРТЕ", x - 50, y - 4, 5, "Inter-Bold.otf", PAL["ink"], 180, 0.2))
    # inner liners: small repeated mark
    for s in ("L", "R"):
        c = info["polys"]["sidelinerL" if s == "L" else "sidelinerR"].centroid
        out.append(T("MFC", c.x, c.y, 18, "InterDisplay-Black.otf", PAL["bone"], 90 if s == "L" else -90, 0, opacity=0.9))
    # bottom
    x, y = ctr("bottom")
    out.append(T("MFC", x, y, 16, "InterDisplay-Black.otf", PAL["ink"], 0))
    out.append(T("дно — мелкий текст / штрихкод", x, y + 8, 3.6, "Inter-Medium.otf", PAL["mute"], 0))
    return layer("ARTWORK", "ARTWORK — концепт (черновик)", "\n".join(out))


def concept_insert(panels, info, outlined):
    R = info["regions"]
    out = []
    for pid, reg in R.items():
        col = PAL["ink"] if pid in ("main", "topflap") or pid.startswith("petal") else PAL["accent"] if pid == "tray" else PAL["bone"]
        out.append('<path id="bg-%s" d="%s" fill="%s"/>' % (pid, geom_d(reg), col))
    T = lambda *a, **k: text_el(*a, outlined=outlined, **k)
    out.append(T("MFC", 512.78, 318, 20, "InterDisplay-Black.otf", PAL["bone"], 0))
    out.append(T("ЛОГОТИП ПОД КЕПКОЙ", 512.78, 328, 3.6, "Inter-SemiBold.otf", PAL["mute"], 0, 0.25))
    out.append(T("MFC", 512.78, 384, 26, "InterDisplay-Black.otf", PAL["ink"], 0))
    out.append(T("ТЕКСТ НА ПОДДОНЕ", 512.78, 398, 4.2, "Inter-Bold.otf", PAL["ink"], 0, 0.3))
    out.append(T("MFC", 512.78, 102, 14, "InterDisplay-Black.otf", PAL["bone"], 0))
    return layer("ARTWORK", "ARTWORK — концепт (черновик)", "\n".join(out))


def write_concept(name, raw, panels, info, art_fn, outdir):
    editable = svg_doc(info["art"], art_fn(panels, info, False) + dieline_layers(raw, panels, info), name)
    open(os.path.join(outdir, name + ".svg"), "w").write(editable)
    # outlined copy (text converted to curves) — used by the 3D viewer and safe to send to print
    outl = svg_doc(info["art"], art_fn(panels, info, True), name)
    path = os.path.join(outdir, name + "_outlined.svg")
    open(path, "w").write(outl)
    to_pdf(path, path[:-4] + ".pdf")
    return outl

# ---------------------------------------------------------------- main


def panel_json(panels):
    keep = ("id", "name", "parent", "poly", "holes", "hinge", "lift", "face")
    return [r2({k: p[k] for k in keep}) for p in panels]


def main():
    # drop the legend samples drawn at the right of each drawing
    clip = lambda raw, xmax: {k: [pl for pl in v if max(q[0] for q in pl) < xmax] for k, v in raw.items()}
    raw_b = clip(read_pdf(SRC_BOX), 800)
    raw_i = clip(read_pdf(SRC_INS), 1000)
    pb = box_panels()
    pi = insert_panels(raw_i)
    ib = sheet_info(pb, raw_b)
    ii = sheet_info(pi, {"bleed": []})
    for d in ("data", "print", "design"):
        os.makedirs(os.path.join(ROOT, d), exist_ok=True)

    tb = write_template("MFC-box-RevH_design-template", raw_b, pb, ib, [
        "MFC — CAP BOX · Rev H · шаблон для дизайна (вид с лицевой стороны, 1:1, мм)",
        "Артборд %s × %s мм. Рисуйте в слое ARTWORK, фон тяните до пунктира BLEED (+3 мм)." % (fmt(ib["art"]["w"]), fmt(ib["art"]["h"])),
        "Текст и логотипы — внутри голубой SAFE-зоны (3 мм от высечки и биговки). Стрелка ВЕРХ = верх на собранной коробке.",
        "Слои CUT / CREASE / SAFE / BLEED / подсказки — технические, перед печатью скрыть (высечку даёт фабрика).",
    ], os.path.join(ROOT, "print"))
    ti = write_template("MFC-insert-RevC_design-template", raw_i, pi, ii, [
        "MFC — CAP INSERT · Rev C · шаблон для дизайна (вид с лицевой стороны, 1:1, мм)",
        "Артборд %s × %s мм. Видна только лицевая сторона основной панели, лепестки и клапаны." % (fmt(ii["art"]["w"]), fmt(ii["art"]["h"])),
        "Крылья складываются назад в трубы-опоры — их печать не видна.",
    ], os.path.join(ROOT, "print"))

    # outlined template copies for the viewer (no live text so the browser renders them identically)
    def outline_template(raw, panels, info):
        body = artwork_placeholder_layer(panels, info) + dieline_layers(raw, panels, info)
        g = []
        for p in panels:
            if p["id"].startswith("petal") or p["rot"] is None:
                continue
            c = info["polys"][p["id"]].representative_point()
            big = info["polys"][p["id"]].area > 9000
            col = {"out": "#1b6e3a", "in": "#9a5a00", "hidden": "#8a8a8a"}[p["face"]]
            g.append('<path transform="translate(%s %s) rotate(%s) scale(%s)" d="%s" fill="%s"/>'
                     % (fmt(c.x), fmt(c.y), fmt(p["rot"]), "2.4" if big else "1.2", ARROW, col))
            g.append(text_el(p["name"].upper(), c.x, c.y, 6 if big else 3, "Inter-Bold.otf", col, p["rot"], 0.04, outlined=True)
                     .replace("rotate(%s)" % fmt(p["rot"]), "rotate(%s) translate(0 %s)" % (fmt(p["rot"]), 26 if big else 13), 1))
        body += "<g>%s</g>" % "\n".join(g)
        return svg_doc(info["art"], body, "template")

    # ---- Rev I: step at the back of the side split (no source PDF: die-line built from the panels)
    pI, infoI = box_panels_rev_i()
    raw_I = dieline_from_panels(pI)
    iI = sheet_info(pI, {"bleed": []})
    write_drawing(pI, raw_I, infoI, os.path.join(ROOT, "print", "MFC-box-RevI-step_dieline.svg"), iI["outline"], iI["bleed"])
    to_pdf(os.path.join(ROOT, "print", "MFC-box-RevI-step_dieline.svg"), os.path.join(ROOT, "print", "MFC-box-RevI-step_dieline.pdf"))
    write_template("MFC-box-RevI_design-template", raw_I, pI, iI, [
        "MFC — CAP BOX · Rev I (уступ %s мм) · шаблон для дизайна (вид с лицевой стороны, 1:1, мм)" % fmt(infoI["step"]),
        "Артборд %s × %s мм. Рисуйте в слое ARTWORK, фон тяните до пунктира BLEED (+3 мм)." % (fmt(iI["art"]["w"]), fmt(iI["art"]["h"])),
        "Текст и логотипы — внутри голубой SAFE-зоны (3 мм от высечки и биговки). Стрелка ВЕРХ = верх на собранной коробке.",
        "Слои CUT / CREASE / SAFE / BLEED / подсказки — технические, перед печатью скрыть (высечку даёт фабрика).",
    ], os.path.join(ROOT, "print"))
    print("Rev I", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in infoI.items()})

    # ---- Rev J (superseded by Rev K, kept for comparison): Rev I + lid hinge at the end of the step, fixed top with lock flaps
    pJ, infoJ = box_panels_rev_j()
    raw_J = dieline_from_panels(pJ)
    iJ = sheet_info(pJ, {"bleed": []})
    write_drawing(pJ, raw_J, infoJ, os.path.join(ROOT, "print", "MFC-box-RevJ_dieline.svg"), iJ["outline"], iJ["bleed"], rev="J")
    to_pdf(os.path.join(ROOT, "print", "MFC-box-RevJ_dieline.svg"), os.path.join(ROOT, "print", "MFC-box-RevJ_dieline.pdf"))
    write_template("MFC-box-RevJ_design-template", raw_J, pJ, iJ, [
        "MFC — CAP BOX · Rev J (уступ %s мм, петля крышки на конце уступа) · шаблон для дизайна (1:1, мм)" % fmt(infoJ["step"]),
        "Артборд %s × %s мм. Рисуйте в слое ARTWORK, фон тяните до пунктира BLEED (+3 мм)." % (fmt(iJ["art"]["w"]), fmt(iJ["art"]["h"])),
        "Текст и логотипы — внутри голубой SAFE-зоны (3 мм от высечки и биговки). Стрелка ВЕРХ = верх на собранной коробке.",
        "Слои CUT / CREASE / SAFE / BLEED / подсказки — технические, перед печатью скрыть (высечку даёт фабрика).",
    ], os.path.join(ROOT, "print"))

    # ---- Rev K (superseded by Rev L): Rev I + lid hinge at the end of the step, fixed top with lock flaps
    pK, infoK = box_panels_rev_k()
    raw_K = dieline_from_panels(pK)
    iK = sheet_info(pK, {"bleed": []})
    write_drawing(pK, raw_K, infoK, os.path.join(ROOT, "print", "MFC-box-RevK_dieline.svg"), iK["outline"], iK["bleed"], rev="K")
    to_pdf(os.path.join(ROOT, "print", "MFC-box-RevK_dieline.svg"), os.path.join(ROOT, "print", "MFC-box-RevK_dieline.pdf"))
    write_template("MFC-box-RevK_design-template", raw_K, pK, iK, [
        "MFC — CAP BOX · Rev K (уступ %s мм, петля на конце уступа, чистые углы) · шаблон для дизайна (1:1, мм)" % fmt(infoK["step"]),
        "Артборд %s × %s мм. Рисуйте в слое ARTWORK, фон тяните до пунктира BLEED (+3 мм)." % (fmt(iK["art"]["w"]), fmt(iK["art"]["h"])),
        "Текст и логотипы — внутри голубой SAFE-зоны (3 мм от высечки и биговки). Стрелка ВЕРХ = верх на собранной коробке.",
        "Слои CUT / CREASE / SAFE / BLEED / подсказки — технические, перед печатью скрыть (высечку даёт фабрика).",
    ], os.path.join(ROOT, "print"))

    # ---- Rev L (superseded by Rev M): Rev I + lid hinge at the end of the step, fixed top with lock flaps
    pL, infoL = box_panels_rev_l()
    raw_L = dieline_from_panels(pL)
    iL = sheet_info(pL, {"bleed": []})
    write_drawing(pL, raw_L, infoL, os.path.join(ROOT, "print", "MFC-box-RevL_dieline.svg"), iL["outline"], iL["bleed"], rev="L")
    to_pdf(os.path.join(ROOT, "print", "MFC-box-RevL_dieline.svg"), os.path.join(ROOT, "print", "MFC-box-RevL_dieline.pdf"))
    write_template("MFC-box-RevL_design-template", raw_L, pL, iL, [
        "MFC — CAP BOX · Rev L (уступ %s мм, петля на конце уступа, язычок на основе) · шаблон для дизайна (1:1, мм)" % fmt(infoL["step"]),
        "Артборд %s × %s мм. Рисуйте в слое ARTWORK, фон тяните до пунктира BLEED (+3 мм)." % (fmt(iL["art"]["w"]), fmt(iL["art"]["h"])),
        "Текст и логотипы — внутри голубой SAFE-зоны (3 мм от высечки и биговки). Стрелка ВЕРХ = верх на собранной коробке.",
        "Слои CUT / CREASE / SAFE / BLEED / подсказки — технические, перед печатью скрыть (высечку даёт фабрика).",
    ], os.path.join(ROOT, "print"))

    # ---- Rev M (production, test print): Rev I + lid hinge at the end of the step, fixed top with lock flaps
    pM, infoM = box_panels_rev_m()
    raw_M = dieline_from_panels(pM)
    iM = sheet_info(pM, {"bleed": []})
    write_drawing(pM, raw_M, infoM, os.path.join(ROOT, "print", "MFC-box-RevM_dieline.svg"), iM["outline"], iM["bleed"], rev="M")
    to_pdf(os.path.join(ROOT, "print", "MFC-box-RevM_dieline.svg"), os.path.join(ROOT, "print", "MFC-box-RevM_dieline.pdf"))
    write_template("MFC-box-RevM_design-template", raw_M, pM, iM, [
        "MFC — CAP BOX · Rev M (уступ %s мм, петля на конце уступа, длинный язычок из внутреннего борта) · шаблон для дизайна (1:1, мм)" % fmt(infoM["step"]),
        "Артборд %s × %s мм. Рисуйте в слое ARTWORK, фон тяните до пунктира BLEED (+3 мм)." % (fmt(iM["art"]["w"]), fmt(iM["art"]["h"])),
        "Текст и логотипы — внутри голубой SAFE-зоны (3 мм от высечки и биговки). Стрелка ВЕРХ = верх на собранной коробке.",
        "Слои CUT / CREASE / SAFE / BLEED / подсказки — технические, перед печатью скрыть (высечку даёт фабрика).",
    ], os.path.join(ROOT, "print"))

    # ---- designs: the chosen one (v1.1 "Stone") goes into the 3D viewer, the others are proposals
    import designs as DS
    from functools import partial

    def write_design(v, outdir, tag):
        os.makedirs(outdir, exist_ok=True)
        o = partial(DS.box_outside, v); n_ = partial(DS.box_inside, v); s_ = partial(DS.insert_art, v)
        dJ_ = write_concept("MFC-box-RevM_%s_outside" % tag, raw_M, pM, iM, o, outdir)
        dJn_ = write_concept("MFC-box-RevM_%s_inside" % tag, raw_M, pM, iM, n_, outdir)
        for ext in (".svg", ".pdf"):   # the un-mirrored outline copy is only for the 3D texture
            os.remove(os.path.join(outdir, "MFC-box-RevM_%s_inside_outlined%s" % (tag, ext)))
        dIns_ = write_concept("MFC-insert-RevC_%s" % tag, raw_i, pi, ii, s_, outdir)
        a = iM["art"]          # inside print as the printer sees it: reverse side of the sheet = mirrored
        mir = svg_doc(a, '<g transform="translate(%s 0) scale(-1 1)">%s%s</g>' % (
            fmt(2 * a["x"] + a["w"]), n_(pM, iM, True), dieline_layers(raw_M, pM, iM)), "inside print, mirrored")
        mp = os.path.join(outdir, "MFC-box-RevM_%s_inside_PRINT-mirrored.svg" % tag)
        open(mp, "w").write(mir)
        to_pdf(mp, mp[:-4] + ".pdf")
        return dict(M=dict(design=dJ_, inside=dJn_),
                    L=dict(design=svg_doc(iL["art"], o(pL, iL, True), tag), inside=svg_doc(iL["art"], n_(pL, iL, True), tag)),
                    K=dict(design=svg_doc(iK["art"], o(pK, iK, True), tag), inside=svg_doc(iK["art"], n_(pK, iK, True), tag)),
                    J=dict(design=svg_doc(iJ["art"], o(pJ, iJ, True), tag), inside=svg_doc(iJ["art"], n_(pJ, iJ, True), tag)),
                    I=dict(design=svg_doc(iI["art"], o(pI, iI, True), tag), inside=svg_doc(iI["art"], n_(pI, iI, True), tag)),
                    H=dict(design=svg_doc(ib["art"], o(pb, ib, True), tag), inside=svg_doc(ib["art"], n_(pb, ib, True), tag)),
                    insert=dIns_)

    ddir = os.path.join(ROOT, "design")
    main_tex = write_design(DS.BY_KEY["stone"], ddir, "design-v1.1")
    dIns = main_tex["insert"]
    variant_tex = {}
    if os.environ.get("CAPBOX_VARIANTS"):
        for v in DS.VARIANTS:
            variant_tex[v.key] = write_design(v, os.path.join(ddir, "variants", v.key), "design-%s" % v.key)

    geo = dict(
        box={"H": dict(panels=panel_json(pb), art=ib["art"], thickness=1.5),
             "I": dict(panels=panel_json(pI), art=iI["art"], thickness=1.5, step=infoI["step"]),
             "J": dict(panels=panel_json(pJ), art=iJ["art"], thickness=1.5, step=infoJ["step"]),
             "K": dict(panels=panel_json(pK), art=iK["art"], thickness=1.5, step=infoK["step"]),
             "L": dict(panels=panel_json(pL), art=iL["art"], thickness=1.5, step=infoL["step"]),
             "M": dict(panels=panel_json(pM), art=iM["art"], thickness=1.5, step=infoM["step"])},
        insert=dict(panels=panel_json(pi), art=ii["art"], thickness=0.9),
    )
    json.dump(geo, open(os.path.join(ROOT, "data", "geometry.json"), "w"), ensure_ascii=False)
    textures = dict(
        box={"H": dict(main_tex["H"], template=outline_template(raw_b, pb, ib)),
             "I": dict(main_tex["I"], template=outline_template(raw_I, pI, iI)),
             "J": dict(main_tex["J"], template=outline_template(raw_J, pJ, iJ)),
             "K": dict(main_tex["K"], template=outline_template(raw_K, pK, iK)),
             "L": dict(main_tex["L"], template=outline_template(raw_L, pL, iL)),
             "M": dict(main_tex["M"], template=outline_template(raw_M, pM, iM))},
        insert=dict(design=dIns, template=outline_template(raw_i, pi, ii)),
    )
    src = open(os.path.join(HERE, "viewer.src.html"), encoding="utf-8").read()
    html = src.replace("/*__GEOMETRY__*/null", json.dumps(geo, ensure_ascii=False, separators=(",", ":")))
    html = html.replace("/*__TEXTURES__*/null", json.dumps(textures, ensure_ascii=False, separators=(",", ":")))
    open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(html)
    vdir = os.environ.get("CAPBOX_VARIANTS")
    for key, vt in variant_tex.items():
        tx = dict(box={k: dict(vt[k], template=textures["box"][k]["template"]) for k in ("H", "I", "J", "K", "L", "M")},
                  insert=dict(design=vt["insert"], template=textures["insert"]["template"]))
        h2 = src.replace("/*__GEOMETRY__*/null", json.dumps(geo, ensure_ascii=False, separators=(",", ":")))
        h2 = h2.replace("/*__TEXTURES__*/null", json.dumps(tx, ensure_ascii=False, separators=(",", ":")))
        open(os.path.join(vdir, key + ".html"), "w", encoding="utf-8").write(h2)
    print("box artboard", ib["art"], "insert artboard", ii["art"])
    print("index.html", os.path.getsize(os.path.join(ROOT, "index.html")) // 1024, "KB")


if __name__ == "__main__":
    main()
