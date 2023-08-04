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

import enum

__all__ = ["Ack", "Command", "CommandArgument", "Event", "OpenCloseState", "Telemetry"]


class Ack(str, enum.Enum):
    ACK = "ack"
    FAIL = "fail"
    NOACK = "noack"
    SUCCESS = "success"


class Command(str, enum.Enum):
    """Enum containing all command names."""

    CLOSE_INSTRUMENT_AIR_VALE = "cmd_closeInstrumentAirValve"
    CLOSE_M1_CELL_VENTS = "cmd_closeM1CellVents"
    CLOSE_M1_COVER = "cmd_closeM1Cover"
    CLOSE_MASTER_AIR_SUPPLY = "cmd_closeMasterAirSupply"
    M1_CLOSE_AIR_VALVE = "cmd_m1CloseAirValve"
    M1_OPEN_AIR_VALVE = "cmd_m1OpenAirValve"
    M1_SET_PRESSURE = "cmd_m1SetPressure"
    M2_CLOSE_AIR_VALVE = "cmd_m2CloseAirValve"
    M2_OPEN_AIR_VALVE = "cmd_m2OpenAirValve"
    M2_SET_PRESSURE = "cmd_m2SetPressure"
    OPEN_INSTRUMENT_AIR_VALVE = "cmd_openInstrumentAirValve"
    OPEN_M1_CELL_VENTS = "cmd_openM1CellVents"
    OPEN_M1_COVER = "cmd_openM1Cover"
    OPEN_MASTER_AIR_SUPPLY = "cmd_openMasterAirSupply"


class CommandArgument(str, enum.Enum):
    """Enum containing all possible command arguments."""

    ID = "id"
    PRESSURE = "pressure"
    SEQUENCE_ID = "sequence_id"
    VALUE = "value"


class Event(str, enum.Enum):
    CELLVENTSTATE = "evt_cellVentsState"
    ESTOP = "evt_eStop"
    INSTRUMENTSTATE = "evt_instrumentState"
    M1COVERLIMITSWITCHES = "evt_m1CoverLimitSwitches"
    M1COVERSTATE = "evt_m1CoverState"
    M1SETPRESSURE = "evt_m1SetPressure"
    M1STATE = "evt_m1State"
    M1VENTSLIMITSWITCHES = "evt_m1VentsLimitSwitches"
    M1VENTSPOSITION = "evt_m1VentsPosition"
    M2STATE = "evt_m2State"
    M2SETPRESSURE = "evt_m2SetPressure"
    MAINVALVESTATE = "evt_mainValveState"
    POWERSTATUS = "evt_powerStatus"


class OpenCloseState(enum.Enum):
    CLOSING = enum.auto()
    CLOSED = enum.auto()
    OPENING = enum.auto()
    OPEN = enum.auto()


class Telemetry(str, enum.Enum):
    LOAD_CELL = "tel_loadCell"
    M1_AIR_PRESSURE = "tel_m1AirPressure"
    M2_AIR_PRESSURE = "tel_m2AirPressure"
    MAIN_AIR_SOURCE_PRESSURE = "tel_mainAirSourcePressure"
