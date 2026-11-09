import pymupdf, sys, json
f=sys.argv[1]
doc=pymupdf.open(f); p=doc[0]
k=25.4/72
out=[]
for d in p.get_drawings():
    col=d.get('color'); fill=d.get('fill'); dash=d.get('dashes'); w=d.get('width')
    segs=[]
    for it in d['items']:
        if it[0]=='l': segs.append(['l',[round(it[1].x*k,2),round(it[1].y*k,2)],[round(it[2].x*k,2),round(it[2].y*k,2)]])
        elif it[0]=='c': segs.append(['c']+[[round(q.x*k,2),round(q.y*k,2)] for q in it[1:5]])
        elif it[0]=='re': r=it[1]; segs.append(['re',[round(r.x0*k,2),round(r.y0*k,2),round(r.x1*k,2),round(r.y1*k,2)]])
        elif it[0]=='qu': q=it[1]; segs.append(['qu',[[round(pt.x*k,2),round(pt.y*k,2)] for pt in (q.ul,q.ur,q.lr,q.ll)]])
    out.append(dict(color=[round(c,3) for c in col] if col else None, fill=[round(c,3) for c in fill] if fill else None, dash=dash, w=round(w*k,3) if w else None, close=d.get('closePath'), segs=segs))
json.dump(out,open(sys.argv[2],'w'))
print(len(out))
from collections import Counter
print(Counter((str(o['color']),str(o['fill']),o['dash']) for o in out))
