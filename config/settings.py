"""
Django settings for config project.

Configurado com suporte para desenvolvimento local (SQLite)
e produção na Vercel com PostgreSQL no Neon.
"""

import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

# Carrega variáveis de ambiente de arquivo .env caso exista
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Chave secreta com valor padrão seguro para simplificar deploy
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-j5+r!5xk)tuwtf5wcb#kcu+=-g(%qy)&e@%i59*fmtl9twka-&'
)

# Debug: desativa automaticamente na Vercel (quando VERCEL=1), mantendo True apenas local
DEBUG = not bool(os.environ.get('VERCEL'))

# Hosts permitidos: aceita domínios da Vercel e localhost por padrão
ALLOWED_HOSTS = ['*', '.vercel.app', 'localhost', '127.0.0.1']

# CSRF Trusted Origins para domínios na Vercel
CSRF_TRUSTED_ORIGINS = [
    'https://*.vercel.app',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]


# Definição das Aplicações
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Servir arquivos estáticos na Vercel
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
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.app'


# ==============================================================================
# BANCO DE DADOS: PostgreSQL (Neon) / SQLite (Fallback Local)
# ==============================================================================
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # Conexão com PostgreSQL no Neon via dj-database-url (usa driver psycopg)
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=True,
        )
    }
else:
    # Desenvolvimento local padrão: SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Validação de Senhas
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internacionalização
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True


# ==============================================================================
# ARQUIVOS ESTÁTICOS E MÍDIA
# ==============================================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'core' / 'static',
]

# Compressão e cache de estáticos via WhiteNoise
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Diretório de uploads e mídias
MEDIA_URL = '/media/'
# Em ambientes serverless (Vercel), grava no diretório temporário /tmp/media se não houver bucket configurado
if os.environ.get('VERCEL'):
    MEDIA_ROOT = Path('/tmp/media')
else:
    MEDIA_ROOT = BASE_DIR / 'media'


# ==============================================================================
# CONFIGURAÇÕES DE USUÁRIO E AUTENTICAÇÃO
# ==============================================================================
AUTH_USER_MODEL = 'core.Usuario'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'solicitante_home'
LOGOUT_REDIRECT_URL = 'login'


# Configuração de E-mail
MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.console.EmailBackend',
    },
}
