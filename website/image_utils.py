"""Helpers for pulling a remote (e.g. ChatGPT / OpenAI) image into Django media storage.

A ChatGPT image URL is a short-lived, signed link. Storing that URL on the model
and rendering it in the template means the <img> breaks as soon as the link
expires. Everything here exists so the *bytes* are copied into MEDIA_ROOT once,
and the database only ever holds the relative path that ImageField.url resolves.
"""

import os
from urllib.parse import unquote, urlparse

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils.text import get_valid_filename

# Content types we accept, mapped to the extension we store them under.
# PNG stays PNG - ultrasound images are never re-encoded to JPEG here.
CONTENT_TYPE_EXTENSIONS = {
    'image/png': '.png',
    'image/jpeg': '.jpg',
    'image/jpg': '.jpg',
    'image/webp': '.webp',
    'image/gif': '.gif',
}

ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}

DEFAULT_MAX_BYTES = 20 * 1024 * 1024
DEFAULT_TIMEOUT = 30


def _max_bytes():
    return getattr(
        settings, 'BLOG_IMAGE_DOWNLOAD_MAX_BYTES', DEFAULT_MAX_BYTES
    )


def _timeout():
    return getattr(
        settings, 'BLOG_IMAGE_DOWNLOAD_TIMEOUT', DEFAULT_TIMEOUT
    )


def build_safe_filename(name, extension='.png'):
    """Return a filesystem-safe file name that keeps its original extension.

    'Amniotic_Fluid.png'                 -> 'Amniotic_Fluid.png'
    'Twin Tiffa Scan.PNG'                -> 'Twin_Tiffa_Scan.png'
    '../../etc/passwd'                   -> 'passwd.png'
    'img-Ab12.png?st=2026&se=2026&sig=x' -> 'img-Ab12.png'
    """
    # Drop any directory component a remote URL may have smuggled in.
    name = unquote(name or '').split('?')[0].split('#')[0]
    for separator in ('/', os.sep, os.altsep or '/'):
        name = name.rsplit(separator, 1)[-1]

    stem, ext = os.path.splitext(name)
    ext = ext.lower()

    if ext not in ALLOWED_EXTENSIONS:
        # No usable extension on the URL (very common for signed ChatGPT
        # links) - fall back to the one derived from the Content-Type.
        stem = stem or name
        ext = extension

    stem = get_valid_filename(stem).strip('._-') or 'image'

    # Leave headroom for the suffix FileSystemStorage adds on a name clash.
    return '%s%s' % (stem[:80], ext)


def download_image(url, *, filename=None):
    """Download ``url`` and return ``(safe_filename, ContentFile)``.

    Raises ValidationError if the URL is unusable, too large, or is not an image.
    """
    parsed = urlparse((url or '').strip())

    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        raise ValidationError(
            'Enter a full http:// or https:// image URL.'
        )

    try:
        response = requests.get(
            parsed.geturl(),
            timeout=_timeout(),
            stream=True,
            headers={'User-Agent': 'naren-ultrasound-blog/1.0'},
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ValidationError(
            'Could not download the image: %s. ChatGPT image links expire '
            'quickly - open the image, copy a fresh link, or upload the file '
            'directly.' % exc
        )

    content_type = response.headers.get('Content-Type', '').split(';')[0].strip().lower()
    extension = CONTENT_TYPE_EXTENSIONS.get(content_type)

    limit = _max_bytes()
    chunks = []
    size = 0

    try:
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            size += len(chunk)
            if size > limit:
                raise ValidationError(
                    'The image is larger than %s MB.' % (limit // (1024 * 1024))
                )
            chunks.append(chunk)
    finally:
        response.close()

    data = b''.join(chunks)

    if not data:
        raise ValidationError('The downloaded image was empty.')

    if extension is None:
        # Content-Type was missing or generic (application/octet-stream is
        # common on signed URLs); sniff the real format from the bytes.
        extension = _sniff_extension(data)

    name = build_safe_filename(filename or parsed.path, extension)
    _verify_is_image(data)

    return name, ContentFile(data)


def _sniff_extension(data):
    from PIL import Image, UnidentifiedImageError
    from io import BytesIO

    try:
        with Image.open(BytesIO(data)) as image:
            fmt = (image.format or '').lower()
    except (UnidentifiedImageError, OSError):
        raise ValidationError('That URL did not return a valid image file.')

    return {
        'png': '.png',
        'jpeg': '.jpg',
        'webp': '.webp',
        'gif': '.gif',
    }.get(fmt, '.png')


def _verify_is_image(data):
    """Guard against saving an HTML error page (or worse) under an .png name."""
    from PIL import Image, UnidentifiedImageError
    from io import BytesIO

    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError):
        raise ValidationError('That URL did not return a valid image file.')


def save_image_from_url(image_field, url, *, filename=None, save=False):
    """Download ``url`` into ``image_field``'s storage.

    ``image_field`` is the field descriptor, e.g. ``post.featured_image``.
    The field's own ``upload_to`` decides the directory, and the resulting
    relative path (``blog/<name>.png``) is what ends up in the database.
    """
    name, content = download_image(url, filename=filename)
    image_field.save(name, content, save=save)
    return image_field.name
