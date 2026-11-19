from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from .forms import LoginForm, SolicitacaoForm
from .models import Anexo, HistoricoStatus, Solicitacao
from .services import gerar_protocolo_unico


def login_view(request):
    """Tela de autenticação do sistema."""
    if request.user.is_authenticated:
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
                f'Solicitação registrada com sucesso! Seu número de protocolo é {solicitacao.protocolo}. '
                f'Você pode acompanhar o andamento nesta tela.'
            )
            return redirect('detalhe_solicitacao', protocolo=solicitacao.protocolo)
        else:
            messages.error(request, 'Houve um erro no preenchimento do formulário. Corrija os campos destacados.')
    else:
        # Preenche com dados conhecidos do usuário autenticado
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

    # Checagem de isolamento de dados
    if (
        solicitacao.solicitante != request.user
        and not request.user.is_colaborador
        and not request.user.is_administrador
    ):
        raise PermissionDenied("Você não possui permissão para visualizar esta solicitação.")

    historicos = solicitacao.historicos.all().order_by('-data_hora')
    anexos = solicitacao.anexos.all()
    excecoes = solicitacao.excecoes_prioridade.all()

    context = {
        'solicitacao': solicitacao,
        'historicos': historicos,
        'anexos': anexos,
        'excecoes': excecoes,
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

    # Validação de permissão
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
