"""Gallery page of the box design directions (snapshots rendered from the 3D model).

    python3 cap-box/tools/gallery.py   ->  cap-box/design/MFC-design-directions.html
"""
import base64
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from designs import BY_KEY  # noqa: E402

DIRS = [
    ("stone", "01", "Stone · v1.1", "Ваше направление, доведённое до чистовика.",
     "Логотип стал опорой композиции: 40 мм на переде, 110 мм тон-в-тон на крышке, крупно внутри и на задней стенке. "
     "Серо-бежевый картон, разреженный Montserrat и курсив Cormorant Garamond для тёплых строк."),
    ("noir", "02", "Noir", "Тёмная коробка, светлое нутро.",
     "Матовый эспрессо снаружи, кремовый текст и логотип. При открытии внутри песочный цвет, вкладыш светлый: "
     "кепка «подсвечена» контрастом. Большой марлин на крышке почти не виден, проявляется на свету."),
    ("coast", "03", "Coastline", "Линия горизонта и «the catch».",
     "Белый, как выцветший на солнце, картон и глубокий сланцево-синий. Перед крышки повторяет вышивку кепки: "
     "«the catch» курсивом с засечками. Тонкая линия горизонта обходит все стороны на высоте 58 мм и продолжается через диагональный шов."),
    ("mark", "04", "Big Mark", "Логотип больше коробки.",
     "Песочный картон и марлин размером 300 мм, обрезанный краями крышки: хвост и рыба на верхе, рыбак "
     "переходит на перед. Текст только по углам. Подход модных домов: знак вместо надписи."),
    ("sun", "05", "Sun-faded", "Закат по диагонали.",
     "Двухцветная коробка: глиняно-терракотовая крышка и кремовая основа. Диагональный шов становится главным "
     "графическим приёмом: сбоку коробка читается как закат над водой. Внутри крышки тот же терракотовый цвет."),
]
VIEWS = [("closed", "Закрыта"), ("open", "Открыта"), ("inside", "Внутри крышки"), ("back", "Сзади"), ("bottomflat", "Дно")]


def img(key, view):
    d = os.path.join(ROOT, "design", "snapshots-v1.1" if key == "stone" else os.path.join("variants", key, "snapshots"))
    data = open(os.path.join(d, "%s_%s.jpg" % (key, view)), "rb").read()
    return "data:image/jpeg;base64," + base64.b64encode(data).decode()


def swatches(v):
    cols = [("Картон", v.board), ("Крышка", v.lid), ("Внутри", v.inside), ("Текст", v.ink), ("Логотип", v.logo)]
    seen, out = set(), []
    for name, c in cols:
        if c in seen:
            continue
        seen.add(c)
        out.append('<li><span class="chip" style="background:%s"></span><span>%s</span><code>%s</code></li>' % (c, name, c))
    return "".join(out)


