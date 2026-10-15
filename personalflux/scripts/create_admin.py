"""Create an administrator (or promote an existing account). Run from the backend folder:

    python ..\\scripts\\create_admin.py

The password is typed hidden and is never stored, only its Argon2id hash.
"""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402

ROLES = ("admin", "analyst", "ml_engineer")

email = input("Email: ").strip().lower()
role = input(f"Role {ROLES} [admin]: ").strip() or "admin"
if role not in ROLES:
    sys.exit(f"Role must be one of {ROLES}")

with SessionLocal() as db:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        password = getpass.getpass("Password (min 10 characters): ")
        if len(password) < 10:
            sys.exit("Password must be at least 10 characters.")
        if password != getpass.getpass("Repeat password: "):
            sys.exit("Passwords did not match.")
        user = User(email=email, password_hash=hash_password(password), role=role)
        db.add(user)
        print(f"Created {role}: {email}")
    else:
        user.role = role
        print(f"Updated existing account {email} to role {role}")
    db.commit()
