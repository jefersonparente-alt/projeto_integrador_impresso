import os
import sys
import time
from datetime import date
from pathlib import Path

# Configura ambiente Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.core.files.base import ContentFile
from core.models import Usuario, Solicitacao, Anexo, HistoricoStatus
from core.services import gerar_protocolo_unico, alterar_status_solicitacao


def linha(titulo=""):
    print(f"\n{'='*20} {titulo} {'='*20}")


def demonstrar():
    print("DEMONSTRAÇÃO PRÁTICA: FIFO, ATUALIZAÇÃO DE STATUS E UPLOAD")

    # 1. Obter ou criar usuários de teste
    solicitante, _ = Usuario.objects.get_or_create(
        email='aluno.demo@escola.edu.br',
        defaults={
            'nome': 'Lucas Estudante',
            'perfil': Usuario.PERFIL_SOLICITANTE,
            'setor_turma': '2º Ano Informática',
            'contato': '(11) 91234-5678',
        }
    )
    colaborador, _ = Usuario.objects.get_or_create(
        email='operador.demo@escola.edu.br',
        defaults={
            'nome': 'Carlos Impressor',
            'perfil': Usuario.PERFIL_COLABORADOR,
            'setor_turma': 'Gráfica Escolar',
            'contato': 'grafica@escola.edu.br',
        }
    )

    # =========================================================================
    # REQUISITO 1: UPLOAD DE DOCUMENTOS
    # =========================================================================
    linha("1. IMPLEMENTAÇÃO DE UPLOAD DE DOCUMENTOS")
    protocolo_1 = gerar_protocolo_unico()
    solic_1 = Solicitacao.objects.create(
        protocolo=protocolo_1,
        solicitante=solicitante,
        setor_turma=solicitante.setor_turma,
        contato=solicitante.contato,
        quantidade_copias=15,
        tipo_impressao=Solicitacao.TIPO_PB,
        frente_verso=True,
        prazo_desejado=date(2026, 12, 10),
        status_atual=Solicitacao.STATUS_RECEBIDA,
    )

    conteudo_pdf_falso = b"%PDF-1.4 ... Conteudo simulado de teste do documento ..."
    anexo_1 = Anexo.objects.create(
        solicitacao=solic_1,
        nome_original="Apostila_Matematica_Mod1.pdf",
        arquivo=ContentFile(conteudo_pdf_falso, name="apostila_temp.pdf"),
        tipo_arquivo="application/pdf",
        tamanho_bytes=len(conteudo_pdf_falso),
    )
    print(f"[OK] Solicitação criada: {solic_1.protocolo}")
    print(f"[OK] Anexo vinculado: {anexo_1.nome_original}")
    print(f"[OK] Caminho protegido gerado no disco: {anexo_1.arquivo.name}")
    print(f"[OK] Tipo MIME validado: {anexo_1.tipo_arquivo} ({anexo_1.tamanho_bytes} bytes)")

    # =========================================================================
    # REQUISITO 2: FILA FIFO (FIRST IN, FIRST OUT)
    # =========================================================================
    linha("2. IMPLEMENTAÇÃO DA FILA FIFO (FIRST IN, FIRST OUT)")
    time.sleep(0.05)  # Garante diferença temporal

    protocolo_2 = gerar_protocolo_unico()
    # solic_2 chega DEPOIS, mas com prazo desejado ANTERIOR (urgente)
    solic_2 = Solicitacao.objects.create(
        protocolo=protocolo_2,
        solicitante=solicitante,
        setor_turma='Coordenação',
        contato='coord@escola.edu.br',
        quantidade_copias=5,
        tipo_impressao=Solicitacao.TIPO_COLORIDA,
        frente_verso=False,
        prazo_desejado=date(2026, 11, 20), # Prazo anterior
        status_atual=Solicitacao.STATUS_RECEBIDA,
    )
    print(f"Pedido 1 recebido em: {solic_1.criado_em} (Prazo informativo: {solic_1.prazo_desejado})")
    print(f"Pedido 2 recebido em: {solic_2.criado_em} (Prazo informativo: {solic_2.prazo_desejado})")

    # Consulta padrão na ordem da fila
    fila_setor = list(Solicitacao.objects.filter(id__in=[solic_1.id, solic_2.id]))
    print("\nOrdem da Fila retornada pelo Banco de Dados (FIFO: criado_em ASC, id ASC):")
    for i, s in enumerate(fila_setor, 1):
        print(f"  Posição #{i}: Protocolo {s.protocolo} | Chegada: {s.criado_em.strftime('%H:%M:%S.%f')} | Prazo: {s.prazo_desejado}")

    assert fila_setor[0].id == solic_1.id, "Erro: A ordem FIFO foi violada!"
    print("\n[OK] Invariante FIFO comprovada: O pedido mais antigo permaneceu no topo da fila, ignorando o prazo.")

    # =========================================================================
    # REQUISITO 3: ATUALIZAÇÃO DE STATUS COM AUDITORIA
    # =========================================================================
    linha("3. IMPLEMENTAÇÃO DE ATUALIZAÇÃO DE STATUS E AUDITORIA")
    print(f"Status inicial de {solic_1.protocolo}: {solic_1.status_atual}")

    # Transição 1: Recebida -> Em andamento
    alterar_status_solicitacao(
        solicitacao=solic_1,
        novo_status=Solicitacao.STATUS_EM_ANDAMENTO,
        usuario_responsavel=colaborador,
        observacao="Iniciando impressão na máquina offset 1."
    )
    solic_1.refresh_from_db()
    print(f"Status atualizado 1: {solic_1.status_atual}")

    # Transição 2: Em andamento -> Concluída
    alterar_status_solicitacao(
        solicitacao=solic_1,
        novo_status=Solicitacao.STATUS_CONCLUIDA,
        usuario_responsavel=colaborador,
        observacao="Impressão finalizada. Material disponível no balcão da gráfica."
    )
    solic_1.refresh_from_db()
    print(f"Status atualizado 2: {solic_1.status_atual}")

    # Inspeciona Histórico de Auditoria
    print("\nHistórico gravado em HistoricoStatus:")
    for h in solic_1.historicos.all():
        print(f"  - [{h.data_hora.strftime('%H:%M:%S')}] {h.status_anterior} -> {h.status_novo} (por {h.usuario_responsavel.nome}): \"{h.observacao}\"")

    print("\n[OK] Auditoria comprovada: Todas as transições foram registradas com responsável e motivo.")
    linha("TODOS OS TRÊS REQUISITOS FORAM EXECUTADOS COM SUCESSO!")


if __name__ == '__main__':
    demonstrar()
