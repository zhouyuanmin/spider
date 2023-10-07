"""
Django settings for spider project.

Generated by 'django-admin startproject' using Django 3.2.15.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

from pathlib import Path
import os
import sys
import datetime

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-7sm@9yxo$na^yh725)!_1u%h**e4gkb8l)g6ty5qvk(eju6v4o"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]

# Application definition

INSTALLED_APPS = [
    "simpleui",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",  # 注册DRF
    "django_filters",  # 过滤器
    "import_export",  # 管理端数据导出服务
    "goods",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "spider.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "spider.wsgi.application"

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    "mysql": {
        "ENGINE": "django.db.backends.mysql",
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),  # 数据库主机
        "PORT": int(os.getenv("DB_PORT", 3306)),  # 数据库端口
        "USER": os.getenv("DB_USER", "root"),  # 数据库用户名
        "PASSWORD": os.getenv("DB_PASSWORD", "root123456"),  # 数据库用户密码
        "NAME": os.getenv("DB_NAME", "spider"),  # 数据库名字
        "OPTIONS": {"charset": "utf8mb4"},
    },
    "sqlite": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    },
}
DATABASES["default"] = DATABASES[os.getenv("DJANGO_DATABASE", "mysql")]

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/
LANGUAGE_CODE = "zh-hans"  # "en-us"

TIME_ZONE = "Asia/Shanghai"  # "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = False  # 仅在国内使用,不启用utc时间

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = "/static/"

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# 日志
LOG_PATH = os.path.join(BASE_DIR, "logs")
if not os.path.exists(LOG_PATH):
    os.mkdir(LOG_PATH)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,  # 是否禁用已经存在的日志器
    "formatters": {  # 日志信息显示的格式
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s %(lineno)d %(message)s"
        },
        "simple": {"format": "%(levelname)s %(module)s %(lineno)d %(message)s"},
    },
    "filters": {  # 对日志进行过滤
        "require_debug_true": {  # django在debug模式下才输出日志
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "handlers": {  # 日志处理方法
        "console": {  # 向终端中输出日志
            "level": "INFO",
            "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file": {  # 向文件中输出日志
            "level": "WARNING",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOG_PATH, "file.log"),  # 日志文件的位置
            "maxBytes": 5 * 1024 * 1024,  # 5M
            "backupCount": 10,
            "formatter": "verbose",
        },
        "celery": {  # celery日志
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOG_PATH, "celery.log"),  # 日志文件的位置
            "maxBytes": 5 * 1024 * 1024,  # 5M
            "backupCount": 10,
            "formatter": "verbose",
        },
    },
    "loggers": {  # 日志器
        "django": {  # 定义了一个名为django的日志器
            "handlers": ["console", "file"],  # 可以同时向终端与文件中输出日志
            "propagate": True,  # 是否继续传递日志信息
            "level": "INFO",  # 日志器接收的最低日志级别
        },
        "celery": {
            "handlers": ["console", "celery"],
            "propagate": True,
            "level": "INFO",
        },
    },
}

REST_FRAMEWORK = {
    # 指定用于支持coreapi的Schema
    "DEFAULT_SCHEMA_CLASS": "rest_framework.schemas.coreapi.AutoSchema",
    # 分页
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 10,
    # 过滤
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
}
