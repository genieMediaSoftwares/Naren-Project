"""Serve persistent uploads under their existing /media/ URLs."""

import mimetypes

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from django.views.decorators.http import require_safe
from django.views.static import serve

from .media_storage import DatabaseMediaStorage


@require_safe
def media(request, path):
    if not isinstance(default_storage, DatabaseMediaStorage):
        return serve(request, path, document_root=settings.MEDIA_ROOT)
    try:
        uploaded = default_storage.open(path, 'rb')
    except (FileNotFoundError, IsADirectoryError, SuspiciousFileOperation):
        raise Http404('Media file not found.')
    content_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
    response = FileResponse(uploaded, content_type=content_type)
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'public, max-age=3600'
    return response
