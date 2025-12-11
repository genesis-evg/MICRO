#include <FastLED.h>
#include <OneButton.h>
#include <GxEPD2_BW.h>
#include <U8g2_for_Adafruit_GFX.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

#define NUM_LEDS 13
#define PINO_LED 14
#define MAX_PARTICIPANTES 8
#define TEMPO_TOTAL 10000

GxEPD2_BW<GxEPD2_420_GDEY042T81, GxEPD2_420_GDEY042T81::HEIGHT> tela(GxEPD2_420_GDEY042T81(5, 17, 16, 4));

U8G2_FOR_ADAFRUIT_GFX fontes;

CRGB leds[NUM_LEDS];
OneButton Botao_Pause(35, true, true);
OneButton Botao_Navegar_Proximo(36, true, true);
OneButton Botao_Navegar_Anterior(37, true, true);
OneButton Botao_Selecionar(38, true, true);
OneButton Botao_Mudar_Tela(39, true, true);

int buzzer = 40;
volatile int estadoTela = 0;
int tempoDebate = 0;
volatile bool atualizarTelaAgora = false;
unsigned long ultimoUpdate = 0;


struct Participante {
  unsigned long tempo_usado = 0;
  unsigned long ultimoTempo = 0;
  unsigned long ultimoBeep = 0;
  unsigned long beepFinal = 0;
  int beepCont = 0;
  int ultimos_leds_acesos = 0;
  int restante = TEMPO_TOTAL;
  bool falando = true;
  bool terminou = false;
  bool condicao20s = true;
  bool estadoLed = false;
  bool pausado = true;
};




Participante p[MAX_PARTICIPANTES];
int participanteAtual = 0;
int numParticipantes = 6;
int participanteSelecionado = 0;
unsigned long instanteAnteriorLed = 0;
unsigned long agora;
bool direcao = true;
unsigned long restante;


TaskHandle_t TaskDisplayHandle;

void TaskDisplay(void *pvParameters);

void setup() {
  Serial.begin(115200);
  Serial.println("começou");

  tela.init();
  tela.setFullWindow();
  fontes.begin(tela);
  fontes.setForegroundColor(GxEPD_BLACK);
  fontes.setBackgroundColor(GxEPD_WHITE);

  tela.fillScreen(GxEPD_WHITE);
  desenhaTelaInicial();
  tela.display(false);

  FastLED.addLeds<WS2812, PINO_LED, GRB>(leds, NUM_LEDS);
  FastLED.clear();
  FastLED.show();
  FastLED.setBrightness(50);
  pinMode(buzzer, OUTPUT);

  Botao_Pause.attachClick(pausar_tempo);
  Botao_Pause.attachLongPressStart(reiniciar_tempo);
  Botao_Navegar_Proximo.attachClick(navegar_participante_proximo);
  Botao_Navegar_Anterior.attachClick(navegar_participante_anterior);
  Botao_Selecionar.attachClick(selecionar_participante);
  Botao_Mudar_Tela.attachLongPressStart(mudarTela);

  xTaskCreatePinnedToCore(
    TaskDisplay,
    "TaskDisplay",
    12000,
    NULL,
    1,
    &TaskDisplayHandle,
    0);
}



//Leds
void atualizarFita(Participante &p) {
  if (p.tempo_usado > TEMPO_TOTAL) 
  {
    p.tempo_usado = TEMPO_TOTAL;
  }
  int leds_acesos = map(p.tempo_usado, 0, TEMPO_TOTAL, 0, NUM_LEDS);



  if (leds_acesos != p.ultimos_leds_acesos) {
    for (int i = p.ultimos_leds_acesos; i < leds_acesos; i++) {
      leds[i] = CRGB::Green;
    }
    FastLED.show();
    p.ultimos_leds_acesos = leds_acesos;
  }
}



void piscarVermelho(bool &estadoLed) {
  if (estadoLed) {
    FastLED.clear();
  }

  else {
    fill_solid(leds, NUM_LEDS, CRGB::Red);
  }

  FastLED.show();
  estadoLed = !estadoLed;
}




// Buzzer
void alerta20s() {
  tone(buzzer, 1000, 500);
}


void alerta5s(int segundosPassados) {
  int freq = 1000 + segundosPassados * 200;
  tone(buzzer, freq, 300);
}


void alertaFim() {
  tone(buzzer, 1000, 300);
}




// Botões
void reiniciar_tempo() 
{
  tempoDebate -= p[participanteAtual].tempo_usado;
  p[participanteAtual].tempo_usado = 0;
  p[participanteAtual].beepCont = 0;
  p[participanteAtual].condicao20s = true;
  p[participanteAtual].ultimos_leds_acesos = 0;
  p[participanteAtual].estadoLed = false;
  p[participanteAtual].pausado = true;
  p[participanteAtual].falando = true;
  p[participanteAtual].terminou = false;
  FastLED.clear();
  FastLED.show();
  atualizarTelaAgora = true;
}


void pausar_tempo() {
  if (p[participanteAtual].pausado) {
    p[participanteAtual].ultimoTempo = agora;
  }

  p[participanteAtual].pausado = !p[participanteAtual].pausado;
}



