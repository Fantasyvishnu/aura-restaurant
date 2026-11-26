"""Generate colourful placeholder images (pure Python, no downloads needed).

Run this once so the website shows something for every dish, gallery photo and
chef. Then replace them with real photos from the Django admin.
Existing files are never overwritten unless you pass --force.

Usage:
    python create_media_assets.py
    python create_media_assets.py --force
"""
import argparse
import os
import struct
import zlib


def create_png(width, height, r1, g1, b1, r2, g2, b2):
    """Generate a smooth diagonal-gradient PNG with a darker border."""
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)

    header = b'\x89PNG\r\n\x1a\n'
    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
    raw_data = bytearray()

    for y in range(height):
        raw_data.append(0)  # filter type: none
        factor_y = y / float(height - 1)
        for x in range(width):
            factor_x = x / float(width - 1)
            f = (factor_y + factor_x) / 2.0
            r = int(r1 * (1 - f) + r2 * f)
            g = int(g1 * (1 - f) + g2 * f)
            b = int(b1 * (1 - f) + b2 * f)
            if x < 4 or x > width - 5 or y < 4 or y > height - 5:
                r, g, b = int(r * 0.7), int(g * 0.7), int(b * 0.7)
            raw_data.extend([min(255, max(0, r)), min(255, max(0, g)), min(255, max(0, b))])

    idat = chunk(b'IDAT', zlib.compress(bytes(raw_data), level=6))
    return header + ihdr + idat + chunk(b'IEND', b'')


# (file name, start RGB, end RGB). File names must match seed_database.py.
FOODS = [
    ('kuzhi_paniyaram.png', (230, 180, 70), (140, 90, 30)),
    ('madurai_chicken_65.png', (200, 50, 30), (100, 20, 15)),
    ('chettinad_pepper_chicken.png', (150, 70, 30), (50, 25, 15)),
    ('mutton_chukka.png', (140, 60, 40), (60, 25, 20)),
    ('meen_kuzhambu.png', (210, 110, 40), (110, 45, 20)),
    ('banana_leaf_meal.png', (70, 150, 70), (25, 80, 40)),
    ('dindigul_biryani.png', (225, 170, 60), (130, 80, 25)),
    ('kasi_halwa.png', (240, 200, 90), (170, 110, 30)),
    ('paal_payasam.png', (245, 225, 170), (190, 150, 90)),
    ('jigarthanda.png', (190, 110, 90), (100, 50, 45)),
    ('filter_coffee.png', (120, 75, 40), (45, 25, 15)),
]

GALLERY = [
    ('palace_dining_hall.png', (200, 140, 50), (70, 35, 20)),
    ('banana_leaf_feast.png', (80, 160, 80), (25, 85, 45)),
    ('filter_coffee_sweets.png', (150, 95, 50), (55, 30, 20)),
    ('courtyard.png', (60, 140, 110), (25, 70, 55)),
    ('thanjavur_sweets.png', (235, 190, 80), (140, 90, 30)),
    ('royal_suite.png', (150, 50, 90), (60, 20, 45)),
]

CHEFS = [
    ('annamalai_chettiar.png', (170, 110, 60), (60, 40, 30)),
    ('meenakshi_raghavan.png', (190, 80, 110), (80, 35, 60)),
    ('karthikeyan_pillai.png', (60, 130, 140), (25, 60, 75)),
]

STATIC = [
    ('hero_dish.png', 600, 600, (226, 54, 44), (245, 184, 36)),
    ('placeholder_dish.png', 400, 300, (60, 40, 35), (25, 15, 12)),
]


def write_png(path, data, force):
    if os.path.exists(path) and not force:
        print(f"Skipped (exists): {os.path.basename(path)}")
        return
    with open(path, 'wb') as f:
        f.write(data)
    print(f"Generated: {os.path.basename(path)}")


def main():
    parser = argparse.ArgumentParser(description="Generate placeholder images.")
    parser.add_argument('--force', action='store_true', help='Overwrite existing files.')
    force = parser.parse_args().force

    base = os.path.dirname(os.path.abspath(__file__))

    groups = [
        (os.path.join(base, 'media', 'food'), FOODS, 600, 450),
        (os.path.join(base, 'media', 'gallery'), GALLERY, 700, 500),
        (os.path.join(base, 'media', 'chefs'), CHEFS, 500, 600),
    ]
    for folder, items, w, h in groups:
        os.makedirs(folder, exist_ok=True)
        for fname, c1, c2 in items:
            write_png(os.path.join(folder, fname), create_png(w, h, *c1, *c2), force)

    static_dir = os.path.join(base, 'static', 'images')
    os.makedirs(static_dir, exist_ok=True)
    for fname, w, h, c1, c2 in STATIC:
        write_png(os.path.join(static_dir, fname), create_png(w, h, *c1, *c2), force)

    print("Done. Replace these placeholders with real photos from the Django admin.")


if __name__ == '__main__':
    main()
