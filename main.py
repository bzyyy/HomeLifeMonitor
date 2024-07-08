from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text
from google.cloud.sql.connector import Connector, IPTypes
from datetime import datetime
import traceback

app = Flask(__name__)

# Configuración de la base de datos
DB_USER = "user"
DB_PASS = "user"
DB_NAME = "db-homelifemonitor"
INSTANCE_CONNECTION_NAME = "ancient-house-323902:us-central1:sql-hlm" # Nombre de conexión de la instancia

connector = Connector()

def getconn() -> Connector:
    conn = connector.connect(
        INSTANCE_CONNECTION_NAME,
        "pymysql",
        user=DB_USER,
        password=DB_PASS,
        db=DB_NAME,
        ip_type=IPTypes.PUBLIC
    )
    return conn

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://'
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "creator": getconn
}
db = SQLAlchemy(app)

# Modelo para almacenar los datos del dispositivo
class DeviceData(db.Model):
    __tablename__ = 'DeviceData'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False)
    device = db.Column(db.String(80), nullable=False)
    power_value = db.Column(db.Float, nullable=False)
    current_value = db.Column(db.Float, nullable=False)
    apparent_power_value = db.Column(db.Float, nullable=False)
    voltage_value = db.Column(db.Float, nullable=False)
    power_factor_value = db.Column(db.Float, nullable=False)
    energy_value = db.Column(db.Float, nullable=False)

@app.route('/test', methods=['GET'])
def test_connection():
    try:
        db.session.execute(text('SELECT 1'))
        return jsonify({'message': 'Connection to the database was successful!'}), 200
    except Exception as e:
        return jsonify({'message': 'Connection to the database failed!', 'error': str(e)}), 500

@app.route('/postData', methods=['POST'])
def receive_data():
    if not request.is_json:
        return jsonify({'message': 'Request body must be JSON'}), 400
    
    content = request.get_json()
    
    try:
        timestamp = datetime.fromisoformat(content['timestamp'][:-1])
        device = content['device']
        data = content['data']
        
        new_device_data = DeviceData(
            timestamp=timestamp,
            device=device,
            power_value=data['power']['value'],
            power_unit=data['power']['unit'],
            power_accuracy=data['power']['accuracy'],
            current_value=data['current']['value'],
            current_unit=data['current']['unit'],
            current_accuracy=data['current']['accuracy'],
            apparent_power_value=data['apparent_power']['value'],
            apparent_power_unit=data['apparent_power']['unit'],
            apparent_power_accuracy=data['apparent_power']['accuracy'],
            voltage_value=data['voltage']['value'],
            voltage_unit=data['voltage']['unit'],
            voltage_accuracy=data['voltage']['accuracy'],
            power_factor_value=data['power_factor']['value'],
            power_factor_accuracy=data['power_factor']['accuracy'],
            energy_value=data['energy']['value'],
            energy_unit=data['energy']['unit'],
            energy_accuracy=data['energy']['accuracy']
        )
        
        db.session.add(new_device_data)
        db.session.commit()
        
        return jsonify({'message': 'Data saved successfully'}), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to save data', 'error': str(e)}), 500

@app.route('/getData', methods=['GET'])
def get_data():
    try:
        all_data = DeviceData.query.all()
        result = []
        for data in all_data:
            data_dict = {
                'id': data.id,
                'timestamp': data.timestamp.isoformat(),
                'device': data.device,
                'power_value': data.power_value,
                'power_unit': data.power_unit,
                'power_accuracy': data.power_accuracy,
                'current_value': data.current_value,
                'current_unit': data.current_unit,
                'current_accuracy': data.current_accuracy,
                'apparent_power_value': data.apparent_power_value,
                'apparent_power_unit': data.apparent_power_unit,
                'apparent_power_accuracy': data.apparent_power_accuracy,
                'voltage_value': data.voltage_value,
                'voltage_unit': data.voltage_unit,
                'voltage_accuracy': data.voltage_accuracy,
                'power_factor_value': data.power_factor_value,
                'power_factor_accuracy': data.power_factor_accuracy,
                'energy_value': data.energy_value,
                'energy_unit': data.energy_unit,
                'energy_accuracy': data.energy_accuracy
            }
            result.append(data_dict)

        return jsonify(result), 200
    except Exception as e:
        return jsonify({'message': 'Failed to retrieve data', 'error': str(e)}), 500


# Lista global para almacenar los datos recibidos temporalmente
received_data = {}
required_topics = [
    '/sonoff/power',
    '/sonoff/current',
    '/sonoff/apparent_power',
    '/sonoff/voltage',
    '/sonoff/power_factor',
    '/sonoff/energy'
]
@app.route('/testPost', methods=['POST'])
def consolidate_data():
    global received_data
    if not request.is_json:
        return jsonify({'message': 'Request body must be JSON'}), 400
    
    content = request.get_json()
    print(content)
    try:
        timestamp = datetime.fromtimestamp(content['timestamp'] / 1000)  
        topic = content['topic']
        payload = content['payload']
        
        # Convertir el payload a un número flotante, manejando el caso de 'na'
        if payload == 'na':
            data_value = 0.0
        else:
            data_value = float(payload)

        device = content.get('clientid', 'unknown_device')  # Ajuste para obtener el 'device' de 'clientid'

        if topic in required_topics:
            if device not in received_data:
                received_data[device] = {}
            received_data[device][topic] = data_value
            
            # Si se han recibido todos los datos necesarios, consolidarlos en uno solo
            if all(topic in received_data[device] for topic in required_topics):
                new_device_data = DeviceData(
                    timestamp=timestamp,
                    device=device,
                    power_value=received_data[device].get('/sonoff/power', 0),
                    current_value=received_data[device].get('/sonoff/current', 0),
                    apparent_power_value=received_data[device].get('/sonoff/apparent_power', 0),
                    voltage_value=received_data[device].get('/sonoff/voltage', 0),
                    power_factor_value=received_data[device].get('/sonoff/power_factor', 0),
                    energy_value=received_data[device].get('/sonoff/energy', 0)
                )
                print(received_data)
                db.session.add(new_device_data)
                db.session.commit()
                received_data.pop(device)  # Limpiar los datos para el dispositivo

                return jsonify({'message': 'Data consolidated and saved successfully'}), 201
            else:
                return jsonify({'message': 'Data received, waiting for more data'}), 202
        else:
            return jsonify({'message': 'Unexpected topic'}), 400
        
    except Exception as e:
            db.session.rollback()
            print(f"Error: {str(e)}")
            traceback.print_exc()
            return jsonify({'message': 'Failed to save data', 'error': str(e)}), 500
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)