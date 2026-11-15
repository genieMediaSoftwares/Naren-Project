from django.contrib.sitemaps import Sitemap

from .seo import ORIGIN


class CanonicalSitemap(Sitemap):
    protocol = "https"

    def get_domain(self, site=None):
        # Canonical identity must not depend on an incoming Host header.
        return ORIGIN.removeprefix("https://")
