import logging
from datetime import datetime
from decimal import Decimal
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import (
    MAX_ONLINE_GUESTS, TIME_INPUT_FORMATS,
    ContactForm, RegisterForm, ReservationForm, flatten_errors,
)
from .models import (
    Bill, Category, Chef, ContactMessage, DiningTable,
    GalleryImage, MenuItem, Order, OrderItem, Reservation,
)

User = get_user_model()
logger = logging.getLogger(__name__)
RESTAURANT_NAME = settings.RESTAURANT['name']


# ── Helpers ──────────────────────────────────────────────────────────────────

def _send_email(subject, body, recipients):
    recipients = [r for r in recipients if r]
    if not recipients:
        return
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=False)
    except Exception:
        logger.exception("Could not send email: %s", subject)


def _safe_next_url(request, next_url):
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
    ):
        return next_url
    return 'dashboard'


def _reservation_initial(request):
    initial = {}
    digits = ''.join(ch for ch in request.GET.get('guests', '') if ch.isdigit())
    if digits:
        initial['guests'] = max(1, min(int(digits), MAX_ONLINE_GUESTS))
    if request.GET.get('date'):
        initial['date'] = request.GET['date']
    raw_time = request.GET.get('time', '').strip()
    for fmt in TIME_INPUT_FORMATS:
        try:
            initial['time'] = datetime.strptime(raw_time, fmt).strftime('%I:%M %p')
            break
        except ValueError:
            continue
    if request.user.is_authenticated:
        initial['name'] = request.user.get_full_name()
        initial['email'] = request.user.email
    return initial


