import dht
import machine

from sensor import Sensor


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
