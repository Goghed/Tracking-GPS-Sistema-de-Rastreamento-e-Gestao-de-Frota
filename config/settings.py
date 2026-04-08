from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-change-this-in-production-fleetcore-2024'

DEBUG = True

ALLOWED_HOSTS = ['*']

# ── CSRF — necessário para funcionar no PythonAnywhere (HTTPS via proxy) ──────
CSRF_TRUSTED_ORIGINS = [
    'https://*.pythonanywhere.com',
    'http://localhost',
    'http://127.0.0.1',
]
# Garante que o cookie CSRF seja acessível pelo JavaScript (document.cookie)
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'django_apscheduler',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.nao_lidos',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            # Espera até 20 segundos antes de lançar "database is locked"
            'timeout': 20,
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

# ── Fulltrack API ──────────────────────────────────────────────
FULLTRACK_API_URL  = 'https://ws.fulltrack2.com'
FULLTRACK_API_KEY    = '5e32542e1b9fbfeaab2393a1d2909568eff3f1f7'
FULLTRACK_SECRET_KEY = 'ff7c818ae5ea8a89a8bbcde66adfc074ab925202'

# ── RabbitMQ (Guarnieri / Itu) ────────────────────────────────
RABBITMQ_HOST       = 'guarnieri.rabbitmq.com.br'
RABBITMQ_PORT       = 5672
RABBITMQ_VHOST      = '/'
RABBITMQ_USER       = 'guarnieri'
RABBITMQ_PASSWORD   = 'A89852ggVnB!rS58'
RABBITMQ_QUEUE      = 'guarnieri'

# ── APScheduler ───────────────────────────────────────────────
APSCHEDULER_DATETIME_FORMAT = "N j, Y, f:s a"
APSCHEDULER_RUN_NOW_TIMEOUT = 25
# Não usar SCHEDULER_CONFIG — o scheduler usa MemoryJobStore definido em scheduler.py
