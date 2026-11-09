// Render an SVG (sized in mm) to a vector PDF with Chromium, which honours clip paths.
// usage: node svg2pdf.js in.svg out.pdf
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [inp, out] = process.argv.slice(2);
  const head = fs.readFileSync(inp, 'utf8').slice(0, 2000);
  const w = head.match(/width="([\d.]+)mm"/)[1], h = head.match(/height="([\d.]+)mm"/)[1];
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.goto('file://' + require('path').resolve(inp));
  await p.pdf({ path: out, width: w + 'mm', height: h + 'mm', printBackground: true, pageRanges: '1',
    margin: { top: '0', right: '0', bottom: '0', left: '0' } });
  await b.close();
})();
