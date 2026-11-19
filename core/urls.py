from django.urls import path
from . import views

urlpatterns = [
    # Autenticação
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Área do Solicitante
    path('', views.solicitante_home, name='solicitante_home'),
    path('solicitacoes/nova/', views.nova_solicitacao, name='nova_solicitacao'),
    path('solicitacoes/<str:protocolo>/', views.detalhe_solicitacao, name='detalhe_solicitacao'),

    # Download seguro de anexos
    path('anexos/<int:anexo_id>/download/', views.download_anexo, name='download_anexo'),
]
