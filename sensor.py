import machine
from time import sleep
import dht



class Sensor:
    def get_data(self) -> dict:
        pass


class LightSensor(Sensor):
    def __init__(self):
        self.__sensor = machine.ADC(machine.Pin(36))

    def get_data(self) -> dict:
        v = self.__sensor.read_uv() / 1e06
        r_ldr = v * (33000 / (3.3 - v))
        lux = 10000 / ((r_ldr / 100) ** (4 / 3))
        return {"light": lux}


class TemperatureSensor(Sensor):
    def __init__(self):
        self.__sensor = machine.I2C(sda=machine.Pin(4), scl=machine.Pin(5))
        self.__sensor.writeto(77, bytearray([0x04, 0b01100000]))
        self.__sensor.writeto(77, bytearray([0]))

    def get_data(self) -> dict:
        high, low = self.__sensor.readfrom(77, 2)
        celsius = (low + (high * 256)) / 128
        return {"temperature": celsius}


class SoilMoistureSensor(Sensor):
    def __init__(self):
        self.__PIN_NUMBER = 35
        self.__sensor = ADC(self.__PIN_NUMBER)
        self.__sensor.atten(ADC.ATTN_11DB)  # Full range: 0 to 3.3V
        self.__sensor.width(ADC.WIDTH_12BIT)  # 12-bit resolution (0-4095)
        self.__MAX_VALUE = 4095
    
    def get_data(self) -> dict:
        print(self.__sensor.read_uv())
        return {"moisture": self.__sensor.read()}
        # return {"moisture": abs(self.__sensor.read_uv()-self.__MAX_VALUE)/self.__MAX_VALUE*100}
    

class HumiditySensor(Sensor):
    def __init__(self):
        self.__PIN_NUMBER = 33
        self.__sensor = dht.DHT11(machine.Pin(self.__PIN_NUMBER))
    
    def get_data(self) -> dict:
        self.__sensor.measure()
        try:
            print(self.__sensor.temperature())
            return {"humidity": self.__sensor.humidity()}
        except Exception as e:
            return {"humidity": None}


class LocationSensor:
    @staticmethod
    def get_data():
        return {"lat": 13.45, "lon": 100.29}

