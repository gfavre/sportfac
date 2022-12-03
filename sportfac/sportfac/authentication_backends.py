from __future__ import absolute_import

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from .database_router import LOCAL_DB, MASTER_DB


UserModel = get_user_model()


class MasterUserBackend(ModelBackend):
    # noinspection PyProtectedMember
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if username is None or password is None:
            return
        try:
            master_user = UserModel._default_manager.using(MASTER_DB).get(email=username)
        except UserModel.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user (#20760).
            UserModel().set_password(password)
            return
        try:
            local_user = UserModel._default_manager.using(LOCAL_DB).get(email=username)
            master_user.is_admin = local_user.is_admin
            master_user.is_active = local_user.is_active
            master_user.is_manager = local_user.is_manager
        except UserModel.DoesNotExist:
            master_user.is_manager = False
            master_user.is_admin = False
        local_user = master_user.save(using=LOCAL_DB)
        if master_user.check_password(password) and self.user_can_authenticate(master_user):
            return local_user
