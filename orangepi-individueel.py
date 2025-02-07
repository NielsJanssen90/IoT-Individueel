import smbus2
import time
import requests
import paho.mqtt.client as mqtt

# Configuratie-instellingen
I2C_BUS = 0
GY30_ADDR = 0x23
BMP280_ADDR = 0x76

# Persoonlijke API-key en kanaalgegevens voor ThingSpeak
READ_API_KEY_2792381 = "IR3IZC3FWLKZUWHX"
THRESHOLD_CHANNEL_ID = 2801364
THRESHOLD_FIELD = 2

# MQTT-configuratie voor ThingSpeak
CLIENT_ID  = "HTslIhMYAjcdJAEhODYEBTc"
USERNAME   = "HTslIhMYAjcdJAEhODYEBTc"
PASSWORD   = "ftrgQbH4P9hzOPNc/uuscb2F"
CHANNEL_ID = "2801364"
THINGSPEAK_MQTT_BROKER = "mqtt3.thingspeak.com"
THINGSPEAK_MQTT_PORT   = 1883

# Pin-definities voor stappermotor (ULN2003) en RGB LED
IN1 = 10
IN2 = 11
IN3 = 12
IN4 = 14
RED_PIN = 6
GREEN_PIN = 13
BLUE_PIN = 9

# Temperatuurdrempels voor de LED-indicatie
COLD_THRESHOLD = 18.0
WARM_THRESHOLD = 24.0

# Stapreeks voor de stappermotor
step_sequence = [
    [1, 1, 0, 0],
    [0, 1, 1, 0],
    [0, 0, 1, 1],
    [1, 0, 0, 1],
]

def read_lux_goal_from_thingspeak():
    """
    Leest de laatst geposte lux-doelwaarde (field2) van het opgegeven kanaal via een HTTP GET.
    """
    url = f"https://api.thingspeak.com/channels/{THRESHOLD_CHANNEL_ID}/fields/{THRESHOLD_FIELD}/last.txt?api_key={READ_API_KEY_2792381}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return float(response.text.strip())
    except Exception as e:
        print(f"Fout bij het lezen van LUX_GOAL: {e}")
        return 100.0

def setup_gpio():
    """
    Initialiseert de GPIO-pinnen voor de stappermotor en RGB LED.
    """
    import wiringpi as wp
    wp.wiringPiSetup()

    # Configureer stappermotorpinnen als uitvoer en zet deze uit
    for pin in (IN1, IN2, IN3, IN4):
        wp.pinMode(pin, wp.OUTPUT)
        wp.digitalWrite(pin, wp.LOW)

    # Configureer RGB LED-pinnen en stel standaardkleur in (blauw)
    for pin in (RED_PIN, GREEN_PIN, BLUE_PIN):
        wp.pinMode(pin, wp.OUTPUT)
    wp.digitalWrite(RED_PIN, wp.LOW)
    wp.digitalWrite(GREEN_PIN, wp.LOW)
    wp.digitalWrite(BLUE_PIN, wp.HIGH)
    return wp

def set_led_color_by_temp(wp, temperature):
    """
    Past de kleur van de RGB LED aan op basis van de temperatuur.
    """
    if temperature < COLD_THRESHOLD:
        wp.digitalWrite(RED_PIN, wp.LOW)
        wp.digitalWrite(GREEN_PIN, wp.LOW)
        wp.digitalWrite(BLUE_PIN, wp.HIGH)
    elif COLD_THRESHOLD <= temperature <= WARM_THRESHOLD:
        wp.digitalWrite(RED_PIN, wp.LOW)
        wp.digitalWrite(GREEN_PIN, wp.HIGH)
        wp.digitalWrite(BLUE_PIN, wp.LOW)
    else:
        wp.digitalWrite(RED_PIN, wp.HIGH)
        wp.digitalWrite(GREEN_PIN, wp.LOW)
        wp.digitalWrite(BLUE_PIN, wp.LOW)

def step_motor(wp, direction, steps, delay=0.002):
    """
    Laat de stappermotor een aantal stappen zetten in de opgegeven richting ('open' of 'close').
    """
    sequence = step_sequence if direction == "open" else step_sequence[::-1]
    for _ in range(steps):
        for step in sequence:
            wp.digitalWrite(IN1, step[0])
            wp.digitalWrite(IN2, step[1])
            wp.digitalWrite(IN3, step[2])
            wp.digitalWrite(IN4, step[3])
            time.sleep(delay)
    for pin in (IN1, IN2, IN3, IN4):
        wp.digitalWrite(pin, wp.LOW)

def read_lux():
    """
    Leest de lux-waarde van de BH1750 (GY-30) sensor via I2C.
    """
    bus = smbus2.SMBus(I2C_BUS)
    bus.write_byte(GY30_ADDR, 0x10)  # Continue high-res mode
    time.sleep(0.2)
    data = bus.read_i2c_block_data(GY30_ADDR, 0x10, 2)
    raw_lux = (data[0] << 8) | data[1]
    return raw_lux / 1.2

