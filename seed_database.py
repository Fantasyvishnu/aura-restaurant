"""Seed the AURA Fine Dining & Bar database with Tamil Nadu menu, gallery and chef data.

Usage:
    python seed_database.py --reset    # FIRST TIME after the Tamil Nadu makeover:
                                       # removes the old French/Japanese demo dishes
    python seed_database.py            # afterwards: safe, creates/updates only, deletes nothing

--reset only deletes menu items, categories, gallery images and chefs.
Reservations, users and contact messages are never touched.

The chef names and bios are SAMPLE text: replace them with your real team in the admin.
Images are expected in media/food, media/gallery and media/chefs
(run create_media_assets.py for placeholders, then upload real photos in the admin).
"""
import argparse
import os
from decimal import Decimal

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'restaurant.settings')
django.setup()

from main.models import Category, Chef, GalleryImage, MenuItem  # noqa: E402

CATEGORIES = [
    {'slug': 'starters', 'name': 'Starters & Snacks', 'display_order': 1},
    {'slug': 'mains', 'name': 'Chettinad & Kongu Mains', 'display_order': 2},
    {'slug': 'specials', 'name': 'Banana-Leaf Feasts', 'display_order': 3},
    {'slug': 'desserts', 'name': 'Sweets & Payasam', 'display_order': 4},
    {'slug': 'drinks', 'name': 'Coffee & Coolers', 'display_order': 5},
]

# 'wine_pairing' is the model's "serving note" field (kept to avoid a database migration)
MENU_ITEMS = [
    # Starters
    {
        'category': 'starters',
        'name': 'Kuzhi Paniyaram Trio',
        'description': 'Golden rice-and-lentil dumplings cooked in a cast-iron pan: classic onion, curry leaf and sweet jaggery-coconut.',
        'price': '260.00',
        'image': 'food/kuzhi_paniyaram.png',
        'is_chef_special': False,
        'dietary_tag': 'Vegetarian',
        'wine_pairing': 'Served with coconut and tomato chutney',
    },
    {
        'category': 'starters',
        'name': 'Madurai Chicken 65',
        'description': 'Crisp, fiery chicken tossed with curry leaves, green chilli and yoghurt-ginger masala, the Madurai way.',
        'price': '420.00',
        'image': 'food/madurai_chicken_65.png',
        'is_chef_special': False,
        'dietary_tag': 'Non-Veg · Spicy',
        'wine_pairing': 'Best with fresh lime soda',
    },
    # Mains
    {
        'category': 'mains',
        'name': 'Chettinad Pepper Chicken',
        'description': 'Country chicken slow-cooked with hand-pounded black pepper, fennel, star anise and kalpasi, finished with fresh curry leaf.',
        'price': '520.00',
        'image': 'food/chettinad_pepper_chicken.png',
        'is_chef_special': True,
        'dietary_tag': 'Non-Veg · Spicy',
        'wine_pairing': 'Served with flaky Malabar parotta',
    },
    {
        'category': 'mains',
        'name': 'Chettinad Mutton Chukka',
        'description': 'Tender mutton dry-roasted in stone-ground Chettinad masala with shallots, garlic and a touch of coconut.',
        'price': '640.00',
        'image': 'food/mutton_chukka.png',
        'is_chef_special': False,
        'dietary_tag': 'Non-Veg · Spicy',
        'wine_pairing': 'Served with ghee rice or parotta',
    },
    {
        'category': 'mains',
        'name': 'Meen Kuzhambu with Steamed Rice',
        'description': 'Tangy tamarind fish curry simmered in a clay pot with shallots and tomato, served with steamed rice and a papad.',
        'price': '560.00',
        'image': 'food/meen_kuzhambu.png',
        'is_chef_special': False,
        'dietary_tag': 'Seafood',
        'wine_pairing': 'Served with beans poriyal',
    },
    # Banana-leaf feasts
    {
        'category': 'specials',
        'name': 'Royal Banana-Leaf Meal',
        'description': 'A full vegetarian feast on a fresh banana leaf: kootu, poriyal, sambar, rasam, appalam, curd rice and payasam, served in the classic order.',
        'price': '950.00',
        'image': 'food/banana_leaf_meal.png',
        'is_chef_special': True,
        'dietary_tag': 'Vegetarian',
        'wine_pairing': 'Unlimited refills, served by your personal host',
    },
    {
        'category': 'specials',
        'name': 'Dindigul Seeraga Samba Biryani',
        'description': 'Fragrant seeraga samba rice dum-cooked with tender chicken, pepper and whole spices, the Dindigul way.',
        'price': '580.00',
        'image': 'food/dindigul_biryani.png',
        'is_chef_special': True,
        'dietary_tag': 'Non-Veg',
        'wine_pairing': 'Served with raita and brinjal thokku',
    },
    # Desserts
    {
        'category': 'desserts',
        'name': 'Thanjavur Kasi Halwa',
        'description': 'Silky ash-gourd halwa slow-cooked in pure ghee with cashew and saffron, a Thanjavur temple-town favourite.',
        'price': '240.00',
        'image': 'food/kasi_halwa.png',
        'is_chef_special': True,
        'dietary_tag': 'Vegetarian',
        'wine_pairing': 'Served warm',
    },
    {
        'category': 'desserts',
        'name': 'Paal Payasam',
        'description': 'Rice simmered slowly in sweetened milk with cardamom, ghee-roasted cashew and raisins.',
        'price': '220.00',
        'image': 'food/paal_payasam.png',
        'is_chef_special': False,
        'dietary_tag': 'Vegetarian',
        'wine_pairing': 'Served warm or chilled',
    },
    # Drinks
    {
        'category': 'drinks',
        'name': 'Madurai Jigarthanda',
        'description': 'The iconic Madurai cooler: chilled milk, almond gum, sarsaparilla syrup and ice cream.',
        'price': '240.00',
        'image': 'food/jigarthanda.png',
        'is_chef_special': False,
        'dietary_tag': 'Vegetarian',
        'wine_pairing': 'Served ice cold',
    },
    {
        'category': 'drinks',
        'name': 'Kumbakonam Degree Filter Coffee',
        'description': 'Freshly brewed South Indian filter coffee with thick creamy milk, served in a traditional davara-tumbler.',
        'price': '120.00',
        'image': 'food/filter_coffee.png',
        'is_chef_special': False,
        'dietary_tag': 'Vegetarian',
        'wine_pairing': 'Best after the meal',
    },
]

