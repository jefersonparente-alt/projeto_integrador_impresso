import time
from datetime import date
from django.test import TestCase
from django.utils import timezone
from .models import Usuario, Solicitacao, Anexo, HistoricoStatus, ExcecaoPrioridade
from .services import (
    gerar_protocolo_unico,
    alterar_status_solicitacao,
    registrar_excecao_prioridade,
)


class BancoDeDadosModelosTestCase(TestCase):
    """
    Testes de integridade do Banco de Dados e Regras de Negócio Invariantes.
    """

    def setUp(self):
        # 1. Usuários de diferentes perfis
        self.solicitante = Usuario.objects.create_user(
            email='aluno@escola.edu.br',
            nome='Carlos Aluno',
            password='senha_segura_123',
            perfil=Usuario.PERFIL_SOLICITANTE,
            setor_turma='3º Ano Informática',
            contato='(11) 98888-7777',
        )

        self.colaborador = Usuario.objects.create_user(
            email='grafica@escola.edu.br',
            nome='Maria Operadora',
            password='senha_segura_123',
            perfil=Usuario.PERFIL_COLABORADOR,
            setor_turma='Setor de Impressões',
            contato='grafica@escola.edu.br',
        )

        self.admin = Usuario.objects.create_superuser(
            email='admin@escola.edu.br',
            nome='Prof. Coordenador',
            password='senha_segura_admin',
        )

    def test_criacao_usuarios_e_perfis(self):
        """Valida a criação e propriedades de perfis do modelo Usuario."""
        self.assertTrue(self.solicitante.is_solicitante)
        self.assertFalse(self.solicitante.is_staff)
        self.assertTrue(self.solicitante.ativo)

        self.assertTrue(self.colaborador.is_colaborador)

        self.assertTrue(self.admin.is_administrador)
        self.assertTrue(self.admin.is_staff)
        self.assertTrue(self.admin.is_superuser)

    def test_geracao_protocolo_unico(self):
        """Valida que protocolos gerados são únicos e possuem formato esperado."""
        p1 = gerar_protocolo_unico()
        p2 = gerar_protocolo_unico()
        self.assertNotEqual(p1, p2)
        self.assertTrue(p1.startswith('IMP-'))

    def test_criacao_solicitacao_e_invariante_fifo(self):
        """
        Valida que a ordenação padrão da fila é estritamente FIFO
        baseada em criado_em ASC, id ASC.
        """
        s1 = Solicitacao.objects.create(
            protocolo=gerar_protocolo_unico(),
            solicitante=self.solicitante,
            setor_turma=self.solicitante.setor_turma,
            contato=self.solicitante.contato,
            quantidade_copias=10,
            tipo_impressao=Solicitacao.TIPO_PB,
            frente_verso=True,
            prazo_desejado=date(2026, 12, 1),
            status_atual=Solicitacao.STATUS_RECEBIDA,
        )

        # Pequeno atraso para garantir diferença no timestamp
        time.sleep(0.01)

        s2 = Solicitacao.objects.create(
            protocolo=gerar_protocolo_unico(),
            solicitante=self.solicitante,
            setor_turma='Coordenação',
            contato='coord@escola.edu.br',
            quantidade_copias=5,
            tipo_impressao=Solicitacao.TIPO_COLORIDA,
            frente_verso=False,
            # Prazo anterior não deve alterar a fila FIFO
            prazo_desejado=date(2026, 11, 20),
            status_atual=Solicitacao.STATUS_RECEBIDA,
        )

        fila = list(Solicitacao.objects.all())
        self.assertEqual(fila[0], s1)
        self.assertEqual(fila[1], s2)

    def test_imutabilidade_criado_em(self):
        """Garante que atualizações na solicitação não alteram criado_em."""
        solicitacao = Solicitacao.objects.create(
            protocolo=gerar_protocolo_unico(),
            solicitante=self.solicitante,
            setor_turma=self.solicitante.setor_turma,
            contato=self.solicitante.contato,
            quantidade_copias=2,
            tipo_impressao=Solicitacao.TIPO_PB,
        )
        data_original = solicitacao.criado_em

        # Atualiza status e salva
        solicitacao.status_atual = Solicitacao.STATUS_EM_ANDAMENTO
        solicitacao.save()
        solicitacao.refresh_from_db()

        self.assertEqual(solicitacao.criado_em, data_original)

    def test_transicao_status_com_historico(self):
        """Valida que alterar_status_solicitacao gera auditoria em HistoricoStatus."""
        solicitacao = Solicitacao.objects.create(
            protocolo=gerar_protocolo_unico(),
            solicitante=self.solicitante,
            setor_turma=self.solicitante.setor_turma,
            contato=self.solicitante.contato,
            quantidade_copias=1,
            tipo_impressao=Solicitacao.TIPO_PB,
        )

        alterar_status_solicitacao(
            solicitacao=solicitacao,
            novo_status=Solicitacao.STATUS_EM_ANDAMENTO,
            usuario_responsavel=self.colaborador,
            observacao="Iniciando impressão no setor.",
        )

        solicitacao.refresh_from_db()
        self.assertEqual(solicitacao.status_atual, Solicitacao.STATUS_EM_ANDAMENTO)

        historicos = solicitacao.historicos.all()
        self.assertEqual(historicos.count(), 1)
        hist = historicos.first()
        self.assertEqual(hist.usuario_responsavel, self.colaborador)
        self.assertEqual(hist.status_anterior, Solicitacao.STATUS_RECEBIDA)
        self.assertEqual(hist.status_novo, Solicitacao.STATUS_EM_ANDAMENTO)
        self.assertEqual(hist.observacao, "Iniciando impressão no setor.")

    def test_anexo_vinculado_a_solicitacao(self):
        """Valida inserção de metadados de anexo."""
        solicitacao = Solicitacao.objects.create(
            protocolo=gerar_protocolo_unico(),
            solicitante=self.solicitante,
            setor_turma=self.solicitante.setor_turma,
            contato=self.solicitante.contato,
        )

        anexo = Anexo.objects.create(
            solicitacao=solicitacao,
            nome_original="trabalho_conclusao.pdf",
            arquivo="anexos/trabalho_conclusao.pdf",
            tipo_arquivo="application/pdf",
            tamanho_bytes=204800,
        )

        self.assertEqual(solicitacao.anexos.count(), 1)
        self.assertEqual(solicitacao.anexos.first().nome_original, "trabalho_conclusao.pdf")

    def test_excecao_prioridade_com_justificativa(self):
        """Valida concessão de prioridade excepcional fora da ordem FIFO."""
        solicitacao = Solicitacao.objects.create(
            protocolo=gerar_protocolo_unico(),
            solicitante=self.solicitante,
            setor_turma=self.solicitante.setor_turma,
            contato=self.solicitante.contato,
        )

        excecao = registrar_excecao_prioridade(
            solicitacao=solicitacao,
            autorizado_por=self.admin,
            justificativa="Impressão urgente para aplicação de prova institucional imediata.",
        )

        self.assertEqual(solicitacao.excecoes_prioridade.count(), 1)
        self.assertEqual(excecao.autorizado_por, self.admin)
        self.assertIn("prova institucional", excecao.justificativa)

    def test_rotina_backup_sistema(self):
        """Valida a execução do comando de backup e a política de retenção."""
        import tempfile
        import zipfile
        from pathlib import Path
        from django.core.management import call_command

        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. Executa comando de backup apontando para diretório temporário
            call_command('backup_sistema', output_dir=temp_dir, keep=2)

            backup_files = list(Path(temp_dir).glob('backup_sistema_*.zip'))
            self.assertEqual(len(backup_files), 1)

            # 2. Inspeciona o arquivo zip gerado
            with zipfile.ZipFile(backup_files[0], 'r') as z:
                nomes = z.namelist()
                self.assertIn('manifesto.json', nomes)
                self.assertIn('banco/dados_dump.json', nomes)

            # 3. Testa política de retenção (gera mais 2 backups para exceder keep=2)
            time.sleep(1.0)
            call_command('backup_sistema', output_dir=temp_dir, keep=2)
            time.sleep(1.0)
            call_command('backup_sistema', output_dir=temp_dir, keep=2)

            backup_files_pos = list(Path(temp_dir).glob('backup_sistema_*.zip'))
            self.assertEqual(len(backup_files_pos), 2)


