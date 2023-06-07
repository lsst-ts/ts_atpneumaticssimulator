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

import asyncio
import logging
import types
import typing

import jsonschema
from lsst.ts import tcpip, utils
from lsst.ts.idl.enums import ATPneumatics

from .dataclasses import LoadCell, M1AirPressure, M2AirPressure, MainAirSourcePressure
from .enums import Ack, CommandKey, Event, Telemetry
from .pneumatics_server_simulator import PneumaticsServerSimulator
from .schemas.registry import registry

__all__ = ["PneumaticsSimulator"]

CMD_ITEMS_TO_IGNORE = frozenset({CommandKey.ID, CommandKey.VALUE})


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

        # Tasks used to run the methods that simulate
        # opening and closing M1 covers and cell vents.
        self._close_m1_covers_task = utils.make_done_future()
        self._open_m1_covers_task = utils.make_done_future()
        self._close_cell_vents_task = utils.make_done_future()
        self._open_cell_vents_task = utils.make_done_future()

        # Event data.
        self.main_valve_state_data = ATPneumatics.AirValveState.CLOSED
        self.m1_set_pressure_data = 0.0
        self.m2_set_pressure_data = 0.0
        self.m1_state_data = ATPneumatics.AirValveState.CLOSED
        self.m2_state_data = ATPneumatics.AirValveState.CLOSED

        # TODO DM-38912 Make this configurable.
        # Configuration items.
        self.m1_covers_close_time = 0.0
        self.m1_covers_open_time = 0.0
        self.cell_vents_close_time = 0.0
        self.cell_vents_open_time = 0.0
        self.main_pressure = 0.0

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
            "closeInstrumentAirValve": self.close_instrument_air_valve,
            "closeM1CellVents": self.close_m1_cell_vents,
            "closeM1Cover": self.close_m1_cover,
            "closeMasterAirSupply": self.close_master_air_supply,
            "m1CloseAirValve": self.m1_close_air_valve,
            "m1OpenAirValve": self.m1_open_air_valve,
            "m1SetPressure": self.m1_set_pressure,
            "m2CloseAirValve": self.m2_close_air_valve,
            "m2OpenAirValve": self.m2_open_air_valve,
            "m2SetPressure": self.m2_set_pressure,
            "openInstrumentAirValve": self.open_instrument_air_valve,
            "openM1CellVents": self.open_m1_cell_vents,
            "openM1Cover": self.open_m1_cover,
            "openMasterAirSupply": self.open_master_air_supply,
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
        await self._write_evt(evt_id=Event.M1SETPRESSURE, pressure=m1_pressure)
        await self._write_evt(evt_id=Event.M2SETPRESSURE, pressure=m2_pressure)
        self.m1_covers_close_time = m1_covers_close_time
        self.m1_covers_open_time = m1_covers_open_time
        self.cell_vents_close_time = cell_vents_close_time
        self.cell_vents_open_time = cell_vents_open_time
        self.main_pressure = main_pressure
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
        await self._write_evt(evt_id=Event.ESTOP, triggered=False)
        await self.set_cell_vents_events(closed=True, opened=False)
        await self.set_m1_cover_events(closed=True, opened=False)
        await self._write_evt(
            evt_id=Event.INSTRUMENTSTATE,
            state=ATPneumatics.AirValveState.OPENED,
        )
        await self._write_evt(
            evt_id=Event.M1STATE, state=ATPneumatics.AirValveState.OPENED
        )
        await self._write_evt(
            evt_id=Event.M2STATE, state=ATPneumatics.AirValveState.OPENED
        )
        await self._write_evt(
            evt_id=Event.MAINVALVESTATE, state=ATPneumatics.AirValveState.OPENED
        )
        await self._write_evt(
            evt_id=Event.POWERSTATUS, powerOnL1=True, powerOnL2=True, powerOnL3=True
        )

    async def cmd_evt_dispatch_callback(self, data: typing.Any) -> None:
        data_ok = await self.verify_data(data=data)
        if not data_ok:
            await self.write_noack_response(sequence_id=data[CommandKey.SEQUENCE_ID])
            return

        await self.write_ack_response(sequence_id=data[CommandKey.SEQUENCE_ID])

        cmd = data[CommandKey.ID].replace("cmd_", "")
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
        if CommandKey.ID not in data or CommandKey.SEQUENCE_ID not in data:
            self.log.error(f"Received invalid {data=}. Ignoring.")
            return False
        payload_id = data[CommandKey.ID].replace("cmd_", "command_")
        if payload_id not in registry:
            self.log.error(f"Unknown command in {data=}.")
            return False

        sequence_id = data[CommandKey.SEQUENCE_ID]
        if self.last_sequence_id == 0:
            self.last_sequence_id = sequence_id
        else:
            if sequence_id - self.last_sequence_id != 1:
                return False

        json_schema = registry[payload_id]
        try:
            jsonschema.validate(data, json_schema)
        except jsonschema.ValidationError as e:
            self.log.exception("Validation failed.", e)
            return False
        return True

    async def close_instrument_air_valve(
        self, sequence_id: int, **kwargs: dict[str, typing.Any]
    ) -> None:
        # TODO DM-39012: Add simulator code.
        await self.write_success_response(sequence_id=sequence_id)

    async def close_m1_cell_vents(
        self, sequence_id: int, **kwargs: dict[str, typing.Any]
    ) -> None:
        # TODO DM-39012: Add simulator code.
        await self.write_success_response(sequence_id=sequence_id)

    async def close_m1_cover(
        self, sequence_id: int, **kwargs: dict[str, typing.Any]
    ) -> None:
        # TODO DM-39012: Add simulator code.
        await self.write_success_response(sequence_id=sequence_id)

    async def close_master_air_supply(
        self, sequence_id: int, **kwargs: dict[str, typing.Any]
    ) -> None:
        # TODO DM-39012: Add simulator code.
        await self.write_success_response(sequence_id=sequence_id)

    async def m1_close_air_valve(
        self, sequence_id: int, **kwargs: dict[str, typing.Any]
    ) -> None:
        # TODO DM-39012: Add simulator code.
        await self.write_success_response(sequence_id=sequence_id)

    async def m1_open_air_valve(
        self, sequence_id: int, **kwargs: dict[str, typing.Any]
    ) -> None:
        # TODO DM-39012: Add simulator code.
        await self.write_success_response(sequence_id=sequence_id)

    async def m1_set_pressure(
        self, sequence_id: int, **kwargs: dict[str, typing.Any]
    ) -> None:
        # TODO DM-39012: Add simulator code.
        await self.write_success_response(sequence_id=sequence_id)

    async def m2_close_air_valve(
        self, sequence_id: int, **kwargs: dict[str, typing.Any]
    ) -> None:
        # TODO DM-39012: Add simulator code.
        await self.write_success_response(sequence_id=sequence_id)

    async def m2_open_air_valve(
        self, sequence_id: int, **kwargs: dict[str, typing.Any]
    ) -> None:
        # TODO DM-39012: Add simulator code.
        await self.write_success_response(sequence_id=sequence_id)

    async def m2_set_pressure(
        self, sequence_id: int, **kwargs: dict[str, typing.Any]
    ) -> None:
        # TODO DM-39012: Add simulator code.
        await self.write_success_response(sequence_id=sequence_id)

    async def open_instrument_air_valve(
        self, sequence_id: int, **kwargs: dict[str, typing.Any]
    ) -> None:
        # TODO DM-39012: Add simulator code.
        await self.write_success_response(sequence_id=sequence_id)

    async def open_m1_cell_vents(
        self, sequence_id: int, **kwargs: dict[str, typing.Any]
    ) -> None:
        # TODO DM-39012: Add simulator code.
        await self.write_success_response(sequence_id=sequence_id)

    async def open_m1_cover(
        self, sequence_id: int, **kwargs: dict[str, typing.Any]
    ) -> None:
        # TODO DM-39012: Add simulator code.
        await self.write_success_response(sequence_id=sequence_id)

    async def open_master_air_supply(
        self, sequence_id: int, **kwargs: dict[str, typing.Any]
    ) -> None:
        # TODO DM-39012: Add simulator code.
        await self.write_success_response(sequence_id=sequence_id)

    async def write_response(self, response: str, sequence_id: int) -> None:
        data = {CommandKey.ID: response, CommandKey.SEQUENCE_ID: sequence_id}
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
        # This needs to be cleaned up as soon as we have moved to Kafka.
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
            await self.start_tasks()
        else:
            await self.stop_tasks()

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

    async def start_tasks(self) -> None:
        """Start background tasks and send events."""
        await self.configure()
        await self.initialize()

    async def stop_tasks(self) -> None:
        """Stop background tasks."""
        self._close_m1_covers_task.cancel()
        self._open_m1_covers_task.cancel()
        self._close_cell_vents_task.cancel()
        self._open_cell_vents_task.cancel()

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
        assert not (closed and opened)
        if not (closed or opened):
            await self._write_evt(
                evt_id=Event.CELLVENTSTATE, state=ATPneumatics.CellVentState.INMOTION
            )

        await self._write_evt(
            evt_id=Event.M1VENTSLIMITSWITCHES,
            ventsClosedActive=closed,
            ventsOpenedActive=opened,
        )
        if opened:
            await self._write_evt(
                evt_id=Event.M1VENTSPOSITION, position=ATPneumatics.VentsPosition.OPENED
            )
            await self._write_evt(
                evt_id=Event.CELLVENTSTATE, state=ATPneumatics.CellVentState.OPENED
            )
        elif closed:
            await self._write_evt(
                evt_id=Event.M1VENTSPOSITION, position=ATPneumatics.VentsPosition.CLOSED
            )
            await self._write_evt(
                evt_id=Event.CELLVENTSTATE, state=ATPneumatics.CellVentState.CLOSED
            )
        else:
            await self._write_evt(
                evt_id=Event.M1VENTSPOSITION,
                position=ATPneumatics.VentsPosition.PARTIALLYOPENED,
            )

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
        await self._write_evt(
            evt_id=Event.M1COVERLIMITSWITCHES,
            cover1ClosedActive=closed,
            cover2ClosedActive=closed,
            cover3ClosedActive=closed,
            cover4ClosedActive=closed,
            cover1OpenedActive=opened,
            cover2OpenedActive=opened,
            cover3OpenedActive=opened,
            cover4OpenedActive=opened,
        )
        if opened and closed:
            await self._write_evt(
                evt_id=Event.M1COVERSTATE, state=ATPneumatics.MirrorCoverState.INVALID
            )
        elif opened:
            await self._write_evt(
                evt_id=Event.M1COVERSTATE, state=ATPneumatics.MirrorCoverState.OPENED
            )
        elif closed:
            await self._write_evt(
                evt_id=Event.M1COVERSTATE, state=ATPneumatics.MirrorCoverState.CLOSED
            )
        else:
            await self._write_evt(
                evt_id=Event.M1COVERSTATE, state=ATPneumatics.MirrorCoverState.INMOTION
            )

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
            main_valve_open = self.main_valve_state_data == opened_state

            if main_valve_open and self.m1_state_data == opened_state:
                self.m1_air_pressure.pressure = self.m1_set_pressure_data
            else:
                self.m1_air_pressure.pressure = 0

            if main_valve_open and self.m2_state_data == opened_state:
                self.m2_air_pressure.pressure = self.m2_set_pressure_data
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

    def __enter__(self) -> None:
        # This class only implements an async context manager.
        raise NotImplementedError("Use 'async with' instead.")

    def __exit__(
        self,
        type: typing.Type[BaseException],
        value: BaseException,
        traceback: types.TracebackType,
    ) -> None:
        # __exit__ should exist in pair with __enter__ but never be executed.
        raise NotImplementedError("Use 'async with' instead.")

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
