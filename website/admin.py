from django.contrib import admin
from django.utils.html import format_html

from .forms import BlogPostAdminForm
from .models import (
    Service,
    Gallery,
    Appointment,
    BlogPhoto,
    BlogPost,
    BlogCategory,
    BlogTag
)

admin.site.register(BlogCategory)
admin.site.register(BlogTag)


class BlogPhotoInline(admin.TabularInline):
    """The "Client photos" section of the Blog Post admin.

    One row per photo, so the client can add rows, reorder them, and tick
    "Delete" to remove an individual photo. These never touch BlogPost.content -
    they are rendered by the template after the article.
    """

    model = BlogPhoto

    extra = 1

    fields = ('preview', 'image', 'caption', 'order')

    readonly_fields = ('preview',)

    ordering = ('order', 'id')

    verbose_name = 'Client photo'

    verbose_name_plural = 'Client photos (shown at the end of the post)'

    @admin.display(description='Preview')
    def preview(self, obj):

        if not obj.pk or not obj.image:
            return '-'

        return format_html(
            '<img src="{}" style="height:80px;border-radius:6px;'
            'object-fit:cover;" />',
            obj.image.url,
        )


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):

    form = BlogPostAdminForm

    inlines = [BlogPhotoInline]

    filter_horizontal = ['tags']

    list_display = (
        'title',
        'author',
        'is_published',
        'created_at'
    )

    prepopulated_fields = {
        'slug': ('title',)
    }

    search_fields = (
        'title',
    )

    list_filter = (
        'is_published',
        'created_at'
    )

    def save_related(self, request, form, formsets, change):

        super().save_related(request, form, formsets, change)

        # Runs after the post and the inline rows are committed, so the bulk
        # uploads are appended to the end of the existing gallery.
        form.save_client_photos(form.instance)


admin.site.register(Service)
admin.site.register(Gallery)
admin.site.register(Appointment)