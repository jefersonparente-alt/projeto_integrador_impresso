import os
import uuid
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager,
)


class UsuarioManager(BaseUserManager):
    """Gerenciador customizado para o modelo Usuario baseado em e-mail."""

    def create_user(self, email: str, nome: str, password: str = None, **extra_fields):
        if not email:
            raise ValueError('O e-mail é obrigatório.')
        email = self.normalize_email(email)
        user = self.model(email=email, nome=nome, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, nome: str = 'Administrador', password: str = None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('perfil', Usuario.PERFIL_ADMINISTRADOR)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superusuário deve possuir is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superusuário deve possuir is_superuser=True.')

        return self.create_user(email, nome, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """
    Modelo de Usuário do sistema (Custom User Model).
    Reflete a tabela USUARIO do DER com perfis: solicitante, colaborador e administrador.
    """

    PERFIL_SOLICITANTE = 'solicitante'
    PERFIL_COLABORADOR = 'colaborador'
    PERFIL_ADMINISTRADOR = 'administrador'

    PERFIL_CHOICES = [
        (PERFIL_SOLICITANTE, 'Solicitante'),
        (PERFIL_COLABORADOR, 'Colaborador'),
        (PERFIL_ADMINISTRADOR, 'Administrador'),
    ]

    nome = models.CharField(max_length=150, verbose_name='Nome')
    email = models.EmailField(unique=True, db_index=True, verbose_name='E-mail')
    perfil = models.CharField(
        max_length=20,
        choices=PERFIL_CHOICES,
        default=PERFIL_SOLICITANTE,
        verbose_name='Perfil',
    )
    setor_turma = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Setor / Turma',
    )
    contato = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Contato (E-mail ou Telefone)',
    )
    is_active = models.BooleanField(
        default=True,
        db_column='ativo',
        verbose_name='Ativo',
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name='Membro da Equipe (Acesso Admin)',
    )
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Criado em',
    )

    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome']

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        ordering = ['nome', 'id']

    def __str__(self) -> str:
        return f"{self.nome} ({self.get_perfil_display()})"

    @property
    def ativo(self) -> bool:
        return self.is_active

    @ativo.setter
    def ativo(self, valor: bool):
        self.is_active = valor

    @property
    def is_solicitante(self) -> bool:
        return self.perfil == self.PERFIL_SOLICITANTE

    @property
    def is_colaborador(self) -> bool:
        return self.perfil == self.PERFIL_COLABORADOR

    @property
    def is_administrador(self) -> bool:
        return self.perfil == self.PERFIL_ADMINISTRADOR or self.is_superuser

    def save(self, *args, **kwargs):
        # Garante permissões de staff para o perfil administrador
        if self.perfil == self.PERFIL_ADMINISTRADOR:
            self.is_staff = True
        super().save(*args, **kwargs)


class Solicitacao(models.Model):
    """
    Representa o pedido de impressão submetido à fila.
    A ordenação padrão segue rigorosamente o princípio FIFO: criado_em ASC, id ASC.
    """

    TIPO_PB = 'pb'
    TIPO_COLORIDA = 'colorida'

    TIPO_IMPRESSAO_CHOICES = [
        (TIPO_PB, 'Preto e Branco'),
        (TIPO_COLORIDA, 'Colorida'),
    ]

    STATUS_RECEBIDA = 'RECEBIDA'
    STATUS_EM_ANDAMENTO = 'EM_ANDAMENTO'
    STATUS_AGUARDANDO_CORRECAO = 'AGUARDANDO_CORRECAO'
    STATUS_CONCLUIDA = 'CONCLUIDA'
    STATUS_CANCELADA = 'CANCELADA'

    STATUS_CHOICES = [
        (STATUS_RECEBIDA, 'Recebida'),
        (STATUS_EM_ANDAMENTO, 'Em andamento'),
        (STATUS_AGUARDANDO_CORRECAO, 'Aguardando correção'),
        (STATUS_CONCLUIDA, 'Concluída'),
        (STATUS_CANCELADA, 'Cancelada'),
    ]

    protocolo = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        verbose_name='Protocolo',
    )
    solicitante = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='solicitacoes',
        verbose_name='Solicitante',
    )
    setor_turma = models.CharField(
        max_length=100,
        verbose_name='Setor / Turma',
    )
    contato = models.CharField(
        max_length=50,
        verbose_name='Contato',
    )
    criado_em = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        editable=False,
        verbose_name='Criado em',
    )
    quantidade_copias = models.PositiveIntegerField(
        default=1,
        verbose_name='Quantidade de Cópias',
    )
    tipo_impressao = models.CharField(
        max_length=10,
        choices=TIPO_IMPRESSAO_CHOICES,
        default=TIPO_PB,
        verbose_name='Tipo de Impressão',
    )
    frente_verso = models.BooleanField(
        default=False,
        verbose_name='Frente e Verso',
    )
    instrucoes = models.TextField(
        blank=True,
        verbose_name='Instruções',
    )
    prazo_desejado = models.DateField(
        null=True,
        blank=True,
        verbose_name='Prazo Desejado (Informativo)',
    )
    status_atual = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_RECEBIDA,
        db_index=True,
        verbose_name='Status Atual',
    )

    class Meta:
        verbose_name = 'Solicitação'
        verbose_name_plural = 'Solicitações'
        # Regra Invariante FIFO: sempre por criado_em ASC e id ASC
        ordering = ['criado_em', 'id']

    def __str__(self) -> str:
        return f"[{self.protocolo}] {self.solicitante.nome} - {self.get_status_atual_display()}"


