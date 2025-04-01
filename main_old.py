from machine import Pin, I2C, ADC
import network
import time
import json
from umqtt.robust import MQTTClient
from config import WIFI_SSID, WIFI_PASS, MQTT_BROKER, MQTT_USER, MQTT_PASS
import asyncio

MQTT_PUBLSH_CHANNEL = ""

class ConnectionManager:
    """Manage the wireless connection (WiFi & MQTT)."""

    def __init__(self):
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.mqtt = None
        self.led_wifi = Pin(2, Pin.OUT)  # WiFi indicator LED
        self.led_wifi.value(1)  # Turn red LED off
        self.iot = Pin(12, Pin.OUT)  # MQTT indicator 
        self.iot.value(1)

    async def __connect_to_wifi(self):
        """Connect to WiFi and indicate status with LED."""
        print("*** Connecting to WiFi...")
        self.wlan.connect(WIFI_SSID, WIFI_PASS)
        attempts = 0
        while not self.wlan.isconnected():
            time.sleep(1)
            attempts += 1
            if attempts > 10:  # Try for 10 seconds
                print("WiFi connection failed.")
                return False
        print("*** WiFi Connected.")
        self.led_wifi.value(0)  # Turn red LED on (connected)
        return True

    async def __connect_to_mqtt(self):
        """Connect to MQTT broker."""
        try:
            self.mqtt = MQTTClient(client_id="", server=MQTT_BROKER, user=MQTT_USER, password=MQTT_PASS)
            self.mqtt.connect()
            print("Connected to MQTT and Subscribed.")
            self.iot.value(0)
            return True
        except Exception as e:
            print(f"MQTT connection failed: {e}")
            return False

    async def connect(self):
        """Main function to establish WiFi & MQTT connections."""
        if await self.__connect_to_wifi():
            await self.__connect_to_mqtt()

    async def check_wifi_connection(self):
        """Monitor WiFi connection and reconnect if disconnected."""
        while True:
            if not self.wlan.isconnected():
                print("WiFi disconnected! Reconnecting...")
                self.led_wifi.value(1)  # Turn red LED off
                self.iot.value(1)
                if await self.__connect_to_wifi():
                    await self.__connect_to_mqtt()
            await asyncio.sleep(5)  # Check WiFi every 5 seconds


class DataReader:
    """Read data from the sensors."""

    def __init__(self):
        self.i2c = I2C(1, sda=Pin(4), scl=Pin(5))
        self.i2c.writeto(77, bytearray([0]))
        self.ldr = ADC(Pin(36))

    def read_temperature(self) -> float:
        """Read temperature from the I2C sensor."""
        data = self.i2c.readfrom(77, 2)
        value = (256 * data[0] + data[1]) / 128
        return value

    def read_light(self) -> float:
        """Read light intensity from the sensor."""
        voltage = self.ldr.read_uv() * 10**(-6)
        resistance = voltage * (33000 / (3.3 - voltage))
        lux = 10000 / ((resistance * 10 / 1000) ** (4 / 3))
        return lux


class SensorPublisher:
    """Periodically read sensor data and publish to MQTT."""

    def __init__(self, connection_manager: ConnectionManager, data_reader: DataReader):
        self.conn_mgr = connection_manager
        self.data_reader = data_reader

    async def sensor_task(self):
        """Read temperature and light, then publish data."""
        while True:
            temp = self.data_reader.read_temperature()
            light = self.data_reader.read_light()
            print(f"Publish temperature={temp}, light={light}")
            data = {
                "temperature": temp,
                "light": light,
                "latitude": 369,
                "longitude": 420
            }
            if self.conn_mgr.mqtt:
                self.conn_mgr.mqtt.publish(MQTT_PUBLSH_CHANNEL, json.dumps(data))
            await asyncio.sleep(10 * 60)  # Publish every 10 minutes

async def main():
    """Main function to start all tasks."""
    conn_mgr = ConnectionManager()
    data_reader = DataReader()
    sensor_publisher = SensorPublisher(conn_mgr, data_reader)

    await conn_mgr.connect()

    asyncio.create_task(conn_mgr.check_wifi_connection())
    asyncio.create_task(sensor_publisher.sensor_task())

    while True:
        await asyncio.sleep(1)

asyncio.run(main())
