from functools import wraps
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .forms import LoginForm, SolicitacaoForm, CadastroUsuarioForm, CorrecaoSolicitacaoForm
from .models import Anexo, HistoricoStatus, Solicitacao, Usuario
from .services import (
    alterar_status_solicitacao,
    gerar_protocolo_unico,
    registrar_excecao_prioridade,
)


def colaborador_required(view_func):
    """Decorator para restringir acesso a colaboradores do setor e administradores."""
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not (request.user.is_colaborador or request.user.is_administrador or request.user.is_superuser):
            raise PermissionDenied("Acesso restrito à equipe do setor de impressos.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def admin_required(view_func):
    """Decorator para restringir acesso a administradores do sistema."""
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not (request.user.is_administrador or request.user.is_superuser):
            raise PermissionDenied("Acesso restrito a administradores do sistema.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def login_view(request):
    """Tela de autenticação do sistema."""
    if request.user.is_authenticated:
        if request.user.is_colaborador:
            return redirect('painel_setor')
        return redirect('solicitante_home')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Bem-vindo(a) de volta, {user.nome}!')
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            if user.is_colaborador:
                return redirect('painel_setor')
            return redirect('solicitante_home')
        else:
            messages.error(request, 'E-mail ou senha incorretos. Verifique suas credenciais e tente novamente.')
    else:
        form = LoginForm(request)

    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    """Encerra a sessão do usuário."""
    logout(request)
    messages.info(request, 'Você encerrou a sua sessão com sucesso.')
    return redirect('login')


def cadastro_view(request):
    """Tela de cadastro de novo Solicitante (Auto-cadastro)."""
    if request.user.is_authenticated:
        return redirect('solicitante_home')

    if request.method == 'POST':
        form = CadastroUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Conta criada com sucesso! Seja bem-vindo(a), {user.nome}.')
            return redirect('solicitante_home')
        else:
            messages.error(request, 'Por favor, corrija os erros apontados no formulário de cadastro.')
    else:
        form = CadastroUsuarioForm()

    return render(request, 'auth/cadastro.html', {'form': form})


# ==============================================================================
# ÁREA DO SOLICITANTE
# ==============================================================================

@login_required
def solicitante_home(request):
    """
    Página inicial do solicitante (Minhas Solicitações).
    Isolamento de dados: lista estritamente as solicitações do usuário logado.
    """
    qs = Solicitacao.objects.filter(solicitante=request.user)

    # Métricas para os cards de resumo
    metricas = {
        'total': qs.count(),
        'recebidas': qs.filter(status_atual=Solicitacao.STATUS_RECEBIDA).count(),
        'em_andamento': qs.filter(status_atual=Solicitacao.STATUS_EM_ANDAMENTO).count(),
        'aguardando_correcao': qs.filter(status_atual=Solicitacao.STATUS_AGUARDANDO_CORRECAO).count(),
        'concluidas': qs.filter(status_atual=Solicitacao.STATUS_CONCLUIDA).count(),
        'canceladas': qs.filter(status_atual=Solicitacao.STATUS_CANCELADA).count(),
    }

    # Filtro opcional por status
    status_filtro = request.GET.get('status', '').strip()
    if status_filtro and status_filtro in dict(Solicitacao.STATUS_CHOICES):
        solicitacoes = qs.filter(status_atual=status_filtro).order_by('-criado_em')
    else:
        solicitacoes = qs.order_by('-criado_em')

    # Busca opcional por protocolo
    busca = request.GET.get('q', '').strip()
    if busca:
        solicitacoes = solicitacoes.filter(protocolo__icontains=busca)

    context = {
        'solicitacoes': solicitacoes,
        'metricas': metricas,
        'status_filtro': status_filtro,
        'busca': busca,
        'status_choices': Solicitacao.STATUS_CHOICES,
    }
    return render(request, 'solicitante/home.html', context)


@login_required
def nova_solicitacao(request):
    """
    Formulário para abertura de nova solicitação de impressão com anexo PDF.
    Gera protocolo único e registra o primeiro evento em HistoricoStatus.
    """
    if request.method == 'POST':
        form = SolicitacaoForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                solicitacao = form.save(commit=False)
                solicitacao.solicitante = request.user
                solicitacao.protocolo = gerar_protocolo_unico()
                solicitacao.status_atual = Solicitacao.STATUS_RECEBIDA
                solicitacao.save()

                arquivo_enviado = form.cleaned_data['arquivo']
                Anexo.objects.create(
                    solicitacao=solicitacao,
                    nome_original=arquivo_enviado.name,
                    arquivo=arquivo_enviado,
                    tipo_arquivo=getattr(arquivo_enviado, 'content_type', 'application/pdf'),
                    tamanho_bytes=arquivo_enviado.size,
                )

                HistoricoStatus.objects.create(
                    solicitacao=solicitacao,
                    usuario_responsavel=request.user,
                    status_anterior='-',
                    status_novo=Solicitacao.STATUS_RECEBIDA,
                    observacao='Solicitação enviada e registrada na fila FIFO.',
                )

            messages.success(
                request,
                f'Solicitação registrada com sucesso! Seu número de protocolo é {solicitacao.protocolo}.'
            )
            return redirect('detalhe_solicitacao', protocolo=solicitacao.protocolo)
        else:
            messages.error(request, 'Houve um erro no preenchimento do formulário. Corrija os campos destacados.')
    else:
        dados_iniciais = {
            'setor_turma': request.user.setor_turma,
            'contato': request.user.contato or request.user.email,
            'quantidade_copias': 1,
            'tipo_impressao': Solicitacao.TIPO_PB,
            'frente_verso': False,
        }
        form = SolicitacaoForm(initial=dados_iniciais)

    return render(request, 'solicitante/nova_solicitacao.html', {'form': form})


@login_required
def detalhe_solicitacao(request, protocolo):
    """
    Exibe os detalhes, anexos e a linha do tempo de histórico de uma solicitação.
    Garante controle de acesso: solicitante só vê seus próprios pedidos.
    """
    solicitacao = get_object_or_404(Solicitacao, protocolo=protocolo)

    if (
        solicitacao.solicitante != request.user
        and not request.user.is_colaborador
        and not request.user.is_administrador
    ):
        raise PermissionDenied("Você não possui permissão para visualizar esta solicitação.")

    # Tratamento de correção de anexo quando status for AGUARDANDO_CORRECAO
    correcao_form = None
    if solicitacao.status_atual == Solicitacao.STATUS_AGUARDANDO_CORRECAO and solicitacao.solicitante == request.user:
        if request.method == 'POST' and request.POST.get('acao') == 'enviar_correcao':
            correcao_form = CorrecaoSolicitacaoForm(request.POST, request.FILES)
            if correcao_form.is_valid():
                with transaction.atomic():
                    novo_arquivo = correcao_form.cleaned_data['arquivo']
                    Anexo.objects.create(
                        solicitacao=solicitacao,
                        nome_original=novo_arquivo.name,
                        arquivo=novo_arquivo,
                        tipo_arquivo=getattr(novo_arquivo, 'content_type', 'application/pdf'),
                        tamanho_bytes=novo_arquivo.size,
                    )
                    obs = correcao_form.cleaned_data.get('observacao', '').strip()
                    msg_obs = f"Correção enviada pelo solicitante. {obs}".strip()
                    alterar_status_solicitacao(
                        solicitacao=solicitacao,
                        novo_status=Solicitacao.STATUS_RECEBIDA,
                        usuario_responsavel=request.user,
                        observacao=msg_obs,
                    )
                messages.success(request, 'Documento corrigido enviado com sucesso! O pedido retornou para a fila de atendimento.')
                return redirect('detalhe_solicitacao', protocolo=solicitacao.protocolo)
        else:
            correcao_form = CorrecaoSolicitacaoForm()

    historicos = solicitacao.historicos.all().order_by('-data_hora')
    anexos = solicitacao.anexos.all()
    excecoes = solicitacao.excecoes_prioridade.all()

    context = {
        'solicitacao': solicitacao,
        'historicos': historicos,
        'anexos': anexos,
        'excecoes': excecoes,
        'correcao_form': correcao_form,
    }
    return render(request, 'solicitante/detalhe_solicitacao.html', context)


@login_required
def download_anexo(request, anexo_id):
    """
    Entrega segura de anexos através de FileResponse protegida.
    Nenhum arquivo pode ser baixado publicamente sem autenticação e autorização.
    """
    anexo = get_object_or_404(Anexo, id=anexo_id)
    solicitacao = anexo.solicitacao

    if (
        solicitacao.solicitante != request.user
        and not request.user.is_colaborador
        and not request.user.is_administrador
    ):
        raise PermissionDenied("Acesso não autorizado a este arquivo.")

    if not anexo.arquivo or not anexo.arquivo.storage.exists(anexo.arquivo.name):
        raise Http404("Arquivo não encontrado no servidor de armazenamento.")

    response = FileResponse(
        anexo.arquivo.open('rb'),
        content_type=anexo.tipo_arquivo or 'application/pdf',
    )
    response['Content-Disposition'] = f'inline; filename="{anexo.nome_original}"'
    return response


# ==============================================================================
# PAINEL DO SETOR DE IMPRESSOS E ATENDIMENTO (COLABORADOR / ADMIN)
# ==============================================================================

@colaborador_required
def painel_setor(request):
    """
    Painel de trabalho do setor de impressos.
    A fila padrão é rigorosamente ordenada por FIFO (criado_em ASC, id ASC).
    """
    hoje = timezone.now().date()
    qs_total = Solicitacao.objects.all()

    # Métricas do Setor
    metricas = {
        'na_fila': qs_total.filter(status_atual=Solicitacao.STATUS_RECEBIDA).count(),
        'em_andamento': qs_total.filter(status_atual=Solicitacao.STATUS_EM_ANDAMENTO).count(),
        'aguardando_correcao': qs_total.filter(status_atual=Solicitacao.STATUS_AGUARDANDO_CORRECAO).count(),
        'concluidas_hoje': qs_total.filter(status_atual=Solicitacao.STATUS_CONCLUIDA, historicos__status_novo=Solicitacao.STATUS_CONCLUIDA, historicos__data_hora__date=hoje).distinct().count(),
        'total_geral': qs_total.count(),
    }

    # Aba ativa: 'fila' (padrão) ou 'historico' (concluídas e canceladas)
    aba = request.GET.get('aba', 'fila').strip()
    status_filtro = request.GET.get('status', '').strip()
    busca = request.GET.get('q', '').strip()

    if aba == 'historico':
        solicitacoes = qs_total.filter(
            Q(status_atual=Solicitacao.STATUS_CONCLUIDA) | Q(status_atual=Solicitacao.STATUS_CANCELADA)
        ).order_by('-criado_em', '-id')
    else:
        # Fila de atendimento padrão: ordenada estritamente por FIFO
        solicitacoes = qs_total.exclude(
            Q(status_atual=Solicitacao.STATUS_CONCLUIDA) | Q(status_atual=Solicitacao.STATUS_CANCELADA)
        ).order_by('criado_em', 'id')

    if status_filtro and status_filtro in dict(Solicitacao.STATUS_CHOICES):
        solicitacoes = solicitacoes.filter(status_atual=status_filtro)

    if busca:
        solicitacoes = solicitacoes.filter(
            Q(protocolo__icontains=busca) |
            Q(solicitante__nome__icontains=busca) |
            Q(setor_turma__icontains=busca)
        )

    context = {
        'solicitacoes': solicitacoes,
        'metricas': metricas,
        'aba': aba,
        'status_filtro': status_filtro,
        'busca': busca,
        'status_choices': Solicitacao.STATUS_CHOICES,
    }
    return render(request, 'setor/painel.html', context)


@colaborador_required
def atendimento_solicitacao(request, protocolo):
    """
    Tela de Atendimento do Setor de Impressos.
    Permite conferir o arquivo, atualizar o status com observação auditada,
    e registrar exceção de prioridade caso necessário.
    """
    solicitacao = get_object_or_404(Solicitacao, protocolo=protocolo)
    anexos = solicitacao.anexos.all()
    historicos = solicitacao.historicos.all().order_by('-data_hora')
    excecoes = solicitacao.excecoes_prioridade.all()

    if request.method == 'POST':
        acao = request.POST.get('acao')

        # 1. Atualização de Status
        if acao == 'atualizar_status':
            novo_status = request.POST.get('novo_status')
            observacao = request.POST.get('observacao', '').strip()

            if novo_status not in dict(Solicitacao.STATUS_CHOICES):
                messages.error(request, 'Status selecionado é inválido.')
            elif novo_status in [Solicitacao.STATUS_AGUARDANDO_CORRECAO, Solicitacao.STATUS_CANCELADA] and not observacao:
                messages.error(request, f'É obrigatório registrar uma observação/motivo ao alterar para "{novo_status}".')
            else:
                alterar_status_solicitacao(
                    solicitacao=solicitacao,
                    novo_status=novo_status,
                    usuario_responsavel=request.user,
                    observacao=observacao,
                )
                messages.success(request, f'Status atualizado para "{solicitacao.get_status_atual_display()}" com sucesso!')
                return redirect('atendimento_solicitacao', protocolo=solicitacao.protocolo)

        # 2. Concessão de Exceção de Prioridade
        elif acao == 'registrar_excecao':
            justificativa = request.POST.get('justificativa', '').strip()
            if not justificativa:
                messages.error(request, 'A justificativa para quebra excepcional da fila é obrigatória.')
            else:
                registrar_excecao_prioridade(
                    solicitacao=solicitacao,
                    autorizado_por=request.user,
                    justificativa=justificativa,
                )
                # Opcional: altera status para em andamento
                if solicitacao.status_atual == Solicitacao.STATUS_RECEBIDA:
                    alterar_status_solicitacao(
                        solicitacao=solicitacao,
                        novo_status=Solicitacao.STATUS_EM_ANDAMENTO,
                        usuario_responsavel=request.user,
                        observacao=f"Prioridade concedida: {justificativa}",
                    )
                messages.success(request, 'Exceção de prioridade registrada com sucesso!')
                return redirect('atendimento_solicitacao', protocolo=solicitacao.protocolo)

    context = {
        'solicitacao': solicitacao,
        'anexos': anexos,
        'historicos': historicos,
        'excecoes': excecoes,
        'status_choices': Solicitacao.STATUS_CHOICES,
    }
    return render(request, 'setor/atendimento.html', context)


# ==============================================================================
# CONSULTA RÁPIDA DE SOLICITAÇÃO (POR PROTOCOLO)
# ==============================================================================

def consulta_publica_protocolo(request):
    """
    Permite consultar a situação e histórico de uma solicitação a partir do protocolo.
    """
    protocolo = request.GET.get('protocolo', '').strip().upper()
    solicitacao = None
    historicos = []

    if protocolo:
        solicitacao = Solicitacao.objects.filter(protocolo=protocolo).first()
        if solicitacao:
            historicos = solicitacao.historicos.all().order_by('-data_hora')
        else:
            messages.warning(request, f'Nenhuma solicitação encontrada com o protocolo "{protocolo}".')

    return render(request, 'consulta.html', {
        'protocolo': protocolo,
        'solicitacao': solicitacao,
        'historicos': historicos,
    })


# ==============================================================================
# GERENCIAMENTO ADMINISTRATIVO (RELATÓRIOS E USUÁRIOS)
# ==============================================================================

@admin_required
def painel_administrativo(request):
    """
    Painel de Gestão e Relatórios da Administração Escolar.
    Métricas globais de volume, status, tipos de impressão e consulta geral.
    """
    from django.db.models import Sum

    qs = Solicitacao.objects.all()

    # Métricas gerais
    total_solicitacoes = qs.count()
    total_copias = qs.aggregate(total=Sum('quantidade_copias'))['total'] or 0
    total_usuarios = Usuario.objects.count()
    usuarios_ativos = Usuario.objects.filter(is_active=True).count()

    # Distribuição por status
    status_counts = {
        'recebidas': qs.filter(status_atual=Solicitacao.STATUS_RECEBIDA).count(),
        'em_andamento': qs.filter(status_atual=Solicitacao.STATUS_EM_ANDAMENTO).count(),
        'aguardando_correcao': qs.filter(status_atual=Solicitacao.STATUS_AGUARDANDO_CORRECAO).count(),
        'concluidas': qs.filter(status_atual=Solicitacao.STATUS_CONCLUIDA).count(),
        'canceladas': qs.filter(status_atual=Solicitacao.STATUS_CANCELADA).count(),
    }

    # Distribuição por tipo de impressão
    tipo_counts = {
        'pb': qs.filter(tipo_impressao=Solicitacao.TIPO_PB).count(),
        'colorida': qs.filter(tipo_impressao=Solicitacao.TIPO_COLORIDA).count(),
    }

    # Filtros de consulta geral
    status_filtro = request.GET.get('status', '').strip()
    busca = request.GET.get('q', '').strip()
    solicitacoes = qs.order_by('-criado_em')

    if status_filtro and status_filtro in dict(Solicitacao.STATUS_CHOICES):
        solicitacoes = solicitacoes.filter(status_atual=status_filtro)

    if busca:
        solicitacoes = solicitacoes.filter(
            Q(protocolo__icontains=busca) |
            Q(solicitante__nome__icontains=busca) |
            Q(solicitante__email__icontains=busca) |
            Q(setor_turma__icontains=busca)
        )

    context = {
        'total_solicitacoes': total_solicitacoes,
        'total_copias': total_copias,
        'total_usuarios': total_usuarios,
        'usuarios_ativos': usuarios_ativos,
        'status_counts': status_counts,
        'tipo_counts': tipo_counts,
        'solicitacoes': solicitacoes[:50],  # Limite para exibição
        'status_filtro': status_filtro,
        'busca': busca,
        'status_choices': Solicitacao.STATUS_CHOICES,
    }
    return render(request, 'admin_panel/painel.html', context)


@admin_required
def gestao_usuarios(request):
    """
    Gestão de Usuários e Permissões.
    Permite aos administradores alterar perfis e ativar/desativar contas.
    """
    if request.method == 'POST':
        usuario_id = request.POST.get('usuario_id')
        acao = request.POST.get('acao')
        usuario_alvo = get_object_or_404(Usuario, id=usuario_id)

        # Não permite auto-desativação do próprio administrador conectado
        if usuario_alvo == request.user and acao == 'alternar_status':
            messages.error(request, 'Você não pode desativar sua própria conta de administrador.')
            return redirect('gestao_usuarios')

        if acao == 'alterar_perfil':
            novo_perfil = request.POST.get('novo_perfil')
            if novo_perfil in dict(Usuario.PERFIL_CHOICES):
                usuario_alvo.perfil = novo_perfil
                if novo_perfil == Usuario.PERFIL_ADMINISTRADOR:
                    usuario_alvo.is_staff = True
                usuario_alvo.save()
                messages.success(request, f'Perfil de {usuario_alvo.nome} atualizado para "{usuario_alvo.get_perfil_display()}".')

        elif acao == 'alternar_status':
            usuario_alvo.is_active = not usuario_alvo.is_active
            usuario_alvo.save()
            estado = "ativada" if usuario_alvo.is_active else "desativada"
            messages.success(request, f'Conta de {usuario_alvo.nome} foi {estado} com sucesso.')

        return redirect('gestao_usuarios')

    perfil_filtro = request.GET.get('perfil', '').strip()
    busca = request.GET.get('q', '').strip()
    usuarios = Usuario.objects.all().order_by('nome')

    if perfil_filtro and perfil_filtro in dict(Usuario.PERFIL_CHOICES):
        usuarios = usuarios.filter(perfil=perfil_filtro)

    if busca:
        usuarios = usuarios.filter(
            Q(nome__icontains=busca) |
            Q(email__icontains=busca) |
            Q(setor_turma__icontains=busca)
        )

    context = {
        'usuarios': usuarios,
        'perfil_filtro': perfil_filtro,
        'busca': busca,
        'perfil_choices': Usuario.PERFIL_CHOICES,
    }
    return render(request, 'admin_panel/usuarios.html', context)
