from enum import Enum
from time import sleep
from datetime import datetime
from typing import Any

import pytz
from adafruit_scd4x import SCD4X
from busio import I2C
from smbus2 import SMBus
from bme280 import BME280
from sqlalchemy import Column, DateTime, Integer, Numeric, Text

from compensated_temp import get_cpu_temperature
from display import Display
from sqlite import SqliteStore, BaseWithMigrations
from thermostat import Thermostat

try:
    # Transitional fix for breaking change in LTR559
    from ltr559 import LTR559
    ltr559 = LTR559()
except ImportError:
    import ltr559

from enviroplus import gas

from fan_scripting import State

from pms5003 import PMS5003, PMS5003Data

import board
import adafruit_scd4x


class Device(Enum):
    WEATHER = 'BME280'
    LIGHT_PROX = "LTR559"
    GAS = "gas"
    PARTICULATE_MATTER = "PMS5003"
    CO2 = "SCD4X"
    THERMOSTAT = "THERMOSTAT"
    DISPLAY = "DISPLAY"


def init_device_suite() -> dict[Device, Any]:
    bus = SMBus(1)
    i2c: I2C = board.I2C()

    weather_bme280: BME280 = BME280(i2c_dev=bus)
    light_prox: LTR559 = LTR559()
    pms5003: PMS5003 = PMS5003()
    scd4x: SCD4X = adafruit_scd4x.SCD4X(i2c)
    disp: Display = Display()
    tstat: Thermostat = Thermostat()

    # Do a run to throwaway readings to get started
    weather_bme280.get_temperature()
    weather_bme280.get_humidity()
    light_prox.update_sensor()
    pms5003.read()
    gas.read_all()
    # scd4x.start_low_periodic_measurement()
    disp.disp.reset()
    sleep(1)

    return {
        Device.WEATHER: weather_bme280,
        Device.LIGHT_PROX: light_prox,
        Device.GAS: gas,
        Device.PARTICULATE_MATTER: pms5003,
        Device.CO2: scd4x,
        Device.THERMOSTAT: tstat,
        Device.DISPLAY: disp
    }


def data_collect(datastore: SqliteStore, devices: dict[Device, Any] = None):
    ts_now = datetime.now(tz=pytz.UTC)

    temp_read_offset: float = 6  # sensor correction

    if devices is None:
        devices = init_device_suite()

    weather_bme280: BME280 = devices[Device.WEATHER]
    light_prox: LTR559 = devices[Device.LIGHT_PROX]
    bulk_gas = devices[Device.GAS]
    pms5003: PMS5003 = devices[Device.PARTICULATE_MATTER]
    scd4x: SCD4X = devices[Device.CO2]
    tstat: Thermostat = devices[Device.THERMOSTAT]
    disp: Display = devices[Device.DISPLAY]

    pm_readings: PMS5003Data = pms5003.read()
    weather_bme280.update_sensor()
    gas_readings = bulk_gas.read_all()

    temp_C: float = weather_bme280.get_temperature()
    temp: float = (temp_C * 9 / 5) + 32
    corrected_temp = temp - temp_read_offset

    instant: int = light_prox.get_lux()
    humidity_pct: float = weather_bme280.get_humidity()

    fan_state: State = tstat.get_fan_state()

    scd41_temp_offset_F: float = (scd4x.temperature_offset * 9 / 5) + 32
    co2_ppm: float = None
    scd41_temp_F: float = None
    scd41_humidity_pct: float = None
    if scd4x.data_ready:
        # print("SCD DATA")
        co2_ppm = scd4x.CO2
        scd41_temp_F = (scd4x.temperature * 9 / 5) + 32
        scd41_humidity_pct = scd4x.relative_humidity

    print(
        f"{ts_now.isoformat()}\t{temp:.2f}\t{corrected_temp:.2f}\t{temp_read_offset:.2f}\t{None}\t{gas_readings.reducing:.2f}\t{gas_readings.oxidising:.2f}\t{gas_readings.nh3:.2f}\t{instant:.2f}\t{humidity_pct:.2f}\t{None}\t{None}\t{None}\t{pm_readings.pm_ug_per_m3(1):.2f}\t{pm_readings.pm_ug_per_m3(2.5):.2f}\t{pm_readings.pm_ug_per_m3(10):.2f}\t{co2_ppm:.2f}\t{scd41_temp_F:.2f}\t{None}\t{scd41_humidity_pct:.2f}")

    message = f"temp: {corrected_temp:.1f}F"
    disp.write_text(message)

    data_collection: ControllerCollect = ControllerCollect(
        ts=ts_now, epoch_ts=int(ts_now.timestamp()),
        temp_F=temp, corrected_temp_F=corrected_temp, temp_offset_F=temp_read_offset, avg_cpu_temp_F=None,
        reducing_ohm=gas_readings.reducing, oxidizing_ohms=gas_readings.oxidising, ammonia_ohms=gas_readings.nh3,
        lux=instant,
        humidity_pct=humidity_pct,
        fan_state=fan_state.value, tstat_action=None, setpoint_F=tstat.cool_setpoint,
        pm1p0_ug_per_m3=pm_readings.pm_ug_per_m3(1), pm2p5_ug_per_m3=pm_readings.pm_ug_per_m3(2.5),
        pm10_ug_per_m3=pm_readings.pm_ug_per_m3(10),
        co2_ppm=co2_ppm, scd41_temp_F=scd41_temp_F, scd41_temp_offset_F=scd41_temp_offset_F,
        scd41_humidity_pct=scd41_humidity_pct
    )
    datastore.store_row(data_collection)


