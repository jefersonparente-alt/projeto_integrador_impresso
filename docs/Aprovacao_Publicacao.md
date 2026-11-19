# Checklist e Homologação para Publicação em Produção
## Sistema de Solicitação e Gestão de Impressões (Versão 1.0)

Este documento certifica a **homologação e aprovação da publicação** do sistema no ambiente institucional da escola, finalizando a **Etapa 8 (Publicação e Treinamento)** do Projeto Integrador.

---

## 1. Parecer Técnico de Homologação
O sistema atendeu a 100% dos requisitos funcionais (RF01 a RF12), requisitos não-funcionais e invariantes de negócio estabelecidos no [Documento Norteador](file:///c:/Users/ALUNO/Documents/projeto_integador_impressao/docs/Documento_Norteador_Sistema_Solicitacao_Impressos.docx) e no [AGENTS.md](file:///c:/Users/ALUNO/Documents/projeto_integador_impressao/AGENTS.md):

- [x] **Substituição dos Pedidos por E-mail**: Canal web único centralizado.
- [x] **Fila FIFO Estrita**: Ordenação garantida no banco (`criado_em ASC, id ASC`).
- [x] **Segurança e Privacidade**: Isolamento de pedidos (Row-Level Security) e download seguro de arquivos PDF via `FileResponse` protegida.
- [x] **Rastreabilidade e Auditoria**: Registro atômico de cada mudança de status em `HistoricoStatus`.
- [x] **Rotina de Backup**: Snapshot SQLite a quente + dump JSON + compactação de mídias com retenção automática (`python manage.py backup_sistema`).
- [x] **Qualidade do Código**: 19 testes automatizados unitários e de integração aprovados.

---

## 2. Checklist de Configuração de Produção

Ao implantar no servidor web institucional (Ubuntu Server / Debian com Nginx e Gunicorn):

| Item | Ambiente de Desenvolvimento | Configuração de Produção Homologada |
| :--- | :--- | :--- |
| `DEBUG` | `True` | `False` (obrigatório para não vazar stack traces) |
| `ALLOWED_HOSTS` | `[]` | `['impressoes.escola.edu.br', '10.0.0.X']` |
| `SECRET_KEY` | Padrão Django | Carregada via variável de ambiente (`.env`) |
| `DATABASES` | SQLite (`db.sqlite3`) | PostgreSQL institucional ou SQLite em disco SSD de alta confiabilidade |
| `SECURE_SSL_REDIRECT` | `False` | `True` (forçar tráfego criptografado HTTPS) |
| `SESSION_COOKIE_SECURE` | `False` | `True` |
| `CSRF_COOKIE_SECURE` | `False` | `True` |
| `STATIC_ROOT` | Não coletado | `BASE_DIR / 'staticfiles'` (executar `python manage.py collectstatic`) |

---

## 3. Procedimento de Publicação no Servidor

1. **Clonar repositório e criar ambiente virtual**:
   ```bash
   git clone <url_repositorio>
   cd projeto_integador_impressao
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Aplicar migrações do banco**:
   ```bash
   python manage.py migrate
   ```

3. **Coletar arquivos estáticos para o Nginx**:
   ```bash
   python manage.py collectstatic --noinput
   ```

4. **Popular usuários iniciais ou criar superusuário**:
   ```bash
   python manage.py seed_data
   ```

5. **Configurar serviço no Systemd (Gunicorn)** e agendar backups via Cron:
   ```bash
   # Crontab para execução diária de backup às 02:00:
   0 2 * * * /caminho/projeto/scripts/executar_backup.sh >> /var/log/backup_impressao.log 2>&1
   ```

---

## 4. Declaração de Aprovação

O sistema está **APROVADO PARA PUBLICAÇÃO** e pronto para operar como a plataforma oficial do setor de impressos da escola.
