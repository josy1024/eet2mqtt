from time import sleep
import os
import sys

import paho.mqtt.client as mqtt

import solmate_sdk
import sdnotify
import json

import queue
from datetime import datetime
from datetime import timezone

# * gets solmate api life data (sol2mqtt)
# *   .. and writes them to mqtt
# * gets set data from queue (queue2sol)
# *   .. and writes them back to solmate api (mqtt2sol)
# * gets subscribed mqtt set data (mqtt2queue)
# *   .. and writes it to a queue


message_queue = queue.Queue()

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

uptime = datetime.now(timezone.utc).isoformat()

print("Connect SolmateAPI SN:" + sn)

solclient = solmate_sdk.SolMateAPIClient(sn)
solclient.quickstart()
mqttid = solclient.serialnum
mqttid = "0"

#client.uri = "ws://sun2plug.local:9124/"
#client.uri = "ws://sun2plug.local:9124/"

wifis = solclient.list_wifis()

#sun2plug.local
print(f"Solmate WIFI: {solclient.serialnum}: {wifis}")
sleep(0.1)
    
subscribe_topics = ["eet/solmate/0/set/user_maximum_injection", "eet/solmate/0/set/user_minimum_injection", "eet/solmate/0/set/user_minimum_battery_percentage"]


    # Callback function for when the client receives a CONNACK response from the broker
def on_connect(mqttClient, userdata, flags, rc):
    print("on_connect: with result code " + str(rc))
    if rc == 0:
        print("on_connect: topics..")
        for topic in subscribe_topics:
            print("  Subscribe: " + topic)
            mqttClient.subscribe(topic)
    else:
        print("Connection to MQTT broker failed. Retrying in 5 seconds...")
        time.sleep(5)
        mqttClient.connect(broker_address, broker_port)
                
def on_message(mqttClient, userdata, msg):
    received_message = msg.payload.decode("utf-8")
    print(f"on_message: Received message on topic {msg.topic}: {received_message}")
    message_queue.put((msg.topic, received_message))  # Add the variables to the queue


def mqtt2sol(topic, received_message):
    print(f"mqtt2sol: Received message on topic {topic}: {received_message}")
    if "user_maximum_injection" in topic:
        solclient.set_max_injection(int(received_message))
    elif "user_minimum_injection" in topic:
        solclient.set_min_injection(int(received_message))
    elif "user_minimum_battery_percentage" in topic:
        solclient.set_min_battery_percentage(int(received_message))

try:
    print("Connect mqtt: " + mqttBroker + ":" + str(mqttport) )
    mqttClient = mqtt.Client("sol2mqtt")
    mqttClient.on_connect = on_connect
    mqttClient.on_message = on_message
    mqttClient.username_pw_set(mqttuser, mqttpasswort)
    mqttClient.connect(mqttBroker, mqttport, 60)
    mqttClient.loop_start()

except Exception as exc:
    print("Die Ip Adresse des Brokers ist falsch?" + mqttBroker + ":" +  str(mqttport) )
    print("Exception:", type(exc).__name__)
    print(str(exc))
    sys.exit()



n = sdnotify.SystemdNotifier()
n.notify("READY=1")

# Create a thread for processing the messages from the queue
# message_thread = threading.Thread(target=process_messages)
# message_thread.start()

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
        live_values = solclient.get_live_values()

        while not message_queue.empty():
            topic, received_message = message_queue.get()  # queue2sol: Retrieve variables from the queue
            mqtt2sol(topic, received_message)  # Call mqtt2sol with the retrieved variables
            sleep(0.1)

        online = solclient.check_online()
        # mqttClient.publish(f"eet/solmate/{client.serialnum}/live_values", json.dumps(live_values), 1)
        mqttClient.publish(f"eet/solmate/{mqttid}/online", online, 1)
        for property_name in live_values.keys():
            mqttClient.publish(f"eet/solmate/{mqttid}/{property_name}", live_values[property_name], 1)                
        
        battery_in = max(float(live_values['battery_flow']),0)
        battery_out = - min(float(live_values['battery_flow']),0)
        mqttClient.publish(f"eet/solmate/{mqttid}/battery_in", battery_in, 1)                
        mqttClient.publish(f"eet/solmate/{mqttid}/battery_out", battery_out, 1)                

        injectsettings = solclient.get_injection_settings()
        # injectsettings_string = json.dumps(injectsettings)
        # mqttClient.publish(f"eet/solmate/{mqttid}/injectsettings ", injectsettings_string , 1)                
        mqttClient.publish(f"eet/solmate/{mqttid}/user_minimum_injection", injectsettings['user_minimum_injection'] , 1)          
        mqttClient.publish(f"eet/solmate/{mqttid}/user_maximum_injection", injectsettings['user_maximum_injection'] , 1)          
        mqttClient.publish(f"eet/solmate/{mqttid}/user_minimum_battery_percentage", injectsettings['user_minimum_battery_percentage'] , 1)          
        #{"user_minimum_injection": 50, "user_maximum_injection": 196, "user_minimum_battery_percentage": 5}
        mqttClient.publish(f"eet/solmate/{mqttid}/uptime", uptime)
        current_timestamp = datetime.now(timezone.utc).isoformat()
        mqttClient.publish(f"eet/solmate/{mqttid}/last_seen", current_timestamp)
        
        n.notify("WATCHDOG=1")
    except Exception as exc:
        print("Exception:", type(exc).__name__)
        print(str(exc))
    sleep(10)
    mqttClient.loop(0.1)
    
