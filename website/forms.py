from django import forms
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import FileExtensionValidator
from django.db.models import Max

from .image_utils import download_image
from .models import Appointment, BlogPhoto, BlogPost


class AppointmentForm(forms.ModelForm):

    class Meta:
        model = Appointment

        fields = ['name', 'phone', 'email', 'date', 'message']

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control'
            }),

            'phone': forms.TextInput(attrs={
                'class': 'form-control'
            }),

            'email': forms.EmailInput(attrs={
                'class': 'form-control'
            }),

            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),

            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4
            }),
        }

class MultipleFileInput(forms.ClearableFileInput):
    """A file input that accepts more than one file at a time.

    Django's own widgets are single-file by design; this opt-in flag is the
    documented way to allow a multi-select <input type="file" multiple>.
    """

    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    """ImageField that cleans a *list* of uploaded images.

    Each file still goes through the normal ImageField checks (Pillow actually
    opens it), plus an extension check limiting uploads to JPG/JPEG/PNG.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            'widget',
            MultipleFileInput(attrs={'accept': '.jpg,.jpeg,.png'}),
        )
        kwargs.setdefault(
            'validators',
            [FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
        )
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        clean_one = super().clean

        if isinstance(data, (list, tuple)):
            return [clean_one(item, initial) for item in data if item]

        if not data:
            return []

        return [clean_one(data, initial)]


class BlogPostAdminForm(forms.ModelForm):
    """Blog create/edit form with a "paste the ChatGPT image link" shortcut.

    The URL is never stored. The bytes behind it are downloaded and written into
    MEDIA_ROOT through the model's own ImageField, so the database ends up with
    the same relative path (``blog/<name>.png``) an ordinary upload produces,
    and the template keeps using ``{{ post.featured_image.url }}``.
    """

    featured_image_url = forms.URLField(
        required=False,
        label='...or download the featured image from a URL',
        help_text=(
            'Paste a ChatGPT/OpenAI image link. The PNG is downloaded and saved '
            'into media storage now - the temporary link itself is not stored, '
            'so the blog image keeps working after the link expires.'
        ),
        widget=forms.URLInput(attrs={'size': 80}),
    )

    client_photos_upload = MultipleImageField(
        required=False,
        label='Add client photos',
        help_text=(
            'Select one or more JPG/JPEG/PNG files to append to the gallery at '
            'the end of this post. Existing photos are listed in the "Client '
            'photos" section below, where each one can be edited or removed.'
        ),
    )

    class Meta:
        model = BlogPost
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Either an upload or a URL is acceptable, so the required check moves
        # to clean() below.
        self.fields['featured_image'].required = False

    def clean(self):
        cleaned_data = super().clean()

        url = (cleaned_data.get('featured_image_url') or '').strip()

        if url:
            try:
                self._downloaded_image = download_image(url)
            except DjangoValidationError as exc:
                self.add_error('featured_image_url', exc)

        elif not cleaned_data.get('featured_image') and not self.instance.featured_image:
            self.add_error(
                'featured_image',
                'Upload a featured image or paste an image URL to download.',
            )

        return cleaned_data

    def save(self, commit=True):
        post = super().save(commit=False)

        downloaded = getattr(self, '_downloaded_image', None)

        if downloaded:
            name, content = downloaded
            # save=False: the ImageField writes the file and records the
            # relative path; the row itself is written just below/by the admin.
            post.featured_image.save(name, content, save=False)

        if commit:
            post.save()
            self.save_m2m()

        return post

    def save_client_photos(self, post):
        """Turn the bulk upload into BlogPhoto rows attached to ``post``.

        Called from the admin once ``post`` definitely has a primary key. Each
        file is written through BlogPhoto.image, so it lands in the configured
        media storage and the database only holds the relative path.
        """

        uploads = self.cleaned_data.get('client_photos_upload') or []

        if not uploads:
            return []

        # Append after whatever is already in the gallery.
        next_order = (
            post.client_photos.aggregate(Max('order'))['order__max'] or 0
        ) + 1

        created = []

        for offset, upload in enumerate(uploads):

            photo = BlogPhoto(
                post=post,
                order=next_order + offset,
            )

            photo.image.save(upload.name, upload, save=False)
            photo.save()

            created.append(photo)

        return created
