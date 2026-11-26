"""Create the admin (superuser) account safely.

Usage:
    python create_superuser.py

Optional environment variables:
    DJANGO_SUPERUSER_USERNAME   (default: admin)
    DJANGO_SUPERUSER_EMAIL      (default: admin@aura.com)
    DJANGO_SUPERUSER_PASSWORD   (default: a random password, printed once)

An existing user is never modified, so running this twice is harmless.
"""
import os
import secrets
import sys

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'restaurant.settings')
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402


def main():
    User = get_user_model()
    username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
    email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@aura.com')
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

    if User.objects.filter(username=username).exists():
        print(f"User '{username}' already exists. Nothing changed.")
        print("To change the password run: python manage.py changepassword " + username)
        return 0

    generated = False
    if not password:
        password = secrets.token_urlsafe(12)
        generated = True

    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Superuser '{username}' created successfully.")
    if generated:
        print(f"Generated password (shown only once, save it now): {password}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
