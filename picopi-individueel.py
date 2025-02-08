import time
import board
import wifi
import socketpool
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from digitalio import DigitalInOut, Direction, Pull

# --------------------------------------------------------------------------------
#                      Wi-Fi + MQTT Configuratie
# --------------------------------------------------------------------------------
SSID = "IoT"
PASSWORD = "IoTPassword"

# ThingSpeak MQTT-configuratie
MQTT_BROKER = "mqtt3.thingspeak.com"
MQTT_PORT = 1883
USERNAME = "MgQUDBofKSsIExEEEDYIKQI"
CLIENT_ID = "MgQUDBofKSsIExEEEDYIKQI"
PASSWORD_MQTT = "aC4fnRB3dYQLZupPBnUWkeDM"
CHANNEL_ID = "2801364"
WRITE_API_KEY = "JQ7V27F8P3ROXKPO"

# Veld om naar te publiceren (pas deze variabele aan als je een ander field wilt gebruiken)
THING_SPEAK_FIELD = 2  # Verander dit naar bijvoorbeeld 8 als je naar field 8 wilt sturen

# Het MQTT-topic voor publiceren
MQTT_TOPIC = f"channels/{CHANNEL_ID}/publish"

# --------------------------------------------------------------------------------
#                           Push-Button op GP12
# --------------------------------------------------------------------------------
button = DigitalInOut(board.GP12)
button.direction = Direction.INPUT
button.pull = Pull.DOWN

# --------------------------------------------------------------------------------
#                           Wi-Fi Connectie
# --------------------------------------------------------------------------------
def connect_wifi():
    try:
        print(f"Connecting to Wi-Fi: {SSID}")
        wifi.radio.connect(SSID, PASSWORD)
        print("Connected to Wi-Fi:", wifi.radio.ipv4_address)
    except Exception as e:
        print("Failed to connect to Wi-Fi:", e)
        while True:
            pass  # Stop als Wi-Fi faalt

# --------------------------------------------------------------------------------
#                           MQTT Setup & Functies
# --------------------------------------------------------------------------------
def on_connect(client, userdata, flags, rc):
    print("[MQTT] Connected to ThingSpeak!")

def on_disconnect(client, userdata, rc):
    print("[MQTT] Disconnected! Reconnecting...")
    time.sleep(5)
    connect_mqtt()

def connect_mqtt():
    try:
        print("[MQTT] Connecting...")
        mqtt_client.connect()
        print("[MQTT] Connected!")
    except Exception as e:
        print("[MQTT] Connection error:", e)
        time.sleep(5)
        connect_mqtt()

def publish_value(value):
    """
    Publiceert een waarde naar het geselecteerde field op ThingSpeak.
    """
    payload = f"api_key={WRITE_API_KEY}&field{THING_SPEAK_FIELD}={value}"
    print(f"[MQTT] Publishing: {payload}")
    try:
        mqtt_client.publish(MQTT_TOPIC, payload)
        print("[MQTT] Publish successful!")
    except Exception as e:
        print("[MQTT] Publish error:", e)
        mqtt_client.disconnect()
        time.sleep(5)
        connect_mqtt()

# --------------------------------------------------------------------------------
#                                Main Loop
# --------------------------------------------------------------------------------
def main():
    global mqtt_client

    # Wi-Fi connectie
    connect_wifi()

    # SocketPool voor MQTT
    pool = socketpool.SocketPool(wifi.radio)

    # MQTT-client configureren
    mqtt_client = MQTT.MQTT(
        broker=MQTT_BROKER,
        port=MQTT_PORT,
        username=USERNAME,
        password=PASSWORD_MQTT,
        client_id=CLIENT_ID,
        socket_pool=pool,
    )
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    connect_mqtt()

    # Startwaarde voor ThingSpeak
    current_value = 90

    # Variabelen voor knoppensysteem
    last_button_state = False
    press_start_time = 0.0
    HOLD_TIME = 2.0  # 2 seconden voor lang indrukken

    while True:
        try:
            # Belangrijk: laat de MQTT-client zijn achtergrondtaken afhandelen.
            # Zonder deze regel kunnen keep-alive berichten en callbacks blijven hangen.
            mqtt_client.loop()

            # Lees de huidige status van de knop
            current_button_state = button.value

            # RISING EDGE (knop wordt ingedrukt)
            if current_button_state and not last_button_state:
                press_start_time = time.monotonic()
                print("Button pressed - detecting short/long press")

            # FALLING EDGE (knop wordt losgelaten)
            if not current_button_state and last_button_state:
                press_duration = time.monotonic() - press_start_time

                if press_duration >= HOLD_TIME:
                    current_value -= 10
                    print(f"Long press ({press_duration:.2f}s) - Decreasing value by 10.")
                else:
                    current_value += 10
                    print(f"Short press ({press_duration:.2f}s) - Increasing value by 10.")

                print(f"New value = {current_value}")
                publish_value(current_value)  # Publiceer direct de nieuwe waarde

            last_button_state = current_button_state

        except Exception as e:
            print("Error in main loop:", e)

        time.sleep(0.1)  # Debounce en CPU-belasting verminderen

# --------------------------------------------------------------------------------
# Programma starten
# --------------------------------------------------------------------------------
if __name__ == "__main__":
    main()
