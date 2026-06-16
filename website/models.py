from django.db import models
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
    
