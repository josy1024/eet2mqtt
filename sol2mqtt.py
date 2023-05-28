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

mqttBroker = config['mqttbrokerip']
mqttport = config['mqttbrokerport']  # 1883 ist der Standard Port
mqttuser = config['mqttbrokeruser']
mqttpasswort = config['mqttbrokerpasswort']

print("Connect SolmateAPI SN:" + sn)

client = solmate_sdk.SolMateAPIClient(sn)
client.quickstart()

def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))

print("Connect mqtt: " + mqttBroker + ":" + str(mqttport) )

try:
    mqttClient = mqtt.Client("sol2mqtt")
    mqttClient.on_connect = on_connect
    mqttClient.username_pw_set(mqttuser, mqttpasswort)
    mqttClient.connect(mqttBroker, mqttport, 60)
except:
    print("Die Ip Adresse des Brokers ist falsch?" + mqttBroker + ":" +  str(mqttport) )
    sys.exit()


        

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
        # mqttClient.publish(f"eet/solmate/{client.serialnum}/live_values", json.dumps(live_values), 1)
        mqttClient.publish(f"eet/solmate/{mqttid}/online", online, 1)
        for property_name in live_values.keys():
            mqttClient.publish(f"eet/solmate/{mqttid}/{property_name}", live_values[property_name], 1)                
        
        battery_in = max(float(live_values['battery_flow']),0)
        battery_out = - min(float(live_values['battery_flow']),0)
        mqttClient.publish(f"eet/solmate/{mqttid}/battery_in", battery_in, 1)                
        mqttClient.publish(f"eet/solmate/{mqttid}/battery_out", battery_out, 1)                

        injectsettings = client.get_injection_settings()
        #         
        
        mqttClient.publish(f"eet/solmate/{mqttid}/injectsettings ", injectsettings , 1)                
        n.notify("WATCHDOG=1")
    except Exception as exc:
        print(exc)
    sleep(10)