def read_temp_and_pressure(bus):
    """
    Voert een forced-mode meting uit op de BMP280 en retourneert de temperatuur (°C) en druk (Pa).
    """
    bus.write_byte_data(BMP280_ADDR, 0xF4, 0x2F)
    time.sleep(0.5)
    data = bus.read_i2c_block_data(BMP280_ADDR, 0xF7, 6)
    raw_pressure = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
    raw_temp = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)

    calib = bus.read_i2c_block_data(BMP280_ADDR, 0x88, 24)
    dig_T1 = calib[1] << 8 | calib[0]
    dig_T2 = (calib[3] << 8 | calib[2]) - (65536 if (calib[3] << 8 | calib[2]) > 32767 else 0)
    dig_T3 = (calib[5] << 8 | calib[4]) - (65536 if (calib[5] << 8 | calib[4]) > 32767 else 0)
    dig_P1 = calib[7] << 8 | calib[6]
    dig_P2 = (calib[9] << 8 | calib[8]) - (65536 if (calib[9] << 8 | calib[8]) > 32767 else 0)
    dig_P3 = (calib[11] << 8 | calib[10]) - (65536 if (calib[11] << 8 | calib[10]) > 32767 else 0)
    dig_P4 = (calib[13] << 8 | calib[12]) - (65536 if (calib[13] << 8 | calib[12]) > 32767 else 0)
    dig_P5 = (calib[15] << 8 | calib[14]) - (65536 if (calib[15] << 8 | calib[14]) > 32767 else 0)
    dig_P6 = (calib[17] << 8 | calib[16]) - (65536 if (calib[17] << 8 | calib[16]) > 32767 else 0)
    dig_P7 = (calib[19] << 8 | calib[18]) - (65536 if (calib[19] << 8 | calib[18]) > 32767 else 0)
    dig_P8 = (calib[21] << 8 | calib[20]) - (65536 if (calib[21] << 8 | calib[20]) > 32767 else 0)
    dig_P9 = (calib[23] << 8 | calib[22]) - (65536 if (calib[23] << 8 | calib[22]) > 32767 else 0)

    var1 = (raw_temp / 16384.0 - dig_T1 / 1024.0) * dig_T2
    var2 = (raw_temp / 131072.0 - dig_T1 / 8192.0) ** 2 * dig_T3
    t_fine = var1 + var2
    temperature = t_fine / 5120.0

    var1_p = t_fine / 2.0 - 64000.0
    var2_p = ((var1_p * var1_p * dig_P6) / 32768.0 + var1_p * dig_P5 * 2.0) / 4.0 + dig_P4 * 65536.0
    var1_p = (dig_P3 * var1_p * var1_p / 524288.0 + dig_P2 * var1_p) / 524288.0
    var1_p = (1.0 + var1_p / 32768.0) * dig_P1
    if var1_p == 0:
        pressure = 0
    else:
        pressure = 1048576.0 - raw_pressure
        pressure = (pressure - var2_p / 4096.0) * 6250.0 / var1_p
        pressure += (dig_P9 * pressure * pressure / 2147483648.0 + pressure * dig_P8 / 32768.0 + dig_P7) / 16.0
    return temperature, pressure

def setup_mqtt_client():
    """
    Initialiseert en verbindt de MQTT-client voor ThingSpeak.
    """
    client = mqtt.Client(client_id=CLIENT_ID)
    client.username_pw_set(USERNAME, PASSWORD)
    client.connect(THINGSPEAK_MQTT_BROKER, THINGSPEAK_MQTT_PORT, 60)
    client.loop_start()
    return client

def publish_to_thingspeak_mqtt(client, lux, temp, pressure_hpa):
    """
    Publiceert lux, temperatuur en druk (in hPa) naar het ThingSpeak-kanaal via MQTT.
    """
    topic = f"channels/{CHANNEL_ID}/publish"
    payload = f"field1={lux}&field3={temp}&field4={pressure_hpa}"
    result = client.publish(topic, payload)
    if result.rc == 0:
        print(f"Gegevens gepubliceerd: lux={lux}, temp={temp}, pressure={pressure_hpa} hPa")
    else:
        print(f"Publicatie mislukt, code: {result.rc}")

def main():
    """
    Hoofdlus: leest sensorgegevens, past de LED-kleur aan, publiceert naar ThingSpeak
    en bestuurt de gordijnen op basis van de lux-waarde.
    """
    wp = setup_gpio()
    bus = smbus2.SMBus(I2C_BUS)
    mqtt_client = setup_mqtt_client()
    state = None  # Houd de huidige staat van de gordijnen bij
    last_update_time = time.time()
    update_interval = 20  # seconden

    try:
        while True:
            current_time = time.time()
            if current_time - last_update_time >= update_interval:
                last_update_time = current_time

                lux_goal = read_lux_goal_from_thingspeak()
                print(f"LUX_GOAL: {lux_goal}")

                lux = read_lux()
                temp, pressure = read_temp_and_pressure(bus)
                pressure_hpa = pressure / 100.0
                print(f"Lux: {lux:.1f}, Temp: {temp:.1f}°C, Pressure: {pressure_hpa:.2f} hPa")

                set_led_color_by_temp(wp, temp)
                publish_to_thingspeak_mqtt(mqtt_client, lux, temp, pressure_hpa)

                desired_state = "open" if lux > lux_goal else ("closed" if lux < lux_goal else state)
                if desired_state != state:
                    if desired_state == "open":
                        print("Gordijnen openen...")
                        step_motor(wp, "open", 512)
                    elif desired_state == "closed":
                        print("Gordijnen sluiten...")
                        step_motor(wp, "close", 512)
                    state = desired_state
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Programma gestopt.")
    finally:
        for pin in (RED_PIN, GREEN_PIN, BLUE_PIN):
            wp.digitalWrite(pin, wp.LOW)
        mqtt_client.loop_stop()
        mqtt_client.disconnect()

if __name__ == "__main__":
    main()