class ViewsFluxoCompletoTestCase(TestCase):
    """
    Testes de Integração de Telas e Fluxos:
    - Login / Logout
    - Minhas Solicitações e Isolamento entre Solicitantes
    - Envio de Nova Solicitação com Validação de PDF
    - Painel do Setor com Ordenação FIFO
    - Tela de Atendimento e Transição de Status
    """

    def setUp(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from .services import gerar_protocolo_unico

        self.senha_padrao = 'senha12345'

        self.solicitante_a = Usuario.objects.create_user(
            email='aluno.a@escola.edu.br',
            nome='Aluno A',
            password=self.senha_padrao,
            perfil=Usuario.PERFIL_SOLICITANTE,
            setor_turma='3º Ano A',
        )

        self.solicitante_b = Usuario.objects.create_user(
            email='aluno.b@escola.edu.br',
            nome='Aluno B',
            password=self.senha_padrao,
            perfil=Usuario.PERFIL_SOLICITANTE,
            setor_turma='3º Ano B',
        )

        self.colaborador = Usuario.objects.create_user(
            email='colaborador@escola.edu.br',
            nome='Operador Gráfica',
            password=self.senha_padrao,
            perfil=Usuario.PERFIL_COLABORADOR,
            setor_turma='Setor de Impressões',
        )

        # Solicitação prévia de A
        self.solic_a = Solicitacao.objects.create(
            protocolo=gerar_protocolo_unico(),
            solicitante=self.solicitante_a,
            setor_turma='3º Ano A',
            contato='aluno.a@escola.edu.br',
            quantidade_copias=2,
            tipo_impressao=Solicitacao.TIPO_PB,
            status_atual=Solicitacao.STATUS_RECEBIDA,
        )

    def test_tela_login_com_sucesso(self):
        """Valida login de usuário e redirecionamento correto."""
        resp = self.client.post('/login/', {
            'username': self.solicitante_a.email,
            'password': self.senha_padrao,
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn(resp.url, ['/', '/minhas-solicitacoes/'])

    def test_cadastro_novo_solicitante(self):
        """Valida auto-cadastro de novo usuário com perfil solicitante."""
        dados = {
            'nome': 'Novo Aluno',
            'email': 'novo.aluno@escola.edu.br',
            'setor_turma': '1º Ano Informática',
            'contato': '(11) 97777-6666',
            'senha': 'senha_super_segura_123',
            'confirmacao_senha': 'senha_super_segura_123',
        }
        resp = self.client.post('/cadastro/', dados)
        self.assertEqual(resp.status_code, 302)

        novo_user = Usuario.objects.filter(email='novo.aluno@escola.edu.br').first()
        self.assertIsNotNone(novo_user)
        self.assertEqual(novo_user.nome, 'Novo Aluno')
        self.assertEqual(novo_user.perfil, Usuario.PERFIL_SOLICITANTE)
        self.assertTrue(novo_user.check_password('senha_super_segura_123'))

    def test_isolamento_solicitante_minhas_solicitacoes(self):
        """Garante que Solicitante B NÃO vê as solicitações do Solicitante A."""
        self.client.login(username=self.solicitante_b.email, password=self.senha_padrao)
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, self.solic_a.protocolo)

        # Mas Solicitante A consegue visualizar
        self.client.logout()
        self.client.login(username=self.solicitante_a.email, password=self.senha_padrao)
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.solic_a.protocolo)

    def test_formulario_nova_solicitacao_pdf_valido(self):
        """Valida abertura de pedido com upload de PDF e criação do anexo."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.login(username=self.solicitante_a.email, password=self.senha_padrao)
        pdf_conteudo = b"%PDF-1.4 ... dados de teste pdf ..."
        arquivo_pdf = SimpleUploadedFile("prova.pdf", pdf_conteudo, content_type="application/pdf")

        dados = {
            'setor_turma': '3º Ano A',
            'contato': 'aluno.a@escola.edu.br',
            'quantidade_copias': 5,
            'tipo_impressao': 'pb',
            'frente_verso': True,
            'instrucoes': 'Imprimir frente e verso.',
            'arquivo': arquivo_pdf,
        }

        resp = self.client.post('/solicitacoes/nova/', dados)
        self.assertEqual(resp.status_code, 302)

        nova = Solicitacao.objects.filter(solicitante=self.solicitante_a).exclude(id=self.solic_a.id).first()
        self.assertIsNotNone(nova)
        self.assertEqual(nova.quantidade_copias, 5)
        self.assertEqual(nova.anexos.count(), 1)
        self.assertEqual(nova.anexos.first().nome_original, 'prova.pdf')

    def test_recusa_arquivo_invalido(self):
        """Valida que arquivo com extensão não permitida (.docx) é rejeitado."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.login(username=self.solicitante_a.email, password=self.senha_padrao)
        arquivo_invalido = SimpleUploadedFile("texto.docx", b"conteudo", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

        dados = {
            'setor_turma': '3º Ano A',
            'contato': 'aluno.a@escola.edu.br',
            'quantidade_copias': 1,
            'tipo_impressao': 'pb',
            'arquivo': arquivo_invalido,
        }

        resp = self.client.post('/solicitacoes/nova/', dados)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Apenas arquivos com extensão .pdf são aceitos")

    def test_painel_setor_fila_fifo(self):
        """Valida acesso do colaborador e ordenação rigorosa FIFO no painel."""
        from .services import gerar_protocolo_unico

        # Cria segunda solicitação para testar FIFO
        time.sleep(0.01)
        solic_2 = Solicitacao.objects.create(
            protocolo=gerar_protocolo_unico(),
            solicitante=self.solicitante_b,
            setor_turma='3º Ano B',
            contato='aluno.b@escola.edu.br',
            quantidade_copias=1,
            tipo_impressao=Solicitacao.TIPO_PB,
            status_atual=Solicitacao.STATUS_RECEBIDA,
        )

        self.client.login(username=self.colaborador.email, password=self.senha_padrao)
        resp = self.client.get('/setor/')
        self.assertEqual(resp.status_code, 200)
        solics = list(resp.context['solicitacoes'])
        self.assertEqual(solics[0], self.solic_a)
        self.assertEqual(solics[1], solic_2)

    def test_atendimento_solicitacao_atualizar_status(self):
        """Valida que colaborador atualiza status e grava observação na tela de atendimento."""
        self.client.login(username=self.colaborador.email, password=self.senha_padrao)
        resp = self.client.post(f'/setor/atendimento/{self.solic_a.protocolo}/', {
            'acao': 'atualizar_status',
            'novo_status': Solicitacao.STATUS_EM_ANDAMENTO,
            'observacao': 'Iniciando produção gráfica.',
        })
        self.assertEqual(resp.status_code, 302)

        self.solic_a.refresh_from_db()
        self.assertEqual(self.solic_a.status_atual, Solicitacao.STATUS_EM_ANDAMENTO)
        self.assertEqual(self.solic_a.historicos.first().observacao, 'Iniciando produção gráfica.')

    def test_solicitante_bloqueado_no_painel_setor(self):
        """Garante que perfil solicitante recebe 403 Forbidden ao tentar acessar painel do setor."""
        self.client.login(username=self.solicitante_a.email, password=self.senha_padrao)
        resp = self.client.get('/setor/')
        self.assertEqual(resp.status_code, 403)


