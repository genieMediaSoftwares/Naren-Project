from django.contrib import admin
from .models import (
    Service,
    Gallery,
    Appointment,
    BlogPost,
    BlogCategory,
    BlogTag
)

admin.site.register(BlogCategory)
admin.site.register(BlogTag)


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):

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


admin.site.register(Service)
admin.site.register(Gallery)
admin.site.register(Appointment)