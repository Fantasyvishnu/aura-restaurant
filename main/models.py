from datetime import datetime, timedelta
from decimal import Decimal
from urllib.parse import quote

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import ExpressionWrapper, F, Sum, DecimalField as DjangoDecimalField
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    MEAL_TYPE_CHOICES = [
        ('all_day',   'All Day'),
        ('breakfast', 'Breakfast (6 AM – 11 AM)'),
        ('lunch',     'Lunch (11 AM – 3 PM)'),
        ('snacks',    'Evening Snacks (3 PM – 7 PM)'),
        ('dinner',    'Dinner (7 PM – 11 PM)'),
    ]

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=150)
    description = models.TextField()
    price = models.DecimalField(max_digits=7, decimal_places=2)
    image = models.ImageField(upload_to='food/', blank=True, help_text="Upload food photo")
    is_chef_special = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    dietary_tag = models.CharField(max_length=50, blank=True, help_text="e.g. Vegetarian, Vegan, Jain, Gluten-Free, Spicy")
    wine_pairing = models.CharField(max_length=150, blank=True, help_text="Serving note, e.g. 'Best with filter coffee'")
    # New fields
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPE_CHOICES, default='all_day', help_text="When is this dish available?")
    prep_time_minutes = models.PositiveSmallIntegerField(default=15, help_text="Estimated kitchen preparation time in minutes")
    is_veg = models.BooleanField(default=False, help_text="Pure vegetarian (green dot on menu)")
    is_spicy = models.BooleanField(default=False, help_text="Mark as spicy dish")
    serve_unit = models.CharField(max_length=30, default='plate', help_text="Unit shown on POS: plate / piece / bowl / glass / bottle")

    class Meta:
        ordering = ['category__display_order', 'name']

    def __str__(self):
        return f"{self.name} (₹{self.price})"

    @property
    def prep_time_display(self):
        if self.prep_time_minutes < 60:
            return f"{self.prep_time_minutes} min"
        h, m = divmod(self.prep_time_minutes, 60)
        return f"{h}h {m}m" if m else f"{h}h"


class GalleryImage(models.Model):
    CATEGORY_CHOICES = [
        ('interior', 'Palace Interiors'),
        ('dishes',   'Signature Dishes'),
        ('drinks',   'Bar, Coffee & Sweets'),
        ('patio',    'The Courtyard'),
    ]
    title = models.CharField(max_length=150)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='interior')
    image = models.ImageField(upload_to='gallery/', help_text="Upload gallery image")
    description = models.CharField(max_length=250, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'title']

    def __str__(self):
        return f"{self.title} ({self.get_category_display()})"


class Chef(models.Model):
    name = models.CharField(max_length=120)
    title = models.CharField(max_length=120, help_text="e.g. Head Chef, Pastry Chef, Host")
    bio = models.TextField()
    image = models.ImageField(upload_to='chefs/', help_text="Upload chef portrait")
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'name']

    def __str__(self):
        return f"{self.name} - {self.title}"


phone_validator = RegexValidator(
    regex=r'^[0-9+()\-\s]{7,20}$',
    message="Enter a valid phone number (digits, spaces, +, -, brackets).",
)


