"""Keep existing article records while improving explicitly mapped public URLs."""
from django.urls.converters import SlugConverter

from .seo import ARTICLE_PUBLIC_SLUGS


class ArticleSlugConverter(SlugConverter):
    def to_python(self, value):
        return next(
            (stored for stored, public in ARTICLE_PUBLIC_SLUGS.items() if public == value),
            value,
        )

    def to_url(self, value):
        return ARTICLE_PUBLIC_SLUGS.get(value, value)
