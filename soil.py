from config import WIFI_SSID, WIFI_PASS, MQTT_USER, MQTT_PASS
from umqtt.robust import MQTTClient
import asyncio
import json
import machine
import math
import network
import time
from sensor import Sensor, LightSensor, TemperatureSensor, SoilMoistureSensor, LocationSensor


class WifiManager:
    MAX_WAIT_TIME = 30
    RECONNECT_INTERVAL = 0.5
    
    def __init__(self):
        self.__wlan = network.WLAN(network.STA_IF)
        self.__led = machine.Pin(2, machine.Pin.OUT)
        self.__led.value(1)
    
    def connect(self) -> None:
        self.__led.value(1)
        self.__wlan.active(False)  
        time.sleep(1)
        self.__wlan.active(True)
        print("*** Connecting to WiFi...")

        try:
            self.__wlan.connect(WIFI_SSID, WIFI_PASS)
            for i in range(WifiManager.MAX_WAIT_TIME / WifiManager.RECONNECT_INTERVAL):
                if self.__wlan.isconnected():
                    print("*** WiFi connected")
                    self.__led.value(0)
                    return
                time.sleep(WifiManager.RECONNECT_INTERVAL)
            
            print("*** Connection Failed, Retrying...")
        except OSError as e:
            print(f"Error: {e}")
    
    def isconnected(self) -> bool:
        return self.__wlan.isconnected()


class MQTTManager:
    def __init__(self):
        self.__client = MQTTClient(
            client_id="",
            server="iot.cpe.ku.ac.th",
            user=MQTT_USER,
            password=MQTT_PASS
        )
        self.__led = machine.Pin(12, machine.Pin.OUT)
        self.__led.value(1)

    def connect(self) -> None:
        self.__led.value(1)
        print("*** Connecting to MQTT broker...")
        try:
            self.__client.connect()
            self.__client.publish("b6610545499/weather_db/debug", "MQTT Reconnected")
            print("*** MQTT broker connected")
            self.__led.value(0)
        except OSError as e:
            print(f"Error: {e}")
    
    def publish(self, topic: str, payload) -> None:
        try:
            self.__client.publish(topic, payload)
        except OSError as e:
            print(f"Error publishing: {e}")

    def set_callback(self, func):
        self.__client.set_callback(func)

    async def check_msg(self):
        while True:
            self.__client.check_msg()
            await asyncio.sleep_ms(0)

    def isconnected(self) -> bool:
        try:
            self.__client.ping()
            return True
        except:
            return False


class ConnectionManager:
    CHECK_CONNECTION_FREQ = 5
    def __init__(self):
        self.wifi = WifiManager()
        self.mqtt = MQTTManager()
    
    def connect(self):
        self.wifi.connect()
        if self.wifi.isconnected():
            self.mqtt.connect()
    
    async def check_connection(self):
        """Check WiFi and MQTT connection every 5 seconds"""
        print(f"*** Checking connection every {self.CHECK_CONNECTION_FREQ} seconds")
        while True:
            if not self.wifi.isconnected():
                print("*** WiFi disconnected, reconnecting...")
                self.wifi.connect()
            if self.wifi.isconnected() and not self.mqtt.isconnected():
                print("*** MQTT disconnected, reconnecting...")
                self.mqtt.connect()
#             if not self.wifi.isconnected() or not self.mqtt.isconnected():
#                 print("*** System unresponsive, restarting...")
#                 await asyncio.sleep(2)
#                 machine.reset()
            await asyncio.sleep(self.CHECK_CONNECTION_FREQ)


class Publisher:
    PUBLISH_INTERVAL = 600
    PUBLISH_TOPIC = "b6610545499/weather_db/in"
    
    def __init__(self, *sensors):
        self.conn_mgr = ConnectionManager()
        self.sensors = list(sensors)
        self.conn_mgr.connect()
    
    def __get_all_sensor_data(self) -> dict:
        temp = dict()
        for sensor in self.sensors:
            temp.update(sensor.get_data())
        return temp
    
    async def __publish_sensor_data_every_interval(self):
        while True:
            if self.conn_mgr.wifi.isconnected():
                data = self.__get_all_sensor_data()
                print(data)
                self.conn_mgr.mqtt.publish(Publisher.PUBLISH_TOPIC, json.dumps(data))
            await asyncio.sleep(Publisher.PUBLISH_INTERVAL)

    def run(self):
        asyncio.create_task(self.conn_mgr.check_connection())
        asyncio.create_task(self.__publish_sensor_data_every_interval())
        asyncio.create_task(self.conn_mgr.mqtt.check_msg())
        self.conn_mgr.mqtt.publish("b6610545499/weather_db/debug", "KidBright restarted")

async def main():
    p = Publisher(LightSensor(), TemperatureSensor(), LocationSensor, SoilMoistureSensor())
    p.run()
    while True:
        await asyncio.sleep(1)

try:
    asyncio.run(main())
except Exception:
    machine.reset()


