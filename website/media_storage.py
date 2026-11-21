"""Store uploads in the existing database; keep bundled media readable.

Database writes participate in the admin's transaction, so a failed post save
also rolls back its new image. No files are written to Vercel's local disk.
"""

import mimetypes
from urllib.parse import quote, urljoin

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, Storage
from django.db import IntegrityError, transaction
from django.utils._os import safe_join
from django.utils.deconstruct import deconstructible

from .models import MediaAsset


@deconstructible
class DatabaseMediaStorage(Storage):
    @property
    def bundled(self):
        return FileSystemStorage(location=settings.MEDIA_ROOT, base_url=settings.MEDIA_URL)

    def _check_name(self, name):
        # Keep URL lookups inside MEDIA_ROOT, including legacy file fallbacks.
        if not name or name.startswith('/') or '\\' in name:
            raise SuspiciousFileOperation('Invalid media path.')
        safe_join(settings.MEDIA_ROOT, name)

    def _open(self, name, mode='rb'):
        self._check_name(name)
        if mode not in ('r', 'rb'):
            raise ValueError('Media files must be replaced through Storage.save().')
        asset = MediaAsset.objects.filter(pk=name).only('data').first()
        if asset is not None:
            return ContentFile(bytes(asset.data), name=name)
        return self.bundled.open(name, mode)

    def get_available_name(self, name, max_length=None):
        return super().get_available_name(name, max_length=max_length or 255).replace('\\', '/')

    def is_name_available(self, name, max_length=None):
        # Django uses os.path.join() for collision suffixes, including on
        # Windows. Persist URL paths with forward slashes on every platform.
        return super().is_name_available(name.replace('\\', '/'), max_length=max_length)

    def _save(self, name, content):
        self._check_name(name)
        limit = getattr(settings, 'MEDIA_UPLOAD_MAX_BYTES', 20 * 1024 * 1024)
        chunks, size = [], 0
        for chunk in content.chunks():
            size += len(chunk)
            if size > limit:
                raise ValueError('The uploaded file exceeds the media size limit.')
            chunks.append(chunk)
        data = b''.join(chunks)
        content_type = mimetypes.guess_type(name)[0] or 'application/octet-stream'
        while True:
            try:
                # A savepoint keeps a rare concurrent filename collision from
                # breaking the enclosing admin transaction.
                with transaction.atomic():
                    MediaAsset.objects.create(
                        name=name, data=data, content_type=content_type, size=size,
                    )
                return name
            except IntegrityError:
                if not MediaAsset.objects.filter(pk=name).exists():
                    raise
                name = self.get_available_name(name)

    def exists(self, name):
        self._check_name(name)
        return MediaAsset.objects.filter(pk=name).exists() or self.bundled.exists(name)

    def size(self, name):
        self._check_name(name)
        asset = MediaAsset.objects.filter(pk=name).only('size').first()
        return asset.size if asset is not None else self.bundled.size(name)

    def url(self, name):
        self._check_name(name)
        return urljoin(settings.MEDIA_URL.rstrip('/') + '/', quote(name))

    def delete(self, name):
        self._check_name(name)
        # Bundled legacy files belong to the deployment; never remove them.
        MediaAsset.objects.filter(pk=name).delete()

    def get_modified_time(self, name):
        self._check_name(name)
        asset = MediaAsset.objects.filter(pk=name).only('created_at').first()
        return asset.created_at if asset is not None else self.bundled.get_modified_time(name)
