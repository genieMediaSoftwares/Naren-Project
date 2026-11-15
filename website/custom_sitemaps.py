from .sitemap_base import CanonicalSitemap
from django.urls import reverse


class PagesSitemap(CanonicalSitemap):

    protocol = "https"
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return [
            'home',
            'about',
            'doctors',
            'gallery',
            'contact',
            'patient_info',
            'blog_list',
        ]

    def location(self, item):
        return reverse(item)


class ServicesSitemap(CanonicalSitemap):

    protocol = "https"
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return [
            'services',
        ]

    def location(self, item):
        return reverse(item)
