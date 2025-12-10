from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
import json 
from .forms import DebateForm, ParticipanteForm 
from .models import Debate, Participante, Tempo 


def iniciar_debate_action(request, debate_id):
    if request.method == 'POST':
        try:
            debate = get_object_or_404(Debate, pk=debate_id)
            
            if debate.status != 'CONFIGURADO':
                 # Se já estiver iniciado/pausado, redireciona sem fazer nada
                 return redirect('editar_debate', debate_id=debate.id)

            # Encontra o primeiro participante (igual à lógica da API)
            primeiro_participante = Participante.objects.filter(debate=debate).order_by('id').first()
            
            if not primeiro_participante:
                # Se não houver participantes, retorna para a tela de edição
                return redirect('editar_debate', debate_id=debate.id) 

            with transaction.atomic():
                debate.status = 'EM_ANDAMENTO'
                debate.participante_ativo = primeiro_participante
                debate.save()
            
            # Redireciona para a página de monitoramento ou gerenciamento
            return redirect('monitorar_debate', debate_id=debate.id) 
            
        except Debate.DoesNotExist:
            return redirect('historico_debates') # Retorna ao histórico se o debate não existir
        except Exception as e:
            # Em caso de erro grave, você pode registrar o erro e redirecionar
            print(f"Erro ao iniciar debate via formulário: {e}")
            return redirect('editar_debate', debate_id=debate_id)
            
    # Se for um GET na rota de ação, apenas redireciona para a página de edição
    return redirect('editar_debate', debate_id=debate_id)



def criar_debate(request):
    if request.method == 'POST':
        form = DebateForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                debate = form.save()
                
                def criar_participantes_e_tempos(grupo_nome, participantes_str):
                    nomes = [n.strip() for n in participantes_str.split(',') if n.strip()] 

                    for nome in nomes:
                        participante = Participante.objects.create(
                            debate=debate,
                            grupo_nome=grupo_nome,
                            participante_nome=nome
                        )
                        Tempo.objects.create(participante=participante, tempo_acumulado_ms=0)
                
                criar_participantes_e_tempos(
                    form.cleaned_data['grupo_a_nome'],
                    form.cleaned_data['participantes_a'] 
                )
                criar_participantes_e_tempos(
                    form.cleaned_data['grupo_b_nome'],
                    form.cleaned_data['participantes_b'] 
                )
            
            return redirect('historico_debates')
            
    else:
        form = DebateForm()

    return render(request, 'criar_debate.html', {'form': form}) 

def historico_debates(request):
    debates = Debate.objects.all().order_by('-data_criacao')
    return render(request, 'historico.html', {'debates': debates})

def editar_debate(request, debate_id):
    debate = get_object_or_404(Debate, pk=debate_id)
    participantes = Participante.objects.filter(debate=debate)

    if request.method == 'POST':
        form_adicionar = ParticipanteForm(request.POST)
        if form_adicionar.is_valid():
            with transaction.atomic():
                novo_participante = form_adicionar.save(commit=False)
                novo_participante.debate = debate
                novo_participante.save()
                Tempo.objects.create(participante=novo_participante)
            return redirect('editar_debate', debate_id=debate.id)
            
    form_adicionar = ParticipanteForm()

    context = {
        'debate': debate,
        'participantes': participantes,
        'form_adicionar': form_adicionar
    }
    return render(request, 'editar_debate.html', context)

def remover_participante(request, participante_id):
    participante = get_object_or_404(Participante, pk=participante_id)
    debate_id = participante.debate.id 
    participante.delete()
    return redirect('editar_debate', debate_id=debate_id)

def monitorar_debate(request, debate_id):
    debate = get_object_or_404(Debate, pk=debate_id)
    participantes_com_tempo = Participante.objects.filter(debate=debate).select_related('tempo').order_by('id')
    
    context = {
        'debate': debate,
        'participantes': participantes_com_tempo,
    }
    return render(request, 'monitorar_debate.html', context)



def api_status_debate(request, debate_id):

    try:
        debate = Debate.objects.get(pk=debate_id)
        participantes_data = Participante.objects.filter(debate=debate).select_related('tempo')

        tempos = []
        for p in participantes_data:
            tempos.append({
                'id': p.id,
                'tempo_ms': p.tempo.tempo_acumulado_ms if hasattr(p, 'tempo') else 0 
            })

        response_data = {
            'debate_id': debate.id,
            'status': debate.status,
            'participante_ativo_id': debate.participante_ativo_id,
            'tempo_total_segundos': debate.tempo_total_segundos,
            'tempos': tempos
        }

        return JsonResponse(response_data)
    except Debate.DoesNotExist:
        return JsonResponse({'status': 'erro', 'mensagem': 'Debate não encontrado.'}, status=404)

