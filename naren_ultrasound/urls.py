from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve as serve_media
from django.contrib.sitemaps.views import sitemap
from website.custom_sitemaps import (
    PagesSitemap,
    ServicesSitemap
)
from website import views
from website.sitemaps import (
    StaticViewSitemap,
    ServicesSitemap,
    PostsSitemap,
    CategoriesSitemap,
    TagsSitemap,
)

pages_sitemap = {
    'pages': PagesSitemap,
}

services_sitemap = {
    'services': ServicesSitemap,
}

pages_sitemap = {
    'pages': PagesSitemap,
}

services_sitemap = {
    'services': ServicesSitemap,
}

sitemaps = {
    'pages': StaticViewSitemap,
    'services': ServicesSitemap,
    'posts': PostsSitemap,
    'categories': CategoriesSitemap,
    'tags': TagsSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path("ckeditor5/", include('django_ckeditor_5.urls')),
    path('', include('website.urls')),


    path(
    'sitemap.xml',
    views.sitemap_index,
    name='sitemap'
),

    path(
    'robots.txt',
    views.robots_txt,
    name='robots_txt'
),

    path(
    'pages.xml',
    sitemap,
    {'sitemaps': pages_sitemap},
    name='pages_xml',
),

    path(
    'services.xml',
    sitemap,
    {'sitemaps': services_sitemap},
    name='services_xml',
),

    path(
    'posts.xml',
    sitemap,
    {'sitemaps': {'posts': PostsSitemap}},
    name='posts_xml',
),

path(
    'categories.xml',
    sitemap,
    {'sitemaps': {'categories': CategoriesSitemap}},
    name='categories_xml',
),

path(
    'tags.xml',
    sitemap,
    {'sitemaps': {'tags': TagsSitemap}},
    name='tags_xml',
),
]

# Serve MEDIA_ROOT ourselves.
#
# django.conf.urls.static.static() only returns a route while DEBUG is True, and
# WhiteNoise only ever serves STATIC_ROOT - it never touches MEDIA_ROOT. That
# combination is why /media/blog/<file>.png returned 404 once DEBUG was off.
# The route is derived from MEDIA_URL so nothing is hardcoded.
urlpatterns += [
    re_path(
        r'^%s(?P<path>.*)$' % settings.MEDIA_URL.lstrip('/'),
        serve_media,
        {'document_root': settings.MEDIA_ROOT},
        name='media',
    ),
]


