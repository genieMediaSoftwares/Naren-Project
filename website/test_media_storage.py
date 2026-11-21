from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .media_storage import DatabaseMediaStorage
from .models import BlogCategory, BlogPhoto, BlogPost, BlogTag, MediaAsset


DATABASE_STORAGES = {
    'default': {'BACKEND': 'website.media_storage.DatabaseMediaStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}


def image_upload(name='featured.png'):
    output = BytesIO()
    Image.new('RGB', (4, 4), 'teal').save(output, 'PNG')
    return SimpleUploadedFile(name, output.getvalue(), content_type='image/png')


@override_settings(STORAGES=DATABASE_STORAGES)
class PersistentMediaTests(TestCase):
    def setUp(self):
        self.storage = DatabaseMediaStorage()

    def test_upload_survives_new_storage_instance_without_filesystem_writes(self):
        upload = image_upload()
        expected = upload.read()
        upload.seek(0)
        with patch.object(FileSystemStorage, '_save', side_effect=OSError('Read-only file system')):
            name = self.storage.save('blog/featured.png', upload)
        reopened = DatabaseMediaStorage()
        self.assertEqual(reopened.open(name).read(), expected)
        self.assertEqual(reopened.size(name), len(expected))
        self.assertEqual(reopened.url(name), '/media/blog/featured.png')

    def test_duplicate_filenames_do_not_overwrite_existing_image(self):
        first = self.storage.save('blog/shared.png', image_upload())
        second = self.storage.save('blog/shared.png', ContentFile(b'second'))
        self.assertNotEqual(first, second)
        self.assertEqual(MediaAsset.objects.count(), 2)
        self.assertNotEqual(self.storage.open(first).read(), b'second')

    def test_media_url_serves_image_and_head(self):
        name = self.storage.save('blog/photo.png', image_upload())
        response = self.client.get(self.storage.url(name))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertEqual(b''.join(response.streaming_content), self.storage.open(name).read())
        self.assertEqual(self.client.head(self.storage.url(name)).status_code, 200)
        self.assertEqual(self.client.post(self.storage.url(name)).status_code, 405)

    def test_missing_or_escaping_paths_return_404(self):
        self.assertEqual(self.client.get('/media/blog/missing.png').status_code, 404)
        self.assertEqual(self.client.get('/media/../settings.py').status_code, 404)
        with self.assertRaises(SuspiciousFileOperation):
            self.storage.open('../settings.py')

    def test_existing_bundled_images_remain_readable_and_are_not_overwritten(self):
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            legacy = Path(directory) / 'blog' / 'legacy.png'
            legacy.parent.mkdir()
            legacy.write_bytes(image_upload().read())
            self.assertTrue(self.storage.exists('blog/legacy.png'))
            self.assertEqual(self.storage.open('blog/legacy.png').read(), legacy.read_bytes())
            response = self.client.get('/media/blog/legacy.png')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b''.join(response.streaming_content), legacy.read_bytes())
            name = self.storage.save('blog/legacy.png', image_upload())
            self.assertNotEqual(name, 'blog/legacy.png')
            self.storage.delete('blog/legacy.png')
            self.assertTrue(legacy.exists())

    @override_settings(MEDIA_UPLOAD_MAX_BYTES=3)
    def test_oversized_upload_is_not_persisted(self):
        with self.assertRaises(ValueError):
            self.storage.save('blog/large.png', ContentFile(b'too large'))
        self.assertFalse(MediaAsset.objects.exists())


@override_settings(STORAGES=DATABASE_STORAGES)
class BlogAdminUploadTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_superuser('editor', 'editor@example.com', 'test-only')
        self.client.force_login(user)
        self.category = BlogCategory.objects.create(name='Scans')
        self.tag = BlogTag.objects.create(name='Pregnancy')

    def post_data(self):
        return {
            'title': 'Storage regression test', 'slug': 'storage-regression-test',
            'featured_image': image_upload(), 'meta_description': 'Test description',
            'content': '<p>Original article content.</p>', 'author': 'Dr. Naren Satya',
            'is_published': 'on', 'category': str(self.category.pk), 'tags': [str(self.tag.pk)],
            'client_photos-TOTAL_FORMS': '1', 'client_photos-INITIAL_FORMS': '0',
            'client_photos-MIN_NUM_FORMS': '0', 'client_photos-MAX_NUM_FORMS': '1000',
            'client_photos-0-image': image_upload('inline.png'),
            'client_photos-0-caption': 'Test caption', 'client_photos-0-order': '0',
            'client_photos_upload': [image_upload('bulk.png')], '_save': 'Save',
        }

    def test_admin_publishes_post_with_featured_inline_and_bulk_images(self):
        with patch.object(FileSystemStorage, '_save', side_effect=OSError('Read-only file system')):
            response = self.client.post(reverse('admin:website_blogpost_add'), self.post_data())
        self.assertEqual(response.status_code, 302)
        post = BlogPost.objects.get(slug='storage-regression-test')
        self.assertEqual(post.content, '<p>Original article content.</p>')
        self.assertEqual(list(post.tags.all()), [self.tag])
        self.assertEqual(post.client_photos.count(), 2)
        self.assertEqual(MediaAsset.objects.count(), 3)
        self.assertEqual(self.client.get(post.featured_image.url).status_code, 200)
        self.assertEqual(self.client.get(reverse('blog_detail', args=[post.slug])).status_code, 200)

    def test_failed_admin_save_rolls_back_post_and_uploaded_images(self):
        with patch('website.admin.BlogPostAdmin.log_addition', side_effect=RuntimeError('save failed')):
            with self.assertRaisesMessage(RuntimeError, 'save failed'):
                self.client.post(reverse('admin:website_blogpost_add'), self.post_data())
        self.assertFalse(BlogPost.objects.exists())
        self.assertFalse(BlogPhoto.objects.exists())
        self.assertFalse(MediaAsset.objects.exists())

    def test_url_download_uses_persistent_storage(self):
        data = self.post_data()
        del data['featured_image']
        data['featured_image_url'] = 'https://example.com/featured.png'
        with patch('website.forms.download_image', return_value=('download.png', ContentFile(image_upload().read()))):
            response = self.client.post(reverse('admin:website_blogpost_add'), data)
        self.assertEqual(response.status_code, 302)
        post = BlogPost.objects.get()
        self.assertTrue(MediaAsset.objects.filter(pk=post.featured_image.name).exists())

    def test_ckeditor_upload_uses_persistent_storage(self):
        response = self.client.post('/ckeditor5/image_upload/', {'upload': image_upload('editor.png')})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(response.json()['url']).status_code, 200)
        self.assertEqual(MediaAsset.objects.count(), 1)
