from django.db import migrations
from django.db.models import Count
from django.db.models.functions import Lower


def lowercase_emails(apps, schema_editor):
    """Lowercase every FamilyUser.email, now that FamilyUser.save() does the same for
    every future write - existing rows saved before that fix can still carry mixed-case
    local parts (BaseUserManager.normalize_email only ever lowercased the domain), which
    silently broke login for anyone typing their email back in a different case than it
    happened to be stored in.

    A pair of accounts differing only by case is left untouched: merging or picking a
    winner is a product decision this migration can't make safely, so those are skipped
    and printed for manual follow-up instead.
    """
    FamilyUser = apps.get_model("profiles", "FamilyUser")
    colliding_emails = set(
        # order_by(): FamilyUser.Meta.ordering ("last_name", "first_name") would otherwise
        # leak into GROUP BY here (a well-known Django gotcha), splitting a genuine email
        # collision into separate groups - and hiding it - whenever the two accounts don't
        # share the exact same name.
        FamilyUser.objects.order_by()
        .annotate(lower_email=Lower("email"))
        .values("lower_email")
        .annotate(count=Count("id"))
        .filter(count__gt=1)
        .values_list("lower_email", flat=True)
    )
    for user in FamilyUser.objects.all():
        lowered = user.email.strip().lower()
        if lowered == user.email:
            continue
        if lowered in colliding_emails:
            print(f"Skipping {user.email!r} (pk={user.pk}): collides with another account once lowercased")
            continue
        user.email = lowered
        user.save(update_fields=["email"])


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0025_add_phone_public"),
    ]

    operations = [
        migrations.RunPython(lowercase_emails, migrations.RunPython.noop),
    ]
