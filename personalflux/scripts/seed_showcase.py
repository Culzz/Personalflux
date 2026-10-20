"""Seed a small curated showcase catalog and backfill demo prices.

The Retailrocket sample has no titles, prices or photos, so the storefront
leans on a curated set of fully-described products (source "showcase") for
the landing experience. The bulk import keeps its dataset titles.

Bulk rows without a price get a stable demo price derived from their item id,
so every price shown is consistent between runs. Demo prices are not real
retail prices.
"""
import os
import sys
from decimal import Decimal
from pathlib import Path

# Run by path from anywhere: the application package lives under backend/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

# The target database comes from the environment or from the same dotenv files
# the API reads (.env.local at the repository root, then backend/.env). It is not
# defaulted here: a wrong default would quietly seed the local database while a
# hosted one stayed empty.
os.environ.setdefault("JWT_SECRET_KEY", "dev-only-secret-dev-only-secret-0123456789")

from sqlalchemy import delete, func, select, text  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models import Product  # noqa: E402

BASE = 900000

SHOWCASE: list[tuple[str, str, str, str, str]] = [
    # title, category, price, description, image seed
    ("Aria Wireless Headphones", "Audio", "129.99",
     "Over-ear Bluetooth headphones with 40-hour battery and folding design.",
     "aria-headphones"),
    ("Aria Soundbar", "Audio", "199.99",
     "Compact 2.1 soundbar with wireless subwoofer for TV and music.",
     "aria-soundbar"),
    ("Tempo Portable Speaker", "Audio", "59.99",
     "Water-resistant portable speaker with 12-hour playtime.",
     "tempo-speaker"),
    ("Studio Monitor Earbuds", "Audio", "79.99",
     "In-ear monitors with memory-foam tips and detachable cable.",
     "studio-earbuds"),
    ("Haven Ceramic Table Lamp", "Home", "49.99",
     "Hand-glazed ceramic lamp with linen shade and warm LED bulb.",
     "haven-lamp"),
    ("Haven Wool Throw", "Home", "39.99",
     "Woven wool throw, 130 x 180 cm, machine washable.",
     "haven-throw"),
    ("Grove Oak Side Table", "Home", "89.99",
     "Solid oak side table, 45 cm high, oil finish.",
     "grove-table"),
    ("Linen Duvet Set", "Home", "119.99",
     "Stonewashed French linen duvet cover with two pillowcases.",
     "linen-duvet"),
    ("Pulse Fitness Tracker", "Wearables", "99.99",
     "Heart-rate, sleep and step tracking with 7-day battery.",
     "pulse-tracker"),
    ("Meridian Chrono Watch", "Wearables", "249.99",
     "Sapphire glass chronograph with Italian leather strap.",
     "meridian-watch"),
    ("Stride Running Shoes", "Wearables", "139.99",
     "Neutral cushioned road shoes, 260 g in size 42.",
     "stride-shoes"),
    ("Orbit Smart Watch", "Wearables", "199.99",
     "AMOLED display, GPS and contactless payments.",
     "orbit-watch"),
    ("Ember Pour-Over Set", "Kitchen", "69.99",
     "Borosilicate carafe, dripper and walnut collar, 600 ml.",
     "ember-pourover"),
    ("Cast Iron Skillet 26cm", "Kitchen", "54.99",
     "Pre-seasoned cast iron skillet, oven safe to 260C.",
     "skillet-26"),
    ("Chef Knife 20cm", "Kitchen", "89.99",
     "German steel chef knife with pakkawood handle.",
     "chef-knife"),
    ("Insulated Bottle 1L", "Kitchen", "29.99",
     "Double-wall vacuum bottle, keeps drinks hot 12 hours.",
     "bottle-1l"),
    ("Draft Desk Organiser", "Office", "34.99",
     "Felt desk organiser with pen loops and phone dock.",
     "draft-organiser"),
    ("Ergo Laptop Stand", "Office", "45.99",
     "Aluminium laptop stand, six height settings.",
     "ergo-stand"),
    ("Mechanical Keyboard", "Office", "109.99",
     "Hot-swap mechanical keyboard with PBT keycaps.",
     "mech-keyboard"),
    ("Desk Lamp with USB", "Office", "39.99",
     "Dimmable LED desk lamp with USB charging port.",
     "desk-lamp-usb"),
    ("Vector Gaming Mouse", "Gaming", "69.99",
     "26K sensor gaming mouse, 59 g ultralight shell.",
     "vector-mouse"),
    ("Arcade Fight Stick", "Gaming", "149.99",
     "Tournament-grade fight stick with Sanwa parts.",
     "arcade-stick"),
    ("7.1 Headset Stand", "Gaming", "79.99",
     "Surround gaming headset with noise-cancelling mic.",
     "headset-71"),
    ("Pixel Stream Deck", "Gaming", "129.99",
     "15-key stream controller with custom icons.",
     "pixel-deck"),
    ("Trail Daypack 22L", "Outdoors", "74.99",
     "Recycled nylon daypack with ventilated back panel.",
     "trail-daypack"),
    ("Summit Tent 2P", "Outdoors", "229.99",
     "Two-person trekking tent, 2.1 kg packed.",
     "summit-tent"),
    ("Camp Cook Set", "Outdoors", "59.99",
     "Nesting pots and kettle for two, anodised aluminium.",
     "camp-cook"),
    ("Hammock with Straps", "Outdoors", "44.99",
     "Double parachute hammock with tree straps included.",
     "hammock-straps"),
    ("Yoga Mat 6mm", "Fitness", "34.99",
     "Non-slip TPE yoga mat with carry strap.",
     "yoga-mat"),
    ("Adjustable Dumbbell", "Fitness", "119.99",
     "Single adjustable dumbbell, 2.5 to 24 kg.",
     "dumbbell-adj"),
]


def main() -> None:
    db = SessionLocal()
    try:
        db.execute(delete(Product).where(Product.catalog_source == "showcase"))
        for i, (title, category, price, desc, seed) in enumerate(SHOWCASE):
            db.add(Product(
                source_item_id=BASE + i,
                catalog_source="showcase",
                title=title,
                description=desc,
                category=category,
                price=Decimal(price),
                image_url=f"https://picsum.photos/seed/{seed}/600/600",
                is_active=True,
            ))
        db.commit()
        n_show = db.scalar(select(func.count()).select_from(Product)
                           .where(Product.catalog_source == "showcase"))

        # Stable demo prices for bulk rows: $4.99-$499.98 from the item id.
        db.execute(text("""
            UPDATE products
            SET price = 4.99 + ((abs(('x' || substr(md5(source_item_id::text), 1, 15))::bit(60)::bigint) % 49500)::numeric / 100)
            WHERE price IS NULL AND catalog_source = 'retailrocket'
        """))
        db.commit()
        n_priced = db.scalar(select(func.count()).select_from(Product).where(Product.price.is_not(None)))
        print(f"showcase products: {n_show}, priced products: {n_priced}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