@csrf_exempt
def api_atualizar_tempo(request):
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            participante_id = data.get('participante_id')
            tempo_total_ms = data.get('tempo_total_ms')

            if not participante_id or not isinstance(tempo_total_ms, int):
                return JsonResponse({'status': 'erro', 'mensagem': 'Dados incompletos ou inválidos.'}, status=400)

            with transaction.atomic():
                tempo_obj = Tempo.objects.select_for_update().get(participante_id=participante_id)
                tempo_obj.tempo_acumulado_ms = tempo_total_ms
                tempo_obj.save()

            return JsonResponse({'status': 'sucesso'})
        except Tempo.DoesNotExist:
            return JsonResponse({'status': 'erro', 'mensagem': 'Participante não encontrado.'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'erro', 'mensagem': 'JSON inválido.'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=500)
    return JsonResponse({'status': 'erro', 'mensagem': 'Método não permitido.'}, status=405)

@csrf_exempt
def api_set_ativo(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            debate_id = data.get('debate_id')
            participante_id = data.get('participante_id')

            debate = Debate.objects.get(pk=debate_id)
            
            if not participante_id or participante_id == 0:
                debate.participante_ativo = None
                debate.status = 'PAUSADO'
            else:
                participante = Participante.objects.get(pk=participante_id)
                debate.participante_ativo = participante
                debate.status = 'EM_ANDAMENTO'
            
            debate.save()
            return JsonResponse({'status': 'sucesso'})
        except (Debate.DoesNotExist, Participante.DoesNotExist):
            return JsonResponse({'status': 'erro', 'mensagem': 'Debate ou Participante não encontrado.'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=500)
    return JsonResponse({'status': 'erro', 'mensagem': 'Método não permitido.'}, status=405)

@csrf_exempt
def api_reset_debate(request):
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            debate_id = data.get('debate_id')

            debate = Debate.objects.get(pk=debate_id)
            
            with transaction.atomic():
                Tempo.objects.filter(participante__debate=debate).update(tempo_acumulado_ms=0)
                
                debate.status = 'CONFIGURADO'
                debate.participante_ativo = None
                debate.save()

            return JsonResponse({'status': 'sucesso', 'mensagem': f'Debate {debate_id} resetado.'})
        except Debate.DoesNotExist:
            return JsonResponse({'status': 'erro', 'mensagem': 'Debate não encontrado.'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=500)
    return JsonResponse({'status': 'erro', 'mensagem': 'Método não permitido.'}, status=405)

@csrf_exempt
def api_encerrar_debate(request):
  
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            debate_id = data.get('debate_id')

            debate = Debate.objects.get(pk=debate_id)
            
            debate.status = 'ENCERRADO'
            debate.participante_ativo = None
            debate.save()

            return JsonResponse({'status': 'sucesso', 'mensagem': f'Debate {debate_id} encerrado.'})
        except Debate.DoesNotExist:
            return JsonResponse({'status': 'erro', 'mensagem': 'Debate não encontrado.'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=500)
    return JsonResponse({'status': 'erro', 'mensagem': 'Método não permitido.'}, status=405)

# debates/views.py

@csrf_exempt
def api_iniciar_debate(request, debate_id):
    
    if request.method == 'POST':
        try:
            debate = Debate.objects.get(pk=debate_id)
            
            # Encontra o primeiro participante do debate para começar
            primeiro_participante = Participante.objects.filter(debate=debate).order_by('id').first()
            
            if not primeiro_participante:
                return JsonResponse({'status': 'erro', 'mensagem': 'Nenhum participante encontrado.'}, status=400)

            with transaction.atomic():
                debate.status = 'EM_ANDAMENTO'
                debate.participante_ativo = primeiro_participante
                debate.save()

            return JsonResponse({
                'status': 'sucesso', 
                'participante_id': primeiro_participante.id,
                'mensagem': f'Debate ID {debate_id} iniciado com participante {primeiro_participante.id}.'
            })
            
        except Debate.DoesNotExist:
            return JsonResponse({'status': 'erro', 'mensagem': 'Debate não encontrado.'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=500)
    
    return JsonResponse({'status': 'erro', 'mensagem': 'Método não permitido.'}, status=405)