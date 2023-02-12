from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from .models import Plan, Thumbnail


class UserAdmin(BaseUserAdmin):
    ordering = ('id',)
    list_display = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal Info'), {'fields': ('name', 'plan')}),
        (
            _('Permissions'),
            {'fields': ('is_active', 'is_staff', 'is_superuser')}
        ),
        (_('Important dates'), {'fields': ('last_login',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'password1', 'password2')
        }),
    )
    search_fields = ('email',)
    search_help_text = 'Search by email'


class ThumbnailInline(admin.TabularInline):
    model = Plan.thumbnails.through
    extra = 1
    verbose_name = "thumbnail"


class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'expired_link', 'original_image')
    list_filter = ("expired_link", 'original_image')
    inlines = (ThumbnailInline,)
    exclude = ('thumbnails',)
    fieldsets = (
        (None, {"fields": ("name",)}),
        (
            _('Expired link'),
            {'classes': ('collapse',), 'fields': ('expired_link',)},
        ),
        (
            _('Original image'),
            {'classes': ('collapse',), 'fields': ('original_image',)},
        ),
    )


admin.site.unregister(Group)
admin.site.register(get_user_model(), UserAdmin)
admin.site.register(Plan, PlanAdmin)
admin.site.register(Thumbnail)
