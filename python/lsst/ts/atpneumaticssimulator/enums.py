# This file is part of ts_atpneumaticssimulator.
#
# Developed for the Vera Rubin Observatory Telescope and Site Systems.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from enum import Enum

__all__ = ["Ack", "CommandKey", "Event", "Telemetry"]


class Ack(str, Enum):
    ACK = "ack"
    FAIL = "fail"
    NOACK = "noack"
    SUCCESS = "success"


class CommandKey(str, Enum):
    ID = "id"
    PRESSURE = "pressure"
    SEQUENCE_ID = "sequence_id"
    VALUE = "value"


class Event(str, Enum):
    CELLVENTSTATE = "cellVentsState"
    ESTOP = "eStop"
    INSTRUMENTSTATE = "instrumentState"
    M1COVERLIMITSWITCHES = "m1CoverLimitSwitches"
    M1COVERSTATE = "m1CoverState"
    M1SETPRESSURE = "m1SetPressure"
    M1STATE = "m1State"
    M1VENTSLIMITSWITCHES = "m1VentsLimitSwitches"
    M1VENTSPOSITION = "m1VentsPosition"
    M2STATE = "m2State"
    M2SETPRESSURE = "m2SetPressure"
    MAINVALVESTATE = "mainValveState"
    POWERSTATUS = "powerStatus"


class Telemetry(str, Enum):
    LOAD_CELL = "loadCell"
    M1_AIR_PRESSURE = "m1AirPressure"
    M2_AIR_PRESSURE = "m2AirPressure"
    MAIN_AIR_SOURCE_PRESSURE = "mainAirSourcePressure"
