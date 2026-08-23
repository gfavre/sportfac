"""Find children with the same normalized first+last name, across every tenant
(school-year period), oldest first. Read-only - lists candidates, deletes nothing
(unlike clean_children.py). For each duplicate group, flags whether the children
also share a birth date and/or a parent home address, as a signal to help tell a
real duplicate from a same-name coincidence. Output is Markdown, meant to be
pasted straight into a doc/ticket.

Paste into `python manage.py shell`.
"""
import unicodedata
from collections import defaultdict

from django_tenants.utils import tenant_context

from backend.models import YearTenant
from registrations.models import Child


def normalize(text):
    text = (text or "").strip().lower()
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("utf-8")


def md_cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ") if value else ""


for tenant in YearTenant.objects.filter(status=YearTenant.STATUS.ready):
    with tenant_context(tenant):
        groups = defaultdict(list)
        for child in Child.objects.select_related("family").all():
            key = (normalize(child.first_name), normalize(child.last_name))
            groups[key].append(child)

        duplicates = {k: v for k, v in groups.items() if len(v) > 1}
        if not duplicates:
            continue

        print(f"## {tenant} ({tenant.schema_name}) - {len(duplicates)} groupe(s) en double\n")

        for (first, last), children in sorted(duplicates.items()):
            birth_dates = {c.birth_date for c in children}
            addresses = {
                (normalize(c.family.address), c.family.zipcode, normalize(c.family.city)) for c in children if c.family
            }
            signals = []
            if len(birth_dates) == 1:
                signals.append("même date de naissance")
            if len(addresses) == 1:
                signals.append("même domicile parent")
            signal_text = " + ".join(signals) if signals else "AUCUN signal commun - à vérifier à la main"

            print(f"### {first} {last} ({len(children)}) - {signal_text}\n")
            print("| ID enfant | Naissance | Inscriptions | Parent | Email | Téléphone |")
            print("|---|---|---|---|---|---|")
            for c in children:
                if c.family:
                    parent = c.family.full_name
                    email = c.family.email
                    phone = c.family.private_phone2 or c.family.private_phone or c.family.private_phone3 or ""
                else:
                    parent, email, phone = "(pas de famille)", "", ""
                has_regs = "oui" if c.registrations.exists() else "non"
                row = (c.pk, c.birth_date, has_regs, parent, email, phone)
                print("| " + " | ".join(md_cell(v) for v in row) + " |")
            print()
