"""
Django settings for aninstance project.
"""
import os

# # # GENERAL
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = 'ewt7vvulgjq=hdn8(s15sqqzu&fa4+igtr57*-1-3#1$!h%tpz'

DOCKERIZED = True  # Note: Remember to change to True for docker deployment!
DEBUG = False  # Note: Remember to change to False for production!
DEMO = True  # Note: authentication to invoicing section NOT REQUIRED when demo is True! Also, disables email.
print('INFO: DEBUG IS SET TO: {}'.format(DEBUG))
print('INFO: DEMO MODE IS SET TO: {}'.format(DEMO))
print('INFO: DOCKERIZED MODE IS SET TO: {}'.format(DOCKERIZED))

# # # LANGUAGE/ TIMEZONE / INTERNATIONALIZATION
LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)
LANGUAGE_CODE = 'en-gb'
TIME_ZONE = 'UTC'
LANGUAGES = (
    ('en', 'English'),
)
USE_I18N = True
USE_L10N = True
USE_TZ = True

# # # NETWORK
SITE_FQDN = 'invoicing.aninstance.com'
ALLOWED_HOSTS = ['invoicing.aninstance.com', 'localhost', '127.0.0.1']
ROOT_URLCONF = 'aninstance.urls'
WSGI_APPLICATION = 'aninstance.wsgi.application'

# Directories
STATICFILES_DIRS = [
    BASE_DIR + '/static/',
]
STATIC_URL = '/static/'
MEDIA_URL = '/media/'
SQLITE_DIR = '/home/docker/docker_persistent_volumes/sqlite' if DOCKERIZED else os.path.join(BASE_DIR)
STATIC_ROOT = '/home/docker/volatile/static/' if DOCKERIZED else os.path.join(BASE_DIR, 'dev_static')
MEDIA_ROOT = '/home/docker/docker_persistent_volumes/media/' if DOCKERIZED else os.path.join(BASE_DIR, 'dev_media')

# Append unique MD5 hash to end of static files, so old versions aren't served from cache when version upgraded
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# # # APPS
INSTALLED_APPS = [
    # django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # haystack
    'haystack',
    # apps
    'invoicing.apps.InvoicingConfig',
    'bootstrap3',
    'anymail',
    'rest_framework',
    'rest_framework.authtoken',
    'django_extensions',
    'django_q',
]

# # # MIDDLEWARE
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'aninstance_framework.middleware.TimezoneMiddleware'
]

# # # TEMPLATES
TEMPLATES = [
    {'BACKEND': 'django.template.backends.django.DjangoTemplates',
     'DIRS': [os.path.join(BASE_DIR, 'templates')],
     'APP_DIRS': True,
     'OPTIONS': {
         'context_processors': [
             'django.template.context_processors.debug',
             'django.template.context_processors.request',
             'django.contrib.auth.context_processors.auth',
             'django.contrib.messages.context_processors.messages',
             'aninstance_framework.custom_context_processors.default_strings',
         ],
     },
     },
]

# # # CACHES
DEFAULT_CACHES_TTL = ((60 * 60) * 60) * 24  # 24 hours
DEFAULT_SEARCH_RESULTS_CACHE_TTL = ((60 * 60) * 5)  # 5 minutes
# if below False, if views haven't overridden this, they won't be cached. This allows per-view caching.
DEFAULT_USE_TEMPLATE_FRAGMENT_CACHING = False

SITE_WIDE_CACHE = False  # django's site-wide caching system. Disabled for more control using view & template caching
if SITE_WIDE_CACHE:
    CACHE_MIDDLEWARE_ALIAS = 'default'
    CACHE_MIDDLEWARE_SECONDS = DEFAULT_CACHES_TTL
    CACHE_MIDDLEWARE_KEY_PREFIX = 'aninstance_production_server'
    MIDDLEWARE.insert(0, 'django.middleware.cache.UpdateCacheMiddleware')  # HAS TO GO FIRST IN MIDDLEWARE LIST
    MIDDLEWARE.append('django.middleware.cache.FetchFromCacheMiddleware')  # HAS TO GO LAST IN MIDDLEWARE LIST

# # # AUTHENTICATION
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
     },
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
     },
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
     },
]

# # # API SERVICES
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAdminUser',),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
    ),
    'PAGE_SIZE': 10
}

# # # HAYSTACK SEARCH
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': os.path.join(os.path.dirname(__file__), 'whoosh_index'),
    },
}

# # # EMAIL SERVICES
ANYMAIL = {
    "POSTMARK_SERVER_TOKEN": '',
    "POSTMARK_API_URL": '',
    "IGNORE_UNSUPPORTED_FEATURES": True,
    "EMAIL_BACKEND": "anymail.backends.postmark.EmailBackend",  # or sendgrid, mailgun, SendGrid, etc - see AnyMail
}

