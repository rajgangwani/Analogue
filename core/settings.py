# core/settings.py
import os
from pathlib import Path
import dj_database_url

# ---------------- BASE DIR ----------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------- SECURITY ----------------
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-later")
DEBUG = os.environ.get("DEBUG", "True") == "True"
ALLOWED_HOSTS = ["analogue-2874.onrender.com", "localhost", "127.0.0.1"]

# ---------------- APPLICATIONS ----------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cloudinary',
    'cloudinary_storage',
    'portal',  # your custom app
]

# ---------------- MIDDLEWARE ----------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # ✅ Required for serving static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ---------------- URLS & WSGI ----------------
ROOT_URLCONF = 'core.urls'
WSGI_APPLICATION = 'core.wsgi.application'

# ---------------- TEMPLATES ----------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # global templates
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ---------------- DATABASE ----------------
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}", conn_max_age=600
    )
}

# ---------------- AUTH PASSWORD ----------------
AUTH_PASSWORD_VALIDATORS = []

# ---------------- TIMEZONE ----------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# ---------------- STATIC FILES (Render Setup) ----------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']           # local static files
STATIC_ROOT = BASE_DIR / 'staticfiles'             # collectstatic target
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ---------------- MEDIA FILES ----------------
import os

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.getenv('CLOUDINARY_API_KEY'),
    'API_SECRET': os.getenv('CLOUDINARY_API_SECRET'),
}

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ---------------- AUTHENTICATION REDIRECTS ----------------
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'login'

# ---------------- DEFAULT AUTO FIELD ----------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------- WHITENOISE CONFIG ----------------
# Let WhiteNoise handle gzip/brotli compression for static files
WHITENOISE_USE_FINDERS = True