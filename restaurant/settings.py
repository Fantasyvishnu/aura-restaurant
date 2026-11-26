from pathlib import Path
import os

from django.contrib.messages import constants as message_constants
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
# Folder for the database and uploaded photos (on Railway this is the /data volume)
DATA_DIR = Path(os.environ.get('DATA_DIR', BASE_DIR))


def env_bool(name, default=False):
    """Read a True/False setting from an environment variable."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=''):
    """Read a comma-separated list from an environment variable."""
    return [item.strip() for item in os.environ.get(name, default).split(',') if item.strip()]


# ==============================================================================
# CORE / SECURITY
# ==============================================================================
# On your own computer nothing needs to be set: it runs in debug mode with the
# development key below. For the real website, set these environment variables:
#   DJANGO_DEBUG=0
#   DJANGO_SECRET_KEY=<a long random string>
#   DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DEBUG = env_bool('DJANGO_DEBUG', True)

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-dev-only-key-change-me')
if not DEBUG and SECRET_KEY.startswith('django-insecure'):
    raise ImproperlyConfigured('Set DJANGO_SECRET_KEY to a long random value when DJANGO_DEBUG is off.')

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS')   # e.g. https://yourdomain.com

# Extra protection that is switched on automatically when DEBUG is off
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool('DJANGO_SSL_REDIRECT', True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ==============================================================================
# APPLICATIONS
# ==============================================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'main',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Optional: serve CSS/JS efficiently in production (pip install whitenoise).
# It is only used if installed, so nothing breaks without it.
try:
    import whitenoise  # noqa: F401
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
    if not DEBUG:
        STORAGES = {
            'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
            'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
        }
except ImportError:
    pass

ROOT_URLCONF = 'restaurant.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'main.context_processors.restaurant',
            ],
        },
    },
]

WSGI_APPLICATION = 'restaurant.wsgi.application'
ASGI_APPLICATION = 'restaurant.asgi.application'

# ==============================================================================
# DATABASE
# ==============================================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DATA_DIR / 'db.sqlite3',
    }
}

# ==============================================================================
# PASSWORDS & LOGIN
# ==============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = 'login'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14   # "Keep me signed in" lasts 14 days

# ==============================================================================
# LANGUAGE & TIME (Tamil Nadu, India)
# ==============================================================================
LANGUAGE_CODE = 'en-in'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# ==============================================================================
# STATIC & MEDIA FILES
# ==============================================================================
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'      # where `python manage.py collectstatic` puts files

MEDIA_URL = '/media/'
MEDIA_ROOT = DATA_DIR / 'media'             # uploaded food, gallery and chef photos

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==============================================================================
# MESSAGES: make error messages use Bootstrap's "danger" colour
# ==============================================================================
MESSAGE_TAGS = {message_constants.ERROR: 'danger'}

# ==============================================================================
# EMAIL
# ==============================================================================
# Development: emails are printed in the terminal window, nothing is sent.
# Production: set EMAIL_HOST, EMAIL_HOST_USER and EMAIL_HOST_PASSWORD as environment
# variables (for example from Gmail, Zoho or your hosting provider).
if os.environ.get('EMAIL_HOST'):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ['EMAIL_HOST']
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'AURA Fine Dining & Bar <no-reply@aurafinedining.in>')

# The restaurant inbox that receives new reservation and contact notifications
CONTACT_NOTIFY_EMAIL = os.environ.get('CONTACT_NOTIFY_EMAIL', '')


# ==============================================================================
# RESTAURANT DETAILS  (edit these in ONE place: every page, email and message uses them)
# ==============================================================================
RESTAURANT = {
    'name': 'AURA Fine Dining & Bar',
    'phone': '+91 98765 43210',                 # TODO: put your real reservations number
    'phone_tel': '+919876543210',               # same number without spaces (for tap-to-call links)
    'events_phone': '+91 98765 43211',          # TODO: events and catering number
    'events_phone_tel': '+919876543211',
    'email_bookings': 'reservations@aurafinedining.in',   # TODO: your real emails
    'email_events': 'events@aurafinedining.in',
    'address_line1': 'No. 7, Temple Road, Alwarpet',      # TODO: your real address
    'address_line2': 'Chennai, Tamil Nadu 600018',
    # Booking is free and nothing is paid online. Money is only ever collected in person at the restaurant.
    # If a guest does not arrive within `grace_minutes` of the booked time, a no-show fine is collected at the restaurant.
    'no_show_fine': int(os.environ.get('NO_SHOW_FINE', '500')),    # rupees, flat per booking
    'grace_minutes': int(os.environ.get('GRACE_MINUTES', '15')),
    'gst_percent': 5,                           # GST added to food bills (check the rate that applies to your restaurant)
    'gstin': '',                                # TODO: your GST number, printed on the bill when filled in
    # Website orders are only accepted during opening hours (set ENFORCE_ORDER_HOURS=0 to test at any time)
    'enforce_order_hours': env_bool('ENFORCE_ORDER_HOURS', True),
    'bar_min_age': 21,                          # please check the current legal drinking age and your licence conditions
}
