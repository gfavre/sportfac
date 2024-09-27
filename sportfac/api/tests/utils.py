from profiles.tests.factories import DEFAULT_PASS


class UserMixin:
    def login(self, user):
        self.tenant_client.login(username=user.email, password=DEFAULT_PASS)
