"""
WSGI config for config project.

Expõe a aplicação WSGI para Gunicorn/uWSGI local
e disponibiliza a variável 'app' exigida pela Vercel Serverless Functions.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()

# Alias 'app' para compatibilidade nativa com a Vercel
app = application
