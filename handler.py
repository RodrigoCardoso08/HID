import json
import os
from twilio.rest import Client
from utils.db import get_connection

SENSOR_LIMITS = {
    'temperature': {'max': 30.0, 'min': 15.0},
    'humidity': {'max': 70.0, 'min': 30.0},
    'light_intensity': {'max': 100, 'min': 0}
}

twilio_client = Client(
    os.environ['TWILIO_API_KEY'],
    os.environ['TWILIO_API_SECRET'],
    os.environ['TWILIO_ACCOUNT_SID']
)

def store_sensor_data(event, context):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        body = json.loads(event['body'])
        sensor_mapping = {
            1: {'field': 'light_intensity', 'name': 'sensor1'},
            2: {'field': 'humidity', 'name': 'sensor2'},
            3: {'field': 'temperature', 'name': 'sensor3'}
        }
        results = {}
        insert_query = """
            INSERT INTO sensor_data (sensor_id, timestamp, temperature, humidity, light_intensity, status)
            VALUES (%s, CURRENT_TIMESTAMP, %s, %s, %s, %s)
            RETURNING id;
        """
        for sensor_id, sensor_info in sensor_mapping.items():
            sensor_key = sensor_info['name']
            if sensor_key in body:
                sensor_data = body[sensor_key]                
                temperature = None
                humidity = None
                light_intensity = None
                sensor_value = sensor_data.get(sensor_info['field'])
                if sensor_value is not None:
                    check_limits(sensor_key, sensor_info['field'], sensor_value)
                if sensor_info['field'] == 'temperature':
                    temperature = sensor_value
                elif sensor_info['field'] == 'humidity':
                    humidity = sensor_value
                elif sensor_info['field'] == 'light_intensity':
                    light_intensity = sensor_value
                cursor.execute(insert_query, (
                    sensor_id,
                    temperature,
                    humidity,
                    light_intensity,
                    sensor_data.get('status', 'active')
                ))
                results[sensor_key] = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Dados dos sensores armazenados com sucesso",
                "results": results
            })
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Erro ao processar dados dos sensores",
                "error": str(e)
            })
        }
    

def send_alert(sensor_name, measurement_type, value, limit_type, limit_value):
    try:
        message = (
            f"ALERTA: Sensor {sensor_name} registrou {measurement_type} de {value}, "
            f"{limit_type} o limite de {limit_value}"
        )
        twilio_client.messages.create(
            body=message,
            from_='whatsapp:' + os.environ['TWILIO_WHATSAPP_SENDER'],
            messaging_service_sid=os.environ['TWILIO_MESSAGING_SERVICE_SID'],
            to='whatsapp:' + os.environ['ALERT_RECIPIENT_NUMBER']
        )
    except Exception as e:
        print(f"Erro ao enviar alerta: {str(e)}")


def check_limits(sensor_name, measurement_type, value):
    if measurement_type not in SENSOR_LIMITS:
        return
    limits = SENSOR_LIMITS[measurement_type]
    if value > limits['max']:
        send_sms_alert(sensor_name, measurement_type, value, "acima", limits['max'])
    elif value < limits['min']:
        send_sms_alert(sensor_name, measurement_type, value, "abaixo", limits['min'])


def send_sms_alert(sensor_name, measurement_type, value, limit_type, limit_value):
    try:
        message = (
            f"ALERTA: Sensor {sensor_name} registrou {measurement_type} de {value}, "
            f"{limit_type} o limite de {limit_value}"
        )
        message = "EI CURIOSOOOOOOOOOOOOOOOOOOO VAI TOMAR NO CU!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        numbers = ["+5521969156390", "+5512982823336", "+5519994473095", "+5518981294701"]
        for number in numbers:
            twilio_client.messages.create(
                body=message,
                to=number,
                messaging_service_sid=os.environ['TWILIO_SMS_SERVICE_SID']
            )
    except Exception as e:
        print(f"Erro ao enviar SMS: {str(e)}")