def do_control(datastore: SqliteStore, devices: dict[Device, Any] = None):
    ts_now = datetime.now(tz=pytz.UTC)

    weather_bme280: BME280 = devices[Device.WEATHER]
    tstat: Thermostat = devices[Device.THERMOSTAT]

    temp_read_offset: float = 6  # sensor correction
    temp_C: float = weather_bme280.get_temperature()
    temp: float = (temp_C * 9 / 5) + 32
    corrected_temp = temp - temp_read_offset

    tstat_run: Thermostat.Result
    fan_state: State
    tstat_run, fan_state = tstat.do_control(corrected_temp)

    data_collection: ControllerCollect = ControllerCollect(
        ts=ts_now, epoch_ts=int(ts_now.timestamp()),
        temp_F=None, corrected_temp_F=None, temp_offset_F=None, avg_cpu_temp_F=None,
        reducing_ohm=None, oxidizing_ohms=None, ammonia_ohms=None,
        lux=None,
        humidity_pct=None,
        fan_state=fan_state.value, tstat_action=tstat_run.value, setpoint_F=tstat.cool_setpoint,
        pm1p0_ug_per_m3=None, pm2p5_ug_per_m3=None,
        pm10_ug_per_m3=None,
        co2_ppm=None, scd41_temp_F=None, scd41_temp_offset_F=None,
        scd41_humidity_pct=None
    )
    datastore.store_row(data_collection)


