import serial
import time
import datetime
import requests
import json

beginMarker = '<'
endMarker = '>'
now = datetime.datetime.now()
nomeArquivo = now.strftime("%Y-%m-%d_%H-%M-%S") +".txt"

API_URL = "https://1yslj5075g.execute-api.us-east-1.amazonaws.com/dev/store-sensor-data"

def readArduino():
    global endMarker, beginMarker
    keyChars = "<>"
    message = ''
    while (arduino.inWaiting() > 0):
        message += arduino.readline(1).decode()
    if (beginMarker in message and endMarker in message): 
        for character in keyChars:
            message = message.replace(character, "")
        arquivo.write(message)
        try:
            valores = message.strip().split(';')[:3]
            light_intensity, humidity, temperature = map(float, valores)
            payload = {
                "sensor1": { "light_intensity": light_intensity },
                "sensor2": { "humidity": humidity },
                "sensor3": { "temperature": temperature }
            }
            response = requests.post(API_URL, json=payload)
            if response.status_code == 200:
                print(f"Dados enviados com sucesso: {response.json()}")
            else:
                print(f"Erro ao enviar dados: {response.status_code}")
        except Exception as e:
            print(f"Erro ao processar ou enviar dados: {str(e)}")
        arduino.reset_input_buffer()


arduino = serial.Serial(
    port='COM7',
    baudrate=9600,
)

print(nomeArquivo)
print("Padr├úo: <Lux;Humidity;Temperature(C);Temperature(F);HeatIndex(C);HeatIndex(F)>")

try:
    while True:
        arquivo = open(nomeArquivo, "a+")
        time.sleep(2)
        readArduino()
        arquivo.close()
except KeyboardInterrupt:
    print("\nPrograma finalizado pelo usu├írio")
except Exception as e:
    print(f"\nErro: {str(e)}")
finally:
    if 'arquivo' in locals():
        arquivo.close()
    if 'arduino' in locals():
        arduino.close()
