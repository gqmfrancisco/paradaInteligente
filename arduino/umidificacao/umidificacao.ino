#include "DHT.h"
#include <Servo.h>

#define PINO_DHT 2
#define TIPO_DHT DHT11
#define PINO_PIR 3
#define PINO_LED 8
#define PINO_SERVO 9

#define LIMITE_UMIDADE 75    // desliga o servo ACIMA deste valor
#define LIMITE_RELIGA 73     // religa somente com este valor ou menos
#define INTERVALO_SERVO 5000
#define TEMPO_MOVIMENTO 500
#define INTERVALO_DHT 2000

DHT dht(PINO_DHT, TIPO_DHT);
Servo motor;

float umidade = 0;

bool presenca = false;
bool ledLigado = false;
bool servoEmMovimento = false;
bool primeiroAcionamento = true;
bool leituraValida = false;
bool umidadeAlta = false;

// 0 = Automatico (PIR)
// 1 = TRUE
// 2 = FALSE
int modoPresenca = 0;

String comando = "";

unsigned long ultimaLeitura = 0;
unsigned long ultimoAcionamento = 0;
unsigned long inicioMovimento = 0;
unsigned long ultimoEnvio = 0;

void setup() {

  Serial.begin(9600);

  pinMode(PINO_PIR, INPUT);
  pinMode(PINO_LED, OUTPUT);
  pinMode(PINO_SERVO, OUTPUT);

  digitalWrite(PINO_LED, LOW);
  digitalWrite(PINO_SERVO, LOW);

  dht.begin();

  Serial.println("Sistema iniciado!");
}

// Recebe comandos da Raspberry
void receberComandos() {

  while (Serial.available() > 0) {

    char caractere = Serial.read();

    if (caractere == '\n') {

      comando.trim();

      if (comando == "AUTO") {
        modoPresenca = 0;
      }

      else if (comando == "TRUE") {
        modoPresenca = 1;
      }

      else if (comando == "FALSE") {
        modoPresenca = 2;
      }

      comando = "";

    } else if (caractere != '\r') {

      if (comando.length() < 20) {
        comando += caractere;
      }
    }
  }
}

void loop() {

  unsigned long agora = millis();

  receberComandos();

  // Verifica a presenca
  if (modoPresenca == 0) {
    presenca = digitalRead(PINO_PIR) == HIGH;
  }

  else if (modoPresenca == 1) {
    presenca = true;
  }

  else {
    presenca = false;
  }

  // LED depende exclusivamente da presenca
  ledLigado = presenca;

  digitalWrite(PINO_LED, presenca ? HIGH : LOW);

  // Leitura da umidade
  if (agora - ultimaLeitura >= INTERVALO_DHT) {

    ultimaLeitura = agora;

    float novaUmidade = dht.readHumidity();

    if (isnan(novaUmidade)) {

      leituraValida = false;

      Serial.println("Erro no DHT11!");

    } else {

      umidade = novaUmidade;
      leituraValida = true;

      // Folga entre desligar e religar
      if (umidade > LIMITE_UMIDADE) {
        umidadeAlta = true;
      } else if (umidade <= LIMITE_RELIGA) {
        umidadeAlta = false;
      }

      Serial.print("Umidade: ");
      Serial.print(umidade);
      Serial.println("%");
    }
  }

  // Servo depende da umidade e da presenca
  bool condicaoAtiva =
    leituraValida &&
    !umidadeAlta &&
    presenca;

  if (condicaoAtiva) {

    if (!motor.attached()) {
      motor.attach(PINO_SERVO);
    }

    // Aciona o servo a cada 5 segundos
    if (!servoEmMovimento &&
        (primeiroAcionamento ||
         agora - ultimoAcionamento >= INTERVALO_SERVO)) {

      motor.write(90);

      inicioMovimento = agora;
      ultimoAcionamento = agora;

      servoEmMovimento = true;
      primeiroAcionamento = false;
    }

    // Retorna o servo apos 500 ms
    if (servoEmMovimento &&
        agora - inicioMovimento >= TEMPO_MOVIMENTO) {

      motor.write(0);

      inicioMovimento = agora;   // marca o inicio do retorno
      servoEmMovimento = false;
    }

  } else {

    // Desativa o servo quando:
    // Umidade > 75% (religa com 73% ou menos)
    // Sem presenca
    // Erro no sensor

    if (motor.attached()) {

      if (servoEmMovimento) {

        // Manda voltar para 0 antes de desligar
        motor.write(0);

        inicioMovimento = agora;
        servoEmMovimento = false;
      }

      else if (agora - inicioMovimento >= TEMPO_MOVIMENTO) {

        motor.detach();
        digitalWrite(PINO_SERVO, LOW);
      }
    }

    primeiroAcionamento = true;
  }

  // Envia informacoes para a Raspberry
  if (agora - ultimoEnvio >= 250) {

    ultimoEnvio = agora;

    Serial.print("Presenca: ");
    Serial.println(presenca ? "SIM" : "NAO");

    Serial.print("LED: ");
    Serial.println(ledLigado ? "LIGADO" : "DESLIGADO");

    Serial.print("Motor: ");
    Serial.println(servoEmMovimento ? "ACIONADO" : "PARADO");

    Serial.print("Sensor: ");
    Serial.println(leituraValida ? "OK" : "ERRO");

    Serial.print("Modo: ");

    if (modoPresenca == 0) {
      Serial.println("AUTO");
    }

    else if (modoPresenca == 1) {
      Serial.println("TRUE");
    }

    else {
      Serial.println("FALSE");
    }
  }
}