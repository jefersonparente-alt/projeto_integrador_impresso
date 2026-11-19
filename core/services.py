import datetime
import random
import string
from django.db import transaction
from django.utils import timezone
from .models import Solicitacao, HistoricoStatus, Usuario, ExcecaoPrioridade


def gerar_protocolo_unico() -> str:
    """
    Gera um protocolo único legível no formato IMP-YYYYMM-XXXX (ex: IMP-202611-7F2A).
    Garante ausência de colisões no banco de dados.
    """
    now = timezone.now()
    ano_mes = now.strftime('%Y%m')

    while True:
        sufixo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        protocolo = f"IMP-{ano_mes}-{sufixo}"
        if not Solicitacao.objects.filter(protocolo=protocolo).exists():
            return protocolo


@transaction.atomic
def alterar_status_solicitacao(
    solicitacao: Solicitacao,
    novo_status: str,
    usuario_responsavel: Usuario,
    observacao: str = "",
) -> Solicitacao:
    """
    Atualiza o status da solicitação de forma atômica,
    gravando obrigatoriamente a auditoria em HistoricoStatus.
    """
    status_anterior = solicitacao.status_atual
    if status_anterior == novo_status and not observacao:
        return solicitacao

    solicitacao.status_atual = novo_status
    solicitacao.save(update_fields=['status_atual'])

    HistoricoStatus.objects.create(
        solicitacao=solicitacao,
        usuario_responsavel=usuario_responsavel,
        status_anterior=status_anterior,
        status_novo=novo_status,
        observacao=observacao,
    )
    return solicitacao


@transaction.atomic
def registrar_excecao_prioridade(
    solicitacao: Solicitacao,
    autorizado_por: Usuario,
    justificativa: str,
) -> ExcecaoPrioridade:
    """
    Registra formalmente uma exceção de prioridade com justificativa técnica/administrativa.
    """
    if not justificativa or not justificativa.strip():
        raise ValueError("A justificativa para quebra de prioridade é obrigatória.")

    return ExcecaoPrioridade.objects.create(
        solicitacao=solicitacao,
        autorizado_por=autorizado_por,
        justificativa=justificativa.strip(),
    )
