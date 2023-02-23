import logging
import telnetlib
from datetime import timedelta, datetime, time

from homeassistant.components.sensor import SensorEntity, SensorStateClass, SensorDeviceClass
from homeassistant.const import UnitOfTemperature, UnitOfPower, UnitOfElectricPotential, UnitOfElectricCurrent, \
    UnitOfEnergy, UnitOfFrequency, UnitOfTime
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.event import async_track_time_interval

SIGNAL = 'solareco'
DOMAIN = 'solareco'

_LOGGER = logging.getLogger("solareco")

SENSORS = {
    "temperature",
    "power",
    "current",
    "voltage",
    "frequency",
    "energy",
    "pulse_height",
    "relay",
    "fan",
    "required_voltage"

}


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
    entities.extend([SolarecoSensor(sensor_connector, variable) for variable in SENSORS])
    async_add_entities(entities, True)

    hass.data.setdefault(DOMAIN, {})


class SolarecoSensor(SensorEntity):
    def __init__(self, sensor_connector, variable):
        super().__init__()
        self.sensor_connector = sensor_connector
        self.variable = variable

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
        return f"{'solareco'} {self.variable}"

    @property
    def name(self):
        return f"{'solareco'} {self.variable}"

    @property
    def native_value(self):
        return self._state

    @property
    def state_class(self):
        if self.variable == "energy":
            return SensorStateClass.TOTAL
        return SensorStateClass.MEASUREMENT

    @property
    def device_class(self):
        if self.variable == "temperature":
            return SensorDeviceClass.TEMPERATURE
        if self.variable == "power":
            return SensorDeviceClass.POWER
        if self.variable == "current":
            return SensorDeviceClass.CURRENT
        if self.variable == "voltage":
            return SensorDeviceClass.VOLTAGE
        if self.variable == "frequency":
            return SensorDeviceClass.FREQUENCY
        if self.variable == "energy":
            return SensorDeviceClass.ENERGY
        return None

    @property
    def native_unit_of_measurement(self):
        if self.variable == "temperature":
            return UnitOfTemperature.CELSIUS
        if self.variable == "power":
            return UnitOfPower.WATT
        if self.variable == "current":
            return UnitOfElectricCurrent.MILLIAMPERE
        if self.variable == "voltage":
            return UnitOfElectricPotential.VOLT
        if self.variable == "frequency":
            return UnitOfFrequency.HERTZ
        if self.variable == "energy":
            return UnitOfEnergy.WATT_HOUR
        if self.variable == "pulse_height":
            return UnitOfTime.MICROSECONDS
        if self.variable == "required_voltage":
            return UnitOfElectricPotential.VOLT
        return None

    @property
    def last_reset(self):
        if self.variable == "energy":
            return datetime.combine(datetime.today(), time.min)
        return None

    @callback
    def _async_update_data(self):
        _LOGGER.info(f'updating value of {self.variable}')
        if self.variable == "temperature":
            self._state = self.sensor_connector.data['temperature']

        if self.variable == "power":
            self._state = self.sensor_connector.data['power']

        if self.variable == "current":
            self._state = self.sensor_connector.data['current']

        if self.variable == "voltage":
            self._state = self.sensor_connector.data['voltage']

        if self.variable == "frequency":
            self._state = self.sensor_connector.data['frequency']

        if self.variable == "pulse_height":
            self._state = self.sensor_connector.data['pulse_height']

        if self.variable == "energy":
            self._state = self.sensor_connector.data['energy']

        if self.variable == "relay":
            self._state = self.sensor_connector.data['relay']

        if self.variable == "fan":
            self._state = self.sensor_connector.data['fan']

        if self.variable == "required_voltage":
            self._state = self.sensor_connector.data['required_voltage']


class SensorConnector:
    def __init__(self, hass, solareco_host, solareco_port):
        self.hass = hass
        self.solareco_host = solareco_host
        self.solareco_port = solareco_port
        self.data = {
            "temperature": None,
            "voltage": None,
            "current": None,
            "power": None,
            "frequency": None,
            "energy": None,
            "pulse_height": None,
            "relay": None,
            "fan": None,
            "required_voltage": None
        }

    def update(self):
        try:
            with telnetlib.Telnet(self.solareco_host, self.solareco_port) as tn:
                line = tn.read_until(b'\n').decode('ascii')
                line_segments = line.split()
                if len(line_segments) == 12:
                    self.data['relay'] = line_segments[2][2:]
                    self.data['fan'] = line_segments[3][2:]
                    self.data['required_voltage'] = line_segments[4][2:]
                    self.data['voltage'] = line_segments[5][:-1]
                    self.data['current'] = line_segments[6][:-2]
                    self.data['power'] = line_segments[7][:-1]
                    self.data['frequency'] = line_segments[8][:-2]
                    self.data['temperature'] = line_segments[9][:-1]
                    self.data['pulse_height'] = line_segments[10][:-2]
                    self.data['energy'] = line_segments[11][:-2]
                    _LOGGER.info("data: " + str(self.data))
                    dispatcher_send(self.hass, SIGNAL)
        except:
            _LOGGER.error("can't connect to SolarEco")
