from config import WIFI_SSID, WIFI_PASS, MQTT_USER, MQTT_PASS
from umqtt.robust import MQTTClient
import asyncio
import json
import machine
import network


class LightSensor:
    def __init__(self):
        self.__sensor = machine.ADC(machine.Pin(36))

    def get_data(self) -> dict:
        v = self.__sensor.read_uv() / 1e06
        r_ldr = v * (33000 / (3.3 - v))
        lux = 10000 / ((r_ldr / 100) ** (4 / 3))
        return {"light": lux}


class TemperatureSensor:
    def __init__(self):
        self.__sensor = machine.I2C(sda=machine.Pin(4), scl=machine.Pin(5))
        self.__sensor.writeto(77, bytearray([0x04, 0b01100000]))
        self.__sensor.writeto(77, bytearray([0]))

    def get_data(self) -> dict:
        high, low = self.__sensor.readfrom(77, 2)
        celsius = (low + (high * 256)) / 128
        return {"temperature": celsius}


class Location:
    @staticmethod
    def get_data() -> dict:
        return {"lat": 13.45, "lon": 100.29}


class SoilSensor:
    MAX_VALUE = 65535

    def __init__(self):
        self.__sensor = machine.ADC(machine.PIN(35))

    def get_data(self) -> dict:
        return self.MAX_VALUE - self.__sensor.read_u16()


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
    SERVER = "iot.cpe.ku.ac.th"
    DEBUG_TOPIC = "b6610545499/placeholder/debug"

    def __init__(self):
        self.__client = MQTTClient(
            client_id="", server=self.SERVER, user=MQTT_USER, password=MQTT_PASS
        )
        self.__led = machine.Pin(12, machine.Pin.OUT)
        self.__led.value(1)

    def connect(self) -> None:
        self.__led.value(1)
        print("*** Connecting to MQTT broker...")
        try:
            self.__client.connect()
            self.__client.publish(self.DEBUG_TOPIC, "MQTT Reconnected")
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


class ConnectionController:
    CHECK_CONNECTION_FREQ = 5

    def __init__(self):
        self.wifi = WifiManager()
        self.mqtt = MQTTManager()

    async def initialise_connection(self) -> None:
        await self.connect()
        asyncio.create_task(self.check_connection())
        # asyncio.create_task(self.mqtt.check_msg())
        self.mqtt.publish(self.mqtt.DEBUG_TOPIC, "KidBright restarted")

    async def connect(self) -> None:
        await self.wifi.connect()
        if self.wifi.isconnected():
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
    PUBLISH_TOPIC = "b6610545499/placeholder/in"

    def __init__(self, *sensors, conn_mgr: ConnectionController):
        self.conn_mgr = conn_mgr
        self.sensors = list(sensors)

    def run(self) -> None:
        asyncio.create_task(self.__publish_sensor_data_every_interval())

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
                self.conn_mgr.mqtt.publish(self.PUBLISH_TOPIC, json.dumps(data))
            await asyncio.sleep(self.PUBLISH_INTERVAL)


async def main():
    conn_mgr = ConnectionController()
    await conn_mgr.initialise_connection()
    p = Publisher(LightSensor(), TemperatureSensor(), Location, conn_mgr=conn_mgr)
    p.run()
    while True:
        await asyncio.sleep(1)


try:
    asyncio.run(main())
except Exception:
    machine.reset()
