from .sitemap_base import CanonicalSitemap
from django.urls import reverse
from .models import BlogPost


class StaticViewSitemap(CanonicalSitemap):

    protocol = "https"
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
            'blog_list',
        ]

    def location(self, item):
        return reverse(item)
    
class ServicesSitemap(CanonicalSitemap):

    protocol = "https"
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return ['services']

    def location(self, item):
        return reverse(item)


class PostsSitemap(CanonicalSitemap):

    protocol = "https"
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return BlogPost.objects.filter(
            is_published=True
        ).order_by('-created_at')

    def location(self, obj):
        return reverse(
            'blog_detail',
            args=[obj.slug]
        )

    def lastmod(self, obj):
        return obj.updated_at



class CategoriesSitemap(CanonicalSitemap):

    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return []



class TagsSitemap(CanonicalSitemap):

    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return []
