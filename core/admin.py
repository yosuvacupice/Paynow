from django.contrib import admin

from .models import ContactMessage, UserAccount


@admin.register(UserAccount)
class UserAccountAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'phone_number', 'gender')
    search_fields = ('email', 'name', 'first_name', 'last_name', 'phone_number')
    list_filter = ('gender',)
    readonly_fields = ('name', 'first_name', 'last_name', 'email', 'phone_number', 'gender', 'password')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return True


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email')
    search_fields = ('name', 'email')
