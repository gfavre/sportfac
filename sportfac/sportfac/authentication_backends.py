from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from .database_router import LOCAL_DB
from .database_router import MASTER_DB


UserModel = get_user_model()


def _get_user_by_email(manager, email):
    """Exact match first, falling back to case-insensitive.

    Mirrors FamilyManager.get_by_natural_key - this backend bypasses that manager method
    with its own direct .get() against each DB alias, so it needs the same handling
    independently: pre-existing case-variant duplicate accounts (confirmed to exist here -
    two active accounts for the same person, differing only by email case) make a bare
    __iexact lookup crash with MultipleObjectsReturned instead of denying the login
    cleanly. Trying the exact case first also keeps today's behavior for those accounts
    (whichever casing was typed still resolves the same row it always did); __iexact is
    only a fallback for accounts that aren't ambiguous.
    """
    try:
        return manager.get(email=email)
    except UserModel.DoesNotExist:
        pass
    try:
        return manager.get(email__iexact=email)
    except UserModel.MultipleObjectsReturned:
        raise UserModel.DoesNotExist(f"Ambiguous email match for {email!r}")


class MasterUserBackend(ModelBackend):
    # noinspection PyProtectedMember
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if username is None or password is None:
            return None
        try:
            master_user = _get_user_by_email(UserModel._default_manager.using(MASTER_DB), username)
        except UserModel.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user (#20760).
            UserModel().set_password(password)
            return None
        try:
            local_user = _get_user_by_email(UserModel._default_manager.using(LOCAL_DB), username)
            # is_admin/is_active/is_manager are the one exception to "master wins": gate
            # authentication on *this tenant's* own values, not master's - e.g. someone
            # suspended in one tenant must stay suspended there even if active in another
            # sharing the same master DB. Every other field (address, phone...) is meant to
            # propagate from master - that's the point of sharing one identity across tenants.
            master_user.is_admin = local_user.is_admin
            master_user.is_active = local_user.is_active
            master_user.is_manager = local_user.is_manager
        except UserModel.DoesNotExist:
            master_user.is_manager = False
            master_user.is_admin = False
        local_user = master_user.save(using=LOCAL_DB)
        if master_user.check_password(password) and self.user_can_authenticate(master_user):
            return local_user
        return None
