"""Download the existing public font/icon styles for local, versioned delivery.

Run explicitly when updating fonts. Normal image/asset builds remain offline.
"""
import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'website/static/vendor/fonts'
SOURCES = (
    'https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Poppins:wght@300;400;500;600;700;800&display=swap',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css',
)
LICENSES = {
    'poppins-OFL.txt': 'https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/OFL.txt',
    'cormorant-garamond-OFL.txt': 'https://raw.githubusercontent.com/google/fonts/main/ofl/cormorantgaramond/OFL.txt',
    'bootstrap-icons-LICENSE.txt': 'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/LICENSE',
    'fontawesome-LICENSE.txt': 'https://raw.githubusercontent.com/FortAwesome/Font-Awesome/6.5.1/LICENSE.txt',
}
ALLOWED_HOSTS = {'fonts.googleapis.com', 'fonts.gstatic.com', 'cdnjs.cloudflare.com', 'cdn.jsdelivr.net', 'raw.githubusercontent.com'}


def build():
    session = requests.Session()
    session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
    assets, sources, styles = {}, {}, []

    @lru_cache(maxsize=None)
    def fetch(url):
        if urlsplit(url).scheme != 'https' or urlsplit(url).hostname not in ALLOWED_HOSTS:
            raise ValueError('Unexpected asset origin: ' + url)
        response = session.get(url, timeout=30)
        response.raise_for_status()
        if not response.content or len(response.content) > 4 * 1024 * 1024:
            raise ValueError('Unexpected asset size: ' + url)
        return response.content

    for url in SOURCES:
        css = fetch(url).decode('utf-8')

        def local_url(match):
            value = match.group(1).strip().strip('\"\'')
            if value.startswith('data:'):
                return match.group(0)
            absolute = urljoin(url, value)
            data = fetch(absolute)
            ext = Path(urlsplit(absolute).path).suffix
            if ext not in ('.woff2', '.woff', '.ttf'):
                raise ValueError('Unexpected font format: ' + absolute)
            name = hashlib.sha256(data).hexdigest()[:20] + ext
            assets[name] = data
            sources[name] = absolute
            return 'url("' + name + '")'

        css = re.sub(r'url\(([^)]+)\)', local_url, css)
        css = re.sub(r'font-display\s*:\s*\w+\s*;?', '', css)
        css = re.sub(r'@font-face\s*\{', '@font-face{font-display:swap;', css)
        styles.append('/* Source: ' + url + ' */\n' + css)
    licenses = {name: fetch(url) for name, url in LICENSES.items()}
    DEST.mkdir(parents=True, exist_ok=True)
    for name, data in {**assets, **licenses}.items():
        (DEST / name).write_bytes(data)
    (DEST / 'site-fonts.css').write_text('\n'.join(styles) + '\n', encoding='utf-8')
    (DEST / 'sources.json').write_text(json.dumps({'stylesheets': SOURCES, 'fonts': sources, 'licenses': LICENSES}, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'font_files': len(assets), 'font_bytes': sum(map(len, assets.values()))}))


if __name__ == '__main__':
    build()
