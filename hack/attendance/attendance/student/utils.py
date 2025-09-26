"""
Database utility functions for handling SQLite lock issues
"""
import time
import functools
from django.db import connection, transaction
from django.core.exceptions import OperationalError


def retry_on_lock(max_retries=3, delay=1):
    """
    Decorator to retry database operations when SQLite is locked
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except OperationalError as e:
                    if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                        print(f"Database locked on attempt {attempt + 1}, retrying in {delay} second(s)...")
                        time.sleep(delay)
                        continue
                    else:
                        raise e
                except Exception as e:
                    raise e
            return None
        return wrapper
    return decorator


def close_db_connections():
    """
    Explicitly close all database connections
    """
    connection.close()


def optimize_sqlite_connection():
    """
    Apply SQLite optimizations for better concurrency
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA busy_timeout=30000;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA cache_size=10000;")
            cursor.execute("PRAGMA temp_store=MEMORY;")
    except Exception as e:
        print(f"Error optimizing SQLite connection: {e}")


@retry_on_lock(max_retries=3, delay=1)
def safe_save(model_instance):
    """
    Safely save a model instance with retry logic
    """
    return model_instance.save()


@retry_on_lock(max_retries=3, delay=1)
def safe_create(model_class, **kwargs):
    """
    Safely create a model instance with retry logic
    """
    return model_class.objects.create(**kwargs)


@retry_on_lock(max_retries=3, delay=1)
def safe_get_or_create(model_class, defaults=None, **kwargs):
    """
    Safely get or create a model instance with retry logic
    """
    return model_class.objects.get_or_create(defaults=defaults, **kwargs)
