"""Search metadata coverage, escaping and canonical sitemap regression checks."""
import json
import re
import xml.etree.ElementTree as ET

from django.test import TestCase, override_settings
from django.urls import reverse

from .models import BlogPost
from .seo import ARTICLE_TOPICS, CLINIC_ID, ORIGIN, PAGE_METADATA, SERVICE_ENTITIES


@override_settings(ALLOWED_HOSTS=["testserver", "narenultrasound.in"])
class SearchMetadataTests(TestCase):
    def test_all_26_pages_keep_content_and_unique_metadata(self):
        titles, descriptions = [], []
        for slug, (title, _) in ARTICLE_TOPICS.items():
            BlogPost.objects.create(
                slug=slug, title=title, content='<h3>Original clinical text</h3>',
                meta_description='Original stored metadata', featured_image='blog/original.png',
            )
        paths = [reverse(name) for name in PAGE_METADATA]
        paths += [reverse('blog_detail', args=[slug]) for slug in ARTICLE_TOPICS]
        self.assertEqual(len(paths), 26)
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path + '?utm_source=test')
                self.assertEqual(response.status_code, 200)
                html = response.content.decode()
                self.assertEqual(len(re.findall(r'<h1\b', html)), 1)
                title = re.search(r'<title>(.*?)</title>', html, re.S).group(1)
                description = re.search(r'name="description"\s+content="([^"]*)"', html).group(1)
                titles.append(title)
                descriptions.append(description)
                self.assertIn('href="' + ORIGIN + path + '"', html)
                schemas = [json.loads(script) for script in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]
                self.assertEqual(schemas[0]['@type'], 'MedicalClinic')
                self.assertEqual(schemas[0]['@id'], CLINIC_ID)
                graph = schemas[1]['@graph']
                self.assertEqual(graph[1]['url'], ORIGIN + path)
                if path.startswith('/blog/') and path != '/blog/':
                    self.assertIn('<h3>Original clinical text</h3>', html)
                    article = graph[-1]
                    self.assertEqual(article['@type'], 'BlogPosting')
                    self.assertNotIn('author', article)
                    self.assertNotIn('dateModified', article)
                    self.assertEqual(article['image'], ORIGIN + '/media/blog/original.png')
        self.assertEqual(len(set(titles)), 26)
        self.assertEqual(len(set(descriptions)), 26)
        self.assertTrue(all(p.content == '<h3>Original clinical text</h3>' for p in BlogPost.objects.all()))

    def test_service_entities_resolve_to_existing_headings_and_links(self):
        html = self.client.get(reverse('services')).content.decode()
        graph = json.loads(re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)[1])['@graph']
        services = [node for node in graph if node['@type'] == 'Service']
        self.assertEqual(len(services), 6)
        for node, (fragment, name) in zip(services, SERVICE_ENTITIES):
            self.assertEqual(node['name'], name)
            self.assertEqual(node['provider'], {'@id': CLINIC_ID})
            self.assertIn('id="' + fragment + '"', html)
            self.assertIn('href="/services/#' + fragment + '"', html)
            self.assertIn({'@id': node['@id']}, graph[1]['mainEntity'])
        self.assertNotIn('<h6', html)

    def test_doctor_identity_has_no_inferred_credentials(self):
        html = self.client.get(reverse('doctors')).content.decode()
        graph = json.loads(re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)[1])['@graph']
        person = graph[-1]
        self.assertEqual(person['name'], 'Dr. Naren Satya')
        self.assertEqual(set(person), {'@type', '@id', 'name', 'url', 'mainEntityOfPage'})
        self.assertEqual(graph[1]['mainEntity'], {'@id': person['@id']})

    def test_robots_and_sitemap_index(self):
        response = self.client.get('/robots.txt')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Sitemap: ' + ORIGIN + '/sitemap.xml', response.content.decode())
        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)
        root = ET.fromstring(response.content)
        locations = [n.text for n in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
        self.assertEqual(set(locations), {ORIGIN + path for path in ['/pages.xml', '/services.xml', '/posts.xml']})

    def test_schema_escaping_and_unmapped_article_fallback(self):
        post = BlogPost.objects.create(
            title='Quoted "title" </script><script>alert(1)</script>', slug='unmapped',
            content='<p>Original</p>', meta_description='A "quoted" description & more',
            featured_image='',
        )
        html = self.client.get(reverse('blog_detail', args=[post.slug])).content.decode()
        scripts = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        self.assertEqual(len(scripts), 2)
        article = json.loads(scripts[1])['@graph'][-1]
        self.assertEqual(article['headline'], post.title)
        self.assertNotIn('image', article)
        self.assertNotIn('</script>', scripts[1])
        for attribute in ['property="og:image"', 'name="twitter:image"']:
            image = re.search(re.escape(attribute) + r'\s+content="([^"]+)"', html)
            self.assertIsNotNone(image)
            self.assertEqual(image.group(1), ORIGIN + '/static/images/logo.png')

    def test_sitemaps_canonical_host_coverage_and_drafts(self):
        published = BlogPost.objects.create(title='Published', slug='published', content='Text', meta_description='Text')
        BlogPost.objects.create(title='Draft', slug='draft', content='Text', meta_description='Text', is_published=False)
        ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        urls = []
        for path in ['/pages.xml', '/services.xml', '/posts.xml']:
            response = self.client.get(path, HTTP_HOST='narenultrasound.in')
            self.assertEqual(response.status_code, 200)
            root = ET.fromstring(response.content)
            urls.extend(n.text for n in root.findall('.//s:loc', ns))
            if path == '/posts.xml':
                self.assertEqual(root.find('.//s:lastmod', ns).text, published.updated_at.date().isoformat())
        self.assertEqual(len(urls), len(set(urls)))
        self.assertEqual(len(urls), 9)
        self.assertTrue(all(u.startswith(ORIGIN + '/') for u in urls))
        self.assertIn(ORIGIN + '/blog/', urls)
        self.assertNotIn(ORIGIN + '/blog/draft/', urls)

    def test_success_pages_stay_noindex_and_hero_is_not_lazy(self):
        for route in ['contact_success', 'appointment_success']:
            html = self.client.get(reverse(route)).content.decode()
            self.assertIn('content="noindex, follow"', html)
        html = self.client.get('/').content.decode()
        images = re.findall(r'<img\b[^>]*>', html)
        hero = next(i for i in images if '/images/hero.png' in i)
        self.assertNotIn('loading="lazy"', hero)
        self.assertTrue(all('loading="lazy"' not in i for i in images if '/images/logo.png' in i))
        self.assertTrue(all('loading="lazy"' in i for i in images if '/images/service' in i))
