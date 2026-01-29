from paho.mqtt import client as mqtt_client


broker = 'z1f4a3e9.ala.cn-hangzhou.emqxsl.cn'
port = 8883
topic = "topic/mqttx2py"
client_id = 'client/py0'
username = 'py_0'
password = '119514'


def connect_mqtt():
    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print("Connected successfully.")
        else:
            print(f"Failed to connect, reason code: {reason_code}")
    # Set Connecting Client ID
    client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2, client_id)
    # Set CA certificate
    client.tls_set(ca_certs='./emqxsl-ca.crt')
    client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client


def subscribe(client: mqtt_client):
    def on_message(client, userdata, msg):
        print(f"Received `{msg.payload.hex()}` from `{msg.topic}` topic")
        

    client.subscribe(topic=topic, qos=0)
    client.on_message = on_message


def run():
    client = connect_mqtt()
    subscribe(client)

    client.loop_forever()


if __name__ == '__main__':
    run()