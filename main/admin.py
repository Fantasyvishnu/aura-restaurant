from django.conf import settings
from django.contrib import admin, messages
from django.utils import timezone

from .models import (
    Bill, Category, Chef, ContactMessage, DiningTable,
    GalleryImage, MenuItem, Order, OrderItem, Reservation,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'display_order')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('display_order',)
    search_fields = ('name',)


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'meal_type', 'price', 'prep_time_minutes', 'is_veg', 'is_spicy', 'is_chef_special', 'is_available')
    list_filter = ('category', 'meal_type', 'is_veg', 'is_spicy', 'is_chef_special', 'is_available')
    search_fields = ('name', 'description')
    list_editable = ('price', 'prep_time_minutes', 'is_veg', 'is_spicy', 'is_chef_special', 'is_available')
    list_select_related = ('category',)


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'display_order')
    list_filter = ('category',)
    search_fields = ('title', 'description')
    list_editable = ('display_order',)


@admin.register(Chef)
class ChefAdmin(admin.ModelAdmin):
    list_display = ('name', 'title', 'display_order')
    search_fields = ('name', 'title', 'bio')
    list_editable = ('display_order',)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'date', 'time', 'guests', 'seating_area', 'status', 'fine_amount', 'fine_paid')
    list_filter = ('status', 'fine_paid', 'seating_area', 'date')
    search_fields = ('name', 'email', 'phone')
    list_editable = ('status', 'fine_amount', 'fine_paid')
    list_select_related = ('user',)
    date_hierarchy = 'date'
    ordering = ('-date', '-time')
    readonly_fields = ('created_at', 'fine_paid_at')
    actions = ['mark_confirmed', 'mark_cancelled', 'mark_completed', 'mark_no_show', 'mark_fine_collected']

    def _bulk_status(self, request, queryset, status, label):
        updated = queryset.update(status=status)
        self.message_user(request, f"{updated} reservation(s) marked as {label}.", messages.SUCCESS)

    @admin.action(description="Mark selected as Confirmed")
    def mark_confirmed(self, request, queryset):
        self._bulk_status(request, queryset, 'CONFIRMED', 'Confirmed')

    @admin.action(description="Mark selected as Cancelled")
    def mark_cancelled(self, request, queryset):
        self._bulk_status(request, queryset, 'CANCELLED', 'Cancelled')

    @admin.action(description="Mark selected as Completed (guest arrived)")
    def mark_completed(self, request, queryset):
        self._bulk_status(request, queryset, 'COMPLETED', 'Completed')

    @admin.action(description="Mark selected as No-show (adds standard fine)")
    def mark_no_show(self, request, queryset):
        fine = settings.RESTAURANT['no_show_fine']
        queryset.filter(fine_amount=0).update(fine_amount=fine)
        self._bulk_status(request, queryset, 'NO_SHOW', 'No-show')

    @admin.action(description="Mark fine as collected")
    def mark_fine_collected(self, request, queryset):
        updated = queryset.filter(fine_amount__gt=0, fine_paid=False).update(fine_paid=True, fine_paid_at=timezone.now())
        self.message_user(request, f"{updated} fine(s) marked as collected.", messages.SUCCESS)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'created_at')
    list_filter = ('subject', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'


@admin.register(DiningTable)
class DiningTableAdmin(admin.ModelAdmin):
    list_display = ('number', 'label', 'capacity', 'section', 'status')
    list_filter = ('section', 'status')
    list_editable = ('status',)
    ordering = ('section', 'number')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('ordered_at', 'ready_at', 'served_at', 'subtotal')
    fields = ('menu_item', 'quantity', 'unit_price', 'notes', 'status', 'ordered_at')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'table', 'customer_name', 'pax', 'status', 'subtotal', 'created_at')
    list_filter = ('status', 'table__section', 'created_at')
    search_fields = ('customer_name', 'table__number')
    readonly_fields = ('created_at', 'updated_at', 'closed_at')
    inlines = [OrderItemInline]


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'subtotal', 'gst_amount', 'total', 'payment_method', 'paid_at')
    list_filter = ('payment_method', 'paid_at')
    readonly_fields = ('created_at',)
