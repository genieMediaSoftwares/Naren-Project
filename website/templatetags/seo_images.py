"""Build-time image variants, with original-image fallback and no runtime writes."""
import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote, urlsplit

from django import template
from django.templatetags.static import static
from django.utils.html import format_html_join

from website.seo import ORIGIN

register = template.Library()


@lru_cache(maxsize=1)
def image_manifest():
    path = Path(__file__).resolve().parents[1] / 'static' / 'seo-images' / 'manifest.json'
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


@register.simple_tag
def seo_static(path, fallback=''):
    """Versioned CSS when built, original static path when not available."""
    entry = image_manifest().get('/static/' + path, {})
    return static(entry.get('path') or fallback or path)


@register.simple_tag
def seo_font_preloads():
    """Discover critical fonts before stylesheets to avoid a late font swap."""
    fonts = image_manifest().get('/static/vendor/fonts/site-fonts.css', {}).get('preloads', [])
    return format_html_join(
        '\n',
        '<link rel="preload" href="{}" as="font" type="font/woff2" crossorigin>',
        ((static(path),) for path in fonts),
    )


@register.inclusion_tag('includes/seo_image.html')
def seo_image(source, alt='', css='', sizes='100vw', eager=False, priority=False, image_style=''):
    """Never fetch an image or infer dimensions for an unknown/remote upload."""
    source = str(getattr(source, 'url', source) or '')
    parsed = urlsplit(source)
    local = not parsed.netloc or parsed.netloc == urlsplit(ORIGIN).netloc
    key = unquote(parsed.path) if local else ''
    entry = image_manifest().get(key, {})
    variants = entry.get('variants', [])
    return {
        'src': source, 'alt': alt, 'css': css, 'sizes': sizes, 'image_style': image_style,
        'width': entry.get('width'), 'height': entry.get('height'),
        'srcset': ', '.join(f"{static(v['path'])} {v['width']}w" for v in variants),
        'eager': eager, 'priority': priority,
    }
