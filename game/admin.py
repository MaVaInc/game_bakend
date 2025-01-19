# file: game/admin.py

from django.contrib import admin
from .models import PlayerState

@admin.register(PlayerState)
class PlayerStateAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'energy_altar',
        'energy_fire',
        'energy_waterfall',
        'food',
        'wood',
        'enhancements_count',
    )
    search_fields = ('user__username',)
    list_filter = ('enhancements_count',)
