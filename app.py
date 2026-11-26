
from flask import Flask, jsonify, render_template, request
import serial
import threading
import time

from historico import (
    inicializar_banco,
    salvar_leitura,
    obter_historico
)

app = Flask(__name__)

PORTA = "/dev/ttyACM0"
BAUDRATE = 9600
LIMITE_UMIDADE = 75

arduino = None

lock = threading.Lock()
lock_serial = threading.Lock()

dados = {
    "umidade": None,
    "presenca": "AGUARDANDO",
    "led": "AGUARDANDO",
    "motor": "AGUARDANDO",
    "sensor": "AGUARDANDO",
    "status": "Aguardando leitura",
    "modo": "AGUARDANDO",
    "limite": LIMITE_UMIDADE
}


# Limpa os dados em caso de desconexão
def desconectar():

    with lock:
        dados.update({
            "umidade": None,
            "presenca": "DESCONHECIDO",
            "led": "DESCONHECIDO",
            "motor": "DESCONHECIDO",
            "sensor": "DESCONHECIDO",
            "modo": "DESCONHECIDO",
            "status": "Desconectado"
        })


# Comunicação com o Arduino
def ler_arduino():

    global arduino

    while True:

        try:

            with serial.Serial(
                PORTA,
                BAUDRATE,
                timeout=2,
                write_timeout=2
            ) as conexao:

                time.sleep(2)

                with lock_serial:
                    arduino = conexao

                print("Arduino conectado!")

                ultima_mensagem = time.monotonic()

                while True:

                    mensagem = conexao.readline().decode(
                        "utf-8",
                        errors="ignore"
                    ).strip()

                    if not mensagem:

                        if time.monotonic() - ultima_mensagem > 6:
                            raise ConnectionError(
                                "Arduino sem resposta"
                            )

                        continue

                    ultima_mensagem = time.monotonic()

                    if mensagem.startswith("Umidade:"):

                        try:

                            valor = mensagem.split(":", 1)[1]

                            umidade = float(
                                valor.replace("%", "").strip()
                            )

                            if not 0 <= umidade <= 100:
                                continue

                        except ValueError:
                            continue

                        with lock:

                            dados["umidade"] = umidade
                            dados["status"] = "Conectado"
                            dados["sensor"] = "OK"

                        try:
                            salvar_leitura(umidade)

                        except Exception as erro:
                            print("Erro no banco:", erro)

                        print(f"Umidade: {umidade}%")

                    elif mensagem.startswith("Presenca:"):

                        with lock:

                            dados["presenca"] = mensagem.split(
                                ":", 1
                            )[1].strip()

                            dados["status"] = "Conectado"

                    elif mensagem.startswith("LED:"):

                        with lock:

                            dados["led"] = mensagem.split(
                                ":", 1
                            )[1].strip()

                    elif mensagem.startswith("Motor:"):

                        with lock:

                            dados["motor"] = mensagem.split(
                                ":", 1
                            )[1].strip()

                    elif mensagem.startswith("Sensor:"):

                        with lock:

                            dados["sensor"] = mensagem.split(
                                ":", 1
                            )[1].strip()

                            if dados["sensor"] == "ERRO":
                                dados["umidade"] = None

                    elif mensagem.startswith("Modo:"):

                        with lock:

                            dados["modo"] = mensagem.split(
                                ":", 1
                            )[1].strip()

                    elif mensagem == "Erro no DHT11!":

                        with lock:

                            dados["sensor"] = "ERRO"
                            dados["umidade"] = None

        except Exception as erro:

            with lock_serial:
                arduino = None

            desconectar()

            print("Erro na comunicacao:", erro)
            print("Tentando reconectar...")

            time.sleep(5)


# Página principal
@app.route("/")
def index():

    return render_template("index.html")


# Dados atuais
@app.route("/dados")
def obter_dados():

    with lock:
        return jsonify(dados.copy())


# Histórico de umidade
@app.route("/historico")
def historico():

    return jsonify(obter_historico())


# Alteração do modo de presença
@app.route("/presenca", methods=["POST"])
def alterar_presenca():

    conteudo = request.get_json(silent=True)

    if not isinstance(conteudo, dict):
        return jsonify({
            "sucesso": False,
            "mensagem": "Dados invalidos"
        }), 400

    modo = conteudo.get("modo")

    if modo not in ["AUTO", "TRUE", "FALSE"]:

        return jsonify({
            "sucesso": False,
            "mensagem": "Modo invalido"
        }), 400

    try:

        with lock_serial:

            if arduino is None or not arduino.is_open:

                return jsonify({
                    "sucesso": False,
                    "mensagem": "Arduino desconectado"
                }), 503

            arduino.write(
                (modo + "\n").encode("utf-8")
            )

            arduino.flush()

        print("Comando enviado:", modo)

        return jsonify({
            "sucesso": True,
            "mensagem": "Comando enviado",
            "modo_solicitado": modo
        })

    except Exception as erro:

        return jsonify({
            "sucesso": False,
            "mensagem": str(erro)
        }), 503


# Inicialização do sistema
if __name__ == "__main__":

    inicializar_banco()

    threading.Thread(
        target=ler_arduino,
        daemon=True
    ).start()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