def caminho_upload_anexo(instance: 'Anexo', filename: str) -> str:
    """Gera um caminho seguro e não adivinhável para o upload do documento."""
    ext = os.path.splitext(filename)[1].lower()
    novo_nome = f"{uuid.uuid4().hex}{ext}"
    return os.path.join('anexos', novo_nome)


class Anexo(models.Model):
    """
    Armazena os metadados e o arquivo anexado à solicitação de impressão.
    """

    solicitacao = models.ForeignKey(
        Solicitacao,
        on_delete=models.CASCADE,
        related_name='anexos',
        verbose_name='Solicitação',
    )
    nome_original = models.CharField(
        max_length=255,
        verbose_name='Nome Original do Arquivo',
    )
    arquivo = models.FileField(
        upload_to=caminho_upload_anexo,
        verbose_name='Arquivo',
    )
    tipo_arquivo = models.CharField(
        max_length=100,
        default='application/pdf',
        verbose_name='Tipo MIME',
    )
    tamanho_bytes = models.BigIntegerField(
        verbose_name='Tamanho em Bytes',
    )
    enviado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Enviado em',
    )

    class Meta:
        verbose_name = 'Anexo'
        verbose_name_plural = 'Anexos'
        ordering = ['enviado_em', 'id']

    def __str__(self) -> str:
        return f"{self.nome_original} ({self.solicitacao.protocolo})"


class HistoricoStatus(models.Model):
    """
    Audita cada mudança de status ocorrida na solicitação.
    """

    solicitacao = models.ForeignKey(
        Solicitacao,
        on_delete=models.CASCADE,
        related_name='historicos',
        verbose_name='Solicitação',
    )
    usuario_responsavel = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historicos_atualizados',
        verbose_name='Usuário Responsável',
    )
    status_anterior = models.CharField(
        max_length=30,
        verbose_name='Status Anterior',
    )
    status_novo = models.CharField(
        max_length=30,
        verbose_name='Status Novo',
    )
    data_hora = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data e Hora da Transição',
    )
    observacao = models.TextField(
        blank=True,
        verbose_name='Observação / Motivo',
    )

    class Meta:
        verbose_name = 'Histórico de Status'
        verbose_name_plural = 'Históricos de Status'
        ordering = ['-data_hora', '-id']

    def __str__(self) -> str:
        return f"{self.solicitacao.protocolo}: {self.status_anterior} -> {self.status_novo}"


class ExcecaoPrioridade(models.Model):
    """
    Registra formalmente a justificativa para antecipar um pedido fora da ordem FIFO.
    """

    solicitacao = models.ForeignKey(
        Solicitacao,
        on_delete=models.CASCADE,
        related_name='excecoes_prioridade',
        verbose_name='Solicitação',
    )
    autorizado_por = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='excecoes_autorizadas',
        verbose_name='Autorizado por',
    )
    justificativa = models.TextField(
        verbose_name='Justificativa da Urgência',
    )
    criada_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Criada em',
    )

    class Meta:
        verbose_name = 'Exceção de Prioridade'
        verbose_name_plural = 'Exceções de Prioridade'
        ordering = ['-criada_em', '-id']

    def __str__(self) -> str:
        return f"Exceção [{self.solicitacao.protocolo}] autorizada por {self.autorizado_por.nome}"
