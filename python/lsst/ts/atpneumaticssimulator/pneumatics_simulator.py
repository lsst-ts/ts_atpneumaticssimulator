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

from __future__ import annotations

__all__ = ["PneumaticsSimulator"]

import asyncio
import logging
import types
import typing

import jsonschema
from lsst.ts import tcpip, utils
from lsst.ts.idl.enums import ATPneumatics

from .dataclasses import (
    LoadCell,
    M1AirPressure,
    M1CoverLimitSwitches,
    M1VentsLimitSwitches,
    M2AirPressure,
    MainAirSourcePressure,
    PowerStatus,
)
from .enums import Ack, Command, CommandArgument, Event, OpenCloseState, Telemetry
from .pneumatics_server_simulator import PneumaticsServerSimulator
from .schemas.registry import registry

CMD_ITEMS_TO_IGNORE = frozenset({CommandArgument.ID, CommandArgument.VALUE})


class PneumaticsSimulator:
    """Simulate the ATPneumatics system."""

    def __init__(self) -> None:
        self.log = logging.getLogger(type(self).__name__)
        self.cmd_evt_server = PneumaticsServerSimulator(
            host=tcpip.LOCALHOST_IPV4,
            port=5000,
            log=self.log,
            dispatch_callback=self.cmd_evt_dispatch_callback,
            connect_callback=self.cmd_evt_connect_callback,
            name="CmdEvtPneumaticsServer",
        )
        self.telemetry_server = PneumaticsServerSimulator(
            host=tcpip.LOCALHOST_IPV4,
            port=6000,
            log=self.log,
            dispatch_callback=self.telemetry_dispatch_callback,
            connect_callback=self.tel_connect_callback,
            name="TelemetryPneumaticsServer",
        )

        # Interval between telemetry updates [sec].
        self.telemetry_interval = 1.0

        # Task that runs while the telemetry_loop runs.
        self._telemetry_task = utils.make_done_future()

        # Keep track of opening and closing states of the covers and vents.
        self.m1_covers_state = OpenCloseState.CLOSED
        self.m1_vents_state = OpenCloseState.CLOSED

        # Event data.
        self.cell_vents_state = ATPneumatics.CellVentState.CLOSED
        self.e_stop = False
        self.instrument_state = ATPneumatics.AirValveState.CLOSED
        self.m1_cover_limit_switches = M1CoverLimitSwitches()
        self.m1_cover_state = ATPneumatics.MirrorCoverState.CLOSED
        self.m1_pressure = 0.0
        self.m1_state = ATPneumatics.AirValveState.CLOSED
        self.m1_vents_limit_switches = M1VentsLimitSwitches()
        self.m1_vents_position = ATPneumatics.VentsPosition.CLOSED
        self.m2_cover_state = ATPneumatics.MirrorCoverState.CLOSED
        self.m2_pressure = 0.0
        self.m2_state = ATPneumatics.AirValveState.CLOSED
        self.main_valve_state = ATPneumatics.AirValveState.CLOSED
        self.power_status = PowerStatus()

        # TODO DM-38912 Make this configurable.
        # Configuration items.
        self.m1_covers_close_time = 0.0
        self.m1_covers_open_time = 0.0
        self.cell_vents_close_time = 0.0
        self.cell_vents_open_time = 0.0

        # Variables holding the data for the telemetry messages.
        self.load_cell = LoadCell()
        self.m1_air_pressure = M1AirPressure()
        self.m2_air_pressure = M2AirPressure()
        self.main_air_source_pressure = MainAirSourcePressure()

        # Keep track of the sequence_id as commands come dripping in. The
        # sequence ID should raise monotonally without gaps. If a gap is seen,
        # a NOACK should be returned.
        self.last_sequence_id = 0

        # Dict of command: function.
        self.dispatch_dict: dict[str, typing.Callable] = {
            Command.CLOSE_INSTRUMENT_AIR_VALE: self.do_close_instrument_air_valve,
            Command.CLOSE_M1_CELL_VENTS: self.do_close_m1_cell_vents,
            Command.CLOSE_M1_COVER: self.do_close_m1_cover,
            Command.CLOSE_MASTER_AIR_SUPPLY: self.do_close_master_air_supply,
            Command.M1_CLOSE_AIR_VALVE: self.do_m1_close_air_valve,
            Command.M1_OPEN_AIR_VALVE: self.do_m1_open_air_valve,
            Command.M1_SET_PRESSURE: self.do_m1_set_pressure,
            Command.M2_CLOSE_AIR_VALVE: self.do_m2_close_air_valve,
            Command.M2_OPEN_AIR_VALVE: self.do_m2_open_air_valve,
            Command.M2_SET_PRESSURE: self.do_m2_set_pressure,
            Command.OPEN_INSTRUMENT_AIR_VALVE: self.do_open_instrument_air_valve,
            Command.OPEN_M1_CELL_VENTS: self.do_open_m1_cell_vents,
            Command.OPEN_M1_COVER: self.do_open_m1_cover,
            Command.OPEN_MASTER_AIR_SUPPLY: self.do_open_master_air_supply,
        }

    # TODO DM-38912 Make this configurable.
    async def configure(
        self,
        m1_covers_close_time: float = 20.0,
        m1_covers_open_time: float = 20.0,
        cell_vents_close_time: float = 5.0,
        cell_vents_open_time: float = 1.0,
        m1_pressure: float = 5.0,
        m2_pressure: float = 6.0,
        main_pressure: float = 10.0,
        cell_load: float = 100.0,
    ) -> None:
        """Set configuration.

        Parameters
        ----------
        m1_covers_close_time : `float`
            Time to close M1 mirror covers [sec].
        m1_covers_open_time : `float`
            Time to open M1 mirror covers [sec].
        cell_vents_close_time : `float`
            Time to close cell vents [sec].
        cell_vents_open_time : `float`
            Time to open cell vents [sec].
        m1_pressure : `float`
            Initial M1 air pressure [Pa].
        m2_pressure : `float`
            Initial M2 air pressure [Pa].
        main_pressure : `float`
            Initial main air pressure [Pa].
        cell_load : `float`
            Initial cell load [kg].
        """
        assert m1_covers_close_time >= 0
        assert m1_covers_close_time >= 0
        assert cell_vents_close_time >= 0
        assert cell_vents_open_time >= 0
        assert m1_pressure > 0
        assert m2_pressure > 0
        assert main_pressure > 0
        assert cell_load > 0
        self.m1_pressure = m1_pressure
        self.m2_pressure = m2_pressure
        await self._write_evt(evt_id=Event.M1SETPRESSURE, pressure=self.m1_pressure)
        await self._write_evt(evt_id=Event.M2SETPRESSURE, pressure=self.m2_pressure)
        self.m1_covers_close_time = m1_covers_close_time
        self.m1_covers_open_time = m1_covers_open_time
        self.cell_vents_close_time = cell_vents_close_time
        self.cell_vents_open_time = cell_vents_open_time
        self.main_air_source_pressure.pressure = main_pressure
        self.load_cell.cellLoad = cell_load

    async def initialize(self) -> None:
        """Initialize events and telemetry.

        * instrumentState
        * m1CoverLimitSwitches
        * m1CoverState
        * m1SetPressure
        * m1State
        * cellVentsState (should be named m1VentsState)
        * m1VentsLimitSwitches
        * m1VentsPosition
        * m2SetPressure
        * m2State
        * mainValveState
        * powerStatus
        """
        self.e_stop = False
        await self._write_evt(evt_id=Event.ESTOP, triggered=self.e_stop)
        await self.set_cell_vents_events(closed=True, opened=False)
        await self.set_m1_cover_events(closed=True, opened=False)
        self.instrument_state = ATPneumatics.AirValveState.OPENED
        await self._write_evt(evt_id=Event.INSTRUMENTSTATE, state=self.instrument_state)
        self.m1_state = ATPneumatics.AirValveState.OPENED
        await self._write_evt(evt_id=Event.M1STATE, state=self.m1_state)
        self.m2_state = ATPneumatics.AirValveState.OPENED
        await self._write_evt(evt_id=Event.M2STATE, state=self.m2_state)
        self.main_valve_state = ATPneumatics.AirValveState.OPENED
        await self._write_evt(evt_id=Event.MAINVALVESTATE, state=self.main_valve_state)
        self.power_status.powerOnL1 = True
        self.power_status.powerOnL2 = True
        self.power_status.powerOnL3 = True
        await self._write_evt(
            evt_id=Event.POWERSTATUS,
            powerOnL1=self.power_status.powerOnL1,
            powerOnL2=self.power_status.powerOnL2,
            powerOnL3=self.power_status.powerOnL3,
        )

    async def cmd_evt_dispatch_callback(self, data: typing.Any) -> None:
        data_ok = await self.verify_data(data=data)
        if not data_ok:
            await self.write_noack_response(
                sequence_id=data[CommandArgument.SEQUENCE_ID]
            )
            return

        await self.write_ack_response(sequence_id=data[CommandArgument.SEQUENCE_ID])

        cmd = data[CommandArgument.ID]
        func = self.dispatch_dict[cmd]
        kwargs = {
            key: value for key, value in data.items() if key not in CMD_ITEMS_TO_IGNORE
        }
        await func(**kwargs)

    async def telemetry_dispatch_callback(self, data: typing.Any) -> None:
        pass

    async def verify_data(self, data: dict[str, typing.Any]) -> bool:
        """Verify the format and values of the data.

        The format of the data is described at
        https://github.com/lsst-ts/ts_labview_tcp_json
        as well as in the JSON schemas in the schemas directory.

        Parameters
        ----------
        data : `dict` of `any`
            The dict to be verified.

        Returns
        -------
        bool:
            Whether the data follows the correct format and has the correct
            contents or not.
        """
        if CommandArgument.ID not in data or CommandArgument.SEQUENCE_ID not in data:
            self.log.error(f"Received invalid {data=}. Ignoring.")
            return False
        payload_id = data[CommandArgument.ID].replace("cmd_", "command_")
        if payload_id not in registry:
            self.log.error(f"Unknown command in {data=}.")
            return False

        sequence_id = data[CommandArgument.SEQUENCE_ID]
        if sequence_id - self.last_sequence_id != 1:
            return False
        self.last_sequence_id = sequence_id

        json_schema = registry[payload_id]
        try:
            jsonschema.validate(data, json_schema)
        except jsonschema.ValidationError as e:
            self.log.exception("Validation failed.", e)
            return False
        return True

    async def do_close_instrument_air_valve(self, sequence_id: int) -> None:
        self.instrument_state = ATPneumatics.AirValveState.CLOSED
        await self._write_evt(evt_id=Event.INSTRUMENTSTATE, state=self.instrument_state)
        await self.write_success_response(sequence_id=sequence_id)

    async def do_close_m1_cell_vents(self, sequence_id: int) -> None:
        if self.m1_vents_state not in [OpenCloseState.CLOSING, OpenCloseState.CLOSED]:
            self.m1_vents_state = OpenCloseState.CLOSING
            if self.m1_vents_position != ATPneumatics.VentsPosition.CLOSED:
                await self.set_cell_vents_events(closed=False, opened=False)
                await asyncio.sleep(self.cell_vents_close_time)
            await self.set_cell_vents_events(closed=True, opened=False)
            self.m1_vents_state = OpenCloseState.CLOSED
        await self.write_success_response(sequence_id=sequence_id)

    async def do_close_m1_cover(self, sequence_id: int) -> None:
        if self.m1_covers_state not in [OpenCloseState.CLOSING, OpenCloseState.CLOSED]:
            self.m1_covers_state = OpenCloseState.CLOSING
            if self.m1_cover_state != ATPneumatics.MirrorCoverState.CLOSED:
                await self.set_m1_cover_events(closed=False, opened=False)
                await asyncio.sleep(self.m1_covers_close_time)
            await self.set_m1_cover_events(closed=True, opened=False)
            self.m1_covers_state = OpenCloseState.CLOSED
        await self.write_success_response(sequence_id=sequence_id)

    async def do_close_master_air_supply(self, sequence_id: int) -> None:
        self.main_valve_state = ATPneumatics.AirValveState.CLOSED
        await self._write_evt(evt_id=Event.MAINVALVESTATE, state=self.main_valve_state)
        await self.write_success_response(sequence_id=sequence_id)

    async def do_m1_close_air_valve(self, sequence_id: int) -> None:
        self.m1_state = ATPneumatics.AirValveState.CLOSED
        await self._write_evt(evt_id=Event.M1STATE, state=self.m1_state)
        await self.write_success_response(sequence_id=sequence_id)

    async def do_m1_open_air_valve(self, sequence_id: int) -> None:
        self.m1_state = ATPneumatics.AirValveState.OPENED
        await self._write_evt(evt_id=Event.M1STATE, state=self.m1_state)
        await self.write_success_response(sequence_id=sequence_id)

    async def do_m1_set_pressure(self, sequence_id: int, pressure: float) -> None:
        self.m1_pressure = pressure
        await self._write_evt(evt_id=Event.M1SETPRESSURE, pressure=self.m1_pressure)
        await self.write_success_response(sequence_id=sequence_id)

    async def do_m2_close_air_valve(self, sequence_id: int) -> None:
        self.m2_state = ATPneumatics.AirValveState.CLOSED
        await self._write_evt(evt_id=Event.M2STATE, state=self.m2_state)
        await self.write_success_response(sequence_id=sequence_id)

    async def do_m2_open_air_valve(self, sequence_id: int) -> None:
        self.m2_state = ATPneumatics.AirValveState.OPENED
        await self._write_evt(evt_id=Event.M2STATE, state=self.m2_state)
        await self.write_success_response(sequence_id=sequence_id)

    async def do_m2_set_pressure(self, sequence_id: int, pressure: float) -> None:
        self.m2_pressure = pressure
        await self._write_evt(evt_id=Event.M2SETPRESSURE, pressure=self.m2_pressure)
        await self.write_success_response(sequence_id=sequence_id)

    async def do_open_instrument_air_valve(self, sequence_id: int) -> None:
        self.instrument_state = ATPneumatics.AirValveState.OPENED
        await self._write_evt(evt_id=Event.INSTRUMENTSTATE, state=self.instrument_state)
        await self.write_success_response(sequence_id=sequence_id)

    async def do_open_m1_cell_vents(self, sequence_id: int) -> None:
        if self.m1_vents_state not in [OpenCloseState.OPENING, OpenCloseState.OPEN]:
            self.m1_vents_state = OpenCloseState.OPENING
            if self.m1_vents_position != ATPneumatics.VentsPosition.OPENED:
                await self.set_cell_vents_events(closed=False, opened=False)
                await asyncio.sleep(self.cell_vents_open_time)
            await self.set_cell_vents_events(closed=False, opened=True)
            self.m1_vents_state = OpenCloseState.OPEN
        await self.write_success_response(sequence_id=sequence_id)

    async def do_open_m1_cover(self, sequence_id: int) -> None:
        if self.m1_covers_state not in [OpenCloseState.OPENING, OpenCloseState.OPEN]:
            self.m1_covers_state = OpenCloseState.OPENING
            if self.m1_cover_state != ATPneumatics.MirrorCoverState.OPENED:
                await self.set_m1_cover_events(closed=False, opened=False)
                await asyncio.sleep(self.m1_covers_open_time)
            await self.set_m1_cover_events(closed=False, opened=True)
            self.m1_covers_state = OpenCloseState.OPEN
        await self.write_success_response(sequence_id=sequence_id)

    async def do_open_master_air_supply(self, sequence_id: int) -> None:
        self.main_valve_state = ATPneumatics.AirValveState.OPENED
        await self._write_evt(evt_id=Event.MAINVALVESTATE, state=self.main_valve_state)
        await self.write_success_response(sequence_id=sequence_id)

    async def write_response(self, response: str, sequence_id: int) -> None:
        data = {CommandArgument.ID: response, CommandArgument.SEQUENCE_ID: sequence_id}
        await self.cmd_evt_server.write_json(data=data)

    async def write_ack_response(self, sequence_id: int) -> None:
        await self.write_response(Ack.ACK, sequence_id)

    async def write_fail_response(self, sequence_id: int) -> None:
        await self.write_response(Ack.FAIL, sequence_id)

    async def write_noack_response(self, sequence_id: int) -> None:
        await self.write_response(Ack.NOACK, sequence_id)

    async def write_success_response(self, sequence_id: int) -> None:
        await self.write_response(Ack.SUCCESS, sequence_id)

    async def _write_evt(self, evt_id: str, **kwargs: typing.Any) -> None:
        await self.cmd_evt_server.write_json(data={"id": evt_id, **kwargs})

    async def _write_telemetry(self, tel_id: str, data: typing.Any) -> None:
        # TODO DM-39615 This needs to be cleaned up as soon as we have moved to
        #  Kafka.
        data_dict = data.get_vars() if hasattr(data, "get_vars") else vars(data)
        items = {k: v for k, v in data_dict.items() if not k.startswith("private")}

        items["id"] = tel_id
        await self.telemetry_server.write_json(data={**items})

    async def cmd_evt_connect_callback(self, server: tcpip.OneClientServer) -> None:
        """Callback function for when a cmd/evt client connects or disconnects.

        When a cmd/evt client connects, background tasks are started and events
        are sent.
        When the cmd/evt client disconnects, all background tasks get stopped.
        """
        if server.connected:
            await self.configure()
            await self.initialize()

    async def tel_connect_callback(self, server: tcpip.OneClientServer) -> None:
        """Callback function for when a tel client connects or disconnects.

        When a tel client connects, the telemetry loop is started.
        When the tel client disconnects, the telemetry loop is stopped.
        """
        if server.connected:
            if self._telemetry_task.done():
                self._telemetry_task = asyncio.create_task(self.telemetry_loop())
        else:
            self._telemetry_task.cancel()

    async def set_cell_vents_events(self, closed: bool, opened: bool) -> None:
        """Set m1VentsLimitSwitches, m1VentsPosition and cellVentsState events.

        Output any changes.

        Parameters
        ----------
        closed : `bool`
            Are the closed switches active?
        opened : `bool`
            Are the opened switches active?
        """
        if not (closed or opened):
            self.cell_vents_state = ATPneumatics.CellVentState.INMOTION
            await self._write_evt(
                evt_id=Event.CELLVENTSTATE, state=self.cell_vents_state
            )

        self.m1_vents_limit_switches.ventsClosedActive = closed
        self.m1_vents_limit_switches.ventsOpenedActive = opened
        await self._write_evt(
            evt_id=Event.M1VENTSLIMITSWITCHES,
            ventsClosedActive=self.m1_vents_limit_switches.ventsClosedActive,
            ventsOpenedActive=self.m1_vents_limit_switches.ventsOpenedActive,
        )
        if opened:
            self.m1_vents_position = ATPneumatics.VentsPosition.OPENED
        elif closed:
            self.m1_vents_position = ATPneumatics.VentsPosition.CLOSED
        else:
            self.m1_vents_position = ATPneumatics.VentsPosition.PARTIALLYOPENED
        await self._write_evt(
            evt_id=Event.M1VENTSPOSITION, position=self.m1_vents_position
        )
        if opened:
            self.cell_vents_state = ATPneumatics.CellVentState.OPENED
        elif closed:
            self.cell_vents_state = ATPneumatics.CellVentState.CLOSED
        await self._write_evt(evt_id=Event.CELLVENTSTATE, state=self.cell_vents_state)

    async def set_m1_cover_events(self, closed: bool, opened: bool) -> None:
        """Set m1CoverLimitSwitches and m1CoverState events.

        Output any changes.

        Parameters
        ----------
        closed : `bool`
            Are the closed switches active?
        opened : `bool`
            Are the opened switches active?
        """
        kwargs = dict()
        for num in range(1, 5):
            closed_attr_name = f"cover{num}ClosedActive"
            opened_attr_name = f"cover{num}OpenedActive"
            setattr(self.m1_cover_limit_switches, closed_attr_name, closed)
            setattr(self.m1_cover_limit_switches, opened_attr_name, opened)
            kwargs[closed_attr_name] = closed
            kwargs[opened_attr_name] = opened
        await self._write_evt(evt_id=Event.M1COVERLIMITSWITCHES, **kwargs)
        if opened and closed:
            self.m1_cover_state = ATPneumatics.MirrorCoverState.INVALID
        elif opened:
            self.m1_cover_state = ATPneumatics.MirrorCoverState.OPENED
        elif closed:
            self.m1_cover_state = ATPneumatics.MirrorCoverState.CLOSED
        else:
            self.m1_cover_state = ATPneumatics.MirrorCoverState.INMOTION
        await self._write_evt(evt_id=Event.M1COVERSTATE, state=self.m1_cover_state)

    async def telemetry_loop(self) -> None:
        """Output telemetry and events that have changed

        Notes
        -----
        Here are the telemetry topics that are output:

        * m1AirPressure
        * m2AirPressure
        * mainAirSourcePressure
        * loadCell

        See `update_events` for the events that are output.
        """
        while True:
            await self.update_telemetry()
            await asyncio.sleep(self.telemetry_interval)

    async def update_telemetry(self) -> None:
        """Output all telemetry data messages."""
        try:
            opened_state = ATPneumatics.AirValveState.OPENED
            main_valve_open = self.main_valve_state == opened_state

            if main_valve_open and self.m1_state == opened_state:
                self.m1_air_pressure.pressure = self.m1_pressure
            else:
                self.m1_air_pressure.pressure = 0

            if main_valve_open and self.m2_state == opened_state:
                self.m2_air_pressure.pressure = self.m2_pressure
            else:
                self.m2_air_pressure.pressure = 0

            await self._write_telemetry(
                tel_id=Telemetry.M1_AIR_PRESSURE,
                data=self.m1_air_pressure,
            )
            await self._write_telemetry(
                tel_id=Telemetry.M2_AIR_PRESSURE,
                data=self.m2_air_pressure,
            )
            await self._write_telemetry(
                tel_id=Telemetry.MAIN_AIR_SOURCE_PRESSURE,
                data=self.main_air_source_pressure,
            )
            await self._write_telemetry(
                tel_id=Telemetry.LOAD_CELL,
                data=self.load_cell,
            )
        except Exception as e:
            print(f"update_telemetry failed: {e}")
            raise

    async def __aenter__(self) -> PneumaticsSimulator:
        return self

    async def __aexit__(
        self,
        type: typing.Type[BaseException],
        value: BaseException,
        traceback: types.TracebackType,
    ) -> None:
        await self.cmd_evt_server.close()
        await self.telemetry_server.close()