def data_control_loop(devices: dict[Device, Any] = None):
    temp_read_offset: float = 6  # sensor correction

    if devices is None:
        devices = init_device_suite()

    weather_bme280: BME280 = devices[Device.WEATHER]
    light_prox: LTR559 = devices[Device.LIGHT_PROX]
    bulk_gas = devices[Device.GAS]
    pms5003: PMS5003 = devices[Device.PARTICULATE_MATTER]
    scd4x: SCD4X = devices[Device.CO2]
    tstat: Thermostat = devices[Device.THERMOSTAT]
    disp: Display = devices[Device.DISPLAY]

    scd41_temp_offset_F: float = (scd4x.temperature_offset * 9 / 5) + 32
    scd4x.start_low_periodic_measurement()
    while not scd4x.data_ready:
        print("waiting on scd4x to be ready")
        sleep(1)

    # init datastore
    datastore: SqliteStore = SqliteStore("sensors", [ControllerCollect])

    print(f"timestamp\ttemp_F\tcorrected_temp_F\ttemp_offset_F\tavg_cpu_temp_F\treducing_ohm\toxidizing_ohms\tammonia_ohms\tlux\thumidity_pct\tfan_state\ttstat_action\tsetpoint_F\tpm1.0 ug/m3\tpm2.5 ug/m3\tpm10 ug/m3\tco2 ppm\tscd41_temp_F\tscd41_temp_offset_F\tscd41_humidity_pct")
    tstat.tstat_mode_override = None  # Thermostat.TstatMode.OFF

    cpu_temps: list[float] = [get_cpu_temperature()] * 5
    sleep_time: int = 60
    while True:
        # Read all sensors
        ts_now = datetime.now(tz=pytz.UTC)
        pm_readings: PMS5003Data = pms5003.read()
        weather_bme280.update_sensor()
        gas_readings = bulk_gas.read_all()

        temp_C: float = weather_bme280.get_temperature()
        temp: float = (temp_C * 9 / 5) + 32
        corrected_temp = temp - temp_read_offset

        # cpu compensated
        cpu_temp: float = get_cpu_temperature()
        cpu_temps = cpu_temps[1:] + [cpu_temp]
        avg_cpu_temp: float = sum(cpu_temps) / float(len(cpu_temps))
        avg_cpu_temp_F: float = (avg_cpu_temp * 9 / 5) + 32

        instant: int = light_prox.get_lux()
        humidity_pct: float = weather_bme280.get_humidity()

        co2_ppm: float = None
        scd41_temp_F: float = None
        scd41_humidity_pct: float = None
        if scd4x.data_ready:
            # print("SCD DATA")
            co2_ppm = scd4x.CO2
            scd41_temp_F = (scd4x.temperature * 9 / 5) + 32
            scd41_humidity_pct = scd4x.relative_humidity

        tstat_run: Thermostat.Result
        fan_state: State
        tstat_run, fan_state = tstat.do_control(corrected_temp, co2_ppm)

        print(f"{ts_now.isoformat()}\t{temp:.2f}\t{corrected_temp:.2f}\t{temp_read_offset:.2f}\t{avg_cpu_temp_F:.2f}\t{gas_readings.reducing:.2f}\t{gas_readings.oxidising:.2f}\t{gas_readings.nh3:.2f}\t{instant:.2f}\t{humidity_pct:.2f}\t{fan_state.value}\t{tstat.cool_setpoint:.2f}\t{tstat_run.value}\t{pm_readings.pm_ug_per_m3(1):.2f}\t{pm_readings.pm_ug_per_m3(2.5):.2f}\t{pm_readings.pm_ug_per_m3(10):.2f}\t{co2_ppm:.2f}\t{scd41_temp_F:.2f}\t{scd41_temp_offset_F:.2f}\t{scd41_humidity_pct:.2f}")

        message = f"temp: {corrected_temp:.1f}F"
        disp.write_text(message)

        data_collection: ControllerCollect = ControllerCollect(
            ts=ts_now, epoch_ts=int(ts_now.timestamp()),
            temp_F=temp, corrected_temp_F=corrected_temp, temp_offset_F=temp_read_offset, avg_cpu_temp_F=avg_cpu_temp_F,
            reducing_ohm=gas_readings.reducing, oxidizing_ohms=gas_readings.oxidising, ammonia_ohms=gas_readings.nh3,
            lux=instant,
            humidity_pct=humidity_pct,
            fan_state=fan_state.value, tstat_action=tstat_run.value, setpoint_F=tstat.cool_setpoint,
            pm1p0_ug_per_m3=pm_readings.pm_ug_per_m3(1), pm2p5_ug_per_m3=pm_readings.pm_ug_per_m3(2.5), pm10_ug_per_m3=pm_readings.pm_ug_per_m3(10),
            co2_ppm=co2_ppm, scd41_temp_F=scd41_temp_F, scd41_temp_offset_F=scd41_temp_offset_F, scd41_humidity_pct=scd41_humidity_pct
        )
        datastore.store_row(data_collection)
        sleep(sleep_time)


class ControllerCollect(BaseWithMigrations):
    @classmethod
    def migrations(cls) -> list[str]:
        return [
            f"ALTER TABLE {cls.__tablename__} ADD COLUMN temp_offset_F;",
            f"ALTER TABLE {cls.__tablename__} ADD COLUMN setpoint_F;",
            f"ALTER TABLE {cls.__tablename__} ADD COLUMN pm1p0_ug_per_m3;",
            f"ALTER TABLE {cls.__tablename__} ADD COLUMN pm2p5_ug_per_m3;",
            f"ALTER TABLE {cls.__tablename__} ADD COLUMN pm10_ug_per_m3;",
            f"ALTER TABLE {cls.__tablename__} ADD COLUMN co2_ppm;",
            f"ALTER TABLE {cls.__tablename__} ADD COLUMN scd41_temp_F;",
            f"ALTER TABLE {cls.__tablename__} ADD COLUMN scd41_temp_offset_F;",
            f"ALTER TABLE {cls.__tablename__} ADD COLUMN scd41_humidity_pct;"
        ]

    __tablename__ = "controller"

    ts = Column(DateTime, primary_key=True, nullable=False)
    epoch_ts = Column(Integer, unique=True, nullable=False)

    temp_F = Column(Numeric)
    corrected_temp_F = Column(Numeric)
    temp_offset_F = Column(Numeric)
    avg_cpu_temp_F = Column(Numeric)

    reducing_ohm = Column(Numeric)
    oxidizing_ohms = Column(Numeric)
    ammonia_ohms = Column(Numeric)

    lux = Column(Numeric)

    humidity_pct = Column(Numeric)

    fan_state = Column(Text)
    tstat_action = Column(Text)
    setpoint_F = Column(Numeric)

    pm1p0_ug_per_m3 = Column(Numeric)
    pm2p5_ug_per_m3 = Column(Numeric)
    pm10_ug_per_m3 = Column(Numeric)

    co2_ppm = Column(Numeric)
    scd41_temp_F = Column(Numeric)
    scd41_temp_offset_F = Column(Numeric)
    scd41_humidity_pct = Column(Numeric)


if __name__ == "__main__":
    data_control_loop()
