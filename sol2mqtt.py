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
import traceback
import math

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
soluri = config['soluri']

uptime = datetime.now(timezone.utc).isoformat()
wifis = ""
print("Connect SolmateAPI SN:" + sn + " " + soluri)

# 

#bugfix if you want to change SolMateAPIClient to LocalSolMateAPIClient
# ~/.config/solmate-sdk
# mv authstore.json authstore-online.json

n = sdnotify.SystemdNotifier()
n.notify("READY=1")

try:
    if not soluri:
        solclient = solmate_sdk.SolMateAPIClient(sn)
    else:
        solclient = solmate_sdk.LocalSolMateAPIClient(sn)
        solclient.uri = soluri
    solclient.quickstart()

except Exception as exc:
    print("Solmate OFFLINE: " + sn + ":" +  str(soluri) )
    print("Exception:", type(exc).__name__)
    print(str(exc))
    #sys.exit()
    
    
#mqttid = solclient.serialnum
mqttid = "0"

#wifis = solclient.list_wifis()

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

def on_disconnect(mqttClient, userdata, rc):
   print("client disconnected ok: rc=" + str(rc))
                
def on_message(mqttClient, userdata, msg):
    received_message = msg.payload.decode("utf-8")
    print(f"on_message: Received message on topic {msg.topic}: {received_message}")
    message_queue.put((msg.topic, received_message))  # Add the variables to the queue


def mqtt2sol(topic, received_message):
    print(f"mqtt2sol: Received message on topic solclient.set {topic}: {received_message}")
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
    mqttClient.on_disconnect = on_disconnect

    mqttClient.username_pw_set(mqttuser, mqttpasswort)
    mqttClient.connect(mqttBroker, mqttport, 60)
    mqttClient.loop_start()

except Exception as exc:
    print("Die Ip Adresse des Brokers ist falsch?" + mqttBroker + ":" +  str(mqttport) )
    print("Exception:", type(exc).__name__)
    print(str(exc))
    sys.exit()



reconnectcounter = 0
solreconnectcounter = 0
# Create a thread for processing the messages from the queue
# message_thread = threading.Thread(target=process_messages)
# message_thread.start()

