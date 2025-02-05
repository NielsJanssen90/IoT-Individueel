import smbus2
import time
import requests

# === Configuratie ===
I2C_BUS = 0  # Gebruik I2C-bus 0
GY30_ADDR = 0x23  # Adres van de GY-30 lichtsensor
BMP280_ADDR = 0x76  # Adres van de BMP280 temperatuursensor
THINGSPEAK_API_KEY = "JQ7V27F8P3ROXKPO"  # API-sleutel voor ThingSpeak
LUX_DOEL = 100  # Drempelwaarde voor lux (voorbeeldwaarde)

# ULN2003 Pin-definities voor de stappenmotor
IN1 = 10  # GPIO 112, wPi 10, Fysieke Pin 18
IN2 = 11  # GPIO 229, wPi 11, Fysieke Pin 19
IN3 = 12  # GPIO 230, wPi 12, Fysieke Pin 21
IN4 = 14  # GPIO 228, wPi 14, Fysieke Pin 23

# RGB LED en knop pin-definities
BUTTON_PIN = 2  # GPIO 118, wPi 2, Fysieke Pin 7
RED_PIN = 6     # GPIO 114, wPi 6, Fysieke Pin 12
GREEN_PIN = 9   # GPIO 111, wPi 9, Fysieke Pin 16
BLUE_PIN = 13   # GPIO 117, wPi 13, Fysieke Pin 22

# Stappenvolgorde voor de stappenmotor
stappen_volgorde = [
    [1, 0, 0, 0],  # Stap 1
    [0, 1, 0, 0],  # Stap 2
    [0, 0, 1, 0],  # Stap 3
    [0, 0, 0, 1],  # Stap 4
]

# === Functies ===

# Initialiseer GPIO-pinnen voor de ULN2003, RGB LED en knop
def setup_gpio():
    import wiringpi as wp
    wp.wiringPiSetup()

    # Stappenmotor-pinnen instellen als uitvoer
    for pin in [IN1, IN2, IN3, IN4]:
        wp.pinMode(pin, wp.OUTPUT)
        wp.digitalWrite(pin, wp.LOW)

    # RGB LED-pinnen instellen als uitvoer
    for pin in [RED_PIN, GREEN_PIN, BLUE_PIN]:
        wp.pinMode(pin, wp.OUTPUT)
        wp.digitalWrite(pin, wp.LOW)

    wp.digitalWrite(BLUE_PIN, wp.HIGH)  # Start met blauwe kleur

    # Knop-pin instellen als invoer met pull-down weerstand
    wp.pinMode(BUTTON_PIN, wp.INPUT)
    wp.pullUpDnControl(BUTTON_PIN, wp.PUD_DOWN)

    return wp

# RGB LED-besturing met de knop
def bedien_rgb_led(wp, huidige_kleur):
    kleuren = ["blauw", "groen", "rood"]
    volgende_kleur_index = (kleuren.index(huidige_kleur) + 1) % len(kleuren)
    volgende_kleur = kleuren[volgende_kleur_index]

    # Stel de LED-kleur in
    wp.digitalWrite(RED_PIN, wp.HIGH if volgende_kleur == "rood" else wp.LOW)
    wp.digitalWrite(GREEN_PIN, wp.HIGH if volgende_kleur == "groen" else wp.LOW)
    wp.digitalWrite(BLUE_PIN, wp.HIGH if volgende_kleur == "blauw" else wp.LOW)

    return volgende_kleur

# Besturing van de stappenmotor
def stuur_motor(wp, richting, stappen, vertraging=0.002):
    if richting not in ["open", "gesloten"]:
        raise ValueError("Ongeldige richting. Gebruik 'open' of 'gesloten'.")

    volgorde = stappen_volgorde if richting == "open" else stappen_volgorde[::-1]

    for _ in range(stappen):
        for stap in volgorde:
            wp.digitalWrite(IN1, stap[0])
            wp.digitalWrite(IN2, stap[1])
            wp.digitalWrite(IN3, stap[2])
            wp.digitalWrite(IN4, stap[3])
            time.sleep(vertraging)

    # Motor uitschakelen
    for pin in [IN1, IN2, IN3, IN4]:
        wp.digitalWrite(pin, wp.LOW)

# Meet de lichtintensiteit met de GY-30 lichtsensor
def meet_lux():
    bus = smbus2.SMBus(I2C_BUS)
    bus.write_byte(GY30_ADDR, 0x10)
    time.sleep(0.2)
    data = bus.read_i2c_block_data(GY30_ADDR, 0x10, 2)
    return (data[0] << 8 | data[1]) / 1.2

# Lees de temperatuur van de BMP280 sensor
def meet_temperatuur(bus):
    bus.write_byte_data(BMP280_ADDR, 0xF4, 0x2F)
    time.sleep(0.5)
    data = bus.read_i2c_block_data(BMP280_ADDR, 0xFA, 3)
    raw_temp = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
    return raw_temp / 5120.0  # Eenvoudigere temperatuurcorrectie

# Verstuur gegevens naar ThingSpeak
def stuur_naar_thingspeak(api_sleutel, lux, temp):
    url = f"https://api.thingspeak.com/update?api_key={api_sleutel}&field1={lux}&field2={temp}"
    requests.get(url)

# === Hoofdprogramma ===
def main():
    wp = setup_gpio()
    bus = smbus2.SMBus(I2C_BUS)
    status = None
    huidige_kleur = "groen"

    laatste_update = time.time()
    update_interval = 5  # Update elke 20 seconden

    try:
        while True:
            # Knop detecteren en RGB LED wijzigen (met debounce)
            if wp.digitalRead(BUTTON_PIN) == wp.HIGH:
                while wp.digitalRead(BUTTON_PIN) == wp.HIGH:
                    time.sleep(0.05)  # Korte debounce
                huidige_kleur = bedien_rgb_led(wp, huidige_kleur)

            # Controleer of het tijd is om gegevens te updaten
            if time.time() - laatste_update >= update_interval:
                laatste_update = time.time()

                lux = meet_lux()
                temp = meet_temperatuur(bus)
                print(f"Lux: {lux:.1f}, Temp: {temp:.1f}°C")

                stuur_naar_thingspeak(THINGSPEAK_API_KEY, lux, temp)

                gewenste_status = "open" if lux > LUX_DOEL else "gesloten"

                if gewenste_status != status:
                    print(f"Gordijnen {gewenste_status}...")
                    stuur_motor(wp, gewenste_status, 512)
                    status = gewenste_status

            time.sleep(0.1)  # Kleine vertraging om CPU-belasting te verminderen
    except KeyboardInterrupt:
        print("Programma gestopt door gebruiker")

# === Start het programma ===
if __name__ == "__main__":
    main()