GALLERY = [
    {
        'title': 'The Palace Dining Hall',
        'category': 'interior',
        'image': 'gallery/palace_dining_hall.png',
        'description': 'Carved teak pillars, brass lamps and silk-draped seating inspired by Chettinad mansions.',
        'display_order': 1,
    },
    {
        'title': 'The Banana-Leaf Feast',
        'category': 'dishes',
        'image': 'gallery/banana_leaf_feast.png',
        'description': 'Our signature meal, served in the traditional order on a fresh banana leaf.',
        'display_order': 2,
    },
    {
        'title': 'Filter Coffee & Sweets',
        'category': 'drinks',
        'image': 'gallery/filter_coffee_sweets.png',
        'description': 'Degree coffee in brass davara-tumblers with Thanjavur sweets.',
        'display_order': 3,
    },
    {
        'title': 'The Courtyard',
        'category': 'patio',
        'image': 'gallery/courtyard.png',
        'description': 'An open courtyard with a lamp-lit tulsi mathadam, perfect for family evenings.',
        'display_order': 4,
    },
    {
        'title': 'Thanjavur Temple Sweets',
        'category': 'dishes',
        'image': 'gallery/thanjavur_sweets.png',
        'description': 'Kasi halwa, payasam and ghee sweets made fresh every day.',
        'display_order': 5,
    },
    {
        'title': 'The Royal Suite',
        'category': 'interior',
        'image': 'gallery/royal_suite.png',
        'description': 'A private suite for family celebrations, business dinners and wedding gatherings.',
        'display_order': 6,
    },
]

# SAMPLE people: replace with your real team in the Django admin.
CHEFS = [
    {
        'name': 'Chef Annamalai Chettiar',
        'title': 'Executive Chef & Founder',
        'bio': 'Leads our Chettinad kitchen with family recipes, stone-ground masalas and a love for slow cooking.',
        'image': 'chefs/annamalai_chettiar.png',
        'display_order': 1,
    },
    {
        'name': 'Chef Meenakshi Raghavan',
        'title': 'Head of Sweets & Thanjavur Kitchen',
        'bio': 'Keeps the temple-town sweet tradition alive, from kasi halwa to creamy payasam made in pure ghee.',
        'image': 'chefs/meenakshi_raghavan.png',
        'display_order': 2,
    },
    {
        'name': 'Karthikeyan Pillai',
        'title': 'Head of Hospitality',
        'bio': 'Makes sure every guest is welcomed with a warm "Vanakkam" and looked after from the first sip of water to the last cup of coffee.',
        'image': 'chefs/karthikeyan_pillai.png',
        'display_order': 3,
    },
]


def reset_tables():
    print("Resetting: deleting existing menu items, categories, gallery images and chefs...")
    MenuItem.objects.all().delete()
    Category.objects.all().delete()
    GalleryImage.objects.all().delete()
    Chef.objects.all().delete()


def seed(reset=False):
    print("Seeding database...")
    if reset:
        reset_tables()

    categories = {}
    for c in CATEGORIES:
        obj, _ = Category.objects.update_or_create(
            slug=c['slug'],
            defaults={'name': c['name'], 'display_order': c['display_order']},
        )
        categories[c['slug']] = obj
    print(f"Categories ready: {len(categories)}")

    for item in MENU_ITEMS:
        data = dict(item)
        name = data.pop('name')
        data['category'] = categories[data['category']]
        data['price'] = Decimal(data['price'])
        data['is_available'] = True
        MenuItem.objects.update_or_create(name=name, defaults=data)
    print(f"Menu items ready: {len(MENU_ITEMS)}")

    for g in GALLERY:
        data = dict(g)
        title = data.pop('title')
        GalleryImage.objects.update_or_create(title=title, defaults=data)
    print(f"Gallery images ready: {len(GALLERY)}")

    for c in CHEFS:
        data = dict(c)
        name = data.pop('name')
        Chef.objects.update_or_create(name=name, defaults=data)
    print(f"Chefs ready: {len(CHEFS)}")

    print("Database successfully seeded!")


def main():
    parser = argparse.ArgumentParser(description="Seed the AURA database.")
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Delete existing menu, gallery and chef data before seeding (needed once to remove the old demo dishes).',
    )
    args = parser.parse_args()
    seed(reset=args.reset)


if __name__ == '__main__':
    main()
