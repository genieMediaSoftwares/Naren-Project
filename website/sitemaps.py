from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import BlogPost


class StaticViewSitemap(Sitemap):

    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return [
            'home',
            'about',
            'services',
            'doctors',
            'gallery',
            'patient_info',
            'contact',
        ]

    def location(self, item):
        return reverse(item)
    
class ServicesSitemap(Sitemap):

    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return ['services']

    def location(self, item):
        return reverse(item)


class PostsSitemap(Sitemap):

    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return BlogPost.objects.filter(
            is_published=True
        )

    def location(self, obj):
        return reverse(
            'blog_detail',
            args=[obj.slug]
        )



class CategoriesSitemap(Sitemap):

    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return []



class TagsSitemap(Sitemap):

    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return []