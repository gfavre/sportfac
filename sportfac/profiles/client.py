from django.db import transaction
from django.utils.dateparse import parse_datetime
from simple_sso.sso_client.client import Client

from profiles.models import FamilyUser


class KepchupClient(Client):
    def build_user(self, user_data):
        parsed = {k: (parse_datetime(v) if k in ("modified", "created") else v) for k, v in user_data.items()}

        try:
            user = FamilyUser.objects.get(id=parsed["id"])
        except FamilyUser.DoesNotExist:
            # The UUID is unknown locally (e.g. new period): try by email before creating,
            # otherwise super().save() would raise IntegrityError and poison the transaction.
            user = FamilyUser.objects.filter(email=parsed.get("email")).first()
            if user is None:
                user = FamilyUser(**parsed)
                user.save()
                return user

        for key, value in parsed.items():
            setattr(user, key, value)
        with transaction.atomic():
            user.save()
        return user
