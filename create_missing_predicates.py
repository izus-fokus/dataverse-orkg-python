"""
Create missing predicates in the ORKG SANDBOX, mirroring their Production definitions.

Missing predicates (from Production):
  P186069  author
  P186072  datePublished
  P186076  keywords
  P186079  dateCreated
  P186081  identifier

Usage:
  mail=<email> pw=<password> python create_missing_predicates.py
"""

import os
import sys
from orkg import ORKG
from orkg.common import Hosts

PREDICATES = [
    {
        "id": "P186069",
        "label": "author",
        "description": (
            "The author of this content or rating. Please note that author is special "
            "in that HTML 5 provides a special mechanism for indicating authorship via "
            "the rel tag. That is equivalent to this and may be used interchangeably."
        ),
    },
    {
        "id": "P186072",
        "label": "datePublished",
        "description": (
            "Date of first publication or broadcast. For example the date a "
            "CreativeWork was broadcast or a Certification was issued."
        ),
    },
    {
        "id": "P186076",
        "label": "keywords",
        "description": (
            "Keywords or tags used to describe some item. Multiple textual entries "
            "in a keywords list are typically delimited by commas, or by repeating "
            "the property."
        ),
    },
    {
        "id": "P186079",
        "label": "dateCreated",
        "description": (
            "The date on which the CreativeWork was created or the item was added "
            "to a DataFeed."
        ),
    },
    {
        "id": "P186081",
        "label": "identifier",
        "description": (
            "The identifier property represents any kind of identifier for any kind "
            "of Thing, such as ISBNs, GTIN codes, UUIDs etc. Schema.org provides "
            "dedicated properties for representing many of these, either as textual "
            "strings or as URL (URI) links. See background notes for more details."
        ),
    },
]


def main() -> None:
    email = os.environ.get("mail")
    password = os.environ.get("pw")

    if not email or not password:
        print("Error: set environment variables 'mail' and 'pw'.", file=sys.stderr)
        sys.exit(1)

    orkg = ORKG(host=Hosts.SANDBOX, creds=(email, password))

    if not orkg.ping():
        print("Warning: SANDBOX did not respond to ping.", file=sys.stderr)

    if not orkg.session:
        print("Error: authentication failed — write operations require credentials.", file=sys.stderr)
        sys.exit(1)

    print(f"Authenticated as: {email}\n")

    for pred in PREDICATES:
        pid = pred["id"]
        label = pred["label"]

        existing = orkg.predicates.by_id(pid)
        if existing.succeeded:
            print(f"[SKIP]   {pid}  '{label}'  — already exists in SANDBOX")
            continue

        resp = orkg.predicates.add(id=pid, label=label)
        if resp.succeeded:
            created_id = resp.content.get("id", pid)
            print(f"[CREATE] {created_id}  '{label}'  — created successfully")
        else:
            print(
                f"[ERROR]  {pid}  '{label}'  — failed: {resp.content}",
                file=sys.stderr,
            )


if __name__ == "__main__":
    main()
