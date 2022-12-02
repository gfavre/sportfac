# -*- coding: utf-8 -*-
from __future__ import absolute_import
from django.utils.dateparse import parse_datetime
from simple_sso.sso_client.client import Client

from profiles.models import FamilyUser


class KepchupClient(Client):
    def build_user(self, user_data):
        try:
            user = FamilyUser.objects.get(id=user_data['id'])
            for key, value in user_data.items():
                if key in ('modified', 'created'):
                    value = parse_datetime(value)
                setattr(user, key, value)
        except FamilyUser.DoesNotExist:
            user = FamilyUser(**user_data)

        # user.set_unusable_password()
        user.save()
        return user
