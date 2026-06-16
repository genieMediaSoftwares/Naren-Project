from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class PagesSitemap(Sitemap):

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
        ]

    def location(self, item):
        return reverse(item)


class ServicesSitemap(Sitemap):

    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return [
            'services',
        ]

    def location(self, item):
        return reverse(item)