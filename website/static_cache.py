"""Only content-addressed display assets may receive an immutable cache policy."""
import re

_VERSIONED = re.compile(r'/seo-(?:images|assets)/[0-9a-f]{20}(?:-\d+\.(?:webp|png)|\.(?:css|woff2?|ttf))$')


def immutable_seo_asset(path, url):
    return bool(_VERSIONED.search(url))
