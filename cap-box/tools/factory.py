"""Factory (production) files: 1:1 die-line PDF with spot colours + layers, and DXF.

    python3 cap-box/tools/factory.py

Writes the 4 factory files to cap-box/factory/ (box + insert: PRO 1:1 die-line, drawing).
Optional: --dxf adds DXF die-lines, --spec adds a one-page production spec.
  *_DIELINE_1to1.pdf  -  vector die-line only, 1:1 mm, spot colours CutContour / Crease,
                       PDF layers CUT, CREASE, INFO (INFO = non-printing notes)
  *_DIELINE.dxf  -  same lines, layers CUT (red) / CREASE (blue), units mm
"""
import math
import os
import shutil
import sys

from shapely.geometry import LineString, MultiLineString
from shapely.ops import linemerge, unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from geometry import read_pdf, box_panels_rev_l  # noqa: E402
from dieline import dieline_from_panels  # noqa: E402

PT = 72.0 / 25.4
MARGIN = 15.0


def merged(polylines):
    if not polylines:
        return []
    g = linemerge(unary_union([LineString(pl) for pl in polylines if len(pl) > 1]))
    geoms = g.geoms if hasattr(g, "geoms") else [g]
    return [list(x.coords) for x in geoms if x.length > 0.05]


def bounds(lines):
    xs = [p[0] for pl in lines for p in pl]
    ys = [p[1] for pl in lines for p in pl]
    return min(xs), min(ys), max(xs), max(ys)


# ------------------------------------------------------------------ PDF (hand-written, spot colours + OCG layers)

