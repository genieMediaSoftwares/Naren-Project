import os

from django.core.validators import FileExtensionValidator
from django.db import DatabaseError, models
from django_ckeditor_5.fields import CKEditor5Field


class Service(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='services/')

    def __str__(self):
        return self.title


class Gallery(models.Model):
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='gallery/')

    def __str__(self):
        return self.title


class Appointment(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    date = models.DateField()
    message = models.TextField()

    def __str__(self):
        return self.name
    
class PatientBooking(models.Model):

    full_name = models.CharField(max_length=200)

    age = models.IntegerField(null=True, blank=True)

    gender = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    phone = models.CharField(max_length=15)

    referred_doctor = models.CharField(
        max_length=200,
        null=True,
        blank=True
    )

    hospital_name = models.CharField(
        max_length=200,
        null=True,
        blank=True
    )

    ldd_date = models.DateField(
        null=True,
        blank=True
    )

    preferred_date = models.DateField()

    preferred_time = models.CharField(max_length=50)

    services = models.TextField()

    message = models.TextField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name
    
class ContactMessage(models.Model):

    name = models.CharField(max_length=200)

    phone = models.CharField(max_length=15)

    email = models.EmailField()

    subject = models.CharField(max_length=200)

    message = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    

from django.utils.text import slugify

from django.utils.text import slugify


class BlogCategory(models.Model):

    name = models.CharField(max_length=100)

    slug = models.SlugField(
        unique=True,
        blank=True
    )

    def save(self, *args, **kwargs):

        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class BlogTag(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True
    )

    slug = models.SlugField(
        unique=True,
        blank=True
    )

    def save(self, *args, **kwargs):

        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class BlogPost(models.Model):

    title = models.CharField(max_length=300)

    slug = models.SlugField(
        unique=True,
        blank=True
    )

    featured_image = models.ImageField(
        upload_to='blog/'
    )

    meta_description = models.CharField(
        max_length=500
    )


    content = CKEditor5Field(
        'Content',
        config_name='default'
    )

    author = models.CharField(
        max_length=100,
        default="Dr. Naren Satya"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    is_published = models.BooleanField(
        default=True
    )

    category = models.ForeignKey(
    BlogCategory,
    on_delete=models.SET_NULL,
    null=True,
    blank=True
    )

    tags = models.ManyToManyField(
        BlogTag,
        blank=True
    )

    content = CKEditor5Field(
        'Content',
        config_name='default'
    )


    def save(self, *args, **kwargs):

        if not self.slug:
            self.slug = slugify(self.title)

        super().save(*args, **kwargs)

    @property
    def tag_list(self):
        return [
            tag.strip()
            for tag in self.tags.split(',')
         if tag.strip()
         ]

    def __str__(self):
        return self.title
    


class BlogPhoto(models.Model):
    """A client-supplied photo shown in a gallery at the END of a blog post.

    Deliberately a separate model rather than anything embedded in
    ``BlogPost.content``: the content field stays exactly as the client wrote
    it, and these photos are appended by the template after the article and its
    CTA/conclusion. Storage goes through the ImageField like every other image
    on the site, so switching to an external/persistent backend is a change to
    STORAGES['default'] alone.
    """

    post = models.ForeignKey(
        BlogPost,
        on_delete=models.CASCADE,
        related_name='client_photos'
    )

    image = models.ImageField(
        upload_to='blog/photos/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png']
            )
        ],
        help_text='JPG, JPEG or PNG.'
    )

    caption = models.CharField(
        max_length=200,
        blank=True,
        help_text='Optional. Shown under the photo, and used as its alt text.'
    )

    order = models.PositiveIntegerField(
        default=0,
        help_text='Lower numbers appear first in the gallery.'
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = ['order', 'id']

        verbose_name = 'Client photo'

        verbose_name_plural = 'Client photos'

    def __str__(self):
        return self.caption or os.path.basename(self.image.name or 'photo')


class DoctorProfile(models.Model):
    """The single, site-wide "About the Doctor" card shown under every blog post.

    Intentionally NOT related to BlogPost: the photo is uploaded once here and
    every post - existing ones included - picks it up automatically, so no blog
    ever has to be re-saved and no per-post doctor upload exists. This is a
    different thing from BlogPhoto (per-post client photos).

    The image goes through a normal ImageField, so it uses whatever backend
    STORAGES['default'] points at - set DJANGO_MEDIA_STORAGE_BACKEND to a
    persistent backend on Vercel and this photo moves with everything else.
    """

    name = models.CharField(
        max_length=150,
        default='Dr. Naren Satya'
    )

    designation = models.CharField(
        max_length=200,
        default='Consultant Radiologist'
    )

    organisation = models.CharField(
        max_length=250,
        blank=True,
        default='Naren Ultrasound and Fetal Medicine Center, Visakhapatnam',
        help_text='Centre and city, shown under the designation.'
    )

    photo = models.ImageField(
        upload_to='doctor/',
        blank=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'webp']
            )
        ],
        help_text='Uploaded once and reused on every blog post.'
    )

    bio = models.TextField(
        blank=True,
        help_text='Optional. A short paragraph shown beside the photo.'
    )

    is_active = models.BooleanField(
        default=True,
        help_text='Untick to hide the doctor section from all blog posts.'
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        verbose_name = 'Doctor profile'

        verbose_name_plural = 'Doctor profile'

    @classmethod
    def get_active(cls):
        """The profile to render, or None when nothing is configured.

        Returns None rather than raising so a blog page never breaks before the
        client has filled this in.
        """

        try:
            return cls.objects.filter(is_active=True).first()
        except DatabaseError:
            # The table may not exist yet on a not-quite-migrated deploy.
            return None

    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)

        # Only ever one active profile, so every post renders the same doctor.
        if self.is_active:
            DoctorProfile.objects.exclude(pk=self.pk).update(is_active=False)

    def __str__(self):
        return self.name
