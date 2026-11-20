"""Root crawler files, supplied clinic copy and published-only link coverage."""
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

from django.test import TestCase, override_settings
from django.urls import get_resolver, resolve, reverse

from .models import BlogPost
from .seo import ARTICLE_TOPICS, ORIGIN, PAGE_METADATA
from . import views


@override_settings(ALLOWED_HOSTS=['testserver', 'narenultrasound.in', 'www.narenultrasound.in'])
class CrawlerGuidanceTests(TestCase):
    def test_root_routes_are_unique_and_plain_text_in_development_and_production(self):
        for path, name, view in (
            ('/robots.txt', 'robots_txt', views.robots_txt),
            ('/llms.txt', 'llms_txt', views.llms_txt),
        ):
            self.assertEqual(reverse(name), path)
            self.assertIs(resolve(path).func, view)
            self.assertEqual(sum(str(p.pattern) == path.lstrip('/') for p in get_resolver().url_patterns), 1)
            for debug in (False, True):
                with self.subTest(path=path, debug=debug), override_settings(DEBUG=debug):
                    for method in (self.client.get, self.client.head):
                        response = method(path)
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response['Content-Type'], 'text/plain; charset=utf-8')
            self.assertNotIn('<html', self.client.get(path).content.decode())

    def test_robots_matches_requested_rules_and_preserves_public_crawling(self):
        text = self.client.get('/robots.txt').content.decode('utf-8')
        directives = [line for line in text.splitlines() if line and not line.startswith('#')]
        self.assertEqual(directives, [
            'User-agent: *', 'Allow: /', 'Disallow: /admin/',
            'Sitemap: ' + ORIGIN + '/sitemap.xml',
        ])
        self.assertTrue(text.startswith('# robots.txt for ' + ORIGIN + '/\n'))
        self.assertIn('# These rules do not replace authentication or access controls.', text)
        self.assertIn('# ' + ORIGIN + '/llms.txt', text)
        self.assertNotIn('\\', text)
        blocked = [line.removeprefix('Disallow: ') for line in text.splitlines() if line.startswith('Disallow: ')]
        public = [reverse(name) for name in PAGE_METADATA]
        public += ['/blog/published-article/', '/static/css/responsive.css', '/static/images/hero.png', '/media/blog/image.png', '/llms.txt']
        for path in public:
            self.assertFalse(any(path.startswith(prefix) for prefix in blocked), path)
        self.assertEqual(resolve('/admin/').view_name, 'admin:index')
        self.assertRedirects(self.client.get('/admin/'), '/admin/login/?next=/admin/', fetch_redirect_response=False)

    def test_llms_preserves_supplied_content_and_all_internal_links_work(self):
        for slug, (title, _) in ARTICLE_TOPICS.items():
            BlogPost.objects.create(slug=slug, title=title, content='<p>Original article</p>', meta_description='Original metadata')
        text = self.client.get('/llms.txt?utm_source=test', HTTP_HOST='narenultrasound.in').content.decode('utf-8')
        self.assertTrue(text.startswith('# Naren Ultrasound & Fetal Medicine Center\n'))
        for expected in (
            'Information on this website is educational and does not replace individualized medical advice.',
            'Antenatal & Gynecological Scans: TIFFA/anomaly scans',
            'amniocentesis and fetal reduction; suitability must be determined by the treating clinician.',
            'Dr. Naren Satya, Consultant Radiologist and Fetal Medicine Specialist.',
            '14-34-9/1, 14-34-9/2 (Opp. Saibaba Temple)',
            'Maharanipeta, Visakhapatnam, Andhra Pradesh 530002, India.',
            '+91 91823 95352; 0891-4599116.',
            '(mailto:narenultrasound@gmail.com)',
            'Monday–Saturday, 8:00 AM–8:00 PM India Standard Time; closed Sunday.',
        ):
            self.assertIn(expected, text)
        self.assertNotIn('&amp;', text)
        self.assertNotIn('testserver', text)
        self.assertNotIn('utm_source', text)
        urls = re.findall(r'\((https://[^)]+)\)', text)
        self.assertGreaterEqual(len(set(urls)), 18)
        article_urls = {url for url in urls if urlsplit(url).path.startswith('/blog/') and urlsplit(url).path != '/blog/'}
        self.assertEqual(len(article_urls), 10)
        for url in set(urls):
            self.assertTrue(url.startswith(ORIGIN + '/'), url)
            response = self.client.get(urlsplit(url).path)
            self.assertEqual(response.status_code, 200, url)
        for post in BlogPost.objects.all():
            self.assertEqual(post.content, '<p>Original article</p>')
            self.assertEqual(post.meta_description, 'Original metadata')

    def test_llms_omits_missing_draft_and_deleted_article_links(self):
        slug = 'nuchal-translucency-scan-a-complete-guide'
        path = reverse('blog_detail', args=[slug])
        self.assertNotIn(ORIGIN + path, self.client.get('/llms.txt').content.decode())
        post = BlogPost.objects.create(slug=slug, title='NT guide', content='Original', meta_description='Original', is_published=False)
        self.assertNotIn(ORIGIN + path, self.client.get('/llms.txt').content.decode())
        post.is_published = True
        post.save(update_fields=['is_published'])
        self.assertIn(ORIGIN + path, self.client.get('/llms.txt').content.decode())
        post.is_published = False
        post.save(update_fields=['is_published'])
        self.assertNotIn(ORIGIN + path, self.client.get('/llms.txt').content.decode())
        post.delete()
        self.assertNotIn(ORIGIN + path, self.client.get('/llms.txt').content.decode())

    def test_existing_sitemap_index_and_published_only_coverage_are_unchanged(self):
        published = BlogPost.objects.create(slug='published-article', title='Published article', content='Original', meta_description='Original')
        BlogPost.objects.create(slug='draft-article', title='Draft article', content='Original', meta_description='Original', is_published=False)
        ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        index = self.client.get('/sitemap.xml')
        self.assertEqual(index.status_code, 200)
        sitemap_urls = [node.text for node in ET.fromstring(index.content).findall('.//s:loc', ns)]
        self.assertEqual(sitemap_urls, [ORIGIN + path for path in ('/pages.xml', '/services.xml', '/posts.xml')])
        locations = []
        for url in sitemap_urls:
            response = self.client.get(urlsplit(url).path)
            self.assertEqual(response.status_code, 200)
            locations += [node.text for node in ET.fromstring(response.content).findall('.//s:loc', ns)]
        expected = {ORIGIN + reverse(name) for name in PAGE_METADATA}
        expected.add(ORIGIN + reverse('blog_detail', args=[published.slug]))
        self.assertEqual(set(locations), expected)
        self.assertEqual(len(locations), len(set(locations)))
        self.assertFalse(any('/admin/' in url or '/draft-article/' in url for url in locations))
