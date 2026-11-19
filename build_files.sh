#!/usr/bin/env bash
# ==============================================================================
# Script de Build para a Vercel
# Instala dependências e coleta arquivos estáticos
# ==============================================================================

echo "--- Iniciando Build na Vercel ---"

# Instala dependências Python
python3 -m pip install -r requirements.txt

# Coleta arquivos estáticos para o diretório staticfiles
python3 manage.py collectstatic --noinput --clear

echo "--- Build Finalizado com Sucesso ---"
