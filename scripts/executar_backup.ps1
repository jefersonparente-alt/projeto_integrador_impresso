# ==============================================================================
# Script de Automação de Backup - Sistema de Solicitação de Impressões
# Pode ser agendado no Agendador de Tarefas do Windows (Task Scheduler)
# ==============================================================================

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

$PythonExe = Join-Path $ProjectRoot "venv\Scripts\python.exe"

if (-Not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Iniciando Rotina de Backup do Sistema..." -ForegroundColor Cyan
Write-Host "Diretório do Projeto: $ProjectRoot"
Write-Host "=========================================="

& $PythonExe manage.py backup_sistema --keep 7

if ($LASTEXITCODE -eq 0) {
    Write-Host "Rotina finalizada com sucesso!" -ForegroundColor Green
} else {
    Write-Host "Erro durante a execução do backup." -ForegroundColor Red
}
