
import argparse

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.user import User


def main():
    parser = argparse.ArgumentParser(
        description="Manage a Setu user's role."
    )
    parser.add_argument("email", help="Email of the existing user")
    parser.add_argument(
        "role",
        choices=["customer", "seller", "admin"],
        help="Role to assign",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        user = db.scalar(
            select(User).where(User.email == args.email)
        )

        if user is None:
            parser.error(f"No user found with email: {args.email}")

        user.role = args.role
        db.commit()

        print(f"Updated {user.email} to role '{user.role}'.")


if __name__ == "__main__":
    main()