def staff_required(view_func):
    """Protects staff-only views. Redirects to custom admin_login — never to Django's /admin/."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please log in with your administrator credentials.")
            return redirect('admin_login')
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(request, "Access denied. Administrator privileges required.")
            return redirect('admin_login')
        return view_func(request, *args, **kwargs)
    return wrapper


# ── Public Pages ─────────────────────────────────────────────────────────────

def home(request):
    featured_items = (
        MenuItem.objects
        .filter(is_chef_special=True, is_available=True)
        .select_related('category')[:3]
    )
    return render(request, 'home.html', {
        'featured_items': featured_items,
        'head_chef': Chef.objects.first(),
        'gallery_preview': GalleryImage.objects.all()[:4],
    })


def menu(request):
    meal_filter = request.GET.get('meal', '')
    all_items = MenuItem.objects.filter(is_available=True).select_related('category')
    if meal_filter and meal_filter in dict(MenuItem.MEAL_TYPE_CHOICES):
        all_items = all_items.filter(Q(meal_type=meal_filter) | Q(meal_type='all_day'))
    return render(request, 'menu.html', {
        'categories': Category.objects.all(),
        'all_items': all_items,
        'meal_types': MenuItem.MEAL_TYPE_CHOICES,
        'active_meal': meal_filter,
    })


def about(request):
    return render(request, 'about.html', {'chefs': Chef.objects.all()})


def reservation(request):
    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            if request.user.is_authenticated:
                booking.user = request.user
            booking.save()
            _send_email(
                f"Booking Request — {RESTAURANT_NAME}",
                booking.guest_message(),
                [booking.email],
            )
            messages.success(request, f"Table request received for {booking.name} on {booking.date} at {booking.time:%I:%M %p}! We'll confirm shortly.")
            return redirect('dashboard' if request.user.is_authenticated else 'reservation')
        for err in flatten_errors(form):
            messages.error(request, err)
    else:
        form = ReservationForm(initial=_reservation_initial(request))
    return render(request, 'reservation.html', {'form': form})


def gallery(request):
    return render(request, 'gallery.html', {'gallery_images': GalleryImage.objects.all()})


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            msg = form.save()
            _send_email(
                f"New inquiry: {msg.subject} — {RESTAURANT_NAME}",
                f"From: {msg.name} <{msg.email}>\n\n{msg.message}",
                [settings.RESTAURANT.get('email_bookings', '')],
            )
            messages.success(request, f"Thank you, {msg.name}! Your message has been sent.")
            return redirect('contact')
        for err in flatten_errors(form):
            messages.error(request, err)
    else:
        form = ContactForm()
    return render(request, 'contact.html', {'form': form})


def policy(request):
    return render(request, 'policy.html')


# ── Customer Auth ─────────────────────────────────────────────────────────────

def customer_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    next_url = request.GET.get('next', '')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = None
        if '@' in username:
            try:
                mu = User.objects.get(email__iexact=username)
                user = authenticate(request, username=mu.username, password=password)
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                pass
        else:
            user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            return redirect(_safe_next_url(request, next_url))
        else:
            messages.error(request, "Invalid username/email or password.")
    return render(request, 'login.html')


def customer_register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to {RESTAURANT_NAME}, {user.first_name or user.username}!")
            return redirect('dashboard')
        for err in flatten_errors(form):
            messages.error(request, err)
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})


@login_required(login_url='login')
def customer_dashboard(request):
    user_reservations = Reservation.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'dashboard.html', {'reservations': user_reservations})


@login_required(login_url='login')
@require_POST
def cancel_reservation(request, pk):
    booking = get_object_or_404(Reservation, pk=pk, user=request.user)
    if not booking.can_cancel():
        messages.error(request, "This booking cannot be cancelled (less than 24 hours before or already past).")
        return redirect('dashboard')
    booking.status = 'CANCELLED'
    booking.save(update_fields=['status'])
    _send_email(
        f"Booking Cancelled — {RESTAURANT_NAME}",
        booking.guest_message(),
        [booking.email],
    )
    messages.success(request, f"Your booking for {booking.date} has been cancelled.")
    return redirect('dashboard')


def custom_logout(request):
    logout(request)
    messages.info(request, "You have been safely signed out. See you again!")
    return redirect('home')


# ── Admin Auth & Dashboard ────────────────────────────────────────────────────

def admin_login_view(request):
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return redirect('admin_dashboard')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_staff or user.is_superuser:
                login(request, user)
                messages.success(request, f"Welcome, {user.username}. Admin console ready.")
                return redirect('admin_dashboard')
            else:
                messages.error(request, "Access Restricted: Administrator / Staff credentials required.")
        else:
            messages.error(request, "Invalid administrator username or password.")
    return render(request, 'admin_login.html')


@staff_required
def admin_dashboard_view(request):
    res_stats = Reservation.objects.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status='PENDING')),
        confirmed=Count('id', filter=Q(status='CONFIRMED')),
        no_shows=Count('id', filter=Q(status='NO_SHOW')),
        today=Count('id', filter=Q(date=timezone.localdate()) & ~Q(status='CANCELLED')),
    )
    customers_qs = User.objects.filter(is_staff=False, is_superuser=False)
    orders_today = Order.objects.filter(created_at__date=timezone.localdate())

    context = {
        # Stats
        'total_reservations':   res_stats['total'],
        'pending_count':        res_stats['pending'],
        'confirmed_count':      res_stats['confirmed'],
        'no_show_count':        res_stats['no_shows'],
        'today_count':          res_stats['today'],
        'fines_due_total':      Reservation.objects.filter(fine_paid=False, fine_amount__gt=0).aggregate(t=Sum('fine_amount'))['t'] or 0,
        'fines_collected_total': Reservation.objects.filter(fine_paid=True).aggregate(t=Sum('fine_amount'))['t'] or 0,
        'today':                timezone.localdate(),
        'total_menu_items':     MenuItem.objects.count(),
        'total_gallery':        GalleryImage.objects.count(),
        'total_chefs':          Chef.objects.count(),
        'total_messages':       ContactMessage.objects.count(),
        'total_customers':      customers_qs.count(),
        'total_tables':         DiningTable.objects.count(),
        'tables_occupied':      DiningTable.objects.filter(status='occupied').count(),
        'orders_today':         orders_today.count(),
        'orders_open':          Order.objects.filter(status__in=['open', 'preparing', 'ready', 'served', 'billed']).count(),
        'default_fine':         settings.RESTAURANT['no_show_fine'],
        # Data
        'reservations':         Reservation.objects.select_related('user').order_by('-created_at')[:200],
        'menu_items':           MenuItem.objects.select_related('category'),
        'categories':           Category.objects.all(),
        'meal_types':           MenuItem.MEAL_TYPE_CHOICES,
        'gallery_images':       GalleryImage.objects.all(),
        'chefs':                Chef.objects.all(),
        'contact_messages':     ContactMessage.objects.all()[:30],
        'customers':            customers_qs.annotate(res_count=Count('reservations')).order_by('-date_joined')[:200],
        'status_choices':       Reservation.STATUS_CHOICES,
        'dining_tables':        DiningTable.objects.all(),
        'table_sections':       DiningTable.SECTION_CHOICES,
        'active_orders':        Order.objects.filter(status__in=['open', 'preparing', 'ready', 'served', 'billed']).select_related('table').prefetch_related('items')[:50],
        'recent_bills':         Bill.objects.select_related('order__table').order_by('-created_at')[:20],
    }
    return render(request, 'admin_dashboard.html', context)


@staff_required
@require_POST
def admin_update_reservation(request, pk):
    booking = get_object_or_404(Reservation, pk=pk)
    new_status = request.POST.get('status')
    if new_status not in dict(Reservation.STATUS_CHOICES):
        messages.error(request, "Invalid status.")
        return redirect('admin_dashboard')
    booking.status = new_status
    fields = ['status']
    if new_status == 'NO_SHOW':
        if booking.fine_amount <= 0:
            booking.fine_amount = settings.RESTAURANT['no_show_fine']
        booking.fine_paid = False
        booking.fine_paid_at = None
        fields += ['fine_amount', 'fine_paid', 'fine_paid_at']
    elif booking.fine_amount > 0 and not booking.fine_paid:
        booking.fine_amount = 0
        fields += ['fine_amount']
    booking.save(update_fields=fields)
    notes = {
        'CONFIRMED': f"Your {RESTAURANT_NAME} reservation is confirmed",
        'NO_SHOW': f"We missed you at {RESTAURANT_NAME}: no-show fine notice",
        'CANCELLED': f"Your {RESTAURANT_NAME} reservation was cancelled",
        'COMPLETED': f"Thank you for dining at {RESTAURANT_NAME}",
    }
    if new_status in notes:
        _send_email(notes[new_status], booking.guest_message() + f"\n\n{RESTAURANT_NAME}", [booking.email])
    text = f"Reservation for {booking.name} marked as {booking.get_status_display()}."
    if new_status == 'NO_SHOW':
        text += f" Fine of ₹{booking.fine_amount:.0f} recorded."
    messages.success(request, text)
    return redirect('admin_dashboard')


@staff_required
@require_POST
def admin_reservation_fine(request, pk):
    booking = get_object_or_404(Reservation, pk=pk)
    action = request.POST.get('action')
    if booking.fine_amount <= 0:
        messages.error(request, "This booking has no fine.")
    elif action == 'collect':
        booking.fine_paid = True
        booking.fine_paid_at = timezone.now()
        booking.save(update_fields=['fine_paid', 'fine_paid_at'])
        messages.success(request, f"Fine of ₹{booking.fine_amount:.0f} from {booking.name} marked as collected.")
    elif action == 'waive':
        booking.fine_amount = 0
        booking.fine_paid = False
        booking.fine_paid_at = None
        booking.save(update_fields=['fine_amount', 'fine_paid', 'fine_paid_at'])
        messages.success(request, f"Fine for {booking.name} has been waived.")
    else:
        messages.error(request, "Unknown action.")
    return redirect('admin_dashboard')


# ── Admin CRUD: Menu Items ────────────────────────────────────────────────────

@staff_required
def admin_add_menu_item(request):
    if request.method == 'POST':
        try:
            cat_id = request.POST.get('category')
            category = get_object_or_404(Category, pk=cat_id)
            item = MenuItem(
                category=category,
                name=request.POST.get('name', '').strip(),
                description=request.POST.get('description', '').strip(),
                price=request.POST.get('price', '0'),
                meal_type=request.POST.get('meal_type', 'all_day'),
                prep_time_minutes=int(request.POST.get('prep_time_minutes', 15)),
                serve_unit=request.POST.get('serve_unit', 'plate'),
                dietary_tag=request.POST.get('dietary_tag', '').strip(),
                wine_pairing=request.POST.get('wine_pairing', '').strip(),
                is_veg=bool(request.POST.get('is_veg')),
                is_spicy=bool(request.POST.get('is_spicy')),
                is_chef_special=bool(request.POST.get('is_chef_special')),
                is_available=bool(request.POST.get('is_available', True)),
            )
            if 'image' in request.FILES:
                item.image = request.FILES['image']
            item.save()
            messages.success(request, f"'{item.name}' added to the menu successfully!")
        except Exception as e:
            messages.error(request, f"Error adding menu item: {e}")
    return redirect('admin_dashboard')


@staff_required
def admin_edit_menu_item(request, pk):
    item = get_object_or_404(MenuItem, pk=pk)
    if request.method == 'GET':
        return render(request, 'edit_menu_item.html', {
            'item': item,
            'categories': Category.objects.all(),
        })
    if request.method == 'POST':
        try:
            item.category = get_object_or_404(Category, pk=request.POST.get('category'))
            item.name = request.POST.get('name', '').strip()
            item.description = request.POST.get('description', '').strip()
            item.price = request.POST.get('price', item.price)
            item.meal_type = request.POST.get('meal_type', item.meal_type)
            item.prep_time_minutes = int(request.POST.get('prep_time_minutes', item.prep_time_minutes))
            item.serve_unit = request.POST.get('serve_unit', item.serve_unit)
            item.dietary_tag = request.POST.get('dietary_tag', '').strip()
            item.wine_pairing = request.POST.get('wine_pairing', '').strip()
            item.is_veg = bool(request.POST.get('is_veg'))
            item.is_spicy = bool(request.POST.get('is_spicy'))
            item.is_chef_special = bool(request.POST.get('is_chef_special'))
            item.is_available = bool(request.POST.get('is_available'))
            if 'image' in request.FILES:
                item.image = request.FILES['image']
            item.save()
            messages.success(request, f"'{item.name}' updated successfully!")
        except Exception as e:
            messages.error(request, f"Error updating menu item: {e}")
    return redirect('admin_dashboard')


@staff_required
@require_POST
def admin_delete_menu_item(request, pk):
    item = get_object_or_404(MenuItem, pk=pk)
    name = item.name
    item.delete()
    messages.success(request, f"'{name}' removed from the menu.")
    return redirect('admin_dashboard')


# ── Admin CRUD: Chefs ─────────────────────────────────────────────────────────

@staff_required
def admin_add_chef(request):
    if request.method == 'POST':
        try:
            chef = Chef(
                name=request.POST.get('name', '').strip(),
                title=request.POST.get('title', '').strip(),
                bio=request.POST.get('bio', '').strip(),
                display_order=int(request.POST.get('display_order', 0)),
            )
            if 'image' in request.FILES:
                chef.image = request.FILES['image']
            chef.save()
            messages.success(request, f"Chef '{chef.name}' added successfully!")
        except Exception as e:
            messages.error(request, f"Error adding chef: {e}")
    return redirect('admin_dashboard')


@staff_required
def admin_edit_chef(request, pk):
    chef = get_object_or_404(Chef, pk=pk)
    if request.method == 'GET':
        return render(request, 'edit_chef.html', {'chef': chef})
    if request.method == 'POST':
        try:
            chef.name = request.POST.get('name', '').strip()
            chef.title = request.POST.get('title', '').strip()
            chef.bio = request.POST.get('bio', '').strip()
            chef.display_order = int(request.POST.get('display_order', chef.display_order))
            if 'image' in request.FILES:
                chef.image = request.FILES['image']
            chef.save()
            messages.success(request, f"Chef '{chef.name}' updated successfully!")
        except Exception as e:
            messages.error(request, f"Error updating chef: {e}")
    return redirect('admin_dashboard')


@staff_required
@require_POST
def admin_delete_chef(request, pk):
    chef = get_object_or_404(Chef, pk=pk)
    name = chef.name
    chef.delete()
    messages.success(request, f"Chef '{name}' removed.")
    return redirect('admin_dashboard')


# ── Admin CRUD: Gallery ───────────────────────────────────────────────────────

@staff_required
def admin_add_gallery(request):
    if request.method == 'POST':
        try:
            img = GalleryImage(
                title=request.POST.get('title', '').strip(),
                category=request.POST.get('category', 'interior'),
                description=request.POST.get('description', '').strip(),
                display_order=int(request.POST.get('display_order', 0)),
            )
            if 'image' in request.FILES:
                img.image = request.FILES['image']
            img.save()
            messages.success(request, f"Gallery image '{img.title}' added!")
        except Exception as e:
            messages.error(request, f"Error adding gallery image: {e}")
    return redirect('admin_dashboard')


@staff_required
def admin_edit_gallery(request, pk):
    img = get_object_or_404(GalleryImage, pk=pk)
    if request.method == 'GET':
        return render(request, 'edit_gallery.html', {'img': img})
    if request.method == 'POST':
        try:
            img.title = request.POST.get('title', '').strip()
            img.category = request.POST.get('category', img.category)
            img.description = request.POST.get('description', '').strip()
            img.display_order = int(request.POST.get('display_order', img.display_order))
            if 'image' in request.FILES:
                img.image = request.FILES['image']
            img.save()
            messages.success(request, f"Gallery image '{img.title}' updated!")
        except Exception as e:
            messages.error(request, f"Error updating gallery image: {e}")
    return redirect('admin_dashboard')


@staff_required
@require_POST
def admin_delete_gallery(request, pk):
    img = get_object_or_404(GalleryImage, pk=pk)
    title = img.title
    img.delete()
    messages.success(request, f"Gallery image '{title}' deleted.")
    return redirect('admin_dashboard')


# ── Admin: Table Management ───────────────────────────────────────────────────

@staff_required
def admin_manage_tables(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            try:
                DiningTable.objects.create(
                    number=int(request.POST.get('number', 0)),
                    label=request.POST.get('label', '').strip(),
                    capacity=int(request.POST.get('capacity', 4)),
                    section=request.POST.get('section', 'Main Hall'),
                    notes=request.POST.get('notes', '').strip(),
                )
                messages.success(request, "Table added successfully!")
            except Exception as e:
                messages.error(request, f"Error adding table: {e}")
        elif action == 'update_status':
            tbl = get_object_or_404(DiningTable, pk=request.POST.get('table_id'))
            tbl.status = request.POST.get('status', tbl.status)
            tbl.save(update_fields=['status'])
            messages.success(request, f"Table {tbl.number} status updated to {tbl.get_status_display()}.")
        elif action == 'bulk_create':
            created = 0
            for i in range(1, 11):
                _, made = DiningTable.objects.get_or_create(
                    number=i,
                    defaults={'capacity': 4 if i <= 6 else 2, 'section': 'Main Hall' if i <= 6 else 'Garden Terrace'}
                )
                if made:
                    created += 1
            messages.success(request, f'Auto-created {created} tables (skipped existing).')
        elif action == 'delete':
            tbl = get_object_or_404(DiningTable, pk=request.POST.get('table_id'))
            num = tbl.number
            tbl.delete()
            messages.success(request, f'Table {num} deleted.')
    return redirect('admin_dashboard')


# ── POS System ────────────────────────────────────────────────────────────────

@staff_required
def pos_home(request):
    """POS landing: table map — click a table to open/create its order."""
    tables = DiningTable.objects.all()
    table_data = []
    for t in tables:
        active = t.active_order
        table_data.append({'table': t, 'active_order': active})
    return render(request, 'pos.html', {
        'table_data': table_data,
        'sections': DiningTable.SECTION_CHOICES,
    })


@staff_required
def pos_order(request, table_id):
    """Full-screen order screen for a specific table."""
    table = get_object_or_404(DiningTable, pk=table_id)
    # Get or create an open order for this table
    order = table.active_order
    if not order:
        pax = int(request.GET.get('pax', 1))
        customer_name = request.GET.get('name', '').strip()
        order = Order.objects.create(
            table=table,
            taken_by=request.user,
            pax=pax,
            customer_name=customer_name,
        )
        table.status = 'occupied'
        table.save(update_fields=['status'])

    # Menu grouped by category
    categories = Category.objects.prefetch_related('items').all()
    meal_filter = request.GET.get('meal', '')

    all_items_qs = MenuItem.objects.filter(is_available=True).select_related('category')
    if meal_filter:
        from django.db.models import Q
        all_items_qs = all_items_qs.filter(Q(meal_type=meal_filter) | Q(meal_type='all_day'))

    return render(request, 'pos_order.html', {
        'table': table,
        'order': order,
        'order_items': order.items.select_related('menu_item').order_by('-ordered_at'),
        'categories': categories,
        'all_items': all_items_qs,
        'meal_types': MenuItem.MEAL_TYPE_CHOICES,
        'active_meal': meal_filter,
    })


@staff_required
@require_POST
def pos_add_item(request, order_id):
    """Add an item (or multiple) to an order."""
    order = get_object_or_404(Order, pk=order_id)
    if order.status not in ('open', 'preparing', 'ready', 'served'):
        messages.error(request, "Cannot add items to a closed order.")
        return redirect('pos_order', table_id=order.table_id)

    menu_item_id = request.POST.get('menu_item_id')
    quantity = max(1, int(request.POST.get('quantity', 1)))
    notes = request.POST.get('notes', '').strip()
    menu_item = get_object_or_404(MenuItem, pk=menu_item_id)

    OrderItem.objects.create(
        order=order,
        menu_item=menu_item,
        quantity=quantity,
        unit_price=menu_item.price,
        notes=notes,
        status='pending',
    )
    # Update order status so kitchen knows
    if order.status == 'served':
        order.status = 'open'
        order.save(update_fields=['status'])

    messages.success(request, f"{quantity}× {menu_item.name} added to order.")
    return redirect('pos_order', table_id=order.table_id)


@staff_required
@require_POST
def pos_remove_item(request, item_id):
    item = get_object_or_404(OrderItem, pk=item_id)
    table_id = item.order.table_id
    if item.status in ('pending', 'preparing'):
        item.status = 'cancelled'
        item.save(update_fields=['status'])
        messages.success(request, f"'{item.menu_item.name}' removed from order.")
    else:
        messages.error(request, "Cannot remove an item that is already ready or served.")
    return redirect('pos_order', table_id=table_id)


@staff_required
@require_POST
def pos_send_to_kitchen(request, order_id):
    """Mark all pending items as 'preparing' — sends the order to the kitchen."""
    order = get_object_or_404(Order, pk=order_id)
    updated = order.items.filter(status='pending').update(status='preparing')
    order.status = 'preparing'
    order.save(update_fields=['status'])
    messages.success(request, f"{updated} item(s) sent to kitchen.")
    return redirect('pos_order', table_id=order.table_id)


@staff_required
@require_POST
def pos_mark_served(request, order_id):
    """Mark all ready items as served."""
    order = get_object_or_404(Order, pk=order_id)
    now = timezone.now()
    order.items.filter(status='ready').update(status='served', served_at=now)
    if order.all_served:
        order.status = 'served'
        order.save(update_fields=['status'])
    messages.success(request, "All ready items marked as served.")
    return redirect('pos_order', table_id=order.table_id)


@staff_required
def pos_generate_bill(request, order_id):
    """Generate or view the bill for an order."""
    order = get_object_or_404(Order, pk=order_id)

    # If bill already exists, just show it
    try:
        bill = order.bill
    except Bill.DoesNotExist:
        bill = None

    if request.method == 'POST' and not bill:
        gst_pct = Decimal(request.POST.get('gst_percent', '5'))
        sc_pct = Decimal(request.POST.get('service_charge_percent', '0'))
        discount = Decimal(request.POST.get('discount_amount', '0'))
        payment_method = request.POST.get('payment_method', 'cash')

        subtotal = order.subtotal
        gst_amt = (subtotal * gst_pct / 100).quantize(Decimal('0.01'))
        sc_amt = (subtotal * sc_pct / 100).quantize(Decimal('0.01'))
        total = subtotal + gst_amt + sc_amt - discount

        bill = Bill.objects.create(
            order=order,
            subtotal=subtotal,
            gst_percent=gst_pct,
            gst_amount=gst_amt,
            service_charge_percent=sc_pct,
            service_charge_amount=sc_amt,
            discount_amount=discount,
            total=total,
            payment_method=payment_method,
        )
        order.status = 'billed'
        order.save(update_fields=['status'])
        messages.success(request, f"Bill generated: ₹{total:.2f}")

    return render(request, 'bill.html', {
        'order': order,
        'bill': bill,
        'order_items': order.items.exclude(status='cancelled').select_related('menu_item'),
        'restaurant': settings.RESTAURANT,
        'payment_methods': Bill.PAYMENT_CHOICES,
    })


@staff_required
@require_POST
def pos_mark_paid(request, bill_id):
    """Mark bill as paid and free the table."""
    bill = get_object_or_404(Bill, pk=bill_id)
    bill.paid_at = timezone.now()
    bill.payment_method = request.POST.get('payment_method', bill.payment_method)
    bill.save(update_fields=['paid_at', 'payment_method'])

    order = bill.order
    order.status = 'paid'
    order.closed_at = timezone.now()
    order.save(update_fields=['status', 'closed_at'])

    table = order.table
    table.status = 'cleaning'
    table.save(update_fields=['status'])

    messages.success(request, f"Bill #{bill.pk} paid (₹{bill.total:.2f}). Table {table.number} set to cleaning.")
    return redirect('pos_home')


# ── Kitchen Display System ────────────────────────────────────────────────────

@staff_required
def kitchen_display(request):
    """Kitchen screen: shows all pending and preparing order items in real time."""
    preparing_items = (
        OrderItem.objects
        .filter(status__in=['pending', 'preparing'])
        .select_related('menu_item', 'order__table')
        .order_by('ordered_at')
    )
    return render(request, 'kitchen.html', {
        'preparing_items': preparing_items,
        'now': timezone.now(),
    })


@staff_required
@require_POST
def kitchen_update_item(request, item_id):
    """Kitchen marks an item as ready."""
    item = get_object_or_404(OrderItem, pk=item_id)
    new_status = request.POST.get('status', 'ready')
    if new_status in ('preparing', 'ready'):
        item.status = new_status
        if new_status == 'ready':
            item.ready_at = timezone.now()
        item.save(update_fields=['status', 'ready_at'])
        # Update parent order status
        order = item.order
        if new_status == 'ready' and not order.items.filter(status__in=['pending', 'preparing']).exists():
            order.status = 'ready'
            order.save(update_fields=['status'])
    return redirect('kitchen_display')
