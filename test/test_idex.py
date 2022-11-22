import logging
from AnalyticalLabware import IDEXMXIIValve

logging.basicConfig(level=logging.DEBUG)
connection_params = {"address": "192.168.1.100", "port": 5000}
valve = IDEXMXIIValve(
    "valve_hplc", connection_mode="tcpip", connection_parameters=connection_params
)

# status querying
logging.info(valve.is_connected())
logging.info(valve.is_ready())

# actuation
valve.move_to_position(1)
valve.move_to_position(2)

# position querying
logging.info(valve.current_position)

# sampling
valve.sample(5, sync=False)
valve.sample(5, sync=True)