while True:
    print(".", end="", flush=True)
    connected = False
    while not connected:
        try:
            print("mqtt reconnect:")
            mqttClient.reconnect()
            connected = True
            reconnectcounter += 1
            print("mqtt reconnect: topics... " + str(reconnectcounter))
            for topic in subscribe_topics:
                print("  Subscribe: " + topic)
                mqttClient.subscribe(topic)
        except:
            print("except reconnect: topics sleep")
            sleep(2)
    try:
        current_timestamp = datetime.now(timezone.utc).isoformat()
        ret = mqttClient.publish(f"eet/solmate/{mqttid}/uptime", uptime, 1, retain=True)
        result, mid = ret
        print("LOOP: mqttpublish uptime: " + str(uptime) + " ret=" + str(result))
        print(str(reconnectcounter))
        sleep(0.1)
        mqttClient.publish(f"eet/solmate/{mqttid}/last_seen", current_timestamp, 1, retain=True)
        mqttClient.publish(f"eet/solmate/{mqttid}/reconnectcounter", str(reconnectcounter), 1, retain=True)
        print("solclient.get_live_values... ")

        connected = False
        sleeploop = 10
        while not connected:
            try:
                mqttClient.publish(f"eet/solmate/{mqttid}/solreconnectcounter", str(solreconnectcounter), 1, retain=True)
                print("sol reconnect... " + str(solreconnectcounter))
                solclient.quickstart()
                live_values = solclient.get_live_values()
                connected = True
                sleep(0.1)
                mqttClient.publish(f"eet/solmate/{mqttid}/availability", "online", 1)
                solreconnectcounter = 0
            except:
                solreconnectcounter += 1
                if solreconnectcounter > 10:
                    sleeploop = 24
                print("sol reconnect: sleep " + str(sleeploop))
                mqttClient.publish(f"eet/solmate/{mqttid}/availability", "offline", 1, retain=True)
                n.notify("WATCHDOG=1")
                if solreconnectcounter > 10:
                    for i in range(10):
                        sleep(sleeploop)
                        n.notify("WATCHDOG=1")
                else:
                    sleep(sleeploop)
                

        # if datetime.now().hour == 10:
        #     solclient.set_min_battery_percentage(15)
             
        for property_name in live_values.keys():
            sleep(0.1)
            mqttClient.publish(f"eet/solmate/{mqttid}/{property_name}", str(live_values[property_name]), 1)                
            print("published:" + property_name + ": " + str(live_values[property_name]))
            # received 1011 (unexpected error) keepalive ping timeout; then sent 1011 (unexpected error) keepalive ping timeout
            # Traceback (most recent call last):

        while not message_queue.empty():
            topic, received_message = message_queue.get()  # queue2sol: Retrieve variables from the queue
            mqttClient.publish(f"eet/last_{topic}", f"{current_timestamp} {received_message}", 1)
            try:
                received_message = int(math.ceil(float(received_message)))
                mqtt2sol(topic, received_message)  # Call mqtt2sol with the retrieved variables
                sleep(0.1)
            except Exception as exc:
                print("Exception: queue2sol", type(exc).__name__)
                print(str(exc))
                print(traceback.format_exc())
                mqttClient.publish(f"eet/solmate/Ex/Exqueue2sol", str(exc), 1, retain=True)
                mqttClient.publish(f"eet/solmate/Ex/Exqueue2solReceivedMessage", str(received_message), 1, retain=True)
                mqttClient.publish(f"eet/solmate/Ex/Exqueue2solReceivedTopic", str(topic), 1, retain=True)
                

        if not soluri:
            online = solclient.check_online()
            mqttClient.publish(f"eet/solmate/{mqttid}/online", online, 1)
        
        battery_in = max(float(live_values['battery_flow']),0)
        battery_out = - min(float(live_values['battery_flow']),0)
        mqttClient.publish(f"eet/solmate/{mqttid}/battery_in", battery_in, 1)                
        mqttClient.publish(f"eet/solmate/{mqttid}/battery_out", battery_out, 1)                

        print("Batt: IN " + str(battery_in) + " OUT: " + str(battery_out))
        
        sleep(0.1)
        injectsettings = solclient.get_injection_settings()

        # injectsettings_string = json.dumps(injectsettings)
        # mqttClient.publish(f"eet/solmate/{mqttid}/injectsettings ", injectsettings_string , 1)                
        mqttClient.publish(f"eet/solmate/{mqttid}/user_minimum_injection", injectsettings['user_minimum_injection'] , 1)          
        mqttClient.publish(f"eet/solmate/{mqttid}/user_maximum_injection", injectsettings['user_maximum_injection'] , 1)          
        ret = mqttClient.publish(f"eet/solmate/{mqttid}/user_minimum_battery_percentage", injectsettings['user_minimum_battery_percentage'] , 1)          
        result, mid = ret
        
        #{"user_minimum_injection": 50, "user_maximum_injection": 196, "user_minimum_battery_percentage": 5}
        print("injectsettings['user_minimum_injection'] = " + str(injectsettings['user_minimum_injection']))
        print("mqttpublish user_minimum_injection: ret=" + str(result))
        n.notify("WATCHDOG=1")
        battery_state = max(float(live_values['battery_state']),0)
        
        sleeptimer = 6
        if battery_state <= 0.1:
            sleeptimer = 24
            n.notify("WATCHDOG=1")
            print(".sleep." + str(sleeptimer))
            sleep(sleeptimer)
            n.notify("WATCHDOG=1")
            print(".sleep." + str(sleeptimer))
        sleep(sleeptimer)
        #mqttClient.disconnect()        

    except Exception as exc:
        print("Exception:", type(exc).__name__)
        print(str(exc))
        print(traceback.format_exc())
        mqttClient.publish(f"eet/solmate/Ex/Exception", str(exc), 1, retain=True)
        mqttClient.publish(f"eet/solmate/Ex/Traceback", traceback.format_exc(), 1, retain=True)
        mqttClient.publish(f"eet/solmate/Ex/reconnectcounter", str(reconnectcounter), 1, retain=True)
        mqttClient.publish(f"eet/solmate/Ex/solreconnectcounter", str(solreconnectcounter), 1, retain=True)
        mqttClient.publish(f"eet/solmate/Ex/uptime" + str(uptime), 1, retain=True)
        mqttClient.publish(f"eet/solmate/Ex/current_timestamp" + str(current_timestamp), 1, retain=True)
