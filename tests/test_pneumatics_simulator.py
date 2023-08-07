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

import asyncio
import contextlib
import logging
import typing
import unittest

import jsonschema
from lsst.ts import atpneumaticssimulator, tcpip

# Standard timeout in seconds.
TIMEOUT = 2

EVENTS_TO_EXPECT = set(atpneumaticssimulator.Event)


class PneumaticsSimulatorTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.log = logging.getLogger(type(self).__name__)

    @contextlib.asynccontextmanager
    async def create_pneumatics_simulator(
        self,
    ) -> typing.AsyncGenerator[atpneumaticssimulator.PneumaticsSimulator, None]:
        async with atpneumaticssimulator.PneumaticsSimulator() as simulator:
            await simulator.cmd_evt_server.start_task
            await simulator.telemetry_server.start_task
            yield simulator

    @contextlib.asynccontextmanager
    async def create_cmd_evt_client(
        self, simulator: atpneumaticssimulator.PneumaticsSimulator
    ) -> typing.AsyncGenerator[tcpip.Client, None]:
        async with tcpip.Client(
            host=simulator.cmd_evt_server.host,
            port=simulator.cmd_evt_server.port,
            log=self.log,
            name="CmdEvtClient",
        ) as cmd_evt_client:
            await asyncio.wait_for(
                simulator.cmd_evt_server.connected_task, timeout=TIMEOUT
            )
            assert simulator.cmd_evt_server.connected
            assert cmd_evt_client.connected
            await self.verify_all_events(client=cmd_evt_client)
            yield cmd_evt_client

    @contextlib.asynccontextmanager
    async def create_telemetry_client(
        self, simulator: atpneumaticssimulator.PneumaticsSimulator
    ) -> typing.AsyncGenerator[tcpip.Client, None]:
        async with tcpip.Client(
            host=simulator.telemetry_server.host,
            port=simulator.telemetry_server.port,
            log=self.log,
            name="TelemetryClient",
        ) as telemetry_client:
            await asyncio.wait_for(
                simulator.telemetry_server.connected_task, timeout=TIMEOUT
            )
            assert simulator.telemetry_server.connected
            assert telemetry_client.connected
            yield telemetry_client

    async def verify_event(
        self,
        client: tcpip.Client,
        evt_name: str,
    ) -> None:
        data = await client.read_json()
        assert "id" in data
        assert data["id"] == evt_name

    async def verify_all_events(self, client: tcpip.Client) -> None:
        """Verify that all events have been emitted."""
        for i in range(len(EVENTS_TO_EXPECT)):
            data = await client.read_json()
            # No need for asserts here. If the data id is not present in
            # registry or the validation of the schema fails, the test will
            # fail as well.
            json_schema = atpneumaticssimulator.registry[
                f"logevent_{data['id'].removeprefix('evt_')}"
            ]
            jsonschema.validate(data, json_schema)

    async def verify_command_response(
        self,
        client: tcpip.Client,
        ack: atpneumaticssimulator.Ack,
        sequence_id: int,
    ) -> None:
        data = await client.read_json()
        assert atpneumaticssimulator.CommandArgument.ID in data
        assert atpneumaticssimulator.CommandArgument.SEQUENCE_ID in data
        assert data[atpneumaticssimulator.CommandArgument.ID] == ack
        assert data[atpneumaticssimulator.CommandArgument.SEQUENCE_ID] == sequence_id

    async def test_close_instrument_air_valve(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_cmd_evt_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandArgument.ID: "cmd_closeInstrumentAirValve",
                    atpneumaticssimulator.CommandArgument.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandArgument.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_event(
                client=cmd_evt_client,
                evt_name=atpneumaticssimulator.Event.INSTRUMENTSTATE,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    async def test_close_m1_cell_vents(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_cmd_evt_client(
            simulator
        ) as cmd_evt_client:
            # Mock a state where the M1 vents are open.
            simulator.m1_vents_state = atpneumaticssimulator.OpenCloseState.OPEN
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandArgument.ID: "cmd_closeM1CellVents",
                    atpneumaticssimulator.CommandArgument.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandArgument.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_event(
                client=cmd_evt_client,
                evt_name=atpneumaticssimulator.Event.M1VENTSLIMITSWITCHES,
            )
            await self.verify_event(
                client=cmd_evt_client,
                evt_name=atpneumaticssimulator.Event.M1VENTSPOSITION,
            )
            await self.verify_event(
                client=cmd_evt_client,
                evt_name=atpneumaticssimulator.Event.CELLVENTSTATE,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    async def test_close_m1_cover(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_cmd_evt_client(
            simulator
        ) as cmd_evt_client:
            # Mock a state where the M1 covers are open.
            simulator.m1_covers_state = atpneumaticssimulator.OpenCloseState.OPEN
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandArgument.ID: "cmd_closeM1Cover",
                    atpneumaticssimulator.CommandArgument.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandArgument.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_event(
                client=cmd_evt_client,
                evt_name=atpneumaticssimulator.Event.M1COVERLIMITSWITCHES,
            )
            await self.verify_event(
                client=cmd_evt_client,
                evt_name=atpneumaticssimulator.Event.M1COVERSTATE,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    async def test_close_master_air_supply(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_cmd_evt_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandArgument.ID: "cmd_closeMasterAirSupply",
                    atpneumaticssimulator.CommandArgument.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandArgument.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_event(
                client=cmd_evt_client,
                evt_name=atpneumaticssimulator.Event.MAINVALVESTATE,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    async def test_m1_close_air_valve(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_cmd_evt_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandArgument.ID: "cmd_m1CloseAirValve",
                    atpneumaticssimulator.CommandArgument.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandArgument.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_event(
                client=cmd_evt_client,
                evt_name=atpneumaticssimulator.Event.M1STATE,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    async def test_m1_open_air_valve(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_cmd_evt_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandArgument.ID: "cmd_m1OpenAirValve",
                    atpneumaticssimulator.CommandArgument.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandArgument.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_event(
                client=cmd_evt_client,
                evt_name=atpneumaticssimulator.Event.M1STATE,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    async def test_m1_set_pressure(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_cmd_evt_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandArgument.ID: "cmd_m1SetPressure",
                    atpneumaticssimulator.CommandArgument.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandArgument.PRESSURE: 0.0,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_event(
                client=cmd_evt_client,
                evt_name=atpneumaticssimulator.Event.M1SETPRESSURE,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    async def test_m2_close_air_valve(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_cmd_evt_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandArgument.ID: "cmd_m2CloseAirValve",
                    atpneumaticssimulator.CommandArgument.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandArgument.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_event(
                client=cmd_evt_client,
                evt_name=atpneumaticssimulator.Event.M2STATE,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    async def test_m2_open_air_valve(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_cmd_evt_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandArgument.ID: "cmd_m2OpenAirValve",
                    atpneumaticssimulator.CommandArgument.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandArgument.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_event(
                client=cmd_evt_client,
                evt_name=atpneumaticssimulator.Event.M2STATE,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    async def test_m2_set_pressure(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_cmd_evt_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandArgument.ID: "cmd_m2SetPressure",
                    atpneumaticssimulator.CommandArgument.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandArgument.PRESSURE: 0.0,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_event(
                client=cmd_evt_client,
                evt_name=atpneumaticssimulator.Event.M2SETPRESSURE,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    async def test_open_instrument_air_valve(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_cmd_evt_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandArgument.ID: "cmd_openInstrumentAirValve",
                    atpneumaticssimulator.CommandArgument.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandArgument.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_event(
                client=cmd_evt_client,
                evt_name=atpneumaticssimulator.Event.INSTRUMENTSTATE,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    async def test_open_m1_cell_vents(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_cmd_evt_client(
            simulator
        ) as cmd_evt_client:
            # Set a much shorter time to speed up the unit test.
            simulator.cell_vents_open_time = 0.1
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandArgument.ID: "cmd_openM1CellVents",
                    atpneumaticssimulator.CommandArgument.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandArgument.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_event(
                client=cmd_evt_client,
                evt_name=atpneumaticssimulator.Event.CELLVENTSTATE,
            )
            await self.verify_event(
                client=cmd_evt_client,
                evt_name=atpneumaticssimulator.Event.M1VENTSLIMITSWITCHES,
            )
            await self.verify_event(
                client=cmd_evt_client,
                evt_name=atpneumaticssimulator.Event.M1VENTSPOSITION,
            )
            await self.verify_event(
                client=cmd_evt_client,
                evt_name=atpneumaticssimulator.Event.CELLVENTSTATE,
            )
            await self.verify_event(
                client=cmd_evt_client,
                evt_name=atpneumaticssimulator.Event.M1VENTSLIMITSWITCHES,
            )
            await self.verify_event(
                client=cmd_evt_client,
                evt_name=atpneumaticssimulator.Event.M1VENTSPOSITION,
            )
            await self.verify_event(
                client=cmd_evt_client,
                evt_name=atpneumaticssimulator.Event.CELLVENTSTATE,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    async def test_open_m1_cover(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_cmd_evt_client(
            simulator
        ) as cmd_evt_client:
            # Set a much shorter time to speed up the unit test.
            simulator.m1_covers_open_time = 0.1
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandArgument.ID: "cmd_openM1Cover",
                    atpneumaticssimulator.CommandArgument.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandArgument.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_event(
                client=cmd_evt_client,
                evt_name=atpneumaticssimulator.Event.M1COVERLIMITSWITCHES,
            )
            await self.verify_event(
                client=cmd_evt_client,
                evt_name=atpneumaticssimulator.Event.M1COVERSTATE,
            )
            await self.verify_event(
                client=cmd_evt_client,
                evt_name=atpneumaticssimulator.Event.M1COVERLIMITSWITCHES,
            )
            await self.verify_event(
                client=cmd_evt_client,
                evt_name=atpneumaticssimulator.Event.M1COVERSTATE,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    async def test_open_master_air_supply(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_cmd_evt_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandArgument.ID: "cmd_openMasterAirSupply",
                    atpneumaticssimulator.CommandArgument.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandArgument.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_event(
                client=cmd_evt_client,
                evt_name=atpneumaticssimulator.Event.MAINVALVESTATE,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    async def test_non_existing_command(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_cmd_evt_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandArgument.ID: "non-existing",
                    atpneumaticssimulator.CommandArgument.SEQUENCE_ID: sequence_id,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.NOACK,
                sequence_id=sequence_id,
            )

    async def test_skip_sequence_id(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_cmd_evt_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandArgument.ID: "cmd_closeInstrumentAirValve",
                    atpneumaticssimulator.CommandArgument.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandArgument.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_event(
                client=cmd_evt_client,
                evt_name=atpneumaticssimulator.Event.INSTRUMENTSTATE,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

            # Skip sequence_id == 2 so we expect a NOACK.
            sequence_id = 3
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandArgument.ID: "cmd_closeInstrumentAirValve",
                    atpneumaticssimulator.CommandArgument.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandArgument.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.NOACK,
                sequence_id=sequence_id,
            )

    async def test_update_telemetry(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_cmd_evt_client(
            simulator
        ), self.create_telemetry_client(
            simulator
        ) as telemetry_client:
            # No need to call ``simulator.update_telemetry`` explicitly since
            # connecting with a cmd_evt_client starts the event and telemetry
            # loop.
            for _ in atpneumaticssimulator.Telemetry:
                data = await telemetry_client.read_json()
                # No need for asserts here. If the data id is not present in
                # registry or the validation of the schema fails, the test will
                # fail as well.
                json_schema = atpneumaticssimulator.registry[f"{data['id']}"]
                jsonschema.validate(data, json_schema)
