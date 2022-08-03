import asyncio
from time import sleep
from datetime import datetime, timedelta

import pytz
from smbus2 import SMBus
from bme280 import BME280

from compensated_temp import get_cpu_temperature
from thermostat import Thermostat

try:
    # Transitional fix for breaking change in LTR559
    from ltr559 import LTR559
    ltr559 = LTR559()
except ImportError:
    import ltr559

from enviroplus import gas

from fan_scripting import onoff_toggle, State

import ST7735
from PIL import Image, ImageDraw, ImageFont
from fonts.ttf import RobotoMedium as UserFont

from gas_calcs import Reducing, Oxidizing, Ammonia

from enviroplus.noise import Noise

# from pms5003 import PMS5003

# particulateSensor = PMS5003()
bus = SMBus(1)
weather_bme280 = BME280(i2c_dev=bus)

temp_read_offset: float = 17.3  # From rpi interferences
temp: float = (weather_bme280.get_temperature() * 9 / 5) + 32 - temp_read_offset
# print(f"Temperature: {temp:.2f} F")
#
# print(f"pressure: {weather_bme280.get_pressure():.2f} hPa, Humidity: {weather_bme280.get_humidity():.2f}%")
# print(weather_bme280.get_altitude())

lightProx: LTR559 = LTR559()
lightProx.update_sensor()
sleep(1)


def five_second_average_lux(lightProx: LTR559) -> float:
    ret: float = 0.0
    for i in range(5):
        inst: int = lightProx.get_lux()
        # print(inst)
        ret += inst
        sleep(1)

    return ret / 5.0

# lightProx.update_sensor()
# print(lightProx.get_integration_time())

instant: int = lightProx.get_lux()
avg: float = None  # five_second_average_lux(lightProx)
# print(f"{instant} Lux, {lightProx.get_proximity()}")

readings = gas.read_all()
# print(readings)
# print(f"Readings (R/O/A) ppm: {gas.read_reducing()} / {gas.read_oxidising()} / {gas.read_nh3()} {gas.read_all()}")
# print(f"Hydrogen (R/O/A) ppm: {Reducing.hydrogen(gas.read_reducing())} / {Oxidizing.hydrogen(gas.read_oxidising())} / {Ammonia.hydrogen(gas.read_nh3())}")

# readings = particulateSensor.read()
# print(readings)

## Display
disp = ST7735.ST7735(
    port=0,
    cs=1,
    dc=9,
    backlight=12,
    rotation=270,
    spi_speed_hz=10000000
)

disp.begin()

# Width and height to calculate text position.
WIDTH = disp.width
HEIGHT = disp.height

img = Image.new('RGB', (WIDTH, HEIGHT), color=(0, 0, 0))
draw = ImageDraw.Draw(img)

# Text settings.
font_size = 25
font = ImageFont.truetype(UserFont, font_size)
text_colour = (255, 255, 255)
back_colour = (0, 170, 170)

print(f"timestamp\ttemp_F\tcorrected_temp_F\tcomp_temp_F\tavg_cpu_temp_F\treducing_ohm\toxidizing_ohms\tammonia_ohms\tlux\thumidity_pct\tfan_state\ttstat_action")
tstat: Thermostat = Thermostat()
cpu_temps: list[float] = [get_cpu_temperature()] * 5
factor: float = 1.95
while True:
    ts_now = datetime.now(tz=pytz.UTC)
    weather_bme280.update_sensor()

    readings = gas.read_all()
    instant: int = lightProx.get_lux()

    temp_C: float = weather_bme280.get_temperature()
    temp: float = (temp_C * 9 / 5) + 32
    corrected_temp = temp - temp_read_offset

    # cpu compensated
    cpu_temp: float = get_cpu_temperature()
    cpu_temps = cpu_temps[1:] + [cpu_temp]
    avg_cpu_temp: float = sum(cpu_temps) / float(len(cpu_temps))
    avg_cpu_temp_F: float = (avg_cpu_temp * 9 / 5) + 32
    comp_temp: float = temp_C - ((avg_cpu_temp - temp_C) / factor)
    comp_temp_F: float = (comp_temp * 9 / 5) + 32

    tstat_run: Thermostat.Result
    fan_state: State
    tstat_run, fan_state = tstat.do_control(corrected_temp)

    print(f"{ts_now.isoformat()}\t{temp:.2f}\t{corrected_temp:.2f}\t{comp_temp_F:.2f}\t{avg_cpu_temp_F:.2f}\t{readings.reducing:.2f}\t{readings.oxidising:.2f}\t{readings.nh3:.2f}\t{instant:.2f}\t{weather_bme280.get_humidity():.2f}\t{fan_state.value}\t{tstat_run.value}")

    message = f"temp: {corrected_temp:.1f}F"
    size_x, size_y = draw.textsize(message, font)

    # Calculate text position
    x = (WIDTH - size_x) / 2
    y = (HEIGHT / 2) - (size_y / 2)

    # Draw background rectangle and write text.
    draw.rectangle((0, 0, 160, 80), back_colour)
    draw.text((x, y), message, font=font, fill=text_colour)
    disp.display(img)
    sleep(5)

# disp.set_backlight(0)

# microphone
noise = Noise()
low, mid, high, amp = noise.get_noise_profile()
low *= 128
mid *= 128
high *= 128
amp *= 64
print(f"Noise profile: low - {low}, mid - {mid}, high = {high}, amp - {amp}")
# while True:
#
#
#     img2 = img.copy()
#     draw.rectangle((0, 0, disp.width, disp.height), (0, 0, 0))
#     img.paste(img2, (1, 0))
#     draw.line((0, 0, 0, amp), fill=(int(low), int(mid), int(high)))
#
#     disp.display(img)