void navegar_participante_aux(bool direcao) {
  if (!p[participanteAtual].pausado) {
    return;
  }

  if (direcao == true) {
    participanteSelecionado++;

    if (participanteSelecionado >= numParticipantes) {
      participanteSelecionado = 0;
    }
  }

  else {
    participanteSelecionado--;

    if (participanteSelecionado < 0) {
      participanteSelecionado = numParticipantes - 1;
    }
  }

  FastLED.clear();

  if (p[participanteSelecionado].terminou) {
    fill_solid(leds, NUM_LEDS, CRGB::Red);
  }

  else {
    for (int i = 0; i < p[participanteSelecionado].ultimos_leds_acesos; i++) {
      leds[i] = CRGB::Green;
    }
  }

  FastLED.show();
  atualizarTelaAgora = true;
}




void navegar_participante_proximo() {
  navegar_participante_aux(true);
}




void navegar_participante_anterior() {
  navegar_participante_aux(false);
}




void selecionar_participante() {
  p[participanteAtual].falando = false;

  participanteAtual = participanteSelecionado;

  p[participanteAtual].falando = true;
  p[participanteAtual].pausado = true;

  p[participanteAtual].ultimoTempo = millis();

  FastLED.clear();

  if (p[participanteAtual].terminou) {
    fill_solid(leds, NUM_LEDS, CRGB::Red);
  } else {
    for (int i = 0; i < p[participanteAtual].ultimos_leds_acesos; i++) {
      leds[i] = CRGB::Green;
    }
  }

  FastLED.show();
  tone(buzzer, 1000, 300);
  atualizarTelaAgora = true;
}


void mudarTela() {
  estadoTela++;

  if (estadoTela > 2) {
    estadoTela = 0;
  }
  Serial.println("mudou tela");

  atualizarTelaAgora = true;
}


// Display

String formatarTempo(int restante) {  // restante = totalSeg

  restante = restante / 1000;

  if (restante < 0)
    restante = 0;
  int min = restante / 60;
  int seg = restante % 60;

  String sMin = String(min);
  String sSeg = String(seg);

  if (seg < 10) {
    sSeg = "0" + sSeg;
  }
  return sMin + ":" + sSeg;
}



void atualizaTela() {
  if (estadoTela == 0) desenhaTelaInicial();
  else if (estadoTela == 1) desenhaTelaParticipante();
  else if (estadoTela == 2) desenhaTelaFinal();

  tela.display(true);
}



void desenhaTelaInicial() {
  tela.fillScreen(GxEPD_WHITE);

  tela.drawRect(0, 105, 400, 300, GxEPD_BLACK);
  tela.drawLine(200, 105, 200, 300, GxEPD_BLACK);

  fontes.setFont(u8g2_font_ncenB18_tr);
  fontes.setCursor(0, 32);
  fontes.print("Bem vindo ao DEBATE");

  fontes.setFont(u8g2_font_ncenB18_tr);
  fontes.setCursor(20, 135);
  fontes.print("Grupo A");

  fontes.setFont(u8g2_font_ncenR14_tr);
  fontes.setCursor(25, 175);
  fontes.print("- Fulano 1");
  fontes.setCursor(25, 215);
  fontes.print("- Fulano 2");
  fontes.setCursor(25, 255);
  fontes.print("- Fulano 3");

  fontes.setFont(u8g2_font_ncenB18_tr);
  fontes.setCursor(220, 135);
  fontes.print("Grupo B");

  fontes.setFont(u8g2_font_ncenR14_tr);
  fontes.setCursor(225, 175);
  fontes.print("- Ciclano 1");
  fontes.setCursor(225, 215);
  fontes.print("- Ciclano 2");
  fontes.setCursor(225, 255);
  fontes.print("- Ciclano 3");
}



void desenhaTelaParticipante() {

  tela.fillScreen(GxEPD_WHITE);


  tela.drawRect(0, 5, 400, 300, GxEPD_BLACK);
  tela.drawLine(0, 250, 400, 250, GxEPD_BLACK);


  fontes.setFont(u8g2_font_ncenB18_tr);
  fontes.setCursor(20, 40);
  fontes.print("Fulano 1");
  fontes.setCursor(20, 120);
  fontes.print("Fulano 2");
  fontes.setCursor(20, 200);
  fontes.print("Fulano 3");

  fontes.setFont(u8g2_font_ncenB18_tr);
  fontes.setCursor(220, 40);
  fontes.print("Ciclano 1");
  fontes.setCursor(220, 120);
  fontes.print("Ciclano 2");
  fontes.setCursor(220, 200);
  fontes.print("Ciclano 3");

  for (int i = 0; i < 6; i++) {

    int x, y;

    if (i <= 2) {
      x = 20;
      y = 70 + (i * 80);
    } else {
      x = 220;
      y = 70 + ((i - 3) * 80);
    }

    fontes.setFont(u8g2_font_ncenR14_tr);
    fontes.setCursor(x, y);

    int restanteParticipante = TEMPO_TOTAL - p[i].tempo_usado;
    fontes.print("Tempo: " + formatarTempo(restanteParticipante));
  }


  fontes.setFont(u8g2_font_ncenB18_tr);
  fontes.setCursor(20, 290);
  fontes.print("Tempo total: " + formatarTempo(tempoDebate));


  int setaX = 0;
  int setaY = 0;

  if (participanteSelecionado <= 2) {
    setaX = 2;
    setaY = 40 + (participanteSelecionado * 80);
  } else {
    setaX = 202;
    setaY = 40 + ((participanteSelecionado - 3) * 80);
  }

  tela.fillTriangle(setaX, setaY - 18, setaX, setaY - 2, setaX + 10, setaY - 10, GxEPD_BLACK);
}


