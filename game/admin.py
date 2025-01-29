# file: game/admin.py

from django.contrib import admin
from django.utils.html import format_html
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import User, PlayerState

class UserResource(resources.ModelResource):
    class Meta:
        model = User
        fields = ('id', 'telegram_id', 'username', 'first_name', 'last_name', 
                 'date_joined', 'last_login', 'is_active')
        export_order = fields

class PlayerStateResource(resources.ModelResource):
    class Meta:
        model = PlayerState
        exclude = ('id',)

@admin.register(User)
class UserAdmin(ImportExportModelAdmin):
    resource_class = UserResource
    list_display = ('telegram_id', 'username', 'colored_name', 'photo_preview', 
                   'date_joined', 'last_login', 'is_active')
    list_filter = ('is_active', 'is_staff', 'date_joined')
    search_fields = ('telegram_id', 'username', 'first_name', 'last_name')
    readonly_fields = ('telegram_id', 'photo_preview')
    fieldsets = (
        ('Telegram Info', {
            'fields': ('telegram_id', 'username', 'photo_url', 'photo_preview')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'email')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
    )

    def colored_name(self, obj):
        return format_html(
            '<span style="color: #1c84ee;">{} {}</span>',
            obj.first_name,
            obj.last_name
        )
    colored_name.short_description = 'Name'

    def photo_preview(self, obj):
        if obj.photo_url:
            return format_html(
                '<img src="{}" style="max-height: 50px;"/>',
                obj.photo_url
            )
        return '-'
    photo_preview.short_description = 'Photo'

@admin.register(PlayerState)
class PlayerStateAdmin(ImportExportModelAdmin):
    resource_class = PlayerStateResource
    list_display = (
        'user', 
        'energy_altar', 
        'energy_fire', 
        'energy_waterfall',
        'food', 
        'wood', 
        'enhancements_count',
        'campfire_status'
    )
    list_filter = (
        'enhancements_count',
        'last_campfire_start',
        'last_altar_activation'
    )
    search_fields = ('user__username', 'user__telegram_id')
    readonly_fields = (
        'last_altar_activation', 
        'last_food_gather', 
        'last_wood_gather', 
        'last_waterfall_activation',
        'last_campfire_start'
    )
    fieldsets = (
        ('User Info', {
            'fields': ('user',)
        }),
        ('Resources', {
            'fields': (
                'food', 
                'wood'
            )
        }),
        ('Energy Levels', {
            'fields': (
                'energy_altar',
                'energy_fire', 
                'energy_waterfall'
            )
        }),
        ('Game Progress', {
            'fields': (
                'enhancements_count',
            )
        }),
        ('Activity Timers', {
            'fields': (
                'last_altar_activation',
                'last_food_gather',
                'last_wood_gather',
                'last_waterfall_activation',
                'last_campfire_start'
            )
        }),
    )

    def campfire_status(self, obj):
        if obj.campfire_is_burning():
            return format_html(
                '<span style="color: #28a745;">🔥 Active</span>'
            )
        return format_html(
            '<span style="color: #dc3545;">❌ Inactive</span>'
        )
    campfire_status.short_description = 'Campfire'
