import asyncio
import json

import machine
import network
from umqtt.robust import MQTTClient

from config import (
    MQTT_BROKER,
    MQTT_DEBUG_TOPIC,
    MQTT_PASS,
    MQTT_SENSOR_TOPIC,
    MQTT_USER,
    MQTT_WATER_TOPIC,
    WIFI_PASS,
    WIFI_SSID,
)
from sensor import (
    LightSensor,
    LocationSensor,
    Sensor,
    SoilMoistureSensor,
    TemperatureSensor,
)


class WifiManager:
    MAX_WAIT_TIME = 30
    RECONNECT_INTERVAL = 0.5

    def __init__(self):
        self.__wlan = network.WLAN(network.STA_IF)
        self.__led = machine.Pin(2, machine.Pin.OUT)
        self.__led.value(1)

    async def connect(self) -> None:
        self.__led.value(1)
        self.__wlan.active(False)
        await asyncio.sleep(1)
        self.__wlan.active(True)
        print("*** Connecting to WiFi...")

        try:
            self.__wlan.connect(WIFI_SSID, WIFI_PASS)
            for _ in range(self.MAX_WAIT_TIME / self.RECONNECT_INTERVAL):
                if self.__wlan.isconnected():
                    print("*** WiFi connected")
                    self.__led.value(0)
                    return
                await asyncio.sleep(self.RECONNECT_INTERVAL)

            print("*** Connection Failed, Retrying...")
        except OSError as e:
            print(f"Error: {e}")

    def isconnected(self) -> bool:
        return self.__wlan.isconnected()


class MQTTManager:
    def __init__(self):
        self.__client = MQTTClient(
            client_id="", server=MQTT_BROKER, user=MQTT_USER, password=MQTT_PASS
        )
        self.__led = machine.Pin(12, machine.Pin.OUT)
        self.__led.value(1)

    def connect(self) -> None:
        self.__led.value(1)
        print("*** Connecting to MQTT broker...")
        try:
            self.__client.connect()
            self.__client.publish(MQTT_DEBUG_TOPIC, "MQTT Reconnected")
            print("*** MQTT broker connected")
            self.__led.value(0)
        except OSError as e:
            print(f"Error: {e}")

    def publish(self, topic: str, payload) -> None:
        try:
            self.__client.publish(topic, payload)
        except OSError as e:
            print(f"Error publishing: {e}")

    def set_callback(self, func) -> None:
        self.__client.set_callback(func)

    def isconnected(self) -> bool:
        try:
            self.__client.ping()
            return True
        except Exception:
            return False

    async def check_msg(self):
        while True:
            self.__client.check_msg()
            await asyncio.sleep_ms(0)


class ConnectionController:
    CHECK_CONNECTION_FREQ = 5

    def __init__(self):
        self.wifi = WifiManager()
        self.mqtt = MQTTManager()

    async def initialise_connection(self) -> None:
        await self.connect()
        asyncio.create_task(self.check_connection())
        asyncio.create_task(self.mqtt.check_msg())
        self.mqtt.publish(MQTT_DEBUG_TOPIC, "KidBright restarted")

    async def connect(self) -> None:
        await self.wifi.connect()
        if self.wifi.isconnected():
            await asyncio.sleep(1)
            self.mqtt.connect()

    async def check_connection(self) -> None:
        """Check WiFi and MQTT connection every 5 seconds"""
        print(f"*** Checking connection every {self.CHECK_CONNECTION_FREQ} seconds")
        while True:
            if not self.wifi.isconnected():
                print("*** WiFi disconnected, reconnecting...")
                await self.connect()
            if self.wifi.isconnected() and not self.mqtt.isconnected():
                print("*** MQTT disconnected, reconnecting...")
                self.mqtt.connect()
            await asyncio.sleep(self.CHECK_CONNECTION_FREQ)


class Publisher:
    PUBLISH_INTERVAL = 600

    def __init__(self, *sensors: Sensor, conn_mgr: ConnectionController):
        self.conn_mgr = conn_mgr
        self.sensors = list(sensors)
        # this is s1 btw
        self.__switch = machine.Pin(16, machine.Pin.IN, machine.Pin.PULL_UP)

    def run(self) -> None:
        asyncio.create_task(self.__publish_sensor_data_every_interval())
        asyncio.create_task(self.__notify_watering())

    def __get_all_sensor_data(self) -> dict:
        temp = dict()
        for sensor in self.sensors:
            temp.update(sensor.get_data())
        return temp

    async def __publish_sensor_data_every_interval(self) -> None:
        while True:
            if self.conn_mgr.wifi.isconnected():
                data = self.__get_all_sensor_data()
                print(data)

                self.conn_mgr.mqtt.publish(MQTT_SENSOR_TOPIC, json.dumps(data))
            await asyncio.sleep(self.PUBLISH_INTERVAL)

    async def __notify_watering(self):
        while True:
            while self.__switch.value() == 1:
                await asyncio.sleep(0)
            data = {"watered": 1}
            self.conn_mgr.mqtt.publish(MQTT_WATER_TOPIC, json.dumps(data))
            while self.__switch.value() == 0:
                await asyncio.sleep(0)
            await asyncio.sleep_ms(10)


async def main():
    conn_mgr = ConnectionController()
    await conn_mgr.initialise_connection()
    p = Publisher(
        LightSensor(),
        TemperatureSensor(),
        LocationSensor,
        SoilMoistureSensor(),
        conn_mgr=conn_mgr,
    )
    p.run()
    while True:
        await asyncio.sleep(1)


try:
    asyncio.run(main())
except Exception as e:
    print(e)
    machine.reset()
