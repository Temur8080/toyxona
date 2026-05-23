from django.contrib import admin

from apps.counting.models import PeopleCount


@admin.register(PeopleCount)
class PeopleCountAdmin(admin.ModelAdmin):
    list_display = ('id', 'hall', 'camera', 'count', 'recorded_at')
    list_filter = ('hall', 'recorded_at')
    date_hierarchy = 'recorded_at'
