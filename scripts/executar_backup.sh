#!/usr/bin/env bash
# ==============================================================================
# Script de Automação de Backup para Servidores Linux (Cron Job)
# Exemplo cron: 0 2 * * * /caminho/projeto/scripts/executar_backup.sh >> /var/log/backup_impressao.log 2>&1
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT" || exit 1

PYTHON_EXE="$PROJECT_ROOT/venv/bin/python"

if [ ! -f "$PYTHON_EXE" ]; then
    PYTHON_EXE="python3"
fi

echo "=========================================="
echo "Iniciando Rotina de Backup: $(date)"
echo "Projeto: $PROJECT_ROOT"
echo "=========================================="

$PYTHON_EXE manage.py backup_sistema --keep 7
