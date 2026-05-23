from django.contrib import admin

from apps.counting.models import HallEvent, PeopleCount


@admin.register(PeopleCount)
class PeopleCountAdmin(admin.ModelAdmin):
    list_display = ('id', 'hall', 'camera', 'count', 'recorded_at')
    list_filter = ('hall', 'recorded_at')
    date_hierarchy = 'recorded_at'


@admin.register(HallEvent)
class HallEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'hall', 'peak_count', 'is_active', 'started_at', 'ended_at')
    list_filter = ('is_active', 'hall')
    date_hierarchy = 'started_at'
