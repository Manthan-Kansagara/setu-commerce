"""Trusted local CLI for changing an existing Setu user's role."""

import argparse

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.user import User


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manage a Setu user's role (trusted local operator only)."
    )
    parser.add_argument("email", help="Email address of the existing user")
    parser.add_argument(
        "role",
        choices=["customer", "seller", "admin"],
        help="Role to assign",
    )
    parser.add_argument(
        "--confirm-admin",
        action="store_true",
        help="Required confirmation when assigning the admin role",
    )
    args = parser.parse_args()

    if args.role == "admin" and not args.confirm_admin:
        parser.error(
            "Assigning the admin role requires --confirm-admin. "
            "Only run this command as a trusted operator."
        )
    if args.role != "admin" and args.confirm_admin:
        parser.error("--confirm-admin can only be used when assigning the admin role.")

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == args.email))
        if user is None:
            parser.error(f"No user found with email: {args.email}")

        user.role = args.role
        db.commit()
        print(f"Updated {user.email} to role '{user.role}'.")


if __name__ == "__main__":
    main()
