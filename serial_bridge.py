import os
import django
import time
import serial
import requests
import json
from datetime import datetime


SERIAL_PORT = 'COM3'
BAUD_RATE = 115200
API_BASE_URL = 'http://127.0.0.1:8000/debates/api/'
DEBATE_ID_ALVO = 1 
CMD_READY = "BRIDGE_READY"



os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MonitorProjeto.settings')
django.setup() 
from debates.models import Participante, Debate, Tempo 


PARTICIPANTE_CACHE = {} 
CACHE_SINCRONIZADO = False



def enviar_comando_api(endpoint, payload=None):
   
    try:
        
        if payload is None:
             response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=5) 
        else:
             response = requests.post(f"{API_BASE_URL}{endpoint}", json=payload, timeout=5) 
        
        response.raise_for_status() 
        return response.json()
    except requests.exceptions.Timeout:
        print(f"ERRO: Tempo limite esgotado ao acessar {endpoint}.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"ERRO ao enviar API POST para {endpoint}: {e}")
        return None



def processar_dados_django(ser):
    
    global CACHE_SINCRONIZADO
    
    try:
        data = enviar_comando_api(f"status_debate/{DEBATE_ID_ALVO}/")
        if data is None:
            return

        ativo_id = data.get('participante_ativo_id') if data.get('participante_ativo_id') else 0
        status_texto = data.get('status')
        tempo_total_debate_s = data.get('tempo_total_segundos') 

       
        if not CACHE_SINCRONIZADO:
            participantes_db = Participante.objects.filter(debate_id=DEBATE_ID_ALVO).order_by('id')
            
            for p_db in participantes_db:
                PARTICIPANTE_CACHE[p_db.id] = {
                    'nome': p_db.participante_nome,
                    'grupo': p_db.grupo_nome
                }
            if PARTICIPANTE_CACHE:
                CACHE_SINCRONIZADO = True
                print("Cache de nomes e grupos sincronizado.")


        data_string = f"STATUS|{ativo_id}|{status_texto}" 
        data_string += f"|TEMPO_DEBATE_S:{tempo_total_debate_s}"
        
        total_acumulado_ms = 0

        for p_api_data in data.get('tempos', []):
            p_id = p_api_data['id']
            p_tempo_ms = p_api_data['tempo_ms']
            total_acumulado_ms += p_tempo_ms

            if p_id in PARTICIPANTE_CACHE:
                
                data_string += f"|PN{p_id}:{PARTICIPANTE_CACHE[p_id]['nome']}"
                data_string += f"|PG{p_id}:{PARTICIPANTE_CACHE[p_id]['grupo']}"
                
           
            data_string += f"|P{p_id}:{p_tempo_ms}" 

       
        tempo_restante_s = max(0, tempo_total_debate_s - (total_acumulado_ms // 1000))
        data_string += f"|TOTAL:{total_acumulado_ms}|LED:{tempo_restante_s}"
        
        ser.write(f"{data_string}\n".encode('ascii')) 


    except Exception as e:
        print(f"Erro no processamento de dados do Django: {e}")
        time.sleep(2)
        return


def processar_comandos_arduino(ser):
    
    if ser.in_waiting > 0:
      
        comando_raw = ser.readline().decode('ascii').strip() 

        if comando_raw.startswith("CMD|"):
            print(f"COMANDO RECEBIDO (Botão): {comando_raw}")
            
            partes = comando_raw.split('|')
            comando = partes[1]
            
            
            if comando == "PAUSE":
                enviar_comando_api('set_ativo', {"debate_id": DEBATE_ID_ALVO, "participante_id": 0})
                
            elif comando == "RESET":
                enviar_comando_api('reset_debate', {"debate_id": DEBATE_ID_ALVO})
                
            elif comando == "ENCERRAR_DEBATE":
                enviar_comando_api('encerrar_debate', {"debate_id": DEBATE_ID_ALVO})

            elif comando == "SET_ATIVO":
                try:
                    participante_id = int(partes[2]) 
                    enviar_comando_api('set_ativo', {"debate_id": DEBATE_ID_ALVO, "participante_id": participante_id})
                except (IndexError, ValueError):
                    print("Erro: Comando SET_ATIVO inválido.")


        elif comando_raw.startswith("TIME:P"):
            
            try:
                partes = comando_raw.split(':')
                participante_id = int(partes[1].replace('P', '')) 
                tempo_total_ms = int(partes[2]) 
                
                
                enviar_comando_api('atualizar_tempo', {
                    "participante_id": participante_id,
                    "tempo_total_ms": tempo_total_ms 
                })
            except Exception as e:
                print(f"Erro ao processar tempo do Arduino: {e}")
        

def iniciar_serial_bridge():
    
    try:
        
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) 
        print(f"Ponte Serial ativa em {SERIAL_PORT}. Iniciando sincronização imediata com Django...")
        
        
        while True:
            
            processar_comandos_arduino(ser)
            
            
            processar_dados_django(ser)
            
            time.sleep(0.5) 

    except serial.SerialException as e:
        print(f"ERRO FATAL SERIAL: {e}")
    except KeyboardInterrupt:
        print("\nComunicação interrompida pelo usuário.")
    except Exception as e:
        print(f"Erro inesperado no Bridge: {e}")
    finally: 
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Porta Serial encerrada.")

if __name__ == '__main__':
    iniciar_serial_bridge()