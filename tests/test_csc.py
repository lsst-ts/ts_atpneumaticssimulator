# This file is part of ts_ATPneumaticsSimulator.
#
# Developed for the LSST Data Management System.
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

import asyncio
import time
import unittest

import asynctest

from lsst.ts import salobj
from lsst.ts import ATPneumaticsSimulator
from lsst.ts.idl.enums import ATPneumatics

STD_TIMEOUT = 2  # standard timeout (sec)
LONG_TIMEOUT = 60
NODATA_TIMEOUT = 0.1  # timeout when no data expected (sec)


class CscTestCase(salobj.BaseCscTestCase, asynctest.TestCase):
    def basic_make_csc(self, initial_state, config_dir, simulation_mode):
        return ATPneumaticsSimulator.ATPneumaticsCsc(initial_state=initial_state)

    async def test_bin_script(self):
        """Test that run_atdometrajectory.py runs the CSC.
        """
        await self.check_bin_script(
            name="ATPneumatics", index=None, exe_name="run_atpneumatics_simulator.py",
        )

    async def test_initial_info(self):
        """Check that all events and telemetry are output at startup

        except the m3PortSelected event
        """
        async with self.make_csc(initial_state=salobj.State.ENABLED):
            state = await self.remote.evt_summaryState.next(
                flush=False, timeout=STD_TIMEOUT
            )
            self.assertEqual(state.summaryState, salobj.State.ENABLED)

            for evt_name in self.csc.salinfo.event_names:
                # Skip events that are not output at startup,
                # or are skipped for a different, stated, reason.
                if evt_name in (
                    "appliedSettingsMatchStart",
                    "detailedState",
                    "errorCode",
                    "logMessage",
                    "settingVersions",
                    "softwareVersions",
                    "settingsApplied",  # not supported by salobj yet
                    "summaryState",  # already read
                ):
                    continue
                event = getattr(self.remote, f"evt_{evt_name}")
                await self.assert_next_sample(event)

            for tel_name in self.csc.salinfo.telemetry_names:
                tel = getattr(self.remote, f"tel_{tel_name}")
                await tel.next(flush=False, timeout=NODATA_TIMEOUT)

    async def test_air_valves(self):
        async with self.make_csc(initial_state=salobj.State.ENABLED):
            state = await self.remote.evt_summaryState.next(
                flush=False, timeout=STD_TIMEOUT
            )
            self.assertEqual(state.summaryState, salobj.State.ENABLED)
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

    async def test_cell_vents(self):
        desired_close_time = 0.4  # sec
        desired_open_time = 0.8  # sec
        async with self.make_csc(initial_state=salobj.State.ENABLED):
            self.csc.configure(
                cell_vents_close_time=desired_close_time,
                cell_vents_open_time=desired_open_time,
            )
            state = await self.remote.evt_summaryState.next(
                flush=False, timeout=STD_TIMEOUT
            )
            self.assertEqual(state.summaryState, salobj.State.ENABLED)

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

            start_time = time.time()
            await self.remote.cmd_openM1CellVents.start(timeout=STD_TIMEOUT)

            await asyncio.wait_for(self.csc._openCellVentsTask, timeout=STD_TIMEOUT)

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
            measured_duration = time.time() - start_time
            await self.assert_next_sample(
                self.remote.evt_m1VentsPosition,
                position=ATPneumatics.VentsPosition.OPENED,
            )
            await self.assert_next_sample(
                self.remote.evt_m1VentsLimitSwitches,
                ventsClosedActive=False,
                ventsOpenedActive=True,
            )

            print(
                f"open time measured {measured_duration:0.2f}; desired {desired_open_time:0.2f}"
            )
            self.assertLess(abs(measured_duration - desired_open_time), 0.3)

            # sending open again has no effect
            await self.remote.cmd_openM1CellVents.start(timeout=STD_TIMEOUT)
            with self.assertRaises(asyncio.TimeoutError):
                await self.remote.evt_cellVentsState.next(
                    flush=False, timeout=NODATA_TIMEOUT
                )

            start_time = time.time()
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
            measured_duration = time.time() - start_time
            await self.assert_next_sample(
                self.remote.evt_m1VentsPosition,
                position=ATPneumatics.VentsPosition.CLOSED,
            )
            await self.assert_next_sample(
                self.remote.evt_m1VentsLimitSwitches,
                ventsClosedActive=True,
                ventsOpenedActive=False,
            )

            print(
                f"close time measured {measured_duration:0.2f}; desired {desired_close_time:0.2f}"
            )
            self.assertLess(abs(measured_duration - desired_close_time), 0.3)

            # sending close again has no effect
            await self.remote.cmd_closeM1CellVents.start(timeout=STD_TIMEOUT)
            with self.assertRaises(asyncio.TimeoutError):
                await self.remote.evt_cellVentsState.next(
                    flush=False, timeout=NODATA_TIMEOUT
                )

    async def test_mirror_covers(self):
        desired_close_time = 0.4  # sec
        desired_open_time = 0.8  # sec
        async with self.make_csc(initial_state=salobj.State.ENABLED):
            self.csc.configure(
                m1_covers_close_time=desired_close_time,
                m1_covers_open_time=desired_open_time,
            )
            state = await self.remote.evt_summaryState.next(
                flush=False, timeout=STD_TIMEOUT
            )
            self.assertEqual(state.summaryState, salobj.State.ENABLED)

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

            start_time = time.time()
            await self.remote.cmd_openM1Cover.start(timeout=STD_TIMEOUT)

            await self.csc._openM1CoversTask

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
            # on the events output nor the time spent opening
            await self.remote.cmd_openM1Cover.start(timeout=STD_TIMEOUT)

            await self.assert_next_sample(
                self.remote.evt_m1CoverState,
                state=ATPneumatics.MirrorCoverState.OPENED,
                timeout=desired_open_time + STD_TIMEOUT,
            )
            measured_duration = time.time() - start_time
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

            print(
                f"open time measured {measured_duration:0.2f}; desired {desired_open_time:0.2f}"
            )
            self.assertLess(abs(measured_duration - desired_open_time), 0.3)

            # sending open again has no effect
            await self.remote.cmd_openM1Cover.start(timeout=STD_TIMEOUT)
            with self.assertRaises(asyncio.TimeoutError):
                await self.remote.evt_m1CoverState.next(
                    flush=False, timeout=NODATA_TIMEOUT
                )

            start_time = time.time()
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
            # on the events output nor the time spent opening
            await self.remote.cmd_closeM1Cover.start(timeout=STD_TIMEOUT)

            await self.assert_next_sample(
                self.remote.evt_m1CoverState,
                state=ATPneumatics.MirrorCoverState.CLOSED,
                timeout=desired_close_time + STD_TIMEOUT,
            )
            measured_duration = time.time() - start_time
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

            print(
                f"close time measured {measured_duration:0.2f}; desired {desired_close_time:0.2f}"
            )
            self.assertLess(abs(measured_duration - desired_close_time), 0.3)

            # sending close again has no effect
            await self.remote.cmd_closeM1Cover.start(timeout=STD_TIMEOUT)
            with self.assertRaises(asyncio.TimeoutError):
                await self.remote.evt_m1CoverState.next(
                    flush=False, timeout=NODATA_TIMEOUT
                )

    async def test_set_pressure(self):
        async with self.make_csc(initial_state=salobj.State.ENABLED):
            # output telemetry often so we don't have to wait
            self.csc.telemetry_interval = 0.1
            init_m1_pressure = 5
            init_m2_pressure = 6
            self.csc.configure(
                m1_pressure=init_m1_pressure, m2_pressure=init_m2_pressure,
            )
            state = await self.remote.evt_summaryState.next(
                flush=False, timeout=STD_TIMEOUT
            )
            self.assertEqual(state.summaryState, salobj.State.ENABLED)

            m1data = await self.remote.tel_m1AirPressure.next(
                flush=True, timeout=STD_TIMEOUT
            )
            self.assertEqual(m1data.pressure, init_m1_pressure)
            m2data = await self.remote.tel_m2AirPressure.next(
                flush=True, timeout=STD_TIMEOUT
            )
            self.assertEqual(m2data.pressure, init_m2_pressure)

            cmd_m1pressure = 35
            cmd_m2pressure = 47

            self.remote.cmd_m1SetPressure.set(pressure=cmd_m1pressure)
            await self.remote.cmd_m1SetPressure.start(timeout=STD_TIMEOUT)
            self.remote.cmd_m2SetPressure.set(pressure=cmd_m2pressure)
            await self.remote.cmd_m2SetPressure.start(timeout=STD_TIMEOUT)

            m1data = await self.remote.tel_m1AirPressure.next(
                flush=True, timeout=STD_TIMEOUT
            )
            self.assertEqual(m1data.pressure, cmd_m1pressure)
            m2data = await self.remote.tel_m2AirPressure.next(
                flush=True, timeout=STD_TIMEOUT
            )
            self.assertEqual(m2data.pressure, cmd_m2pressure)

    async def test_standard_state_transitions(self):
        """Test standard CSC state transitions.
        """
        async with self.make_csc(initial_state=salobj.State.STANDBY):
            self.assertEqual(self.csc.summary_state, salobj.State.STANDBY)
            # make sure start_task completes
            await asyncio.wait_for(self.csc.start_task, timeout=STD_TIMEOUT)

            state = await self.remote.evt_summaryState.next(
                flush=False, timeout=STD_TIMEOUT
            )
            self.assertEqual(state.summaryState, salobj.State.STANDBY)

            # send start; new state is DISABLED
            await self.remote.cmd_start.start()
            self.assertEqual(self.csc.summary_state, salobj.State.DISABLED)
            state = await self.remote.evt_summaryState.next(
                flush=False, timeout=STD_TIMEOUT
            )
            self.assertEqual(state.summaryState, salobj.State.DISABLED)

            # send enable; new state is ENABLED
            await self.remote.cmd_enable.start()
            self.assertEqual(self.csc.summary_state, salobj.State.ENABLED)
            state = await self.remote.evt_summaryState.next(
                flush=False, timeout=STD_TIMEOUT
            )
            self.assertEqual(state.summaryState, salobj.State.ENABLED)

            # send disable; new state is DISABLED
            await self.remote.cmd_disable.start()
            self.assertEqual(self.csc.summary_state, salobj.State.DISABLED)
            state = await self.remote.evt_summaryState.next(
                flush=False, timeout=STD_TIMEOUT
            )
            self.assertEqual(state.summaryState, salobj.State.DISABLED)

            # send standby; new state is STANDBY
            await self.remote.cmd_standby.start()
            self.assertEqual(self.csc.summary_state, salobj.State.STANDBY)
            state = await self.remote.evt_summaryState.next(
                flush=False, timeout=STD_TIMEOUT
            )
            self.assertEqual(state.summaryState, salobj.State.STANDBY)

            # send exitControl; new state is OFFLINE
            await self.remote.cmd_exitControl.start()
            self.assertEqual(self.csc.summary_state, salobj.State.OFFLINE)
            state = await self.remote.evt_summaryState.next(
                flush=False, timeout=STD_TIMEOUT
            )
            self.assertEqual(state.summaryState, salobj.State.OFFLINE)

            await asyncio.wait_for(self.csc.done_task, timeout=5)


if __name__ == "__main__":
    unittest.main()
