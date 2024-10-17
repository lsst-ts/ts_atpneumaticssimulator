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
import pathlib
import unittest
from typing import Any

import pytest
from lsst.ts import atpneumaticssimulator, salobj
from lsst.ts.xml import sal_enums
from lsst.ts.xml.enums import ATPneumatics

STD_TIMEOUT = 60.0  # standard timeout (sec)
NODATA_TIMEOUT = 0.1  # timeout when no data expected (sec)

CONFIG_DIR = pathlib.Path(__file__).parent / "data" / "config"


class CscTestCase(salobj.BaseCscTestCase, unittest.IsolatedAsyncioTestCase):
    def basic_make_csc(
        self,
        initial_state: salobj.State,
        config_dir: str,
        override: str = "",
        **kwargs: Any,
    ) -> atpneumaticssimulator.ATPneumaticsCsc:
        return atpneumaticssimulator.ATPneumaticsCsc(
            initial_state=initial_state,
            config_dir=config_dir,
            simulation_mode=1,
            override=override,
        )

    async def test_bin_script(self) -> None:
        """Test that run_atdometrajectory runs the CSC."""
        await self.check_bin_script(
            name="ATPneumatics",
            index=None,
            exe_name="run_atpneumatics_simulator",
        )

    async def test_initial_info(self) -> None:
        """Check that all events and telemetry are output at startup

        except the m3PortSelected event
        """
        async with self.make_csc(
            initial_state=salobj.State.ENABLED, config_dir=CONFIG_DIR
        ):
            await self.assert_next_summary_state(salobj.State.ENABLED)
            await self.assert_next_sample(
                topic=self.remote.evt_softwareVersions,
                cscVersion=atpneumaticssimulator.__version__ + "-sim",
                subsystemVersions="",
            )

            skip_evt_names = frozenset(
                (
                    "detailedState",  # not output by the simulator
                    "logMessage",  # not necessarily output at startup
                    "largeFileObjectAvailable",  # not output
                    "softwareVersions",  # already read
                    "summaryState",  # already read
                )
            )

            for evt_name in self.csc.salinfo.event_names:
                # Skip the following events for the stated reasons
                if evt_name in skip_evt_names:
                    continue
                with self.subTest(evt_name=evt_name):
                    event = getattr(self.remote, f"evt_{evt_name}")
                    await self.assert_next_sample(event)

            for tel_name in self.csc.salinfo.telemetry_names:
                tel = getattr(self.remote, f"tel_{tel_name}")
                await tel.next(flush=False, timeout=STD_TIMEOUT)

    async def test_air_valves(self) -> None:
        async with self.make_csc(
            initial_state=salobj.State.ENABLED, config_dir=CONFIG_DIR
        ):
            await self.assert_next_sample(
                self.remote.evt_instrumentState, state=ATPneumatics.AirValveState.OPENED
            )
            await self.assert_next_sample(
                self.remote.evt_mainValveState, state=ATPneumatics.AirValveState.OPENED
            )
            await self.assert_next_sample(
                self.remote.evt_m1State, state=ATPneumatics.AirValveState.OPENED
            )
            await self.assert_next_sample(
                self.remote.evt_m2State, state=ATPneumatics.AirValveState.OPENED
            )

            await self.remote.cmd_closeInstrumentAirValve.start(timeout=STD_TIMEOUT)
            await self.assert_next_sample(
                self.remote.evt_instrumentState, state=ATPneumatics.AirValveState.CLOSED
            )

            await self.remote.cmd_closeMasterAirSupply.start(timeout=STD_TIMEOUT)
            await self.assert_next_sample(
                self.remote.evt_mainValveState, state=ATPneumatics.AirValveState.CLOSED
            )

            await self.remote.cmd_m1CloseAirValve.start(timeout=STD_TIMEOUT)
            await self.assert_next_sample(
                self.remote.evt_m1State, state=ATPneumatics.AirValveState.CLOSED
            )

            await self.remote.cmd_m2CloseAirValve.start(timeout=STD_TIMEOUT)
            await self.assert_next_sample(
                self.remote.evt_m2State, state=ATPneumatics.AirValveState.CLOSED
            )

            await self.remote.cmd_openInstrumentAirValve.start(timeout=STD_TIMEOUT)
            await self.assert_next_sample(
                self.remote.evt_instrumentState, state=ATPneumatics.AirValveState.OPENED
            )

            await self.remote.cmd_openMasterAirSupply.start(timeout=STD_TIMEOUT)
            await self.assert_next_sample(
                self.remote.evt_mainValveState, state=ATPneumatics.AirValveState.OPENED
            )

            await self.remote.cmd_m1OpenAirValve.start(timeout=STD_TIMEOUT)
            await self.assert_next_sample(
                self.remote.evt_m1State, state=ATPneumatics.AirValveState.OPENED
            )

            await self.remote.cmd_m2OpenAirValve.start(timeout=STD_TIMEOUT)
            await self.assert_next_sample(
                self.remote.evt_m2State, state=ATPneumatics.AirValveState.OPENED
            )

    async def test_cell_vents(self) -> None:
        desired_close_time = 0.4  # sec
        desired_open_time = 0.8  # sec
        async with self.make_csc(
            initial_state=salobj.State.ENABLED, config_dir=CONFIG_DIR
        ):
            await self.csc.simulator.configure(
                cell_vents_close_time=desired_close_time,
                cell_vents_open_time=desired_open_time,
            )

            await self.assert_next_sample(
                self.remote.evt_cellVentsState, state=ATPneumatics.CellVentState.CLOSED
            )
            await self.assert_next_sample(
                self.remote.evt_m1VentsPosition,
                position=ATPneumatics.VentsPosition.CLOSED,
            )
            await self.assert_next_sample(
                self.remote.evt_m1VentsLimitSwitches,
                ventsClosedActive=True,
                ventsOpenedActive=False,
            )

            await self.remote.cmd_openM1CellVents.start(timeout=STD_TIMEOUT)

            await self.assert_next_sample(
                self.remote.evt_cellVentsState,
                state=ATPneumatics.CellVentState.INMOTION,
            )
            await self.assert_next_sample(
                self.remote.evt_m1VentsPosition,
                position=ATPneumatics.VentsPosition.PARTIALLYOPENED,
            )
            await self.assert_next_sample(
                self.remote.evt_m1VentsLimitSwitches,
                ventsClosedActive=False,
                ventsOpenedActive=False,
            )

            # sending open again is acceptable but has no effect
            # on the events output nor the time spent opening
            await self.remote.cmd_openM1CellVents.start(timeout=STD_TIMEOUT)

            await self.assert_next_sample(
                self.remote.evt_cellVentsState,
                state=ATPneumatics.CellVentState.OPENED,
                timeout=desired_open_time + STD_TIMEOUT,
            )
            await self.assert_next_sample(
                self.remote.evt_m1VentsPosition,
                position=ATPneumatics.VentsPosition.OPENED,
            )
            await self.assert_next_sample(
                self.remote.evt_m1VentsLimitSwitches,
                ventsClosedActive=False,
                ventsOpenedActive=True,
            )

            # sending open again has no effect
            await self.remote.cmd_openM1CellVents.start(timeout=STD_TIMEOUT)
            with pytest.raises(asyncio.TimeoutError):
                await self.remote.evt_cellVentsState.next(
                    flush=False, timeout=NODATA_TIMEOUT
                )

            await self.remote.cmd_closeM1CellVents.start(timeout=STD_TIMEOUT)

            await self.assert_next_sample(
                self.remote.evt_cellVentsState,
                state=ATPneumatics.CellVentState.INMOTION,
            )
            await self.assert_next_sample(
                self.remote.evt_m1VentsPosition,
                position=ATPneumatics.VentsPosition.PARTIALLYOPENED,
            )
            await self.assert_next_sample(
                self.remote.evt_m1VentsLimitSwitches,
                ventsClosedActive=False,
                ventsOpenedActive=False,
            )

            # sending close again is acceptable but has no effect
            # on the events output nor the time spent opening
            await self.remote.cmd_closeM1CellVents.start(timeout=STD_TIMEOUT)

            await self.assert_next_sample(
                self.remote.evt_cellVentsState,
                state=ATPneumatics.CellVentState.CLOSED,
                timeout=desired_close_time + STD_TIMEOUT,
            )
            await self.assert_next_sample(
                self.remote.evt_m1VentsPosition,
                position=ATPneumatics.VentsPosition.CLOSED,
            )
            await self.assert_next_sample(
                self.remote.evt_m1VentsLimitSwitches,
                ventsClosedActive=True,
                ventsOpenedActive=False,
            )

            # sending close again has no effect
            await self.remote.cmd_closeM1CellVents.start(timeout=STD_TIMEOUT)
            with pytest.raises(asyncio.TimeoutError):
                await self.remote.evt_cellVentsState.next(
                    flush=False, timeout=NODATA_TIMEOUT
                )

    async def test_mirror_covers(self) -> None:
        desired_close_time = 0.4  # sec
        desired_open_time = 0.8  # sec
        async with self.make_csc(
            initial_state=salobj.State.ENABLED, config_dir=CONFIG_DIR
        ):
            await self.csc.simulator.configure(
                m1_covers_close_time=desired_close_time,
                m1_covers_open_time=desired_open_time,
            )

            await self.assert_next_sample(
                self.remote.evt_m1CoverState, state=ATPneumatics.MirrorCoverState.CLOSED
            )
            await self.assert_next_sample(
                self.remote.evt_m1CoverLimitSwitches,
                cover1ClosedActive=True,
                cover2ClosedActive=True,
                cover3ClosedActive=True,
                cover4ClosedActive=True,
                cover1OpenedActive=False,
                cover2OpenedActive=False,
                cover3OpenedActive=False,
                cover4OpenedActive=False,
            )

            await self.remote.cmd_openM1Cover.start(timeout=STD_TIMEOUT)

            await self.assert_next_sample(
                self.remote.evt_m1CoverState,
                state=ATPneumatics.MirrorCoverState.INMOTION,
            )
            await self.assert_next_sample(
                self.remote.evt_m1CoverLimitSwitches,
                cover1ClosedActive=False,
                cover2ClosedActive=False,
                cover3ClosedActive=False,
                cover4ClosedActive=False,
                cover1OpenedActive=False,
                cover2OpenedActive=False,
                cover3OpenedActive=False,
                cover4OpenedActive=False,
            )

            # sending open again is acceptable but has no effect
            # on the events output
            await self.remote.cmd_openM1Cover.start(timeout=STD_TIMEOUT)

            await self.assert_next_sample(
                self.remote.evt_m1CoverState,
                state=ATPneumatics.MirrorCoverState.OPENED,
                timeout=desired_open_time + STD_TIMEOUT,
            )
            await self.assert_next_sample(
                self.remote.evt_m1CoverLimitSwitches,
                cover1ClosedActive=False,
                cover2ClosedActive=False,
                cover3ClosedActive=False,
                cover4ClosedActive=False,
                cover1OpenedActive=True,
                cover2OpenedActive=True,
                cover3OpenedActive=True,
                cover4OpenedActive=True,
            )

            # sending open again has no effect
            await self.remote.cmd_openM1Cover.start(timeout=STD_TIMEOUT)
            with pytest.raises(asyncio.TimeoutError):
                await self.remote.evt_m1CoverState.next(
                    flush=False, timeout=NODATA_TIMEOUT
                )

            await self.remote.cmd_closeM1Cover.start(timeout=STD_TIMEOUT)

            await self.assert_next_sample(
                self.remote.evt_m1CoverState,
                state=ATPneumatics.MirrorCoverState.INMOTION,
            )
            await self.assert_next_sample(
                self.remote.evt_m1CoverLimitSwitches,
                cover1ClosedActive=False,
                cover2ClosedActive=False,
                cover3ClosedActive=False,
                cover4ClosedActive=False,
                cover1OpenedActive=False,
                cover2OpenedActive=False,
                cover3OpenedActive=False,
                cover4OpenedActive=False,
            )

            # sending close again is acceptable but has no effect
            # on the events output
            await self.remote.cmd_closeM1Cover.start(timeout=STD_TIMEOUT)

            await self.assert_next_sample(
                self.remote.evt_m1CoverState,
                state=ATPneumatics.MirrorCoverState.CLOSED,
                timeout=desired_close_time + STD_TIMEOUT,
            )
            await self.assert_next_sample(
                self.remote.evt_m1CoverLimitSwitches,
                cover1ClosedActive=True,
                cover2ClosedActive=True,
                cover3ClosedActive=True,
                cover4ClosedActive=True,
                cover1OpenedActive=False,
                cover2OpenedActive=False,
                cover3OpenedActive=False,
                cover4OpenedActive=False,
            )

            # sending close again has no effect
            await self.remote.cmd_closeM1Cover.start(timeout=STD_TIMEOUT)
            with pytest.raises(asyncio.TimeoutError):
                await self.remote.evt_m1CoverState.next(
                    flush=False, timeout=NODATA_TIMEOUT
                )

    async def test_set_pressure(self) -> None:
        async with self.make_csc(
            initial_state=salobj.State.ENABLED, config_dir=CONFIG_DIR
        ):
            # output telemetry often so we don't have to wait
            self.csc.telemetry_interval = 0.1
            init_m1_pressure = 5
            init_m2_pressure = 6
            await self.csc.simulator.configure(
                m1_pressure=init_m1_pressure,
                m2_pressure=init_m2_pressure,
            )

            m1data = await self.remote.tel_m1AirPressure.next(
                flush=True, timeout=STD_TIMEOUT
            )
            assert m1data.pressure == pytest.approx(init_m1_pressure)
            m2data = await self.remote.tel_m2AirPressure.next(
                flush=True, timeout=STD_TIMEOUT
            )
            assert m2data.pressure == pytest.approx(init_m2_pressure)

            cmd_m1pressure = 35
            cmd_m2pressure = 47

            await self.remote.cmd_m1SetPressure.set_start(
                pressure=cmd_m1pressure, timeout=STD_TIMEOUT
            )
            await self.remote.cmd_m2SetPressure.set_start(
                pressure=cmd_m2pressure, timeout=STD_TIMEOUT
            )

            m1data = await self.remote.tel_m1AirPressure.next(
                flush=True, timeout=STD_TIMEOUT
            )
            assert m1data.pressure == pytest.approx(cmd_m1pressure)
            m2data = await self.remote.tel_m2AirPressure.next(
                flush=True, timeout=STD_TIMEOUT
            )
            assert m2data.pressure == pytest.approx(cmd_m2pressure)

    async def test_standard_state_transitions(self) -> None:
        """Test standard CSC state transitions."""
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, config_dir=CONFIG_DIR
        ):
            await self.check_standard_state_transitions(
                enabled_commands=(
                    "closeInstrumentAirValve",
                    "closeM1CellVents",
                    "closeM1Cover",
                    "closeMasterAirSupply",
                    "m1CloseAirValve",
                    "m1SetPressure",
                    "m2CloseAirValve",
                    "m1OpenAirValve",
                    "m2OpenAirValve",
                    "m2SetPressure",
                    "openInstrumentAirValve",
                    "openM1CellVents",
                    "openM1Cover",
                    "openMasterAirSupply",
                )
            )

    async def test_csc_state_commands(self) -> None:
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, config_dir=CONFIG_DIR
        ):
            await self.remote.cmd_start.start()
            await self.csc.simulator.configure()
            assert self.csc.simulator.simulator_state == sal_enums.State.DISABLED

            await self.remote.cmd_enable.start()
            assert self.csc.simulator.simulator_state == sal_enums.State.ENABLED

            await self.remote.cmd_disable.start()
            assert self.csc.simulator.simulator_state == sal_enums.State.DISABLED

            await self.remote.cmd_standby.start()
            assert self.csc.simulator.simulator_state == sal_enums.State.STANDBY

            await self.remote.cmd_start.start()
            assert self.csc.simulator.simulator_state == sal_enums.State.DISABLED

            await self.remote.cmd_enable.start()
            assert self.csc.simulator.simulator_state == sal_enums.State.ENABLED

            await self.remote.cmd_disable.start()
            assert self.csc.simulator.simulator_state == sal_enums.State.DISABLED

            await self.remote.cmd_standby.start()
            assert self.csc.simulator.simulator_state == sal_enums.State.STANDBY

    async def test_csc_with_fault_state(self) -> None:
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, config_dir=CONFIG_DIR
        ):
            await self.remote.cmd_start.start()
            await self.csc.simulator.configure()
            assert self.csc.simulator.simulator_state == sal_enums.State.DISABLED

            await self.remote.cmd_standby.start()
            assert self.csc.simulator.simulator_state == sal_enums.State.STANDBY

            self.csc.simulator.go_to_fault_state = True
            await self.remote.cmd_start.set_start()
            assert self.csc.simulator.simulator_state == sal_enums.State.FAULT

            await self.remote.cmd_standby.set_start()
            assert self.csc.simulator.simulator_state == sal_enums.State.STANDBY
