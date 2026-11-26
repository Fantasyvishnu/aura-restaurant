from datetime import time, timedelta

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.utils import timezone
from django.utils.text import slugify

from .models import Category, Chef, ContactMessage, DiningTable, GalleryImage, MenuItem, Reservation, phone_validator

User = get_user_model()

# ── Restaurant rules ─────────────────────────────────────────────────────────
MAX_ADVANCE_DAYS    = 30
MAX_ONLINE_GUESTS   = 20
RESTAURANT_CAPACITY = 60

OPENING_HOURS = {day: (time(12, 0), time(22, 30)) for day in range(7)}
TIME_INPUT_FORMATS = ['%I:%M %p', '%H:%M', '%H:%M:%S']

CONTACT_SUBJECTS = [
    ('General Dining Inquiry',        'General Dining Inquiry'),
    ('Private Dining / Full Buyout',  'Private Dining / Full Buyout'),
    ('Wedding & Event Catering',      'Wedding & Event Catering'),
    ('Dietary & Allergen Guidance',   'Dietary & Allergen Guidance'),
    ('Press & Media Relations',       'Press & Media Relations'),
]


def flatten_errors(form):
    out = []
    for field, errors in form.errors.items():
        if field == '__all__':
            label = ''
        else:
            label = form.fields[field].label or field.replace('_', ' ').title()
        for error in errors:
            out.append(f"{label}: {error}" if label else str(error))
    return out


# ── Reservation form (online booking) ────────────────────────────────────────

class ReservationForm(forms.ModelForm):
    time = forms.TimeField(input_formats=TIME_INPUT_FORMATS,
                           error_messages={'invalid': 'Please choose a valid seating time.'})
    requests      = forms.CharField(required=False, max_length=1000, widget=forms.Textarea)
    accept_policy = forms.BooleanField(
        required=True,
        error_messages={'required': 'Please tick the box to accept the booking policy.'},
    )

    class Meta:
        model  = Reservation
        fields = ['name', 'email', 'phone', 'guests', 'date', 'time', 'seating_area', 'occasion']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['guests'].min_value = 1
        self.fields['guests'].max_value = MAX_ONLINE_GUESTS
        self.fields['guests'].widget.attrs.update({'min': 1, 'max': MAX_ONLINE_GUESTS})

    def clean_name(self):
        return self.cleaned_data['name'].strip()

    def clean_guests(self):
        g = self.cleaned_data['guests']
        if g > MAX_ONLINE_GUESTS:
            raise ValidationError(f"Online bookings limited to {MAX_ONLINE_GUESTS} guests.")
        return g

    def clean_date(self):
        d = self.cleaned_data['date']
        today = timezone.localdate()
        if d < today:
            raise ValidationError("Please choose today or a future date.")
        if d > today + timedelta(days=MAX_ADVANCE_DAYS):
            raise ValidationError(f"Reservations open {MAX_ADVANCE_DAYS} days in advance.")
        return d

    def clean_occasion(self):
        return self.cleaned_data.get('occasion') or 'Casual Fine Dining'

    def clean(self):
        cleaned = super().clean()
        d = cleaned.get('date')
        t = cleaned.get('time')
        g = cleaned.get('guests')
        if d and t:
            first, last = OPENING_HOURS[d.weekday()]
            if not (first <= t <= last):
                self.add_error('time',
                    f"On {d:%A}s we seat guests between {first:%I:%M %p} and {last:%I:%M %p}.")
            elif d == timezone.localdate() and t <= timezone.localtime().time():
                self.add_error('time', "That time has already passed today.")
            elif g:
                already = (
                    Reservation.objects
                    .filter(date=d, time=t)
                    .exclude(status='CANCELLED')
                    .aggregate(total=Sum('guests'))['total'] or 0
                )
                if already + g > RESTAURANT_CAPACITY:
                    self.add_error('time', "Sorry, that time slot is fully booked. Please choose another.")
        return cleaned

    def save(self, commit=True):
        res = super().save(commit=False)
        res.special_requests = self.cleaned_data.get('requests', '').strip()
        if commit:
            res.save()
        return res


# ── Contact form ──────────────────────────────────────────────────────────────

class ContactForm(forms.ModelForm):
    website = forms.CharField(required=False)   # honeypot
    subject = forms.ChoiceField(choices=CONTACT_SUBJECTS, required=False)

    class Meta:
        model  = ContactMessage
        fields = ['name', 'email', 'phone', 'subject', 'message']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['phone'].validators.append(phone_validator)

    def clean_website(self):
        if self.cleaned_data.get('website'):
            raise ValidationError("Spam detected.")
        return ''

    def clean_subject(self):
        return self.cleaned_data.get('subject') or CONTACT_SUBJECTS[0][0]

    def clean_message(self):
        m = self.cleaned_data['message'].strip()
        if len(m) < 10:
            raise ValidationError("Please write at least 10 characters.")
        return m


# ── Customer registration form ────────────────────────────────────────────────

class RegisterForm(forms.Form):
    full_name        = forms.CharField(max_length=150, required=False)
    username         = forms.CharField(max_length=150, validators=User._meta.get_field('username').validators)
    email            = forms.EmailField()
    password         = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def clean_username(self):
        u = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=u).exists():
            raise ValidationError("That username is already taken.")
        return u

    def clean_email(self):
        e = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=e).exists():
            raise ValidationError("An account with this email already exists.")
        return e

    def clean(self):
        cleaned = super().clean()
        p  = cleaned.get('password')
        cp = cleaned.get('confirm_password')
        if p and cp and p != cp:
            self.add_error('confirm_password', "Passwords do not match.")
        elif p:
            tmp = User(username=cleaned.get('username', ''), email=cleaned.get('email', ''))
            try:
                validate_password(p, user=tmp)
            except ValidationError as e:
                self.add_error('password', e)
        return cleaned

    def save(self):
        full = self.cleaned_data.get('full_name', '').strip()
        first, _, last = full.partition(' ')
        return User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password'],
            first_name=first,
            last_name=last.strip(),
        )


# ── Admin CRUD forms ──────────────────────────────────────────────────────────

class MenuItemForm(forms.ModelForm):
    class Meta:
        model  = MenuItem
        fields = [
            'category', 'name', 'description', 'price',
            'meal_type', 'prep_time_minutes', 'serve_unit',
            'dietary_tag', 'wine_pairing',
            'is_veg', 'is_spicy', 'is_chef_special', 'is_available', 'image',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class ChefForm(forms.ModelForm):
    class Meta:
        model  = Chef
        fields = ['name', 'title', 'bio', 'image', 'display_order']
        widgets = {'bio': forms.Textarea(attrs={'rows': 3})}


class GalleryImageForm(forms.ModelForm):
    class Meta:
        model  = GalleryImage
        fields = ['title', 'category', 'image', 'description', 'display_order']


class CategoryForm(forms.ModelForm):
    class Meta:
        model  = Category
        fields = ['name', 'slug', 'display_order']

    def clean_slug(self):
        slug = self.cleaned_data.get('slug') or slugify(self.cleaned_data.get('name', ''))
        if Category.objects.filter(slug=slug).exists():
            raise ValidationError("A category with this slug already exists.")
        return slug


class DiningTableForm(forms.ModelForm):
    class Meta:
        model  = DiningTable
        fields = ['number', 'label', 'capacity', 'section', 'notes']