class Reservation(models.Model):
    STATUS_CHOICES = [
        ('PENDING',   'Pending Confirmation'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed (Guest Arrived)'),
        ('NO_SHOW',   'No-show'),
    ]
    SEATING_CHOICES = [
        ('Main Hall',      'Main Hall'),
        ('Garden Terrace', 'Courtyard'),
        ('Chef Counter',   "Chef's Table"),
        ('Private Lounge', 'Royal Suite'),
    ]
    OCCASION_CHOICES = [
        ('Casual Fine Dining',    'Casual Fine Dining'),
        ('Anniversary',           'Anniversary Celebration'),
        ('Birthday',              'Birthday Gathering'),
        ('Business Entertaining', 'Business Entertaining'),
        ('Romantic Date Night',   'Romantic Date Night'),
        ('Proposal',              'Wedding Proposal'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reservations',
    )
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=30, validators=[phone_validator])
    guests = models.PositiveSmallIntegerField(
        default=2, validators=[MinValueValidator(1), MaxValueValidator(20)],
    )
    date = models.DateField()
    time = models.TimeField()
    seating_area = models.CharField(max_length=50, choices=SEATING_CHOICES, default='Main Hall')
    occasion = models.CharField(max_length=100, choices=OCCASION_CHOICES, default='Casual Fine Dining', blank=True)
    special_requests = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    fine_amount = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    fine_paid = models.BooleanField(default=False)
    fine_paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-date', '-time', '-created_at']
        indexes = [
            models.Index(fields=['date', 'time']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        at = f"{self.time:%I:%M %p}" if self.time else "time not set"
        return f"Reservation for {self.name} - {self.guests} guests on {self.date} at {at}"

    @property
    def starts_at(self):
        if not self.date or not self.time:
            return None
        return timezone.make_aware(datetime.combine(self.date, self.time))

    def can_cancel(self):
        if self.status not in ('PENDING', 'CONFIRMED') or self.starts_at is None:
            return False
        return self.starts_at - timezone.now() >= timedelta(hours=24)

    @property
    def fine_due(self):
        return self.fine_amount > 0 and not self.fine_paid

    @property
    def is_past_grace(self):
        if self.starts_at is None:
            return False
        grace = timedelta(minutes=settings.RESTAURANT['grace_minutes'])
        return timezone.now() >= self.starts_at + grace

    @property
    def when_text(self):
        if not self.time:
            return f"{self.date:%A, %d %B %Y}"
        return f"{self.date:%A, %d %B %Y} at {self.time:%I:%M %p}"

    def policy_text(self):
        info = settings.RESTAURANT
        return (
            f"Booking is free. Nothing is paid online. "
            f"We hold your table for {info['grace_minutes']} minutes. "
            f"No-show fine: Rs. {info['no_show_fine']}. "
            f"Cancel at least 24 hours before or call {info['phone']}."
        )

    def guest_message(self):
        info = settings.RESTAURANT
        name = info['name']
        if self.status == 'NO_SHOW':
            paid = " Fine has been received. Thank you." if self.fine_paid else ""
            return (
                f"Dear {self.name}, we missed you at {name} on {self.when_text}. "
                f"No-show fine of Rs. {self.fine_amount:.0f} to be collected at next visit.{paid} "
                f"Questions? Call {info['phone']}."
            )
        if self.status == 'CANCELLED':
            return f"Dear {self.name}, your {name} booking for {self.when_text} has been cancelled."
        if self.status == 'COMPLETED':
            return f"Dear {self.name}, thank you for dining with us at {name}. Hope to see you again!"
        if self.status == 'CONFIRMED':
            return (
                f"Dear {self.name}, your table for {self.guests} at {name} is CONFIRMED for {self.when_text} "
                f"({self.get_seating_area_display()}). {self.policy_text()}"
            )
        return (
            f"Dear {self.name}, we received your table request for {self.guests} at {name} on {self.when_text}. "
            f"We will confirm shortly. {self.policy_text()}"
        )

    @property
    def whatsapp_link(self):
        digits = ''.join(ch for ch in self.phone if ch.isdigit())
        if len(digits) == 10:
            digits = '91' + digits
        elif digits.startswith('0') and len(digits) == 11:
            digits = '91' + digits[1:]
        return f"https://wa.me/{digits}?text={quote(self.guest_message())}"


class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Message from {self.name}: {self.subject}"


# ==============================================================================
# POS / IN-RESTAURANT ORDERING SYSTEM
# ==============================================================================

class DiningTable(models.Model):
    """Physical table in the restaurant — used by the POS (Point of Sale) system."""
    SECTION_CHOICES = [
        ('Main Hall',      'Main Hall'),
        ('Garden Terrace', 'Garden Terrace / Courtyard'),
        ('Chef Counter',   "Chef's Counter"),
        ('Private Lounge', 'Royal Suite / Private Lounge'),
        ('Bar',            'Bar Area'),
    ]
    STATUS_CHOICES = [
        ('free',     'Free'),
        ('occupied', 'Occupied'),
        ('reserved', 'Reserved (Online Booking)'),
        ('cleaning', 'Being Cleaned'),
    ]
    number   = models.PositiveIntegerField(unique=True, help_text="Table number shown to staff")
    label    = models.CharField(max_length=20, blank=True, help_text="Optional label, e.g. T-01, VIP-1")
    capacity = models.PositiveSmallIntegerField(default=4, help_text="Max guests this table can seat")
    section  = models.CharField(max_length=50, choices=SECTION_CHOICES, default='Main Hall')
    status   = models.CharField(max_length=20, choices=STATUS_CHOICES, default='free')
    notes    = models.CharField(max_length=150, blank=True, help_text="e.g. Near window, accessibility friendly")

    class Meta:
        ordering = ['section', 'number']

    def __str__(self):
        label = f" ({self.label})" if self.label else ""
        return f"Table {self.number}{label} — {self.section} — {self.get_status_display()}"

    @property
    def active_order(self):
        """Returns the current open/active order for this table, if any."""
        return self.orders.filter(
            status__in=['open', 'preparing', 'ready', 'served', 'billed']
        ).first()


class Order(models.Model):
    """An in-restaurant order for a dining table (offline / POS order)."""
    STATUS_CHOICES = [
        ('open',      'Open — Taking Orders'),
        ('preparing', 'In Kitchen'),
        ('ready',     'Ready to Serve'),
        ('served',    'All Dishes Served'),
        ('billed',    'Bill Requested'),
        ('paid',      'Paid & Closed'),
        ('cancelled', 'Cancelled'),
    ]

    table       = models.ForeignKey(DiningTable, on_delete=models.PROTECT, related_name='orders')
    reservation = models.ForeignKey(
        Reservation, null=True, blank=True, on_delete=models.SET_NULL, related_name='table_orders',
        help_text="Link to an online reservation if the guest pre-booked"
    )
    taken_by    = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='orders_taken',
    )
    customer_name = models.CharField(max_length=120, blank=True, help_text="Walk-in guest name (optional)")
    pax           = models.PositiveSmallIntegerField(default=1, help_text="Number of guests at this table")
    notes         = models.TextField(blank=True, help_text="Special instructions for this order")
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)
    closed_at     = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.pk} — Table {self.table.number} — {self.get_status_display()}"

    @property
    def subtotal(self):
        result = self.items.exclude(status='cancelled').aggregate(
            total=Sum(
                ExpressionWrapper(F('unit_price') * F('quantity'), output_field=DjangoDecimalField())
            )
        )['total']
        return result or Decimal('0.00')

    @property
    def item_count(self):
        return self.items.exclude(status='cancelled').count()

    @property
    def all_served(self):
        return not self.items.filter(status__in=['pending', 'preparing', 'ready']).exists()


