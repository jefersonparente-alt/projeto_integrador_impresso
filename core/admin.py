from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Usuario, Solicitacao, Anexo, HistoricoStatus, ExcecaoPrioridade


class AnexoInline(admin.TabularInline):
    model = Anexo
    extra = 0
    readonly_fields = ('nome_original', 'tipo_arquivo', 'tamanho_bytes', 'enviado_em')


class HistoricoStatusInline(admin.TabularInline):
    model = HistoricoStatus
    extra = 0
    readonly_fields = ('usuario_responsavel', 'status_anterior', 'status_novo', 'data_hora', 'observacao')
    can_delete = False


class ExcecaoPrioridadeInline(admin.StackedInline):
    model = ExcecaoPrioridade
    extra = 0
    readonly_fields = ('autorizado_por', 'justificativa', 'criada_em')


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    list_display = ('nome', 'email', 'perfil', 'setor_turma', 'contato', 'is_active', 'is_staff', 'criado_em')
    list_filter = ('perfil', 'is_active', 'is_staff')
    search_fields = ('nome', 'email', 'setor_turma', 'contato')
    ordering = ('nome',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informações Pessoais', {'fields': ('nome', 'setor_turma', 'contato')}),
        ('Perfil e Permissões', {'fields': ('perfil', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Datas Importantes', {'fields': ('last_login', 'criado_em')}),
    )

    readonly_fields = ('criado_em', 'last_login')

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nome', 'perfil', 'setor_turma', 'contato', 'password'),
        }),
    )


@admin.register(Solicitacao)
class SolicitacaoAdmin(admin.ModelAdmin):
    list_display = (
        'protocolo',
        'solicitante',
        'setor_turma',
        'status_atual',
        'quantidade_copias',
        'tipo_impressao',
        'frente_verso',
        'criado_em',
        'prazo_desejado',
    )
    list_filter = ('status_atual', 'tipo_impressao', 'frente_verso', 'criado_em')
    search_fields = ('protocolo', 'solicitante__nome', 'solicitante__email', 'setor_turma')
    readonly_fields = ('protocolo', 'criado_em')
    # Regra FIFO no admin
    ordering = ('criado_em', 'id')
    inlines = [AnexoInline, HistoricoStatusInline, ExcecaoPrioridadeInline]


@admin.register(Anexo)
class AnexoAdmin(admin.ModelAdmin):
    list_display = ('nome_original', 'solicitacao', 'tipo_arquivo', 'tamanho_bytes', 'enviado_em')
    list_filter = ('tipo_arquivo', 'enviado_em')
    search_fields = ('nome_original', 'solicitacao__protocolo')
    readonly_fields = ('enviado_em',)


@admin.register(HistoricoStatus)
class HistoricoStatusAdmin(admin.ModelAdmin):
    list_display = ('solicitacao', 'usuario_responsavel', 'status_anterior', 'status_novo', 'data_hora')
    list_filter = ('status_novo', 'data_hora')
    search_fields = ('solicitacao__protocolo', 'usuario_responsavel__nome')
    readonly_fields = ('data_hora',)


@admin.register(ExcecaoPrioridade)
class ExcecaoPrioridadeAdmin(admin.ModelAdmin):
    list_display = ('solicitacao', 'autorizado_por', 'criada_em')
    search_fields = ('solicitacao__protocolo', 'autorizado_por__nome', 'justificativa')
    readonly_fields = ('criada_em',)
