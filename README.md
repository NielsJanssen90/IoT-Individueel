# Samenvatting van de IoT-oplossing met Orange Pi 3 LTS en Raspberry Pi Pico

## Overzicht
Deze IoT-oplossing combineert een **Orange Pi 3 LTS** en een **Raspberry Pi Pico** om een slim verlichtings- en klimaatregelsysteem te implementeren. Het systeem meet lichtintensiteit (lux), temperatuur en luchtdruk, publiceert de data naar **ThingSpeak**, en bestuurt een **RGB LED** en een **stappermotor** om gordijnen aan te passen op basis van lichtniveaus. Een **knop** op de Raspberry Pi Pico stelt de gewenste lux-doelwaarde in.

---

## Orange Pi 3 LTS - Sensormodule & Actuatoren
De **Orange Pi** is verantwoordelijk voor het uitlezen van sensoren en het aansturen van actuatoren.

### Sensoren
- **GY-30 (BH1750) lichtsensor** - Meet de lichtintensiteit (lux).
- **BMP280 temperatuur- en luchtdruksensor** - Meet temperatuur en luchtdruk.

### Actuatoren
- **RGB LED** - Geeft de temperatuurstatus weer:
  - **Blauw**: Koud (< 18°C)
  - **Groen**: Gemiddeld (18-24°C)
  - **Rood**: Warm (> 24°C)
- **ULN2003 Stappermotor** - Opent of sluit de gordijnen op basis van de gemeten lux-waarde en de ingestelde doelwaarde.

---

## ThingSpeak MQTT Publicatie
- Sensorwaarden worden periodiek naar **ThingSpeak** gepubliceerd via **MQTT**.
- De **lux-doelwaarde** wordt uit ThingSpeak opgehaald om de gordijnstatus te bepalen.

---

## Logica voor gordijnregeling
- Als de **gemeten lux-waarde hoger** is dan de **ingestelde lux-doelwaarde**, worden de gordijnen **geopend**.
- Als de **gemeten lux-waarde lager** is dan de **ingestelde lux-doelwaarde**, worden de gordijnen **gesloten**.
- Huidige status wordt bijgehouden om **onnodige motorbewegingen** te voorkomen.

---

## Raspberry Pi Pico - Knopbediening
De **Raspberry Pi Pico** fungeert als een bedieningsinterface waarmee gebruikers de **lux-doelwaarde handmatig** kunnen aanpassen.

### Functie van de knop (GP12)
- **Korte druk** → **+10 lux**
- **Lange druk** (>2s) → **-10 lux**

---

## Wi-Fi en MQTT Connectie
- De **Pico** maakt via **Wi-Fi** verbinding met **ThingSpeak**.
- **MQTT** wordt gebruikt om de **lux-doelwaarde** te publiceren naar **ThingSpeak**.
### Youtube Video

📺 **Demo Video:** [Kijk op youtube](https://youtu.be/fnaWUmIffEQ)
