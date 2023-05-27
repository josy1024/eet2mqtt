from time import sleep
import os
import sys

import paho.mqtt.client as mqtt

import solmate_sdk
import sdnotify
import json

configFile = os.path.dirname(os.path.realpath(__file__)) + '/config.json'

# Überprüfung ob ein Config Datei vorhanden ist sonst kommt eine Fehlermeldung und beendet das Programm
if not os.path.exists(configFile):
    print("Kein Config.json gefunden bitte eines anlegen.")
    sys.exit(-1)

# Überprüfung ob die Config gelesen werden kann
if not os.access(configFile, os.R_OK):
    print("ConfigFile " + configFile + " kann nicht gelesen werden!\n\n")
    sys.exit(-2)

# Einlesen der Config
config = json.load(open(configFile))

# Überprüfung ob alle Daten in der Config vorhanden sind
neededConfig = ['mqttbrokerip', 'mqttbrokerport',
                'mqttbrokeruser', 'mqttbrokerpasswort']
for conf in neededConfig:
    if conf not in config:
        print(conf + ' Fehlt im Configfile!')
        sys.exit(3)


# solmate serial number
sn = config['sn']

# Aktulle Werte auf Console ausgeben (True | False)
printValue = config['printValue']

mqttBroker = config['mqttbrokerip']
mqttport = config['mqttbrokerport']  # 1883 ist der Standard Port
mqttuser = config['mqttbrokeruser']
mqttpasswort = config['mqttbrokerpasswort']

client = solmate_sdk.SolMateAPIClient(sn)
client.quickstart()

def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))


mqttClient = mqtt.Client()
mqttClient.on_connect = on_connect
mqttClient.username_pw_set(mqttuser, mqttpasswort)
mqttClient.connect(mqttBroker, mqttport, 60)

n = sdnotify.SystemdNotifier()
n.notify("READY=1")


mqttid = client.serialnum
mqttid = 0
while True:
    print(".", end="", flush=True)
    connected = False
    while not connected:
        try:
            mqttClient.reconnect()
            connected = True
        except:
            time.sleep(2)
    try:
        live_values = client.get_live_values()
        online = client.check_online()
        mqttClient.publish(f"eet/solmate/{client.serialnum}/live_values", json.dumps(live_values), 1)
        # mqttClient.publish(f"eet/solmate/{client.serialnum}/online", online, 1)
        for property_name in live_values.keys():
            mqttClient.publish(f"eet/solmate/{mqttid}/{property_name}", live_values[property_name], 1)                
        n.notify("WATCHDOG=1")
    except Exception as exc:
        print(exc)
    sleep(10)

