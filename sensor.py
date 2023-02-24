import logging
import telnetlib
from datetime import timedelta, datetime, time
from typing import Callable, Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass, SensorDeviceClass
from homeassistant.const import UnitOfTemperature, UnitOfPower, UnitOfElectricPotential, UnitOfElectricCurrent, \
    UnitOfEnergy, UnitOfFrequency, UnitOfTime
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.event import async_track_time_interval

SIGNAL = 'solareco'
DOMAIN = 'solareco'

_LOGGER = logging.getLogger('solareco')


class SolarecoSensorConfig:
    def __init__(self, name,
                 unit_of_measurement,
                 device_class,
                 data_transformation,
                 state_class=SensorStateClass.MEASUREMENT,
                 last_reset: Callable[[], Any] = lambda: None):
        self.name = name
        self.unit_of_measurement = unit_of_measurement
        self.device_class = device_class
        self.data_transformation = data_transformation
        self.state_class = state_class
        self.last_reset = last_reset


SENSORS = [
    SolarecoSensorConfig('relay', None, None, lambda data: data[2][2:]),
    SolarecoSensorConfig('fan', None, None, lambda data: data[3][2:]),
    SolarecoSensorConfig('required_voltage', UnitOfElectricPotential.VOLT, None, lambda data: data[4][2:]),
    SolarecoSensorConfig('voltage', UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, lambda data: data[5][:-1]),
    SolarecoSensorConfig('current', UnitOfElectricCurrent.MILLIAMPERE, SensorDeviceClass.CURRENT, lambda data: data[6][:-2]),
    SolarecoSensorConfig('power', UnitOfPower.WATT, SensorDeviceClass.POWER, lambda data: data[7][:-1]),
    SolarecoSensorConfig('frequency', UnitOfFrequency.HERTZ, SensorDeviceClass.FREQUENCY, lambda data: data[8][:-2]),
    SolarecoSensorConfig('temperature', UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, lambda data: data[9][:-1]),
    SolarecoSensorConfig('pulse_width', UnitOfTime.MICROSECONDS, None, lambda data: data[10][:-2]),
    SolarecoSensorConfig('energy', UnitOfEnergy.WATT_HOUR, SensorDeviceClass.ENERGY, lambda data: data[11][:-2], SensorStateClass.TOTAL, lambda: datetime.combine(datetime.today(), time.min)),
]


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None) -> True:
    _LOGGER.info(str(config))
    sensor_connector = SensorConnector(hass, config['host'], config['port'])
    # Do first update
    await hass.async_add_executor_job(sensor_connector.update)

    # Poll for updates in the background
    async_track_time_interval(
        hass,
        lambda now: sensor_connector.update(),
        timedelta(seconds=int(config['poll_interval_seconds'])),
    )

    entities: list[SensorEntity] = []
    entities.extend([SolarecoSensor(sensor_connector, sensor_config) for sensor_config in SENSORS])
    async_add_entities(entities, True)

    hass.data.setdefault(DOMAIN, {})


class SolarecoSensor(SensorEntity):
    def __init__(self, sensor_connector, sensor_config: SolarecoSensorConfig):
        super().__init__()
        self.sensor_connector = sensor_connector
        self.sensor_config = sensor_config

        self._state = None
        self._state_attributes = None

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(self.hass, SIGNAL, self._async_update_callback)
        )

    @callback
    def _async_update_callback(self):
        self._async_update_data()
        self.async_write_ha_state()

    @property
    def unique_id(self):
        return f"{'solareco'} {self.sensor_config.name}"

    @property
    def name(self):
        return f"{'solareco'} {self.sensor_config.name}"

    @property
    def native_value(self):
        return self._state

    @property
    def state_class(self):
        return self.sensor_config.state_class

    @property
    def device_class(self):
        return self.sensor_config.device_class

    @property
    def native_unit_of_measurement(self):
        return self.sensor_config.unit_of_measurement

    @property
    def last_reset(self):
        return self.sensor_config.last_reset()

    @callback
    def _async_update_data(self):
        self._state = self.sensor_connector.data[self.sensor_config.name]


class SensorConnector:
    def __init__(self, hass, solareco_host, solareco_port):
        self.hass = hass
        self.solareco_host = solareco_host
        self.solareco_port = solareco_port
        self.data = {SENSORS[i]: None for i in range(0, len(SENSORS))}

    def update(self):
        try:
            with telnetlib.Telnet(self.solareco_host, self.solareco_port) as tn:
                line = tn.read_until(b'\n').decode('ascii')
                line_segments = line.split()
                if len(line_segments) == 12:
                    for i in range(0, len(SENSORS)):
                        sensor = SENSORS[i]
                        self.data[sensor.name] = sensor.data_transformation(line_segments)
                    dispatcher_send(self.hass, SIGNAL)
        except:
            _LOGGER.error("can't connect to SolarEco")
