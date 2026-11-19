# Guia de Desenvolvimento e Instruções para Agentes (AGENTS.md)

Este documento estabelece as diretrizes de engenharia, contratos de dados, regras de negócio e boas práticas para **Agentes de Inteligência Artificial** e desenvolvedores que atuam no repositório **Sistema de Solicitação e Gestão de Impressões** (Projeto Integrador - Python/Django).

---

## 1. Missão do Projeto e Escopo

O objetivo do sistema é extinguir o recebimento desorganizado de pedidos de impressão via e-mail escolar, substituindo-o por um portal web unificado, seguro e auditável com fila orientada a **FIFO** (*First In, First Out*).

### Documentos de Referência Base
- Documento Norteador: [Documento_Norteador_Sistema_Solicitacao_Impressos.docx](file:///c:/Users/ALUNO/Documents/projeto_integador_impressao/docs/Documento_Norteador_Sistema_Solicitacao_Impressos.docx)
- Diagrama Entidade-Relacionamento: [diagrama_er_banco.png](file:///c:/Users/ALUNO/Documents/projeto_integador_impressao/docs/diagrama_er_banco.png)

### Restrições do MVP (Primeira Versão)
- **Formatos aceitos**: Estritamente documentos em formato **PDF** (`application/pdf`).
- **Autenticação**: Suporte a login nativo Django, separando os perfis: `solicitante`, `colaborador` e `administrador`.
- **Fila Cronológica**: A ordem padrão no setor é sempre baseada no instante de chegada registrado pelo servidor.
- **Armazenamento Privado**: Nenhum anexo de impressão pode ser acessível publicamente via URL direta de pasta estática/mídia.

---

## 2. Invariantes de Negócio (Regras Inegociáveis)

Todo agente de IA deve respeitar as seguintes regras em qualquer refatoração, implementação de view ou consulta ORM:

1. **Ordenação da Fila do Setor**:
   - A listagem de atendimento do setor **DEVE SEMPRE** ser ordenada por:
     ```python
     Solicitacao.objects.filter(...).order_by('criado_em', 'id')
     ```
   - O campo `prazo_desejado` é meramente informativo/consultivo e **NUNCA** pode interferir na ordenação cronológica automática da fila padrão.
2. **Imutabilidade Temporal**:
   - O campo `criado_em` da solicitação registra o momento exato de recebimento e **JAMAIS** pode ser alterado durante atualizações de status ou correções.
3. **Auditoria de Transições de Status**:
   - Toda alteração de `status_atual` em uma solicitação **DEVE** disparar obrigatoriamente a criação de um registro em `HistoricoStatus`, contendo:
     - `solicitacao`
     - `usuario_responsavel` (o usuário autenticado que efetuou a alteração)
     - `status_anterior`
     - `status_novo`
     - `data_hora` (timestamp atual)
     - `observacao` (justificativa técnica ou orientação de correção)
4. **Isolamento de Dados (Row-Level Security)**:
   - Um usuário com perfil `solicitante` **SÓ PODE** visualizar e acessar suas próprias solicitações (`solicitante=request.user`) e seus respectivos anexos.
   - Colaboradores e Administradores possuem permissão para inspecionar solicitações gerais da fila.
5. **Exceção de Prioridade Controlada**:
   - Se uma solicitação for tratada com urgência fora da ordem FIFO, o sistema exige a criação do registro na entidade `ExcecaoPrioridade`, vinculando o usuário autorizador e uma `justificativa` obrigatória em texto.

---

## 3. Especificação do Modelo de Dados (ORM Django)

A modelagem de dados reflete fielmente o Diagrama Entidade-Relacionamento homologado:

```
[USUARIO] (1) ──── (N) [SOLICITACAO] (1) ──── (N) [ANEXO]
    │                        │
    │ (1)                    │ (1)
    └─── (N) [HISTORICO_STATUS] ┘
    │                        │
    │ (1)                    │ (1)
    └─── (N) [EXCECAO_PRIORIDADE] ┘
```

### 3.1 Definição das Entidades e Campos

#### A. Modelo `Usuario` (Custom User Model ou Perfil Vinculado)
- `nome` (CharField)
- `email` (EmailField, unique=True)
- `perfil` (CharField, choices: `solicitante`, `colaborador`, `administrador`, default: `solicitante`)
- `setor_turma` (CharField, max_length=100)
- `contato` (CharField, max_length=50, e-mail institucional ou telefone)
- `ativo` (BooleanField, default=True)
- `criado_em` (DateTimeField, auto_now_add=True)

#### B. Modelo `Solicitacao`
- `protocolo` (CharField, unique=True, max_length=32, indexado)
- `solicitante` (ForeignKey para `Usuario`, on_delete=models.CASCADE, related_name='solicitacoes')
- `setor_turma` (CharField, max_length=100)
- `contato` (CharField, max_length=50)
- `criado_em` (DateTimeField, auto_now_add=True, db_index=True, editable=False)
- `quantidade_copias` (PositiveIntegerField, default=1)
- `tipo_impressao` (CharField, choices: `pb` [Preto e Branco], `colorida` [Colorida])
- `frente_verso` (BooleanField, default=False)
- `instrucoes` (TextField, blank=True)
- `prazo_desejado` (DateField, null=True, blank=True)
- `status_atual` (CharField, choices:
  - `RECEBIDA`: "Recebida"
  - `EM_ANDAMENTO`: "Em andamento"
  - `AGUARDANDO_CORRECAO`: "Aguardando correção"
  - `CONCLUIDA`: "Concluída"
  - `CANCELADA`: "Cancelada"
  default=`RECEBIDA`, db_index=True)

#### C. Modelo `Anexo`
- `solicitacao` (ForeignKey para `Solicitacao`, on_delete=models.CASCADE, related_name='anexos')
- `nome_original` (CharField, max_length=255)
- `arquivo` (FileField, upload_to com caminho customizado seguro)
- `tipo_arquivo` (CharField, max_length=100, ex: `application/pdf`)
- `tamanho_bytes` (BigIntegerField)
- `enviado_em` (DateTimeField, auto_now_add=True)

#### D. Modelo `HistoricoStatus`
- `solicitacao` (ForeignKey para `Solicitacao`, on_delete=models.CASCADE, related_name='historicos')
- `usuario_responsavel` (ForeignKey para `Usuario`, on_delete=models.SET_NULL, null=True, related_name='historicos_atualizados')
- `status_anterior` (CharField, max_length=30)
- `status_novo` (CharField, max_length=30)
- `data_hora` (DateTimeField, auto_now_add=True)
- `observacao` (TextField, blank=True)

#### E. Modelo `ExcecaoPrioridade`
- `solicitacao` (ForeignKey ou OneToOneField para `Solicitacao`, on_delete=models.CASCADE, related_name='excecoes_prioridade')
- `autorizado_por` (ForeignKey para `Usuario`, on_delete=models.CASCADE, related_name='excecoes_autorizadas')
- `justificativa` (TextField)
- `criada_em` (DateTimeField, auto_now_add=True)

---

## 4. Diretrizes Técnicas de Implementação

### 4.1 Camada de Serviços e Transições de Status
Evite acoplar lógica complexa dentro de views ou templates. Recomenda-se utilizar uma camada de serviço (ex.: `core/services.py`):

```python
# Exemplo de padrão arquitetural recomendado:
@transaction.atomic
def alterar_status_solicitacao(solicitacao, novo_status, usuario_responsavel, observacao=""):
    status_anterior = solicitacao.status_atual
    if status_anterior == novo_status:
        return solicitacao
    
    solicitacao.status_atual = novo_status
    solicitacao.save(update_fields=['status_atual'])
    
    HistoricoStatus.objects.create(
        solicitacao=solicitacao,
        usuario_responsavel=usuario_responsavel,
        status_anterior=status_anterior,
        status_novo=novo_status,
        observacao=observacao
    )
    return solicitacao
```

### 4.2 Geração de Protocolo
- O protocolo deve ser legível, determinístico e não adivinhável em lote.
- Padrão recomendado: `IMP-{ANO}{MES}-{SEQ/RANDOM}` (exemplo: `IMP-202611-0042` ou UUID compacto de 8 caracteres alfanuméricos em caixa alta).
- Deve possuir restrição `unique=True` no banco de dados.

### 4.3 Segurança e Download de Anexos
- **Nunca expor o diretório de uploads em `MEDIA_URL` com navegação pública desprotegida.**
- A visualização ou download de arquivos deve ocorrer por meio de uma view protegida (usando `FileResponse`), com validação rigorosa de autorização:
  ```python
  # O solicitante dono do pedido OU colaboradores/administradores têm permissão
  if request.user != solicitacao.solicitante and request.user.perfil not in ['colaborador', 'administrador']:
      raise PermissionDenied("Acesso não autorizado a este arquivo.")
  ```
- No upload, validar:
  1. Extensão do arquivo (`.pdf`).
  2. Mime type real (`application/pdf`).
  3. Tamanho máximo (ex.: limite padrão de 25MB).

---

## 5. Convenções de Código e Estrutura de Arquivos

- **Linguagem**: Python 3.10+ seguindo rigidamente o **PEP 8**.
- **Docstrings e Tipagem**: Adicione Type Hints nos métodos de serviços e modelos.
- **Nomenclatura**:
  - Modelos e Classes: `PascalCase` (`Solicitacao`, `HistoricoStatus`).
  - Funções, Métodos e Atributos: `snake_case` (`alterar_status`, `quantidade_copias`).
  - Constantes e Choices: `SCREAMING_SNAKE_CASE` (`STATUS_RECEBIDA`, `PERFIL_COLABORADOR`).
- **Templates**: Herança a partir de `core/templates/base.html`, utilizando classes utilitárias do Bootstrap 5 para responsividade e acessibilidade.

---

## 6. Critérios de Aceitação e Testes Obrigatórios

Ao implementar ou alterar qualquer funcionalidade, os seguintes testes unitários e de integração (`core/tests.py`) devem permanecer verdes:

| ID | Cenário de Teste Obrigatório |
| :--- | :--- |
| **TC01** | Usuário autenticado submete formulário com dados válidos e PDF -> gera `Solicitacao`, `Anexo`, protocolo único e status inicial `Recebida`. |
| **TC02** | Submissão com campos obrigatórios ausentes ou arquivo inválido (ex: `.exe`, `.docx` no MVP) é barrada com mensagens de erro claras. |
| **TC03** | Arquivo que excede o tamanho limite configurado é rejeitado na validação do form. |
| **TC04** | A consulta da fila pelo colaborador lista pedidos estritamente por ordem de chegada (`criado_em` ASC). |
| **TC05** | Alteração de status não modifica o valor de `criado_em`. |
| **TC06** | Solicitante A não consegue visualizar detalhes nem baixar anexos da solicitação do Solicitante B. |
| **TC07** | Alteração de status realizada por colaborador gera registro em `HistoricoStatus` com o status anterior, novo e observação. |
| **TC08** | Solicitante consegue consultar o andamento e o histórico de observações de suas solicitações. |
| **TC09** | Concessão de prioridade excepcional fora da ordem FIFO exige justificativa e usuário autorizador. |
| **TC10** | Auto-cadastro de novos solicitantes com validação de e-mail único e hash seguro de senha. |
| **TC11** | Painel executivo e relatórios restritos exclusivamente a administradores (`@admin_required`). |
| **TC12** | Administrador consegue alterar perfis e ativar/desativar contas com proteção contra auto-bloqueio. |
| **TC13** | Reenvio de arquivo PDF corrigido pelo solicitante quando o pedido estiver em `Aguardando correção`. |
| **TC14** | Rotina de backup gera pacote zip com snapshot SQLite, dump JSON, mídias e retenção automática. |

---

## 7. Módulos e Rotas Ativas do Sistema

| Funcionalidade | Rota | View / Responsabilidade | Acesso |
| :--- | :--- | :--- | :--- |
| **Login** | `/login/` | `login_view`: Autenticação por e-mail | Público |
| **Auto-cadastro** | `/cadastro/` | `cadastro_view`: Criação de conta de solicitante | Público |
| **Consulta Rápida** | `/consulta/` | `consulta_publica_protocolo`: Busca por código de protocolo | Público |
| **Minhas Solicitações**| `/` ou `/minhas-solicitacoes/`| `solicitante_home`: Listagem isolada do usuário logado | Solicitante |
| **Nova Solicitação** | `/solicitacoes/nova/` | `nova_solicitacao`: Formulário com upload de PDF e protocolo | Solicitante |
| **Detalhes do Pedido** | `/solicitacoes/<protocolo>/`| `detalhe_solicitacao`: Timeline de status e reenvio de correção | Solicitante / Equipe |
| **Fila FIFO do Setor** | `/setor/` | `painel_setor`: Fila de atendimento cronológica (#1, #2...) | Colaborador / Admin |
| **Atendimento Técnico**| `/setor/atendimento/<protocolo>/`| `atendimento_solicitacao`: Visualizador PDF, status e exceções | Colaborador / Admin |
| **Gestão e Relatórios**| `/gestao/` | `painel_administrativo`: Indicadores, volume e busca global | Administrador |
| **Gestão de Usuários** | `/gestao/usuarios/` | `gestao_usuarios`: Alteração de perfis e ativação de contas | Administrador |
| **Download de Anexo** | `/anexos/<id>/download/` | `download_anexo`: Entrega segura via `FileResponse` | Autorizado |

---

## 8. Instruções para Agentes Autônomos (Workflow de Execução)

1. **Antes de codificar**:
   - Leia as regras de negócio deste arquivo e do `README.md`.
   - Inspecione as migrações existentes antes de alterar qualquer modelo.
2. **Ao modificar Modelos**:
   - Sempre gere as migrações (`python manage.py makemigrations`) e teste sua aplicação (`python manage.py migrate`).
   - Garanta `related_name` semânticos em todas as ForeignKeys para evitar colisões reversas.
3. **Ao implementar Views**:
   - Utilize decorators (`@login_required`) e verificação de perfil de acesso (`request.user.perfil`).
   - Retorne feedback ao usuário via `django.contrib.messages` (mensagens de sucesso, aviso e erro).
4. **Ao finalizar alterações**:
   - Execute a suíte de testes: `python manage.py test`.
   - Certifique-se de que nenhum arquivo sensível, chave secreta ou lixo de build seja commitado.