void desenhaTelaFinal() {
  tela.fillScreen(GxEPD_WHITE);

  tela.drawRect(0, 5, 400, 300, GxEPD_BLACK);
  tela.drawLine(0, 40, 400, 40, GxEPD_BLACK);

  fontes.setFont(u8g2_font_ncenB18_tr);
  fontes.setCursor(120, 30);
  fontes.print("Resultados: ");

  fontes.setFont(u8g2_font_ncenB14_tr);
  fontes.setCursor(20, 70);
  fontes.print("Fulano 1");
  fontes.setCursor(20, 150);
  fontes.print("Fulano 2");
  fontes.setCursor(20, 230);
  fontes.print("Fulano 3");

  fontes.setFont(u8g2_font_ncenB14_tr);
  fontes.setCursor(220, 70);
  fontes.print("Ciclano 1");
  fontes.setCursor(220, 150);
  fontes.print("Ciclano 2");
  fontes.setCursor(220, 230);
  fontes.print("Ciclano 3");

  for (int i = 0; i < 6; i++) {

    int x, y;

    if (i <= 2) {
      x = 20;
      y = 95 + (i * 80);
    } else {
      x = 220;
      y = 95 + ((i - 3) * 80);
    }

    fontes.setFont(u8g2_font_ncenR12_tr);
    fontes.setCursor(x, y);

    fontes.print("Tempo: " + formatarTempo(p[i].tempo_soma));
  }
}

// Taks

void TaskDisplay(void *pvParameters) {
  while (true) {
    if (atualizarTelaAgora == true) {
      atualizaTela();
      atualizarTelaAgora = false;
      taskYIELD();
    } else {
      vTaskDelay(pdMS_TO_TICKS(20));
    }
  }
}

void loop() 
{

  if(estadoTela == 0)
  {
    Botao_Mudar_Tela.tick();
  }

  else
  {
    Botao_Pause.tick();
    Botao_Navegar_Proximo.tick();
    Botao_Navegar_Anterior.tick();
    Botao_Selecionar.tick();
    Botao_Mudar_Tela.tick();
  }

  agora = millis();

  if (p[participanteAtual].falando && !p[participanteAtual].terminou && !p[participanteAtual].pausado) {

    unsigned long delta = agora - p[participanteAtual].ultimoTempo;
    p[participanteAtual].tempo_usado += delta;

    if (p[participanteAtual].beepCont > 0)
    {
      delta = 0;
    }
    tempoDebate += delta;

    p[participanteAtual].restante = TEMPO_TOTAL - p[participanteAtual].tempo_usado;

    if (estadoTela == 1 && (agora - ultimoUpdate >= 1000)) {
      if (atualizarTelaAgora == false) {
        atualizarTelaAgora = true;
        ultimoUpdate = agora;
      }
    }

    if (p[participanteAtual].restante <= 20000 && p[participanteAtual].condicao20s == true) {
      alerta20s();
      p[participanteAtual].condicao20s = false;
    }


    if (p[participanteAtual].restante <= 5000 && p[participanteAtual].tempo_usado < TEMPO_TOTAL) {
      int segundosPassados = (5000 - p[participanteAtual].restante) / 1000;
      if (agora - p[participanteAtual].ultimoBeep >= 1000) {
        alerta5s(segundosPassados);
        p[participanteAtual].ultimoBeep = agora;
      }
    }

    if (p[participanteAtual].tempo_usado >= TEMPO_TOTAL) {
      if (agora - p[participanteAtual].beepFinal >= 600 && p[participanteAtual].beepCont < 5) {
        noTone(buzzer);
        alertaFim();
        p[participanteAtual].beepFinal = agora;
        p[participanteAtual].beepCont++;
        piscarVermelho(p[participanteAtual].estadoLed);
      }


      if (p[participanteAtual].beepCont == 6) {
        FastLED.clear();
        FastLED.show();
        p[participanteAtual].terminou = true;
        p[participanteAtual].falando = false;
        vTaskDelay(pdMS_TO_TICKS(100));
        atualizarTelaAgora = true;
      }
    }
  }
  if (agora - instanteAnteriorLed >= 500)
  {
    atualizarFita(p[participanteAtual]);
    instanteAnteriorLed = agora;
  }
  p[participanteAtual].ultimoTempo = agora;
  vTaskDelay(pdMS_TO_TICKS(10));
}
