# Descrição do Projeto: Debate Timer Inteligente


Este projeto é, na essência, um sistema de monitoramento e gerenciamento de um debate que une um painel web centralizado (Django) com um display de hardware em tempo real (Arduino/ESP32).

O objetivo principal era superar a limitação de timers de debate comuns que não registram o tempo de forma persistente ou centralizada.

Objetivo Principal
O objetivo principal do nosso projeto é criar uma solução de controle centralizada e persistente para debates, onde:

O Estado é Único: O estado exato do debate (quem está falando, quanto tempo usou, se está pausado) é armazenado em um único lugar: o Banco de Dados (Django).

Controle Flexível: O operador pode iniciar, pausar e selecionar o orador através de uma Interface Web (HTML) ou de Botões Físicos (Arduino).

Feedback em Tempo Real: O hardware (Arduino com display e LEDs) exibe o status atualizado em tempo real, lendo o estado do banco de dados.

Em resumo, queríamos construir um timer que não perde o progresso e pode ser gerenciado de qualquer lugar (web) ou diretamente (botões).

Documentos Criados para o Projeto
Para alcançar esse objetivo, tivemos que construir um conjunto de documentos (arquivos de código) que se comunicam através de um protocolo comum.

1. O Cérebro (Django - Python)
O Django é a parte de backend que hospeda os dados e a lógica de negócios.

models.py: Define a estrutura do banco de dados: Debate, Participante e Tempo.

Conceito: Persistência de Dados. Garante que o estado (ex: tempo usado) sobreviva mesmo que o sistema seja desligado.

views.py: Contém a lógica para as páginas HTML e, crucialmente, as APIs que o Serial Bridge usa.

Conceito: Lógica de Negócios e API Gateway. Traduz requisições HTTP em ações no banco de dados (ex: api_atualizar_tempo recebe o tempo e o salva).

urls.py: Mapeia as URLs (endereços web) para as funções em views.py.

Conceito: Roteamento. Define os "caminhos" (rotas) que ativam as APIs (Ex: /api/status_debate/1/).

Templates HTML: Os arquivos monitorar_debate.html, criar_debate.html, etc.

Conceito: Interface de Operação (I.U.). Permite que o usuário crie, configure e inicie o debate via web.

2. A Ponte (Serial Bridge - Python)
O serial_bridge.py é o script intermediário que faz a tradução entre as duas linguagens.

serial_bridge.py: Roda continuamente, fazendo um loop entre a consulta à API do Django (GET) e a leitura/escrita na porta Serial.

Conceito: Parsing e Sincronização Bidirecional. Traduz JSON (web) para String Serial (hardware) e vice-versa.

3. O Terminal (Arduino/ESP32 - C++)
O código do microcontrolador é responsável por receber o estado e gerenciar a interface física.

arduino_timer.ino: Contém as funções de parsing da Serial, lógica de timer local, e controle do display, LEDs e botões.

Conceito: Interface de Hardware e I/O. Recebe a string STATUS|..., atualiza a tela e envia comandos de volta (CMD|PAUSE, TIME:P...).

Funções de Display: desenhaTelaInicial(), desenhaTelaParticipante(), etc.

Conceito: Feedback em Tempo Real. Exibe os dados dinâmicos (nomes, grupos, tempos) lidos do Django, garantindo que o hardware reflita o estado central.