def main():
    sections = []
    for key, num, title, lede, body in DIRS:
        v = BY_KEY[key]
        thumbs = "".join(
            '<button type="button" class="th%s" data-src="%s" aria-label="%s"><img src="%s" alt="%s — %s"><span>%s</span></button>'
            % (" on" if i == 0 else "", img(key, vw), lab, img(key, vw), title, lab, lab)
            for i, (vw, lab) in enumerate(VIEWS))
        sections.append(f"""
<section class="dir" id="{key}">
  <div class="stage"><img class="hero" src="{img(key, 'closed')}" alt="{title}: закрытая коробка"></div>
  <div class="copy">
    <div class="num">{num}</div>
    <h2>{title}</h2>
    <p class="lede">{lede}</p>
    <p>{body}</p>
    <ul class="pal">{swatches(v)}</ul>
    <div class="thumbs">{thumbs}</div>
  </div>
</section>""")
    html = TEMPLATE.replace("%%SECTIONS%%", "\n".join(sections))
    out = os.path.join(ROOT, "design", "MFC-design-directions.html")
    open(out, "w", encoding="utf-8").write(html)
    print(out, os.path.getsize(out) // 1024, "KB")


TEMPLATE = """<title>MFC Box Directions</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600&family=Cormorant+Garamond:ital,wght@1,400;1,500&display=swap">
<style>
/* Layout: one direction per band, the box shot big on the left, the story and the other views beside it. */
:root{
  --bg:#ebe6de; --paper:#f4f0ea; --fg:#2f2b27; --muted:#7a7067; --line:#d6cfc4; --accent:#4a3a2f;
  --f-caps:"Montserrat",system-ui,sans-serif; --f-serif:"Cormorant Garamond",Georgia,serif;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#1d1b19; --paper:#262320; --fg:#ece6dc; --muted:#a69c90; --line:#3a3530; --accent:#d9c3a5; color-scheme:dark}}
:root[data-theme="dark"]{--bg:#1d1b19; --paper:#262320; --fg:#ece6dc; --muted:#a69c90; --line:#3a3530; --accent:#d9c3a5; color-scheme:dark}
body{background:var(--bg);color:var(--fg);font-family:var(--f-caps);font-size:14px;line-height:1.6}
.wrap{max-width:1240px;margin:0 auto;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:48px 72px}
header{display:grid;gap:10px;margin-bottom:40px;max-width:62ch}
.kicker{font-size:11px;letter-spacing:.32em;text-transform:uppercase;color:var(--muted)}
h1{font-family:var(--f-caps);font-weight:500;font-size:clamp(26px,4vw,40px);letter-spacing:.42em;margin:0;text-wrap:balance}
header p{margin:0;color:var(--muted)}
header .serif{font-family:var(--f-serif);font-style:italic;font-size:20px;color:var(--fg)}
nav{display:flex;flex-wrap:wrap;gap:8px 18px;margin-top:6px}
nav a{color:var(--fg);text-decoration:none;font-size:11px;letter-spacing:.24em;text-transform:uppercase;border-bottom:1px solid var(--line);padding-bottom:2px}
nav a:hover,nav a:focus-visible{border-color:var(--fg)}
.dir{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(0,1fr);gap:clamp(20px,4vw,48px);align-items:start;padding-block:36px;border-top:1px solid var(--line)}
.stage{background:#e6e1d9;border-radius:2px;overflow:hidden;aspect-ratio:1/1;max-width:100%}
.hero{width:100%;height:100%;object-fit:cover;display:block}
.copy{display:flex;flex-direction:column;gap:12px;min-width:0}
.num{font-size:11px;letter-spacing:.3em;color:var(--muted)}
h2{font-weight:500;font-size:22px;letter-spacing:.32em;text-transform:uppercase;margin:0}
.lede{font-family:var(--f-serif);font-style:italic;font-size:22px;line-height:1.3;margin:0;color:var(--accent)}
.copy p{margin:0;max-width:60ch}
.pal{list-style:none;margin:6px 0 0;padding:0;display:flex;flex-wrap:wrap;gap:8px 16px;font-size:11px;color:var(--muted)}
.pal li{display:flex;align-items:center;gap:6px}
.chip{width:16px;height:16px;border-radius:50%;border:1px solid var(--line)}
.pal code{font-family:var(--f-caps);font-size:10px;letter-spacing:.06em}
.thumbs{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin-top:8px}
.th{all:unset;cursor:pointer;display:flex;flex-direction:column;gap:6px}
.th img{width:100%;aspect-ratio:1/1;object-fit:cover;border:1px solid var(--line);border-radius:2px;display:block;background:#e6e1d9}
.th span{font-size:9.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--muted);text-align:center}
.th.on img{border-color:var(--fg);outline:1px solid var(--fg)}
.th:focus-visible img{outline:2px solid var(--fg);outline-offset:2px}
footer{border-top:1px solid var(--line);padding-top:24px;color:var(--muted);font-size:12px;max-width:70ch}
@media (max-width:820px){.dir{grid-template-columns:1fr}.thumbs{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
<div class="wrap">
  <header>
    <div class="kicker">MFC · The Catch Cap · Rev I</div>
    <h1>MFC BOX</h1>
    <p class="serif">Пять направлений дизайна коробки.</p>
    <p>Все снимки сделаны на той же 3D-модели по реальной высечке Rev I и вкладышу Rev C. Печать внутри крышки показана как опция с двусторонней печатью. Дно у всех одинаковое: печать, флаг, «Designed in California» и значки.</p>
    <nav><a href="#stone">Stone</a><a href="#noir">Noir</a><a href="#coast">Coastline</a><a href="#mark">Big Mark</a><a href="#sun">Sun-faded</a></nav>
  </header>
%%SECTIONS%%
  <footer>Нажмите на миниатюру, чтобы открыть её крупно. Для каждого направления есть файлы для печати (PDF, текст в кривых) и редактируемые SVG в <code>cap-box/design/variants/</code>.</footer>
</div>
<script>
document.querySelectorAll('.dir').forEach(sec=>{
  const hero=sec.querySelector('.hero');
  sec.querySelectorAll('.th').forEach(b=>b.addEventListener('click',()=>{
    hero.src=b.dataset.src; hero.alt=b.querySelector('img').alt;
    sec.querySelectorAll('.th').forEach(x=>x.classList.toggle('on',x===b));
  }));
});
</script>
"""

if __name__ == "__main__":
    main()
