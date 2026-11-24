import serial
import time

PORTA = "/dev/ttyACM0"
BAUDRATE = 9600

def ler_arduino():
    arduino = serial.Serial(PORTA, BAUDRATE, timeout=2)
    time.sleep(2)

    print("Arduino conectado!")

    try:
        while True:
            mensagem = arduino.readline().decode(
                "utf-8", errors="ignore"
            ).strip()

            if mensagem:
                print(mensagem)

    finally:
        arduino.close()

if __name__ == "__main__":
    ler_arduino()