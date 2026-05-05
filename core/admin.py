from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Section, Subsection, WasteItem


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('WasteMap', {'fields': ('role', 'section', 'subsection')}),
    )
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'is_active']
    list_filter = ['role', 'is_active']


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'latitude', 'longitude']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Subsection)
class SubsectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'section', 'slug', 'latitude', 'longitude']


@admin.register(WasteItem)
class WasteItemAdmin(admin.ModelAdmin):
    list_display = ['waste_type', 'properties', 'confidence', 'section', 'subsection', 'captured_by', 'timestamp']
    list_filter = ['waste_type', 'properties', 'section']
