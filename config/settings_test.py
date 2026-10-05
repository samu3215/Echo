from .settings import *

SECRET_KEY = os.getenv('SECRET_KEY', 'test-secret-key')
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'test_db.sqlite3',
    }
}
