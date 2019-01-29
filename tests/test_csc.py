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
import shutil
import time
import unittest

from lsst.ts import salobj
from lsst.ts import ATPneumaticsSimulator

import SALPY_ATPneumatics


class Harness:
    def __init__(self, initial_state):
        salobj.test_utils.set_random_lsst_dds_domain()
        self.remote = salobj.Remote(SALPY_ATPneumatics, index=0)
        self.csc = ATPneumaticsSimulator.ATPneumaticsCsc(
            initial_state=initial_state, initial_simulation_mode=1)

    async def next_evt(self, name, flush=False, timeout=1):
        try:
            evt = getattr(self.remote, f"evt_{name}")
            return await evt.next(flush=flush, timeout=timeout)
        except Exception as e:
            raise RuntimeError(f"Cound not get data for event {name}") from e

    def get_evt(self, name):
        try:
            evt = getattr(self.remote, f"evt_{name}")
            return evt.get()
        except Exception as e:
            raise RuntimeError(f"Cound not get data for event {name}") from e


class CscTestCase(unittest.TestCase):

    def test_initial_info(self):
        """Check that all events and telemetry are output at startup

        except the m3PortSelected event
        """

        async def doit():
            harness = Harness(initial_state=salobj.State.ENABLED)
            state = await harness.remote.evt_summaryState.next(flush=False, timeout=5)
            self.assertEqual(state.summaryState, salobj.State.ENABLED)

            for evt_name in harness.csc.salinfo.manager.getEventNames():
                if evt_name in (
                    # not output at startup
                    "eStopTriggered", "resetEStopTriggered",
                    "summaryState",  # already read
                    "appliedSettingsMatchStart", "detailedState",
                    "errorCode", "logMessage", "settingVersions",
                ):
                    continue
                await harness.next_evt(evt_name)

            for tel_name in harness.csc.salinfo.manager.getTelemetryNames():
                tel = getattr(harness.remote, f"tel_{tel_name}")
                await tel.next(flush=False, timeout=0.1)

        asyncio.get_event_loop().run_until_complete(doit())

    def test_air_valves(self):
        async def doit():
            harness = Harness(initial_state=salobj.State.ENABLED)
            state = await harness.remote.evt_summaryState.next(flush=False, timeout=5)
            self.assertEqual(state.summaryState, salobj.State.ENABLED)
            st = await harness.next_evt("instrumentState")
            self.assertEqual(st.state,
                             SALPY_ATPneumatics.ATPneumatics_shared_AirValveState_ValveOpenedState)
            st = await harness.next_evt("mainValveState")
            self.assertEqual(st.state,
                             SALPY_ATPneumatics.ATPneumatics_shared_AirValveState_ValveOpenedState)
            st = await harness.next_evt("m1State")
            self.assertEqual(st.state,
                             SALPY_ATPneumatics.ATPneumatics_shared_AirValveState_ValveOpenedState)
            st = await harness.next_evt("m2State")
            self.assertEqual(st.state,
                             SALPY_ATPneumatics.ATPneumatics_shared_AirValveState_ValveOpenedState)

            await harness.remote.cmd_closeInstrumentAirValve.start(timeout=1)
            st = await harness.next_evt("instrumentState")
            self.assertEqual(st.state,
                             SALPY_ATPneumatics.ATPneumatics_shared_AirValveState_ValveClosedState)

            await harness.remote.cmd_closeMasterAirSupply.start(timeout=1)
            st = await harness.next_evt("mainValveState")
            self.assertEqual(st.state,
                             SALPY_ATPneumatics.ATPneumatics_shared_AirValveState_ValveClosedState)

            await harness.remote.cmd_m1CloseAirValve.start(timeout=1)
            st = await harness.next_evt("m1State")
            self.assertEqual(st.state,
                             SALPY_ATPneumatics.ATPneumatics_shared_AirValveState_ValveClosedState)

            await harness.remote.cmd_m2CloseAirValve.start(timeout=1)
            st = await harness.next_evt("m2State")
            self.assertEqual(st.state,
                             SALPY_ATPneumatics.ATPneumatics_shared_AirValveState_ValveClosedState)

            await harness.remote.cmd_openInstrumentAirValve.start(timeout=1)
            st = await harness.next_evt("instrumentState")
            self.assertEqual(st.state,
                             SALPY_ATPneumatics.ATPneumatics_shared_AirValveState_ValveOpenedState)

            await harness.remote.cmd_openMasterAirSupply.start(timeout=1)
            st = await harness.next_evt("mainValveState")
            self.assertEqual(st.state,
                             SALPY_ATPneumatics.ATPneumatics_shared_AirValveState_ValveOpenedState)

            await harness.remote.cmd_m1OpenAirValve.start(timeout=1)
            st = await harness.next_evt("m1State")
            self.assertEqual(st.state,
                             SALPY_ATPneumatics.ATPneumatics_shared_AirValveState_ValveOpenedState)

            await harness.remote.cmd_m2OpenAirValve.start(timeout=1)
            st = await harness.next_evt("m2State")
            self.assertEqual(st.state,
                             SALPY_ATPneumatics.ATPneumatics_shared_AirValveState_ValveOpenedState)

        asyncio.get_event_loop().run_until_complete(doit())

    def test_cell_vents(self):
        async def doit():
            desired_close_time = 0.4  # sec
            desired_open_time = 0.8  # sec
            harness = Harness(initial_state=salobj.State.ENABLED)
            harness.csc.configure(
                cell_vents_close_time=desired_close_time,
                cell_vents_open_time=desired_open_time,
            )
            state = await harness.remote.evt_summaryState.next(flush=False, timeout=5)
            self.assertEqual(state.summaryState, salobj.State.ENABLED)

            st = await harness.next_evt("cellVentsState")
            self.assertEqual(st.state,
                             SALPY_ATPneumatics.ATPneumatics_shared_CellVentState_CellVentsClosedState)
            pos = await harness.next_evt("m1VentsPosition")
            self.assertEqual(pos.position, SALPY_ATPneumatics.ATPneumatics_shared_VentsPosition_Closed)
            sw = await harness.next_evt("m1VentsLimitSwitches")
            self.assertTrue(sw.ventsClosedActive)
            self.assertFalse(sw.ventsOpenedActive)

            start_time = time.time()
            await harness.remote.cmd_openM1CellVents.start(timeout=1)

            st = await harness.next_evt("cellVentsState", timeout=1)
            self.assertEqual(st.state,
                             SALPY_ATPneumatics.ATPneumatics_shared_CellVentState_InMotionState)
            pos = await harness.next_evt("m1VentsPosition")
            self.assertEqual(pos.position,
                             SALPY_ATPneumatics.ATPneumatics_shared_VentsPosition_PartiallyOpened)
            sw = await harness.next_evt("m1VentsLimitSwitches")
            self.assertFalse(sw.ventsClosedActive)
            self.assertFalse(sw.ventsOpenedActive)

            # sending open again is acceptable but has no effect
            # on the events output nor the time spent opening
            await harness.remote.cmd_openM1CellVents.start(timeout=1)

            st = await harness.next_evt("cellVentsState", timeout=desired_open_time + 2)
            measured_duration = time.time() - start_time
            self.assertEqual(st.state,
                             SALPY_ATPneumatics.ATPneumatics_shared_CellVentState_CellVentsOpenedState)
            pos = await harness.next_evt("m1VentsPosition")
            self.assertEqual(pos.position,
                             SALPY_ATPneumatics.ATPneumatics_shared_VentsPosition_Opened)
            sw = await harness.next_evt("m1VentsLimitSwitches")
            self.assertFalse(sw.ventsClosedActive)
            self.assertTrue(sw.ventsOpenedActive)

            print(f"open time measured {measured_duration:0.2f}; desired {desired_open_time:0.2f}")
            self.assertLess(abs(measured_duration - desired_open_time), 0.3)

            # sending open again has no effect
            await harness.remote.cmd_openM1CellVents.start(timeout=1)
            with self.assertRaises(asyncio.TimeoutError):
                await harness.remote.evt_cellVentsState.next(flush=False, timeout=0.1)

            start_time = time.time()
            await harness.remote.cmd_closeM1CellVents.start(timeout=1)

            st = await harness.next_evt("cellVentsState", timeout=1)
            self.assertEqual(st.state,
                             SALPY_ATPneumatics.ATPneumatics_shared_CellVentState_InMotionState)
            pos = await harness.next_evt("m1VentsPosition")
            self.assertEqual(pos.position,
                             SALPY_ATPneumatics.ATPneumatics_shared_VentsPosition_PartiallyOpened)
            sw = await harness.next_evt("m1VentsLimitSwitches")
            self.assertFalse(sw.ventsClosedActive)
            self.assertFalse(sw.ventsOpenedActive)

            # sending close again is acceptable but has no effect
            # on the events output nor the time spent opening
            await harness.remote.cmd_closeM1CellVents.start(timeout=1)

            st = await harness.next_evt("cellVentsState", timeout=desired_close_time + 2)
            measured_duration = time.time() - start_time
            self.assertEqual(st.state,
                             SALPY_ATPneumatics.ATPneumatics_shared_CellVentState_CellVentsClosedState)
            pos = await harness.next_evt("m1VentsPosition")
            self.assertEqual(pos.position, SALPY_ATPneumatics.ATPneumatics_shared_VentsPosition_Closed)
            sw = await harness.next_evt("m1VentsLimitSwitches")
            self.assertTrue(sw.ventsClosedActive)
            self.assertFalse(sw.ventsOpenedActive)

            print(f"close time measured {measured_duration:0.2f}; desired {desired_close_time:0.2f}")
            self.assertLess(abs(measured_duration - desired_close_time), 0.3)

            # sending close again has no effect
            await harness.remote.cmd_closeM1CellVents.start(timeout=1)
            with self.assertRaises(asyncio.TimeoutError):
                await harness.remote.evt_cellVentsState.next(flush=False, timeout=0.1)

        asyncio.get_event_loop().run_until_complete(doit())

    def test_mirror_covers(self):
        async def doit():
            desired_close_time = 0.4  # sec
            desired_open_time = 0.8  # sec
            harness = Harness(initial_state=salobj.State.ENABLED)
            harness.csc.configure(
                m1_covers_close_time=desired_close_time,
                m1_covers_open_time=desired_open_time,
            )
            state = await harness.remote.evt_summaryState.next(flush=False, timeout=5)
            self.assertEqual(state.summaryState, salobj.State.ENABLED)

            st = await harness.next_evt("m1CoverState")
            self.assertEqual(st.state,
                             SALPY_ATPneumatics.ATPneumatics_shared_MirrorCoverState_MirrorCoversClosedState)
            pos = await harness.next_evt("m1CoverPosition")
            self.assertEqual(pos.position, SALPY_ATPneumatics.ATPneumatics_shared_CoverPosition_Closed)
            sw = await harness.next_evt("m1CoverLimitSwitches")
            self.assertTrue(sw.cover1ClosedActive)
            self.assertTrue(sw.cover2ClosedActive)
            self.assertTrue(sw.cover3ClosedActive)
            self.assertTrue(sw.cover4ClosedActive)
            self.assertFalse(sw.cover1OpenedActive)
            self.assertFalse(sw.cover2OpenedActive)
            self.assertFalse(sw.cover3OpenedActive)
            self.assertFalse(sw.cover4OpenedActive)

            start_time = time.time()
            await harness.remote.cmd_openM1Cover.start(timeout=1)

            st = await harness.next_evt("m1CoverState", timeout=1)
            self.assertEqual(st.state,
                             SALPY_ATPneumatics.ATPneumatics_shared_MirrorCoverState_InMotionState)
            pos = await harness.next_evt("m1CoverPosition")
            self.assertEqual(pos.position,
                             SALPY_ATPneumatics.ATPneumatics_shared_CoverPosition_PartiallyOpened)
            sw = await harness.next_evt("m1CoverLimitSwitches")
            self.assertFalse(sw.cover1ClosedActive)
            self.assertFalse(sw.cover2ClosedActive)
            self.assertFalse(sw.cover3ClosedActive)
            self.assertFalse(sw.cover4ClosedActive)
            self.assertFalse(sw.cover1OpenedActive)
            self.assertFalse(sw.cover2OpenedActive)
            self.assertFalse(sw.cover3OpenedActive)
            self.assertFalse(sw.cover4OpenedActive)

            # sending open again is acceptable but has no effect
            # on the events output nor the time spent opening
            await harness.remote.cmd_openM1Cover.start(timeout=1)

            st = await harness.next_evt("m1CoverState", timeout=desired_open_time + 2)
            measured_duration = time.time() - start_time
            self.assertEqual(st.state,
                             SALPY_ATPneumatics.ATPneumatics_shared_MirrorCoverState_MirrorCoversOpenedState)
            pos = await harness.next_evt("m1CoverPosition")
            self.assertEqual(pos.position,
                             SALPY_ATPneumatics.ATPneumatics_shared_CoverPosition_Opened)
            sw = await harness.next_evt("m1CoverLimitSwitches")
            self.assertFalse(sw.cover1ClosedActive)
            self.assertFalse(sw.cover2ClosedActive)
            self.assertFalse(sw.cover3ClosedActive)
            self.assertFalse(sw.cover4ClosedActive)
            self.assertTrue(sw.cover1OpenedActive)
            self.assertTrue(sw.cover2OpenedActive)
            self.assertTrue(sw.cover3OpenedActive)
            self.assertTrue(sw.cover4OpenedActive)

            print(f"open time measured {measured_duration:0.2f}; desired {desired_open_time:0.2f}")
            self.assertLess(abs(measured_duration - desired_open_time), 0.3)

            # sending open again has no effect
            await harness.remote.cmd_openM1Cover.start(timeout=1)
            with self.assertRaises(asyncio.TimeoutError):
                await harness.remote.evt_m1CoverState.next(flush=False, timeout=0.1)

            start_time = time.time()
            await harness.remote.cmd_closeM1Cover.start(timeout=1)

            st = await harness.next_evt("m1CoverState", timeout=1)
            self.assertEqual(st.state,
                             SALPY_ATPneumatics.ATPneumatics_shared_MirrorCoverState_InMotionState)
            pos = await harness.next_evt("m1CoverPosition")
            self.assertEqual(pos.position,
                             SALPY_ATPneumatics.ATPneumatics_shared_CoverPosition_PartiallyOpened)
            sw = await harness.next_evt("m1CoverLimitSwitches")
            self.assertFalse(sw.cover1ClosedActive)
            self.assertFalse(sw.cover2ClosedActive)
            self.assertFalse(sw.cover3ClosedActive)
            self.assertFalse(sw.cover4ClosedActive)
            self.assertFalse(sw.cover1OpenedActive)
            self.assertFalse(sw.cover2OpenedActive)
            self.assertFalse(sw.cover3OpenedActive)
            self.assertFalse(sw.cover4OpenedActive)

            # sending close again is acceptable but has no effect
            # on the events output nor the time spent opening
            await harness.remote.cmd_closeM1Cover.start(timeout=1)

            st = await harness.next_evt("m1CoverState", timeout=desired_close_time + 2)
            measured_duration = time.time() - start_time
            self.assertEqual(st.state,
                             SALPY_ATPneumatics.ATPneumatics_shared_MirrorCoverState_MirrorCoversClosedState)
            pos = await harness.next_evt("m1CoverPosition")
            self.assertEqual(pos.position, SALPY_ATPneumatics.ATPneumatics_shared_CoverPosition_Closed)
            sw = await harness.next_evt("m1CoverLimitSwitches")
            self.assertTrue(sw.cover1ClosedActive)
            self.assertTrue(sw.cover2ClosedActive)
            self.assertTrue(sw.cover3ClosedActive)
            self.assertTrue(sw.cover4ClosedActive)
            self.assertFalse(sw.cover1OpenedActive)
            self.assertFalse(sw.cover2OpenedActive)
            self.assertFalse(sw.cover3OpenedActive)
            self.assertFalse(sw.cover4OpenedActive)

            print(f"close time measured {measured_duration:0.2f}; desired {desired_close_time:0.2f}")
            self.assertLess(abs(measured_duration - desired_close_time), 0.3)

            # sending close again has no effect
            await harness.remote.cmd_closeM1Cover.start(timeout=1)
            with self.assertRaises(asyncio.TimeoutError):
                await harness.remote.evt_m1CoverState.next(flush=False, timeout=0.1)

        asyncio.get_event_loop().run_until_complete(doit())

    def test_run(self):
        salobj.test_utils.set_random_lsst_dds_domain()
        exe_name = "run_atpneumatics_simulator.py"
        exe_path = shutil.which(exe_name)
        if exe_path is None:
            self.fail(f"Could not find bin script {exe_name}; did you setup and scons this package?")

        async def doit():
            process = await asyncio.create_subprocess_exec(exe_name)
            try:
                remote = salobj.Remote(SALPY_ATPneumatics, index=0)
                summaryState_data = await remote.evt_summaryState.next(flush=False, timeout=10)
                self.assertEqual(summaryState_data.summaryState, salobj.State.STANDBY)

                id_ack = await remote.cmd_exitControl.start(timeout=2)
                self.assertEqual(id_ack.ack.ack, remote.salinfo.lib.SAL__CMD_COMPLETE)
                summaryState_data = await remote.evt_summaryState.next(flush=False, timeout=10)
                self.assertEqual(summaryState_data.summaryState, salobj.State.OFFLINE)

                await asyncio.wait_for(process.wait(), 2)
            except Exception:
                if process.returncode is None:
                    process.terminate()
                raise

        asyncio.get_event_loop().run_until_complete(doit())

    def test_set_pressure(self):
        async def doit():
            harness = Harness(initial_state=salobj.State.ENABLED)
            # output telemetry often so we don't have to wait
            harness.csc.telemetry_interval = 0.1
            init_m1_pressure = 5
            init_m2_pressure = 6
            harness.csc.configure(
                m1_pressure=init_m1_pressure,
                m2_pressure=init_m2_pressure,
            )
            state = await harness.remote.evt_summaryState.next(flush=False, timeout=5)
            self.assertEqual(state.summaryState, salobj.State.ENABLED)

            m1data = await harness.remote.tel_m1AirPressure.next(flush=True, timeout=1)
            self.assertEqual(m1data.pressure, init_m1_pressure)
            m2data = await harness.remote.tel_m2AirPressure.next(flush=True, timeout=1)
            self.assertEqual(m2data.pressure, init_m2_pressure)

            cmd_m1pressure = 35
            cmd_m2pressure = 47

            harness.remote.cmd_m1SetPressure.set(pressure=cmd_m1pressure)
            await harness.remote.cmd_m1SetPressure.start(timeout=1)
            harness.remote.cmd_m2SetPressure.set(pressure=cmd_m2pressure)
            await harness.remote.cmd_m2SetPressure.start(timeout=1)

            m1data = await harness.remote.tel_m1AirPressure.next(flush=True, timeout=1)
            self.assertEqual(m1data.pressure, cmd_m1pressure)
            m2data = await harness.remote.tel_m2AirPressure.next(flush=True, timeout=1)
            self.assertEqual(m2data.pressure, cmd_m2pressure)

        asyncio.get_event_loop().run_until_complete(doit())

    def test_standard_state_transitions(self):
        """Test standard CSC state transitions.
        """
        async def doit():
            harness = Harness(initial_state=salobj.State.STANDBY)
            self.assertEqual(harness.csc.summary_state, salobj.State.STANDBY)
            # make sure start_task completes
            await asyncio.wait_for(harness.csc.start_task, timeout=1)

            state = await harness.remote.evt_summaryState.next(flush=False, timeout=1)
            self.assertEqual(state.summaryState, salobj.State.STANDBY)

            # send start; new state is DISABLED
            id_ack = await harness.remote.cmd_start.start()
            self.assertEqual(id_ack.ack.ack, harness.remote.salinfo.lib.SAL__CMD_COMPLETE)
            self.assertEqual(id_ack.ack.error, 0)
            self.assertEqual(harness.csc.summary_state, salobj.State.DISABLED)
            state = await harness.remote.evt_summaryState.next(flush=False, timeout=1)
            self.assertEqual(state.summaryState, salobj.State.DISABLED)

            # send enable; new state is ENABLED
            id_ack = await harness.remote.cmd_enable.start()
            self.assertEqual(id_ack.ack.ack, harness.remote.salinfo.lib.SAL__CMD_COMPLETE)
            self.assertEqual(id_ack.ack.error, 0)
            self.assertEqual(harness.csc.summary_state, salobj.State.ENABLED)
            state = await harness.remote.evt_summaryState.next(flush=False, timeout=1)
            self.assertEqual(state.summaryState, salobj.State.ENABLED)

            # send disable; new state is DISABLED
            id_ack = await harness.remote.cmd_disable.start()
            self.assertEqual(id_ack.ack.ack, harness.remote.salinfo.lib.SAL__CMD_COMPLETE)
            self.assertEqual(id_ack.ack.error, 0)
            self.assertEqual(harness.csc.summary_state, salobj.State.DISABLED)
            state = await harness.remote.evt_summaryState.next(flush=False, timeout=1)
            self.assertEqual(state.summaryState, salobj.State.DISABLED)

            # send standby; new state is STANDBY
            id_ack = await harness.remote.cmd_standby.start()
            self.assertEqual(id_ack.ack.ack, harness.remote.salinfo.lib.SAL__CMD_COMPLETE)
            self.assertEqual(id_ack.ack.error, 0)
            self.assertEqual(harness.csc.summary_state, salobj.State.STANDBY)
            state = await harness.remote.evt_summaryState.next(flush=False, timeout=1)
            self.assertEqual(state.summaryState, salobj.State.STANDBY)

            # send exitControl; new state is OFFLINE
            id_ack = await harness.remote.cmd_exitControl.start()
            self.assertEqual(id_ack.ack.ack, harness.remote.salinfo.lib.SAL__CMD_COMPLETE)
            self.assertEqual(id_ack.ack.error, 0)
            self.assertEqual(harness.csc.summary_state, salobj.State.OFFLINE)
            state = await harness.remote.evt_summaryState.next(flush=False, timeout=1)
            self.assertEqual(state.summaryState, salobj.State.OFFLINE)

            await asyncio.wait_for(harness.csc.done_task, 2)

        asyncio.get_event_loop().run_until_complete(doit())


if __name__ == "__main__":
    unittest.main()
