import asyncio
from enum import Enum

from kasa import SmartPlug, Discover, SmartDevice


class State(Enum):
    ON = "on"
    OFF = "off"
    UNKNOWN = "unknown"


async def discover() -> dict[str, SmartDevice]:
    devices: dict[str, SmartDevice] = await Discover.discover(timeout=10)
    ret: dict[str, SmartDevice] = {}
    for addr, dev in devices.items():
        await dev.update()
        # print(f"{addr} >> {dev}")
        ret[dev.alias] = dev
    return ret


async def connect_plug(host: str):
    plug = SmartPlug(host)
    await plug.update()
    # print(plug.alias)
    # await plug.turn_on()
    # await plug.set_led(True)


async def connect_plug(host: str):
    plug = SmartPlug(host)
    await plug.update()


async def onoff_toggle(alias: str, state: State):
    devices: dict[str, SmartDevice] = await discover()
    dev = devices[alias]
    await dev.update()
    if state == State.ON:
        await dev.turn_on()
    else:
        await dev.turn_off()


async def get_state(alias: str):
    ret: State = State.UNKNOWN
    try:
        devices: dict[str, SmartDevice] = await discover()
        dev = devices[alias]
        await dev.update()
        ret = State.ON if dev.is_on else State.OFF
    except Exception as ex:
        print(ex)
    return ret


async def main():
    devices: dict[str, SmartDevice] = await discover()
    await connect_plug(devices["Fan"].host)

try:
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
except AttributeError as e:
    # print(f"nvm, not windows")
    pass

if __name__ == "__main__":
    asyncio.run(main())
