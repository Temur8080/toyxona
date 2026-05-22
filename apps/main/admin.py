from django.contrib import admin

from apps.main.models import District, Hall, Region


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name_uz')


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ('id', 'name_uz', 'region')
    list_filter = ('region',)


@admin.register(Hall)
class HallAdmin(admin.ModelAdmin):
    list_display = ('id', 'name_uz', 'district', 'server_ip', 'is_online', 'max_capacity', 'activity_suspended')
    list_filter = ('district', 'is_online', 'activity_suspended')
    search_fields = ('name_uz', 'slug', 'server_ip')
