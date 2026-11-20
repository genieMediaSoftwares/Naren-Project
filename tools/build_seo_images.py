"""Generate versioned display variants for explicitly public image sources.

Run with ``python tools/build_seo_images.py`` before collectstatic. Originals,
medical article bodies and database fields are never changed. No network I/O.
"""
import hashlib
import json
import shutil
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'website' / 'static' / 'seo-images'
PUBLIC_BLOG_IMAGES = (
    'Twin_Routine_Growth_Scan.png', 'Routine_Growth_scan.png', 'Twin_Late_Tiffa.png',
    'Late_Tiffa.png', 'Twin_Viability_Scan.png', 'Viability_Scan.png',
    'Early_Twin_Tiffa_Scan.png', 'Early_Tiffa_Scan_bgt0pNk.png',
    'WhatsApp_Image_2026-09-01_at_2.11.07_PM.jpeg',
    'WhatsApp_Image_2026-09-01_at_2.26.57_PM_1.jpeg',
    'WhatsApp_Image_2026-09-01_at_3.41.29_PM.jpeg',
    'WhatsApp_Image_2026-08-31_at_2.41.10_PM.jpeg',
    'Twin_NT_Scan.jpeg', 'NT_Scan.jpeg', 'Amniotic_Fluid.png',
    'Twin_Tiffa_Scan.png', 'tifascan.png', 'fetal.jpg',
)


def build():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    sources = [(p, '/static/images/' + p.name) for p in sorted((ROOT / 'website/static/images').iterdir()) if p.suffix.lower() in {'.png', '.jpg', '.jpeg'}]
    sources += [(ROOT / 'media/blog' / name, '/media/blog/' + name) for name in PUBLIC_BLOG_IMAGES]
    # This photo is already public on the existing article doctor card.
    sources.append((ROOT / 'media/doctor/Doctor.jpeg', '/media/doctor/Doctor.jpeg'))
    manifest = {}
    for path, url in sources:
        if not path.is_file():
            continue  # Unknown/new uploads keep their original-image fallback.
        data = path.read_bytes()
        with Image.open(BytesIO(data)) as original:
            image = ImageOps.exif_transpose(original).convert('RGBA' if 'A' in original.getbands() else 'RGB')
            width, height = image.size
            # Small logo variants retain transparency and the full image.
            widths = sorted({min(width, w) for w in ((96, 192, 384) if path.name == 'logo.png' else (480, 768, 1280))})
            variants = []
            for target in widths:
                resized = image.copy()
                resized.thumbnail((target, max(1, round(height * target / width))), Image.Resampling.LANCZOS)
                buf = BytesIO()
                resized.save(buf, 'WEBP', quality=88, method=6)
                content = buf.getvalue()
                digest = hashlib.sha256(content).hexdigest()[:20]
                filename = f'{digest}-{resized.width}.webp'
                destination = OUTPUT / filename
                if not destination.exists() or destination.read_bytes() != content:
                    destination.write_bytes(content)
                variants.append({'path': 'seo-images/' + filename, 'width': resized.width, 'bytes': len(content)})
            manifest[url] = {'width': width, 'height': height, 'original_bytes': len(data), 'variants': variants}
    asset_output = ROOT / 'website/static/seo-assets'
    asset_output.mkdir(parents=True, exist_ok=True)
    font_root = ROOT / 'website/static/vendor/fonts'
    for font in sorted(font_root.glob('*')):
        if font.suffix in ('.woff', '.woff2', '.ttf'):
            digest = hashlib.sha256(font.read_bytes()).hexdigest()[:20]
            if font.stem != digest:
                raise ValueError('Font filename does not match its content: ' + font.name)
            shutil.copyfile(font, asset_output / font.name)
    with Image.open(ROOT / 'website/static/images/logo.png') as logo:
        icon = ImageOps.exif_transpose(logo).convert('RGBA')
        icon.thumbnail((32, 32), Image.Resampling.LANCZOS)
        buf = BytesIO()
        icon.save(buf, 'PNG', optimize=True)
        data = buf.getvalue()
        filename = hashlib.sha256(data).hexdigest()[:20] + '-32.png'
        (asset_output / filename).write_bytes(data)
        manifest['/static/images/favicon.png'] = {'path': 'seo-assets/' + filename}
    stylesheets = {
        'css/dist/styles.css': ROOT / 'theme/static/css/dist/styles.css',
        'css/responsive.css': ROOT / 'website/static/css/responsive.css',
        'vendor/fonts/site-fonts.css': font_root / 'site-fonts.css',
    }
    for relative, path in stylesheets.items():
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()[:20]
        filename = digest + '.css'
        (asset_output / filename).write_bytes(data)
        manifest['/static/' + relative] = {'path': 'seo-assets/' + filename}
    text = json.dumps(manifest, indent=2, sort_keys=True) + '\n'
    (OUTPUT / 'manifest.json').write_text(text, encoding='utf-8')
    images = [entry for entry in manifest.values() if 'variants' in entry]
    print(json.dumps({'sources': len(images), 'original_bytes': sum(x['original_bytes'] for x in images),
                      'largest_variant_bytes': sum(x['variants'][-1]['bytes'] for x in images)}))


if __name__ == '__main__':
    build()