def pdf_escape(s):
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_pdf(path, cut, crease, info_lines, title):
    allp = cut + crease
    minx, miny, maxx, maxy = bounds(allp)
    W = (maxx - minx) + 2 * MARGIN
    H = (maxy - miny) + 2 * MARGIN + 30          # room for the info block under the die-line
    X = lambda x: (x - minx + MARGIN) * PT
    Y = lambda y: (H - (y - miny + MARGIN)) * PT

    def paths(lines):
        out = []
        for pl in lines:
            out.append("%.3f %.3f m" % (X(pl[0][0]), Y(pl[0][1])))
            for p in pl[1:]:
                out.append("%.3f %.3f l" % (X(p[0]), Y(p[1])))
            out.append("S")
        return "\n".join(out)
    lw = 0.25 * PT
    content = []
    content.append("/OC /ocCut BDC q /CsCut CS 1 SCN %.3f w 1 J 1 j\n%s\nQ EMC" % (lw, paths(cut)))
    content.append("/OC /ocCrease BDC q /CsCrease CS 1 SCN %.3f w 1 J 1 j\n%s\nQ EMC" % (lw, paths(crease)))
    txt = ["/OC /ocInfo BDC q BT /F1 %.2f Tf 0 0 0 1 k" % (3.2 * PT)]
    ty = H - (maxy - miny + MARGIN + 8)
    for i, ln in enumerate([title] + info_lines):
        txt.append("1 0 0 1 %.3f %.3f Tm (%s) Tj" % (MARGIN * PT, (ty - i * 4.6) * PT, pdf_escape(ln)))
    txt.append("ET Q EMC")
    content.append("\n".join(txt))
    stream = "\n".join(content).encode("latin-1")

    objs = []

    def add(o):
        objs.append(o)
        return len(objs)
    fn_cut = "<< /FunctionType 2 /Domain [0 1] /C0 [0 0 0 0] /C1 [0 1 0 0] /N 1 >>"
    fn_crease = "<< /FunctionType 2 /Domain [0 1] /C0 [0 0 0 0] /C1 [1 0 0 0] /N 1 >>"
    oc_cut = add("<< /Type /OCG /Name (CUT - CutContour) >>")
    oc_crease = add("<< /Type /OCG /Name (CREASE - Crease) >>")
    oc_info = add("<< /Type /OCG /Name (INFO - do not print) /Usage << /Print << /PrintState /OFF >> >> >>")
    font = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    cont = add(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
    page_id = len(objs) + 2
    pages = add("<< /Type /Pages /Kids [%d 0 R] /Count 1 >>" % page_id)
    add(("<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %.3f %.3f] /TrimBox [0 0 %.3f %.3f] /Contents %d 0 R "
         "/Resources << /Font << /F1 %d 0 R >> /ColorSpace << /CsCut [/Separation /CutContour /DeviceCMYK %s] "
         "/CsCrease [/Separation /Crease /DeviceCMYK %s] >> /Properties << /ocCut %d 0 R /ocCrease %d 0 R /ocInfo %d 0 R >> >> >>")
        % (pages, W * PT, H * PT, W * PT, H * PT, cont, font, fn_cut, fn_crease, oc_cut, oc_crease, oc_info))
    ocgs = "[%d 0 R %d 0 R %d 0 R]" % (oc_cut, oc_crease, oc_info)
    cat = add("<< /Type /Catalog /Pages %d 0 R /OCProperties << /OCGs %s /D << /Order %s /ON %s "
              "/AS [<< /Event /Print /Category [/Print] /OCGs %s >>] >> >> >>" % (pages, ocgs, ocgs, ocgs, ocgs))
    info = add("<< /Title (%s) /Creator (cap-box/tools/factory.py) >>" % pdf_escape(title))
    out = bytearray(b"%PDF-1.6\n%\xe2\xe3\xcf\xd3\n")
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        body = o if isinstance(o, bytes) else o.encode("latin-1")
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for o in offs:
        out += b"%010d 00000 n \n" % o
    out += b"trailer\n<< /Size %d /Root %d 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, cat, info, xref)
    open(path, "wb").write(bytes(out))
    return W, H


# ------------------------------------------------------------------ DXF R12

def write_dxf(path, cut, crease):
    minx, miny, maxx, maxy = bounds(cut + crease)
    Y = lambda y: maxy - y          # DXF is y-up; origin at the lower-left of the die-line
    X = lambda x: x - minx
    L = []
    a = L.append
    for s in ("0", "SECTION", "2", "HEADER", "9", "$ACADVER", "1", "AC1009", "9", "$INSUNITS", "70", "4",
              "9", "$EXTMIN", "10", "0", "20", "0", "30", "0", "9", "$EXTMAX", "10", "%.3f" % (maxx - minx),
              "20", "%.3f" % (maxy - miny), "30", "0", "0", "ENDSEC",
              "0", "SECTION", "2", "TABLES", "0", "TABLE", "2", "LAYER", "70", "2"):
        a(s)
    for name, col in (("CUT", 1), ("CREASE", 5)):
        for s in ("0", "LAYER", "2", name, "70", "0", "62", str(col), "6", "CONTINUOUS"):
            a(s)
    for s in ("0", "ENDTAB", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"):
        a(s)
    for layer, lines in (("CUT", cut), ("CREASE", crease)):
        for pl in lines:
            for p, q in zip(pl[:-1], pl[1:]):
                if math.dist(p, q) < 1e-4:
                    continue
                for s in ("0", "LINE", "8", layer, "10", "%.4f" % X(p[0]), "20", "%.4f" % Y(p[1]), "30", "0",
                          "11", "%.4f" % X(q[0]), "21", "%.4f" % Y(q[1]), "31", "0"):
                    a(s)
    for s in ("0", "ENDSEC", "0", "EOF"):
        a(s)
    open(path, "w").write("\n".join(L) + "\n")


def main():
    out = os.path.join(ROOT, "factory")
    os.makedirs(out, exist_ok=True)

    # ---- BOX Rev L (die-line from the panel geometry)
    pI, info = box_panels_rev_l()
    rb = dieline_from_panels(pI)
    b_cut, b_crease = merged(rb["cut"]), merged(rb["crease"] + rb["dbl"])
    bx = bounds(b_cut)
    box_info = [
        "Sheet (die-line) %.1f x %.1f mm. Scale 1:1, units mm, view from OUTSIDE (print side)." % (bx[2] - bx[0], bx[3] - bx[1]),
        "Material: E-flute litho-laminated board ~1.5 mm. Flutes parallel to the long side folds. NO GLUE.",
        "Closed box outside approx. 218.2 W x 233.6 D x 199 H; clear inside 206 x 226 x 196 (fits insert Rev C).",
        "CutContour = cut (incl. 6 lock slots in bottom, thumb notch). Crease = fold; pairs 2 mm apart = 180 deg folds.",
        "Rev L: step %.0f mm, slope %.1f deg; lid hinges on the crease %.1f mm from the back (fixed top with 2 lock flaps)."
        % (info["step"], info["slope_deg"], info["fixed_top"]),
        "Printer to confirm crease/slot allowances.",
    ]
    write_pdf(os.path.join(out, "MFC-box-RevL_PRO-dieline-1to1.pdf"), b_cut, b_crease, box_info, "MFC CAP BOX - Rev L - DIELINE 1:1")
    if "--dxf" in sys.argv:
        write_dxf(os.path.join(out, "MFC-box-RevL_dieline.dxf"), b_cut, b_crease)
    shutil.copy(os.path.join(ROOT, "print", "MFC-box-RevL_dieline.pdf"), os.path.join(out, "MFC-box-RevL_drawing.pdf"))

    # ---- INSERT Rev C (die-line from the source PDF vectors)
    raw = read_pdf(os.path.join(ROOT, "source", "MFC-insert-RevC.pdf"))
    keep = lambda v: [pl for pl in v if max(q[0] for q in pl) < 1000]
    i_cut, i_crease = merged(keep(raw["cut"])), merged(keep(raw["crease"]))
    ix = bounds(i_cut)
    ins_info = [
        "Sheet (die-line) %.1f x %.1f mm. Scale 1:1, units mm, view from PRINT side." % (ix[2] - ix[0], ix[3] - ix[1]),
        "Material: F-flute (or SBS 28-30 pt). Main panel 202 x 217, top flap 48, tray flap 83.6. NO GLUE.",
        "Fits box inside 206 W x 226 D x 196 H. Wings fold back into two support tubes (tube back wall 100).",
        "CutContour = cut (arch, petals, finger hole, lock tabs). Crease = fold.",
        "Printer to confirm crease allowances for the chosen board.",
    ]
    write_pdf(os.path.join(out, "MFC-insert-RevC_PRO-dieline-1to1.pdf"), i_cut, i_crease, ins_info, "MFC CAP INSERT - Rev C - DIELINE 1:1")
    if "--dxf" in sys.argv:
        write_dxf(os.path.join(out, "MFC-insert-RevC_dieline.dxf"), i_cut, i_crease)
    shutil.copy(os.path.join(ROOT, "source", "MFC-insert-RevC.pdf"), os.path.join(out, "MFC-insert-RevC_drawing.pdf"))
    print("box", [round(v, 1) for v in bx], "lines", len(b_cut), len(b_crease))
    print("insert", [round(v, 1) for v in ix], "lines", len(i_cut), len(i_crease))


if __name__ == "__main__":
    main()


SPEC = [
    ("h1", "MFC CAP BOX + CAP INSERT - PRODUCTION SPEC"),
    ("p", "Box Rev L (glueless, E-flute) and insert Rev C (F-flute). All dimensions in mm."),
    ("h2", "1. Files"),
    ("p", "MFC-box-RevL_DIELINE_1to1.pdf / .dxf  -  Box die-line, 1:1 (production file)"),
    ("p", "MFC-box-RevL_DRAWING.pdf  -  Box drawing with dimensions and assembly notes"),
    ("p", "MFC-insert-RevC_DIELINE_1to1.pdf / .dxf  -  Insert die-line, 1:1 (production file)"),
    ("p", "MFC-insert-RevC_DRAWING.pdf  -  Insert drawing with dimensions"),
    ("p", "PDF die-lines: spot colour CutContour (magenta) = cut, spot colour Crease (cyan) = crease."),
    ("p", "PDF layers: CUT, CREASE, INFO (INFO is set to non-printing). DXF layers: CUT (red), CREASE (blue), units mm."),
    ("h2", "2. Box - Rev L"),
    ("p", "Style: one-piece glueless folding box, lid hinged on the back top edge, short tuck."),
    ("p", "Board: E-flute litho-laminated, caliper ~1.5 mm. Flutes parallel to the long side folds."),
    ("p", "Closed size, outside approx.: 218.2 W x 233.6 D x 199 H. Clear inside: 206 W x 226 D x 196 H."),
    ("p", "Flat sheet (die-line): 731.6 x 947.6 mm."),
    ("p", "Side split: base side wall stays full height (196) for 60 mm from the back wall (step),"),
    ("p", "then slopes 44.6 deg to the front. Lid side ends 65.4 mm from the hinge."),
    ("p", "180 deg folds (liners, inner lip, lid inner front, tuck) use a double crease 2 mm apart."),
    ("p", "Locking: 6 slots in the bottom take the tabs of the side liners (4) and the inner lip (2). No glue anywhere."),
    ("h2", "3. Insert - Rev C"),
    ("p", "Board: F-flute (or SBS 28-30 pt). Flat sheet: 945.1 x 370.8 mm."),
    ("p", "Main panel 202 x 217 at 65 deg, top flap 48 (to back wall), tray flap 83.6 (on box floor)."),
    ("p", "Wings fold back into two support tubes (tube back wall 100); inner walls lock with tabs/notches."),
    ("p", "Arch: petals fold forward to hold the cap crown. Fits box inside 206 x 226 x 196."),
    ("h2", "4. Printing"),
    ("p", "Artwork will be supplied separately on the same 1:1 template: CMYK, 3 mm bleed outside the cut line,"),
    ("p", "text min. 3 mm inside cut and crease lines, all fonts outlined. Print side = outside of the box."),
    ("p", "Die-line layers must not print."),
    ("h2", "5. Before production"),
    ("p", "1. Please make a WHITE (unprinted) sample of the box and the insert together and send photos."),
    ("p", "2. Please confirm crease and slot allowances for your board and adjust the die if needed."),
    ("p", "3. Check: insert sits flat, lid closes without force, tuck goes in behind the inner lip."),
    ("p", "4. Please send the final die-line back for approval before cutting the die."),
]


def write_spec(path):
    y, body = 20.0, []
    for kind, s in SPEC:
        size, weight, gap = {"h1": (7, 700, 12), "h2": (5, 700, 9), "p": (3.6, 400, 5.6)}[kind]
        if kind == "h2":
            y += 3
        body.append('<text x="18" y="%.1f" font-family="Helvetica, Arial, sans-serif" font-size="%s" font-weight="%d" fill="#111">%s</text>'
                    % (y, size, weight, s.replace("&", "&amp;")))
        y += gap
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">'
           '<rect width="210" height="297" fill="#fff"/>%s</svg>' % "".join(body))
    tmp = path[:-4] + ".svg"
    open(tmp, "w").write(svg)
    import pymupdf
    d = pymupdf.open(tmp)
    pymupdf.open("pdf", d.convert_to_pdf()).save(path)
    os.remove(tmp)


if __name__ == "__main__":
    if "--spec" in sys.argv:
        write_spec(os.path.join(ROOT, "factory", "MFC_FACTORY-SPEC.pdf"))
