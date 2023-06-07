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
    async def create_evt_cmd_client(
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
            json_schema = atpneumaticssimulator.registry[f"logevent_{data['id']}"]
            jsonschema.validate(data, json_schema)

    async def verify_command_response(
        self,
        client: tcpip.Client,
        ack: atpneumaticssimulator.Ack,
        sequence_id: int,
    ) -> None:
        data = await client.read_json()
        assert atpneumaticssimulator.CommandKey.ID in data
        assert atpneumaticssimulator.CommandKey.SEQUENCE_ID in data
        assert data[atpneumaticssimulator.CommandKey.ID] == ack
        assert data[atpneumaticssimulator.CommandKey.SEQUENCE_ID] == sequence_id

    # TODO DM-39012: Improve this test after adding the simulator code.
    async def test_close_instrument_air_valve(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_evt_cmd_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandKey.ID: "cmd_closeInstrumentAirValve",
                    atpneumaticssimulator.CommandKey.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandKey.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    # TODO DM-39012: Improve this test after adding the simulator code.
    async def test_close_m1_cell_vents(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_evt_cmd_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandKey.ID: "cmd_closeM1CellVents",
                    atpneumaticssimulator.CommandKey.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandKey.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    # TODO DM-39012: Improve this test after adding the simulator code.
    async def test_close_m1_cover(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_evt_cmd_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandKey.ID: "cmd_closeM1Cover",
                    atpneumaticssimulator.CommandKey.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandKey.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    # TODO DM-39012: Improve this test after adding the simulator code.
    async def test_close_master_air_supply(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_evt_cmd_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandKey.ID: "cmd_closeMasterAirSupply",
                    atpneumaticssimulator.CommandKey.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandKey.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    # TODO DM-39012: Improve this test after adding the simulator code.
    async def test_m1_close_air_valve(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_evt_cmd_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandKey.ID: "cmd_m1CloseAirValve",
                    atpneumaticssimulator.CommandKey.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandKey.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    # TODO DM-39012: Improve this test after adding the simulator code.
    async def test_m1_open_air_valve(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_evt_cmd_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandKey.ID: "cmd_m1OpenAirValve",
                    atpneumaticssimulator.CommandKey.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandKey.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    # TODO DM-39012: Improve this test after adding the simulator code.
    async def test_m1_set_pressure(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_evt_cmd_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandKey.ID: "cmd_m1SetPressure",
                    atpneumaticssimulator.CommandKey.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandKey.PRESSURE: 0.0,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    # TODO DM-39012: Improve this test after adding the simulator code.
    async def test_m2_close_air_valve(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_evt_cmd_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandKey.ID: "cmd_m2CloseAirValve",
                    atpneumaticssimulator.CommandKey.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandKey.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    # TODO DM-39012: Improve this test after adding the simulator code.
    async def test_m2_open_air_valve(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_evt_cmd_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandKey.ID: "cmd_m2OpenAirValve",
                    atpneumaticssimulator.CommandKey.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandKey.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    # TODO DM-39012: Improve this test after adding the simulator code.
    async def test_m2_set_pressure(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_evt_cmd_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandKey.ID: "cmd_m2SetPressure",
                    atpneumaticssimulator.CommandKey.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandKey.PRESSURE: 0.0,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    # TODO DM-39012: Improve this test after adding the simulator code.
    async def test_open_instrument_air_valve(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_evt_cmd_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandKey.ID: "cmd_openInstrumentAirValve",
                    atpneumaticssimulator.CommandKey.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandKey.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    # TODO DM-39012: Improve this test after adding the simulator code.
    async def test_open_m1_cell_vents(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_evt_cmd_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandKey.ID: "cmd_openM1CellVents",
                    atpneumaticssimulator.CommandKey.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandKey.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    # TODO DM-39012: Improve this test after adding the simulator code.
    async def test_open_m1_cover(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_evt_cmd_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandKey.ID: "cmd_openM1Cover",
                    atpneumaticssimulator.CommandKey.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandKey.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    # TODO DM-39012: Improve this test after adding the simulator code.
    async def test_open_master_air_supply(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_evt_cmd_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandKey.ID: "cmd_openMasterAirSupply",
                    atpneumaticssimulator.CommandKey.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandKey.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.SUCCESS,
                sequence_id=sequence_id,
            )

    # TODO DM-39012: Improve this test after adding the simulator code.
    async def test_non_existing_command(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_evt_cmd_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandKey.ID: "non-existing",
                    atpneumaticssimulator.CommandKey.SEQUENCE_ID: sequence_id,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.NOACK,
                sequence_id=sequence_id,
            )

    # TODO DM-39012: Improve this test after adding the simulator code.
    async def test_skip_sequence_id(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_evt_cmd_client(
            simulator
        ) as cmd_evt_client:
            sequence_id = 1
            await cmd_evt_client.write_json(
                data={
                    atpneumaticssimulator.CommandKey.ID: "cmd_closeInstrumentAirValve",
                    atpneumaticssimulator.CommandKey.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandKey.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.ACK,
                sequence_id=sequence_id,
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
                    atpneumaticssimulator.CommandKey.ID: "cmd_closeInstrumentAirValve",
                    atpneumaticssimulator.CommandKey.SEQUENCE_ID: sequence_id,
                    atpneumaticssimulator.CommandKey.VALUE: True,
                }
            )
            await self.verify_command_response(
                client=cmd_evt_client,
                ack=atpneumaticssimulator.Ack.NOACK,
                sequence_id=sequence_id,
            )

    async def test_update_telemetry(self) -> None:
        async with self.create_pneumatics_simulator() as simulator, self.create_telemetry_client(
            simulator
        ) as telemetry_client:
            await simulator.update_telemetry()
            for _ in atpneumaticssimulator.Telemetry:
                data = await telemetry_client.read_json()
                # No need for asserts here. If the data id is not present in
                # registry or the validation of the schema fails, the test will
                # fail as well.
                json_schema = atpneumaticssimulator.registry[f"tel_{data['id']}"]
                jsonschema.validate(data, json_schema)
