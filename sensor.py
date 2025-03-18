from abc import ABC
from machine import ADC
import machine

class Sensor(ABC):    
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
        self.__PIN_NUMBER = 34
        self.__sensor = ADC(self.__PIN_NUMBER)
        self.__MAX_VALUE = 65535
    
    def get_data(self) -> dict:
        return {"moisture": abs(self.__sensor()-self.__MAX_VALUE)/self.__MAX_VALUE*100}
        