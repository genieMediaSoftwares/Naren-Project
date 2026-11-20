"""Render an isolated fixture site and check it in a separate headless Chrome.

Never reads the production database or submits a form. Reports/screenshots are
written to outputs/responsive-check. Requires an installed Chrome on Windows.
"""
import argparse
import html
import json
import os
import re
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['DJANGO_SETTINGS_MODULE'] = 'naren_ultrasound.test_settings'

import django
django.setup()

from django.contrib.staticfiles import finders
from django.test import Client
from django.test.utils import setup_databases, teardown_databases
from django.urls import reverse
from website.models import BlogPost, DoctorProfile
from website.seo import ARTICLE_TOPICS, PAGE_METADATA

OUTPUT = ROOT / 'outputs/responsive-check'
CHROME = Path('C:/Program Files/Google/Chrome/Application/chrome.exe')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serve', action='store_true', help='Serve the isolated fixture site for local performance audits.')
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--compare-font-layout', action='store_true', help='Compare fully loaded homepage geometry with and without font preloads.')
    options = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    database = setup_databases(verbosity=0, interactive=False)
    try:
        for slug, (title, _) in ARTICLE_TOPICS.items():
            BlogPost.objects.create(
                slug=slug, title=title, meta_description='Local responsive check',
                featured_image='blog/tifascan.png',
                content='<h2>Understanding your appointment</h2><p>Local preview content for checking readable article layouts across screen sizes.</p>',
            )
        DoctorProfile.objects.create(photo='doctor/Doctor.jpeg', bio='Local preview of the existing doctor card.')
        paths = [reverse(name) for name in PAGE_METADATA]
        paths += [reverse('blog_detail', args=[slug]) for slug in ARTICLE_TOPICS]
        paths += [reverse('appointment_success'), reverse('contact_success')]
        client, pages = Client(), {}
        for path in paths:
            response = client.get(path)
            if response.status_code != 200:
                raise RuntimeError(f'Preview failed: {path}: {response.status_code}')
            markup = response.content.decode()
            # Keep this fixture preview offline and free of analytics events.
            markup = re.sub(r'<script\b[^>]*src="https://www\.googletagmanager\.com/[^>]*>\s*</script>', '', markup)
            markup = re.sub(r'(<iframe\b[^>]*\bsrc=)"[^"]*"', r'\1"about:blank"', markup)
            pages[path] = markup.encode()
        if options.compare_font_layout:
            pages['/font-before/'] = re.sub(rb'<link\b[^>]*rel="preload"[^>]*as="font"[^>]*>', b'', pages['/'])
            pages['/font-after/'] = pages['/']
        harness = r'''<!doctype html><html><head><meta charset="utf-8"></head><body>
<pre id="result">RUNNING</pre><iframe id="preview" style="border:0;height:1000px"></iframe>
<script>
const paths = PATHS, widths = [320,360,390,640,768,1024,1279,1280,1440,1920];
const frame = document.getElementById('preview');
const nextFrame = () => new Promise(resolve => setTimeout(resolve, 20));
(async () => {
 const results = [], failures = [];
 for (const path of paths) {
  document.getElementById('result').textContent = 'RUNNING ' + path + ' load';
  await new Promise(resolve => { frame.onload = resolve; frame.src = path; });
  const doc = frame.contentDocument;
  document.getElementById('result').textContent = 'RUNNING ' + path + ' images';
  for (const img of doc.images) img.loading = 'eager';
  for (let attempt = 0; attempt < 40 && [...doc.images].some(img => !img.complete); attempt++) {
   await new Promise(resolve => setTimeout(resolve, 100));
  }
  document.getElementById('result').textContent = 'RUNNING ' + path + ' fonts';
  await doc.fonts.ready;
  document.getElementById('result').textContent = 'RUNNING ' + path + ' widths';
  for (const width of widths) {
   frame.style.width = width + 'px';
   await nextFrame();
   const win = frame.contentWindow;
   const overflow = doc.documentElement.scrollWidth > win.innerWidth + 1;
   const offending = overflow ? [...doc.querySelectorAll('body *')].filter(el => {
    const r = el.getBoundingClientRect();
    return r.width && (r.right > win.innerWidth + 1 || r.left < -1);
   }).slice(0,12).map(el => ({tag:el.tagName,classes:el.className,text:el.textContent.trim().slice(0,55)})) : [];
   const brokenImages = [...doc.images].filter(img => !img.naturalWidth).map(img => img.getAttribute('src'));
   let splitCity = false;
   const heading = doc.querySelector('h1');
   if (heading) {
    const walker = doc.createTreeWalker(heading, win.NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
     const node = walker.currentNode, start = node.textContent.indexOf('Visakhapatnam');
     if (start >= 0) {
      const range = doc.createRange();
      range.setStart(node, start); range.setEnd(node, start + 'Visakhapatnam'.length);
      splitCity = splitCity || range.getClientRects().length > 1;
     }
    }
   }
   const button = doc.getElementById('menu-btn'), menu = doc.getElementById('mobile-menu');
   let menuOK = true;
   if (width < 1280) {
    button.click();
    menuOK = button.getAttribute('aria-expanded') === 'true' && win.getComputedStyle(menu).display !== 'none';
    doc.dispatchEvent(new win.KeyboardEvent('keydown', {key:'Escape',bubbles:true}));
    menuOK = menuOK && button.getAttribute('aria-expanded') === 'false';
   }
   const row = {path,width,scrollWidth:doc.documentElement.scrollWidth,overflow,brokenImages,menuOK,splitCity,offending};
   results.push(row);
   if (overflow || brokenImages.length || !menuOK || splitCity) failures.push(row);
  }
 }
 document.getElementById('result').textContent = JSON.stringify({pages:paths.length,checks:results.length,failures,results});
 document.title = 'COMPLETE';
})().catch(error => { document.getElementById('result').textContent = JSON.stringify({error:String(error)}); });
</script></body></html>'''.replace('PATHS', json.dumps(paths)).encode()
        if options.compare_font_layout:
            harness = r'''<!doctype html><html><body><pre id="result">RUNNING</pre>
<iframe id="preview" style="border:0;height:1000px"></iframe><script>
(async () => {
 const frame = document.getElementById('preview'), results = [], failures = [];
 for (const width of [390,1335,1440]) {
  const snapshots = [];
  for (const path of ['/font-before/','/font-after/']) {
   frame.style.width = width + 'px';
   await new Promise(resolve => { frame.onload = resolve; frame.src = path; });
   const doc = frame.contentDocument;
   for (const img of doc.images) img.loading = 'eager';
   for (let n=0;n<40 && [...doc.images].some(img => !img.complete);n++)
    await new Promise(resolve => setTimeout(resolve,100));
   await doc.fonts.ready;
   await new Promise(resolve => setTimeout(resolve,100));
   snapshots.push([...doc.querySelectorAll('body *')].map(el => {
    const r = el.getBoundingClientRect();
    return {tag:el.tagName,classes:el.className,x:r.x,y:r.y,width:r.width,height:r.height};
   }));
  }
  const differences = snapshots[0].flatMap((before,index) => {
   const after=snapshots[1][index];
   return !after || ['x','y','width','height'].some(key => Math.abs(before[key]-after[key])>0.05)
    ? [{before,after}] : [];
  });
  const row={width,elementsCompared:snapshots[0].length,differences};
  results.push(row);
  if (differences.length || snapshots[0].length!==snapshots[1].length) failures.push(row);
 }
 document.getElementById('result').textContent=JSON.stringify({checks:results.length,failures,results});
})().catch(error => document.getElementById('result').textContent=JSON.stringify({error:String(error)}));
</script></body></html>'''.encode()

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                path = unquote(urlsplit(self.path).path)
                data, content_type = pages.get(path), 'text/html; charset=utf-8'
                if path == '/responsive-check.html':
                    data = harness
                elif path == '/screenshot.html':
                    query = parse_qs(urlsplit(self.path).query)
                    preview_path = query.get('path', ['/'])[0]
                    width = int(query.get('width', ['390'])[0])
                    # Chrome's outer window has a minimum width. An iframe
                    # gives the screenshot an exact mobile layout viewport.
                    data = ('<!doctype html><style>html,body{margin:0}iframe{display:block;border:0}</style>'
                            f'<iframe src="{html.escape(preview_path, quote=True)}" width="{width}" height="1000"></iframe>').encode()
                elif path.startswith(('/static/', '/media/')):
                    if path.startswith('/static/'):
                        found = finders.find(path.removeprefix('/static/'))
                        target = Path(found) if found else None
                    else:
                        target = ROOT / path.lstrip('/')
                    if target and target.is_file() and target.resolve().is_relative_to(ROOT):
                        data = target.read_bytes()
                        content_type = {'.css':'text/css', '.woff2':'font/woff2', '.woff':'font/woff', '.ttf':'font/ttf', '.png':'image/png', '.webp':'image/webp', '.jpeg':'image/jpeg', '.jpg':'image/jpeg'}.get(target.suffix, 'application/octet-stream')
                self.send_response(200 if data is not None else 404)
                self.send_header('Content-Type', content_type)
                self.end_headers()
                if data is not None:
                    self.wfile.write(data)

        server = ThreadingHTTPServer(('127.0.0.1', options.port), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        origin = 'http://127.0.0.1:' + str(server.server_port)
        if options.serve:
            print('Isolated performance preview: ' + origin, flush=True)
            try:
                threading.Event().wait()
            except KeyboardInterrupt:
                pass
            finally:
                server.shutdown()
            return 0
        args = [str(CHROME), '--headless=new', '--no-first-run', '--no-default-browser-check', '--disable-background-networking', '--disable-sync', '--disable-extensions', '--disable-gpu', '--hide-scrollbars', '--user-data-dir=' + str(OUTPUT / 'chrome-profile')]
        try:
            result = subprocess.run(args + ['--dump-dom', '--virtual-time-budget=60000', origin + '/responsive-check.html'], capture_output=True, timeout=100, creationflags=subprocess.CREATE_NO_WINDOW)
            markup = result.stdout.decode('utf-8', errors='replace')
            match = re.search(r'<pre id="result">(.*?)</pre>', markup, re.S)
            if not match or match[1].startswith('RUNNING'):
                (OUTPUT / 'browser-output.html').write_text(markup, encoding='utf-8')
                (OUTPUT / 'browser-errors.txt').write_bytes(result.stderr)
                raise RuntimeError('Browser check did not complete: ' + (match[1] if match else 'no output'))
            report = json.loads(html.unescape(match[1]))
            report_name = 'font-layout-comparison.json' if options.compare_font_layout else 'report.json'
            (OUTPUT / report_name).write_text(json.dumps(report, indent=2), encoding='utf-8')
            print(json.dumps({k:v for k,v in report.items() if k != 'results'}))
            if options.compare_font_layout:
                return 1 if report.get('failures') or report.get('error') else 0
            for path, width in [('/gallery/',390),('/blog/',390),('/contact/',390),('/blog/',1280),('/',320)]:
                name = (path.strip('/') or 'home') + '-' + str(width) + '.png'
                preview_url = origin + '/screenshot.html?path=' + quote(path, safe='') + '&width=' + str(width)
                subprocess.run(args + [f'--window-size={width},1000', '--virtual-time-budget=4000', '--screenshot=' + str(OUTPUT / name), preview_url], capture_output=True, timeout=25, creationflags=subprocess.CREATE_NO_WINDOW)
            return 1 if report.get('failures') or report.get('error') else 0
        finally:
            server.shutdown()
    finally:
        teardown_databases(database, verbosity=0)


if __name__ == '__main__':
    raise SystemExit(main())
