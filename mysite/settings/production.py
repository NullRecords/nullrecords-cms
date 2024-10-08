from .base import *
import os
from os.path import join, normpath

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'null-cms',
        'PASSWORD': os.environ.get("PASSWORD"),
        'USER': 'cms_user',
        'HOST': 'db-mysql-nyc3-97229-do-user-2508039-0.b.db.ondigitalocean.com',
        'PORT': '25060',
    }
}

DEBUG = True

ALLOWED_HOSTS = ['nullrecords-cms-6xw4e.ondigitalocean.app', 'nullrecords.com', '127.0.0.1', '[::1]','www.nullrecords.com']

CORS_ORIGIN_ALLOW_ALL = True

try:
    from .local import *
except ImportError:
    pass
