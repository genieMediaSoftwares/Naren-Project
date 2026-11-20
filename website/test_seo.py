"""Search metadata coverage, escaping and canonical sitemap regression checks."""
import json
import hashlib
import re
from html import unescape
from pathlib import Path
import xml.etree.ElementTree as ET

from django.test import TestCase, override_settings
from django.urls import reverse
from django.template import Context, Template
from django.test import RequestFactory
from django.http import HttpResponse
from PIL import Image
from whitenoise.middleware import WhiteNoiseMiddleware

from .models import BlogPost
from .seo import ARTICLE_TOPICS, CLINIC_ID, ORIGIN, PAGE_METADATA, SERVICE_ENTITIES
from .templatetags.seo_images import image_manifest
from .static_cache import immutable_seo_asset


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
                self.assertLessEqual(len(unescape(title)), 60)
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

    def test_contact_and_gallery_keep_service_and_appointment_links(self):
        for route in ('contact', 'gallery'):
            with self.subTest(route=route):
                html = self.client.get(reverse(route)).content.decode()
                self.assertIn('href="' + reverse('services') + '"', html)
                self.assertIn('href="' + reverse('patient_info') + '"', html)

    def test_tiffa_url_redirect_links_and_sitemap_preserve_the_article(self):
        slug = 'your-babys-first-detailed-health-check-understandi'
        body = '<p>Existing TIFFA article and images remain intact.</p>'
        post = BlogPost.objects.create(
            title='Existing TIFFA title', slug=slug, content=body,
            meta_description='Existing description', featured_image='blog/tifascan.png',
        )
        canonical = '/blog/tiffa-scan-guide/'
        self.assertEqual(reverse('blog_detail', args=[slug]), canonical)
        for method in (self.client.get, self.client.head):
            response = method('/blog/' + slug + '/?utm_source=audit&ref=original')
            self.assertEqual(response.status_code, 301)
            self.assertEqual(response['Location'], canonical + '?utm_source=audit&ref=original')
        html = self.client.get(canonical).content.decode()
        self.assertIn(body, html)
        self.assertIn('href="' + ORIGIN + canonical + '"', html)
        self.assertIn('content="' + ORIGIN + canonical + '"', html)
        for path in (reverse('blog_list'), reverse('services')):
            self.assertIn('href="' + canonical + '"', self.client.get(path).content.decode())
        sitemap = self.client.get('/posts.xml').content.decode()
        self.assertIn(ORIGIN + canonical, sitemap)
        self.assertNotIn(slug, sitemap)
        post.refresh_from_db()
        self.assertEqual(post.slug, slug)
        self.assertEqual(post.content, body)
        self.assertEqual(post.featured_image.name, 'blog/tifascan.png')
        post.is_published = False
        post.save(update_fields=['is_published'])
        for path in (canonical, '/blog/' + slug + '/'):
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_new_long_article_titles_keep_full_visible_heading(self):
        heading = 'Understanding your ultrasound appointment and preparing questions for your referring doctor'
        post = BlogPost.objects.create(title=heading, slug='new-long-title', content='<p>Original</p>', meta_description='Original')
        html = self.client.get(reverse('blog_detail', args=[post.slug])).content.decode()
        title = unescape(re.search(r'<title>(.*?)</title>', html, re.S).group(1))
        self.assertLessEqual(len(title), 60)
        self.assertTrue(title.endswith(' | Naren Ultrasound'))
        self.assertIn(heading, html)

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

    def test_breadcrumbs_match_visible_navigation_and_ignore_query_parameters(self):
        post = BlogPost.objects.create(title='Patient "guide" & questions', slug='patient-guide', content='Original', meta_description='Original', featured_image='')
        path = reverse('blog_detail', args=[post.slug])
        html = self.client.get(path + '?utm_source=example').content.decode()
        scripts = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        graph = json.loads(scripts[1])['@graph']
        crumbs = next(n for n in graph if n['@type'] == 'BreadcrumbList')
        self.assertEqual([n['position'] for n in crumbs['itemListElement']], [1, 2, 3])
        self.assertEqual([n['item'] for n in crumbs['itemListElement']], [ORIGIN + '/', ORIGIN + '/blog/', ORIGIN + path])
        self.assertIn('aria-label="Breadcrumb"', html)
        self.assertIn('aria-current="page">Patient &quot;guide&quot; &amp; questions', html)
        self.assertNotIn('utm_source', scripts[1])

    def test_related_guides_and_service_links_exclude_drafts_and_missing_posts(self):
        slug = 'nuchal-translucency-scan-a-complete-guide'
        twin_slug = 'twin-nuchal-translucency-scan-a-complete-guide-of'
        post = BlogPost.objects.create(title='NT scan guide', slug=slug, content='<p>Clinical body stays intact</p>', meta_description='Stored', featured_image='')
        twin = BlogPost.objects.create(title='Twin NT scan guide', slug=twin_slug, content='Original twin text', meta_description='Stored', is_published=False, featured_image='')
        html = self.client.get(reverse('blog_detail', args=[slug])).content.decode()
        self.assertNotIn('href="' + reverse('blog_detail', args=[twin_slug]) + '"', html)
        twin.is_published = True
        twin.save(update_fields=['is_published', 'updated_at'])
        html = self.client.get(reverse('blog_detail', args=[slug])).content.decode()
        self.assertIn('href="' + reverse('blog_detail', args=[twin_slug]) + '"', html)
        self.assertIn('href="/services/#antenatal-gynecological-scans"', html)
        self.assertIn('href="/patient-info/"', html)
        service_html = self.client.get('/services/').content.decode()
        self.assertIn('href="' + reverse('blog_detail', args=[slug]) + '"', service_html)
        self.assertNotIn('/blog/what-is-a-fetal-anomaly-scan/', service_html)
        post.refresh_from_db()
        self.assertEqual(post.content, '<p>Clinical body stays intact</p>')
        self.assertEqual(post.meta_description, 'Stored')
        self.assertEqual(post.title, 'NT scan guide')
        self.assertIn('NT Scan in Pregnancy: A Patient Guide', html)
        graph = json.loads(re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)[1])['@graph']
        self.assertEqual(graph[-1]['headline'], 'NT Scan in Pregnancy: A Patient Guide')

    def test_responsive_image_assets_are_versioned_decodable_and_keep_original_fallback(self):
        root = Path(__file__).resolve().parent / 'static'
        manifest = image_manifest()
        self.assertEqual(len([e for e in manifest.values() if 'variants' in e]), 33)
        for source, entry in manifest.items():
            if 'variants' not in entry:
                data = (root / entry['path']).read_bytes()
                self.assertIn(hashlib.sha256(data).hexdigest()[:20], entry['path'])
                continue
            self.assertGreater(entry['width'], 0)
            self.assertGreater(entry['height'], 0)
            for variant in entry['variants']:
                path = root / variant['path']
                self.assertIn(hashlib.sha256(path.read_bytes()).hexdigest()[:20], path.name)
                with Image.open(path) as image:
                    self.assertEqual(image.format, 'WEBP')
                    self.assertEqual(image.width, variant['width'])
                    self.assertAlmostEqual(image.height / image.width, entry['height'] / entry['width'], delta=0.02)
        html = self.client.get('/').content.decode()
        hero = next(i for i in re.findall(r'<img\b[^>]*>', html) if '/images/hero.png' in i)
        self.assertIn('width="968" height="642"', hero)
        self.assertIn('fetchpriority="high"', hero)
        self.assertNotIn('loading="lazy"', hero)
        self.assertIn('<source type="image/webp"', html)
        self.assertIn('src="/static/images/hero.png"', hero)
        unknown = Template('{% load seo_images %}{% seo_image source alt=label %}').render(Context({'source': 'https://other.example/image.png', 'label': 'A "quoted" image'}))
        self.assertIn('src="https://other.example/image.png"', unknown)
        self.assertNotIn('<source', unknown)
        self.assertIn('alt="A &quot;quoted&quot; image"', unknown)

    @override_settings(DEBUG=False, WHITENOISE_AUTOREFRESH=False, WHITENOISE_USE_FINDERS=True)
    def test_immutable_cache_only_for_content_addressed_assets(self):
        variant = image_manifest()['/static/images/hero.png']['variants'][0]['path']
        url = '/static/' + variant
        self.assertTrue(immutable_seo_asset('', url))
        self.assertFalse(immutable_seo_asset('', '/static/images/hero.png'))
        self.assertFalse(immutable_seo_asset('', '/static/css/responsive.css'))
        middleware = WhiteNoiseMiddleware(lambda request: HttpResponse(status=404))
        response = middleware(RequestFactory().get(url))
        self.assertEqual(response.status_code, 200)
        self.assertIn('immutable', response['Cache-Control'])
        response.close()
        for original in ['/static/css/dist/styles.css', '/static/css/responsive.css', '/static/images/favicon.png', '/static/vendor/fonts/site-fonts.css']:
            css_url = '/static/' + image_manifest()[original]['path']
            response = middleware(RequestFactory().get(css_url))
            self.assertEqual(response.status_code, 200)
            self.assertIn('immutable', response['Cache-Control'])
            response.close()

    @override_settings(DEBUG=False, WHITENOISE_AUTOREFRESH=False, WHITENOISE_USE_FINDERS=True)
    def test_local_font_styles_preserve_families_and_deliver_cached_files(self):
        root = Path(__file__).resolve().parent / 'static'
        css = (root / image_manifest()['/static/vendor/fonts/site-fonts.css']['path']).read_text(encoding='utf-8')
        for family in ('Poppins', 'Cormorant Garamond', 'Font Awesome 6 Free', 'bootstrap-icons'):
            self.assertIn(family, css)
        font_faces = re.findall(r'@font-face\s*\{([^}]+)\}', css)
        self.assertTrue(font_faces)
        self.assertTrue(all('font-display:swap;' in face for face in font_faces))
        urls = re.findall(r'url\("([^"]+)"\)', css)
        self.assertTrue(urls)
        self.assertTrue(all(not url.startswith(('http:', 'https:')) for url in urls))
        for url in urls:
            font = root / 'seo-assets' / url
            self.assertTrue(font.is_file(), url)
            self.assertEqual(font.stem, hashlib.sha256(font.read_bytes()).hexdigest()[:20])
        middleware = WhiteNoiseMiddleware(lambda request: HttpResponse(status=404))
        response = middleware(RequestFactory().get('/static/seo-assets/' + urls[0]))
        self.assertEqual(response.status_code, 200)
        self.assertIn('immutable', response['Cache-Control'])
        response.close()
        html = self.client.get('/').content.decode()
        styles = re.findall(r'<link\b[^>]*rel="stylesheet"[^>]*>', html)
        self.assertTrue(all('href="/static/' in style for style in styles))

    def test_critical_fonts_are_preloaded_before_styles_without_duplicate_downloads(self):
        root = Path(__file__).resolve().parent / 'static'
        entry = image_manifest()['/static/vendor/fonts/site-fonts.css']
        fonts = entry['preloads']
        self.assertEqual(len(fonts), 6)
        self.assertEqual(len(set(fonts)), len(fonts))
        css = (root / entry['path']).read_text(encoding='utf-8')
        html = self.client.get('/').content.decode()
        for path in fonts:
            preload = '<link rel="preload" href="/static/' + path + '" as="font" type="font/woff2" crossorigin>'
            self.assertEqual(html.count(preload), 1)
            self.assertLess(html.index(preload), html.index('rel="stylesheet"'))
            self.assertIn('url("' + Path(path).name + '")', css)
            self.assertEqual((root / path).read_bytes()[:4], b'wOF2')
