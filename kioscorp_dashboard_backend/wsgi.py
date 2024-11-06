"""
WSGI config for kioscorp_dashboard_backend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os
import threading

from django.core.wsgi import get_wsgi_application

# Import the backup function
from .backup_db import (
    start_backup_loop,
)  # Ensure backup_db.py is in the same directory as settings.py

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kioscorp_dashboard_backend.settings")

# Start the backup loop in a background thread
backup_thread = threading.Thread(target=start_backup_loop, daemon=True)
backup_thread.start()

application = get_wsgi_application()
