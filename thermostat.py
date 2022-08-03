import asyncio
from enum import Enum
from typing import Tuple, Optional
from datetime import datetime, timedelta, time

import pytz

import fan_scripting
from fan_scripting import State, onoff_toggle, get_state


class Thermostat:
    class TstatMode(Enum):
        AUTO = "AUTO"
        OFF = "OFF"
        HEAT = "HEAT"
        COOL = "COOL"

    class Result(Enum):
        DEVICE_ERROR = "DEVICE_ERROR"
        NO_CHANGE = "NO_CHANGE"
        SUCCESS = "SUCCESS"
        COOLDOWN = "COOLDOWN"
        NO_ACTION = "NO_ACTION"

    def __init__(self, tstat_mode: TstatMode = TstatMode.AUTO, setpoint_F: float = 70.0, cooldown_duration_s: int = 300):
        self.tstat_mode: Thermostat.TstatMode = tstat_mode

        self.heat_setpoint = setpoint_F
        self.cool_setpoint = setpoint_F

        self.last_command_ts: datetime = datetime.min
        self.last_command_ts = self.last_command_ts.replace(tzinfo=pytz.UTC)

        self.cooldown_duration: timedelta = timedelta(seconds=cooldown_duration_s)

        self.previous_command = State.UNKNOWN

        self.control_loop_ts: datetime = datetime.min
        self.control_loop_ts = self.control_loop_ts.replace(tzinfo=pytz.UTC)

        self.schedule_on: list[Tuple[time, time]] = [
            (time(hour=8, minute=0, second=0), time(hour=23, minute=59, second=59))
        ]

        self.schedule_timezone = pytz.timezone("US/Pacific")

        self.tstat_mode_override: Optional[Thermostat.TstatMode] = None

    def is_on_cooldown(self) -> bool:
        return self.control_loop_ts - self.last_command_ts < self.cooldown_duration

    def generate_command(self, current_temp_F: float) -> State:
        new_command: State = State.OFF
        if self.cool_setpoint < current_temp_F:
            new_command = State.ON
        return new_command

    def needs_command(self, new_command: State, force: bool = False):
        return force or new_command != self.previous_command

    def fan_control(self, new_command: State) -> Tuple[Result, State]:
        try:
            asyncio.run(onoff_toggle("Fan", new_command))
            self.previous_command = new_command
            self.last_command_ts = self.control_loop_ts
        except:
            return Thermostat.Result.DEVICE_ERROR, self.previous_command
        return Thermostat.Result.SUCCESS, new_command

    def get_scheduled_mode(self, ts: datetime) -> TstatMode:
        for segment in self.schedule_on:
            if segment[0] < ts.astimezone().time() < segment[1]:
                return Thermostat.TstatMode.COOL

        return Thermostat.TstatMode.OFF

    def do_control(self, current_temp_F: float) -> Tuple[Result, State]:
        self.control_loop_ts: datetime = datetime.now(pytz.UTC)

        self.tstat_mode = self.get_scheduled_mode(self.control_loop_ts)

        tstat_mode_to_use: Thermostat.TstatMode = self.tstat_mode_override or self.tstat_mode

        if tstat_mode_to_use == Thermostat.TstatMode.OFF:
            return Thermostat.Result.NO_ACTION, self.previous_command

        if self.is_on_cooldown():
            return Thermostat.Result.COOLDOWN, self.previous_command

        new_command: State = self.generate_command(current_temp_F)

        if not self.needs_command(new_command):
            return Thermostat.Result.NO_CHANGE, new_command

        return self.fan_control(new_command)

    @staticmethod
    def get_fan_state() -> fan_scripting.State:
        return asyncio.run(get_state("Fan"))
