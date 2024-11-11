from django.apps import AppConfig
from django.core.management import call_command
from django.db import connections
from django.db.utils import OperationalError


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self):
        # Import the signals module
        import accounts.signals

        # Try to run migrations after the server starts
        try:
            # Check if the database is ready
            connection = connections["default"]
            connection.cursor()

            # Run migrations after server startup
            call_command("migrate")
        except OperationalError:
            # Handle the case where the database is not ready yet
            print("Database is not ready, retrying migration later.")
