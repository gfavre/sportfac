import unicodedata

from profiles.models import FamilyUser
from registrations.models import Child


def clean_name(name):
    name = name.strip()
    return unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode("utf-8")


for f in FamilyUser.objects.all():
    if f.children.count() <= 1:
        continue

    to_conserve = []
    to_conserve_names = []
    for child in f.children.all():
        if child.registrations.exists():
            to_conserve.append(child.pk)
            to_conserve_names.append(clean_name(child.get_full_name()))

    if f.children.count() != len(to_conserve):
        print(f.children_names)
    names = []
    for child in f.children.exclude(pk__in=to_conserve):
        name = clean_name(child.get_full_name())
        if name in to_conserve_names:
            child.delete()
        if name in names:
            child.delete()
        names.append(name)


children = {}
for child in Child.objects.all():
    name = child.full_name
    if name not in children:
        children[name] = [child]
    else:
        children[name].append(child)


duplicates = {k: v for k, v in children.items() if len(v) > 1}
count = 0
for children_list in duplicates.values():
    for child in children_list:
        if not child.registrations.exists():
            child.delete()
            count += 1
            print(f"Deleted {child.full_name} ({child.pk})")

print(f"Deleted {count} children")
# Deleted 172 children


for children in duplicates.values():
    for c in children:
        print(
            "\t".join(
                (
                    c.full_name,
                    c.family.full_name if c.family else "",
                    ", ".join([str(reg) for reg in c.registrations.all()]),
                )
            )
        )
