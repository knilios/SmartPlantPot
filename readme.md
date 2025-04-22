# Smart Plant Pot - Stop Worrying About When To Water Your Plant
## About
This repository contains the micropython code for deployment on KidBright microcontroller boards (or, theoretically, any ESP32 boards), as well as Node-RED workflow.

For the application and APIs, please refer to [Jangsoodlir/smart-plant-pot-app](https://github.com/Jangsoodlor/smart-plant-pot-app)


This project is also a part of Data Acquisition subject 2024, Software and Knowledge Engineering, Kasetsart University.

# Set Up
## Prerequisites
- A KidBright board (or, theoretically, any ESP32 devices).
- A ZX-SOIL moisture sensor.
- A database for data collection is [set up](https://github.com/Jangsoodlor/smart-plant-pot-app/wiki/Database-Schema-&-Setup) in advance.

## Set up the ESP32 device
1. Flash micropython to the device.
1. Clone or download this repo.
1. Copy `config.py.example` to `config.py`.
1. Edit `config.py` to match your credentials.
1. The sensor PIN in `sensor.py` and in your device may not be the same, please make sure to change that as well.
1. Save `main.py` and `sensor.py` to your KidBirght Board.
1. You can ignore `humidity.py`. It's not necessary to set up. Although if you want to do so and have basic programming skills, you can set that up in 15 minutes.

## Set Up Node-RED
1. Import `flows.json` to Node-RED.
1. Change the input topics to match `SENSOR_TOPIC`, `WATER_TOPIC`.
1. Change table names in all `template` flows to match your table names .
1. Change the database to your own database.
1. You can delete the entire "Weathering every 3 hours" flow if you want.
1. Click deploy.
1. Thoughts and prayers.
