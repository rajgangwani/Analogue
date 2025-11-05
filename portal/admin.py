from django.contrib import admin
from .models import Profile, Module

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_type', 'is_premium', 'trial_expiry', 'days_left')

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_free')
