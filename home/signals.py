from django.db import connection
from django.db.backends.signals import connection_created
from django.dispatch import receiver

@receiver(connection_created)
def enable_foreign_keys(sender, **kwargs):
    if sender.vendor == 'sqlite':
        cursor = connection.cursor()
        cursor.execute('PRAGMA foreign_keys = ON;')
