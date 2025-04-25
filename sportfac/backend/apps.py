from django.apps import AppConfig


class BackendConfig(AppConfig):
    name = "backend"  # Update if your app name is different

    def ready(self):
        import backend.signals  # noqa: F401; This ensures signals are registered on startup
