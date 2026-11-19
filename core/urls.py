from django.urls import path
from . import views

urlpatterns = [
    # Autenticação e Cadastro
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('cadastro/', views.cadastro_view, name='cadastro'),

    # Consulta Rápida por Protocolo (Consulta de Solicitações)
    path('consulta/', views.consulta_publica_protocolo, name='consulta_protocolo'),

    # Área do Solicitante (Minhas Solicitações)
    path('', views.solicitante_home, name='solicitante_home'),
    path('minhas-solicitacoes/', views.solicitante_home, name='minhas_solicitacoes'),
    path('solicitacoes/nova/', views.nova_solicitacao, name='nova_solicitacao'),
    path('solicitacoes/<str:protocolo>/', views.detalhe_solicitacao, name='detalhe_solicitacao'),

    # Painel do Setor de Impressos e Atendimento
    path('setor/', views.painel_setor, name='painel_setor'),
    path('setor/atendimento/<str:protocolo>/', views.atendimento_solicitacao, name='atendimento_solicitacao'),

    # Gerenciamento Administrativo (Métricas, Relatórios e Usuários)
    path('gestao/', views.painel_administrativo, name='painel_administrativo'),
    path('gestao/usuarios/', views.gestao_usuarios, name='gestao_usuarios'),

    # Download seguro de anexos
    path('anexos/<int:anexo_id>/download/', views.download_anexo, name='download_anexo'),
]
