# -*- coding: utf-8 -*-
from django.utils.timezone import datetime

from simple_sso.sso_client.client import Client

from profiles.models import FamilyUser


class KepchupClient(Client):
    def build_user(self, user_data):
        try:
            user = FamilyUser.objects.get(id=user_data['id'])
            for key, value in user_data:
                if key in ('modified', 'created'):
                    value = datetime.fromisoformat(value)
                setattr(user, key, value)
        except FamilyUser.DoesNotExist:
            user = FamilyUser(**user_data)

        # user.set_unusable_password()
        user.save()
        return user