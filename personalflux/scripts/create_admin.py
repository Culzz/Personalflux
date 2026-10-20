"""Create an administrator (or promote an existing account). Run from the backend folder:

    python ..\\scripts\\create_admin.py --email you@example.com

The password is typed hidden and is never stored, only its Argon2id hash. Set
PF_ADMIN_PASSWORD to supply it without a prompt, for a script or a CI step.
"""
import argparse
import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402

ROLES = ("admin", "analyst", "ml_engineer")


def read_password() -> str:
    """The new password, from the environment or typed twice without echo."""
    supplied = os.environ.get("PF_ADMIN_PASSWORD")
    if supplied is not None:
        return supplied
    password = getpass.getpass("Password (min 10 characters): ")
    if password != getpass.getpass("Repeat password: "):
        sys.exit("Passwords did not match.")
    return password


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or promote an account.")
    parser.add_argument("--email", help="account email; prompts when omitted")
    parser.add_argument("--role", choices=ROLES, help="defaults to admin")
    args = parser.parse_args()

    email = (args.email or input("Email: ")).strip().lower()
    if args.role:
        role = args.role
    elif args.email:
        # Non-interactive run: take the default the prompt would have offered.
        role = "admin"
    else:
        role = input(f"Role {ROLES} [admin]: ").strip() or "admin"

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            password = read_password()
            if len(password) < 10:
                sys.exit("Password must be at least 10 characters.")
            user = User(email=email, password_hash=hash_password(password), role=role)
            db.add(user)
            print(f"Created {role}: {email}")
        else:
            user.role = role
            print(f"Updated existing account {email} to role {role}")
        db.commit()


if __name__ == "__main__":
    main()
