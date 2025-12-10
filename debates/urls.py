from django.urls import path
from . import views

urlpatterns = [
    # Rotas de Navegação e Formulário
    path('', views.criar_debate, name='criar_debate'),
    path('historico/', views.historico_debates, name='historico_debates'), 
    
    # Rotas de Gerenciamento e Monitoramento
    path('debate/<int:debate_id>/', views.editar_debate, name='editar_debate'),
    path('participante/<int:participante_id>/remover/', views.remover_participante, name='remover_participante'),
    path('debate/<int:debate_id>/monitorar/', views.monitorar_debate, name='monitorar_debate'),
    
    # ROTAS DE API (INTEGRAÇÃO SERIAL)
    path('api/status_debate/<int:debate_id>/', views.api_status_debate, name='api_status_debate'),
    path('api/atualizar_tempo/', views.api_atualizar_tempo, name='api_atualizar_tempo'),
    path('api/set_ativo/', views.api_set_ativo, name='api_set_ativo'),
    path('api/reset_debate/', views.api_reset_debate, name='api_reset_debate'),
    path('api/encerrar_debate/', views.api_encerrar_debate, name='api_encerrar_debate'),
    path('debate/<int:debate_id>/iniciar/', views.iniciar_debate_action, name='iniciar_debate_action'),
]