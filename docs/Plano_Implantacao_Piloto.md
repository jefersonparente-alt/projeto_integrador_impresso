# Plano de Implantação Piloto e Homologação
## Sistema de Solicitação e Gestão de Impressões

Este documento organiza as diretrizes operacionais para a execução da **Etapa 7: Implantação Piloto** na instituição escolar, conforme previsto no Documento Norteador e no `README.md`.

---

## 1. Escopo e Público do Piloto
A fase piloto tem como meta validar a substituição do e-mail escolar em um ambiente controlado antes da liberação geral.

- **Grupo Amostral de Solicitantes**:
  - 2 a 3 turmas técnicas (ex: 3º Ano Informática e 3º Ano Administração).
  - Coordenação Pedagógica e Secretaria Escolar.
- **Setor Operacional**:
  - Equipe técnica e estagiários da Gráfica/Setor de Impressos.
- **Período de Execução Sugerido**:
  - Duração de 2 semanas letivas.

---

## 2. Roteiro Passo a Passo de Execução

### Fase 1: Preparação do Ambiente e Contas
1. Executar as migrações mais recentes no banco:
   ```bash
   python manage.py migrate
   ```
2. Garantir as contas padrão iniciais rodando o comando:
   ```bash
   python manage.py seed_data
   ```
3. Configurar a rotina de backup automática diária:
   - Windows: Agendador de Tarefas acionando `scripts/executar_backup.ps1`.
   - Linux: Cron diário chamando `scripts/executar_backup.sh`.

### Fase 2: Treinamento e Instrução dos Usuários
- **Para Solicitantes**:
  - Distribuição do guia rápido: como acessar `/login/`, cadastrar-se em `/cadastro/`, submeter PDFs com especificações e consultar o protocolo em `/consulta/`.
- **Para Colaboradores**:
  - Treinamento no Painel da Fila FIFO (`/setor/`): respeito à ordem de chegada, abertura dos arquivos e regras para marcação de `Aguardando correção` com justificativa obrigatória.

### Fase 3: Operação Assistida e Coleta de Métricas
Durante o piloto, a equipe administrativa acompanha os seguintes indicadores pelo painel em `/gestao/`:
- Volume de solicitações abertas por dia/semana.
- Tempo médio entre o recebimento e o início do atendimento.
- Quantidade de pedidos concluídos, cancelados ou com pendência.
- Eficácia das validações de arquivos PDF.

---

## 3. Matriz de Aceitação e Critérios de Conclusão do Piloto

| Critério de Sucesso | Meta no Piloto | Verificação |
| :--- | :--- | :--- |
| **Aderência à Fila FIFO** | 100% dos pedidos atendidos por ordem cronológica (salvo urgências com justificativa) | Painel `/setor/` e histórico |
| **Integridade dos Anexos** | Zero falhas de integridade ou links corrompidos | Visualizador embutido e download |
| **Isolamento de Dados** | Nenhum vazamento de arquivo entre solicitantes | Testes de segurança / Row-Level |
| **Resolução de Pendências** | Solicitantes conseguem corrigir e reenviar PDFs sem abrir novo pedido | Fluxo `Aguardando correção` |
| **Satisfação dos Usuários** | Redução relatada de mensagens de e-mail perdidas | Feedback qualitativo |

---

## 4. Plano de Transição para Produção (Rollout)
Após o encerramento do piloto e validação dos critérios de sucesso:
1. Apresentação do relatório de volume ao comitê escolar.
2. Liberação do cadastro para todas as turmas e departamentos.
3. Desativação oficial do e-mail escolar como canal de recebimento de arquivos para impressão.