EMAIL_BACKEND = "anymail.backends.postmark.EmailBackend"
DEFAULT_FROM_EMAIL = 'productions@aninstance.com'

# # # DJANGO_Q
Q_CLUSTER = {
    'name': 'aninstance',
    'workers': 2,
    'daemonize_workers': True,
    'recycle': 500,
    'timeout': 60,
    'retry': 60,
    'compress': True,
    'save_limit': 250,
    'guard_cycle': 30,
    'sync': False,  # True forces everything to be run synchronously, even async tasks
    'queue_limit': 4,
    'cpu_affinity': 1,
    'label': 'Django Q',
    'catch_up': True,
    'redis': {
        'host': 'redis',
        'port': 6379,
        'db': 11,
        'password': None,
        'socket_timeout': None,
        'charset': 'utf-8',
        'errors': 'strict',
        'unix_socket_path': None
    }
}

# PRODUCTION MODE (i.e. if DEBUG = False)
if not DEBUG:
    SECURE_SSL_REDIRECT = True  # network & session
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # # # SESSIONS
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'sessions'
    SESSION_SAVE_EVERY_REQUEST = True
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': 'redis://redis:6379/1',
            'TIMEOUT': DEFAULT_CACHES_TTL,  # default TTL for the cache in sects(e.g. 5 mins = 'TIMEOUT': 60 * 5)
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient'
            },
            'KEY_PREFIX': 'aninstance_production_server'
        },
        'pages': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': 'redis://redis:6379/2',
            'TIMEOUT': DEFAULT_CACHES_TTL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient'
            },
            'KEY_PREFIX': 'aninstance_production_server'
        },
        'sessions': {  # used by SESSION_CACHE_ALIAS, below
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': 'redis://redis:6379/3',
            'TIMEOUT': 60 * 60,  # cache session data for an hour
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient'
            },
            'KEY_PREFIX': 'aninstance_production_server'
        },
        'template_fragments': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': 'redis://redis:6379/4',
            'TIMEOUT': DEFAULT_CACHES_TTL,  # cache session data for an hour
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient'
            },
            'KEY_PREFIX': 'aninstance_production_server'
        }
    }

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(SQLITE_DIR, 'aninstance-invoicing_db')
        }
    }

# DEVELOPMENT MODE (i.e. if DEBUG = True)
else:
    SESSION_COOKIE_SECURE = False
    SECURE_SSL_REDIRECT = False
    CACHES = {'default':
                  {'BACKEND': 'django.core.cache.backends.dummy.DummyCache', },
              'template_fragments':
                  {'BACKEND': 'django.core.cache.backends.dummy.DummyCache', }
              }
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(SQLITE_DIR, 'aninstance-invoicing_db')
        }
    }

# # # INVOICING
INVOICING = {'DEFAULT_INVOICE_PREPEND': 'ANI',
             'TAX': {  # tax rates (percent)
                 'STANDARD': 20,
                 'REDUCED': 5,
                 'ZERO': 0,
                 'NONE': 0,
             },
             'CURRENCY': {'ABBR': 'GBP', 'SYMBOL': '£'.encode('utf-8')},
             'LOGO_SIZE': (75, 75),
             'LOGO_MAX_FILESIZE': 1024 * 1024,
             'BUSINESS_NAME_IN_PDF_HEADER': True,
             'PDF_DIR': os.path.relpath(os.path.join('protected', 'pdf')),
             'EMAIL_ACTIVE': True,
             }

# STRIPE (Optional Aninstance Framework app)
STRIPE = {
    'STRIPE_TEST_MODE': True,
    'STRIPE_TEST_API_KEY': '',
    'STRIPE_TEST_PUBLISHABLE_KEY': '',
    'STRIPE_API_KEY': '',
    'STRIPE_PUBLISHABLE_KEY': '',
    'STRIPE_JS_URL': 'https://js.stripe.com/v2/',
}

# # # LOGGING
# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'formatters': {
#         'verbose': {
#             'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
#         },
#         'simple': {
#             'format': '%(asctime)s %(levelname)s %(message)s'
#         }
#     },
#     'handlers': {
#         'console': {
#             'level': 'DEBUG',
#             'class': 'logging.StreamHandler',
#             'formatter': 'simple'
#         },
#         'file': {
#             'level': 'DEBUG',
#             'class': 'logging.FileHandler',
#             'filename': '/var/log/django_main/debug.log',
#             'formatter': 'verbose'
#         },
#     },
#     'loggers': {
#         'main': {
#             'handlers': ['console', 'file'],
#             'level': 'DEBUG',
#             'propagate': True,
#         },
#         'django': {
#             'handlers': ['file'],
#             'level': 'DEBUG',
#             'propagate': True,
#         },
#     },
# }