class OrderItem(models.Model):
    """One line item in an in-restaurant order."""
    ITEM_STATUS = [
        ('pending',   '⏳ Waiting in Queue'),
        ('preparing', '🔥 Preparing'),
        ('ready',     '✅ Ready — Pick Up'),
        ('served',    '🍽 Served to Table'),
        ('cancelled', '❌ Cancelled'),
    ]

    order     = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT, related_name='order_items')
    quantity  = models.PositiveSmallIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=7, decimal_places=2, help_text="Price at time of order")
    notes     = models.CharField(max_length=250, blank=True, help_text="e.g. No onions, extra spicy, medium well")
    status    = models.CharField(max_length=20, choices=ITEM_STATUS, default='pending')
    ordered_at = models.DateTimeField(auto_now_add=True)
    ready_at   = models.DateTimeField(null=True, blank=True)
    served_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['ordered_at']

    def __str__(self):
        return f"{self.quantity}× {self.menu_item.name} (Order #{self.order_id})"

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    @property
    def estimated_ready_at(self):
        """When this item is expected to be ready based on prep time."""
        return self.ordered_at + timedelta(minutes=self.menu_item.prep_time_minutes)

    @property
    def minutes_until_ready(self):
        remaining = (self.estimated_ready_at - timezone.now()).total_seconds() / 60
        return max(0, int(remaining))


class Bill(models.Model):
    """Bill generated at the end of an in-restaurant order."""
    PAYMENT_CHOICES = [
        ('cash',  'Cash'),
        ('card',  'Debit / Credit Card'),
        ('upi',   'UPI / QR Code'),
        ('split', 'Split Payment'),
    ]

    order                  = models.OneToOneField(Order, on_delete=models.PROTECT, related_name='bill')
    subtotal               = models.DecimalField(max_digits=9, decimal_places=2)
    gst_percent            = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('5.00'))
    gst_amount             = models.DecimalField(max_digits=9, decimal_places=2)
    service_charge_percent = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.00'))
    service_charge_amount  = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal('0.00'))
    discount_amount        = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal('0.00'))
    total                  = models.DecimalField(max_digits=9, decimal_places=2)
    payment_method         = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='cash')
    paid_at                = models.DateTimeField(null=True, blank=True)
    created_at             = models.DateTimeField(auto_now_add=True)
    notes                  = models.CharField(max_length=250, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Bill #{self.pk} — Order #{self.order_id} — ₹{self.total}"
