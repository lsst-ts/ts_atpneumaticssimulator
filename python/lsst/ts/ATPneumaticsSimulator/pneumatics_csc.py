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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__all__ = ["ATPneumaticsCsc"]

import asyncio

from lsst.ts import salobj
import SALPY_ATPneumatics


class ATPneumaticsCsc(salobj.BaseCsc):
    """Simulator for the auxiliary telescope pneumatics controller CSC.

    Parameters
    ----------
    initial_state : `salobj.State` or `int` (optional)
        The initial state of the CSC. This is provided for unit testing,
        as real CSCs should start up in `State.STANDBY`, the default.
    initial_simulation_mode : `int` (optional)
        Initial simulation mode.
        The only allowed value is 1: simulating.

    Notes
    -----
    **Events**

    * cellVentsState
    * eStopTriggered
    * instrumentState
    * m1CoverLimitSwitches
    * m1CoverPosition
    * m1CoverState
    * m1State
    * m1VentsLimitSwitches
    * m1VentsPosition
    * m2State
    * mainValveState
    * powerStatus
    * resetEStopTriggered
    """
    def __init__(self, initial_state=salobj.State.STANDBY, initial_simulation_mode=1):
        super().__init__(SALPY_ATPneumatics, index=0, initial_state=initial_state,
                         initial_simulation_mode=initial_simulation_mode)
        self.telemetry_interval = 1.0
        """Interval between telemetry updates (sec)"""
        self._closeM1CoversTask = None  # task for closing mirror covers
        self._openM1CoversTask = None  # task for opening mirror covers
        self._closeCellVentsTask = None  # task for closing cell vents
        self._openCellVentsTask = None  # task for opening cell vents
        # I hope these two will go away once we have events to report
        # and store the commanded pressure
        self.cmd_m1_pressure = None
        self.cmd_m2_pressure = None
        self.configure()
        self.initialize()

    def configure(self,
                  m1_covers_close_time=20,
                  m1_covers_open_time=20,
                  cell_vents_close_time=5,
                  cell_vents_open_time=1,
                  m1_pressure=5,
                  m2_pressure=6,
                  main_pressure=10,
                  cell_load=100,
                  ):
        """Configure the CSC.

        Parameters
        ----------
        m1_covers_close_time : `float`
            Time to close M1 mirror covers (sec)
        m1_covers_open_time : `float`
            Time to open M1 mirror covers (sec)
        cell_vents_close_time : `float`
            Time to close cell vents (sec)
        cell_vents_open_time : `float`
            Time to open cell vents (sec)
        m1_pressure : `float`
            Initial M1 air pressure (units?)
        m2_pressure : `float`
            Initial M2 air pressure (units?)
        cell_load : `float`
            Initial cell load (units?)
        """
        assert m1_covers_close_time >= 0
        assert m1_covers_close_time >= 0
        assert cell_vents_close_time >= 0
        assert cell_vents_open_time >= 0
        assert m1_pressure > 0
        assert m2_pressure > 0
        assert main_pressure > 0
        assert cell_load > 0
        self.m1_covers_close_time = m1_covers_close_time
        self.m1_covers_open_time = m1_covers_open_time
        self.cell_vents_close_time = cell_vents_close_time
        self.cell_vents_open_time = cell_vents_open_time
        self.cmd_m1_pressure = m1_pressure
        self.cmd_m2_pressure = m2_pressure
        self.main_pressure = main_pressure
        self.cell_load = cell_load

    def initialize(self):
        """Initialize events and telemetry.

        * instrumentState
        * m1CoverLimitSwitches
        * m1CoverPosition
        * m1CoverState
        * m1State
        * cellVentsState (should be named m1VentsState)
        * m1VentsLimitSwitches
        * m1VentsPosition
        * m2State
        * mainValveState
        * powerStatus
        """
        self.set_cell_vents_events(closed=True, opened=False)
        self.set_m1_cover_events(closed=True, opened=False)
        self.evt_instrumentState.set_put(
            state=SALPY_ATPneumatics.ATPneumatics_shared_AirValveState_ValveOpenedState,
        )
        self.evt_m1State.set_put(
            state=SALPY_ATPneumatics.ATPneumatics_shared_AirValveState_ValveOpenedState,
        )
        self.evt_m2State.set_put(
            state=SALPY_ATPneumatics.ATPneumatics_shared_AirValveState_ValveOpenedState,
        )
        self.evt_mainValveState.set_put(
            state=SALPY_ATPneumatics.ATPneumatics_shared_AirValveState_ValveOpenedState,
        )
        self.evt_powerStatus.set_put(
            powerOnL1=True,
            powerOnL2=True,
            powerOnL3=True,
        )

    def do_closeInstrumentAirValve(self, id_data):
        self.assert_enabled("closeInstrumentAirValve")
        self.evt_instrumentState.set_put(
            state=SALPY_ATPneumatics.ATPneumatics_shared_AirValveState_ValveClosedState,
        )

    def do_closeM1CellVents(self, id_data):
        self.assert_enabled("closeM1CellVents")
        if self.m1VentsOpening:
            self._openCellVentsTask.cancel()
        if self.m1VentsClosing:
            return
        self._closeCellVentsTask = asyncio.ensure_future(self.closeCellVents())

    def do_closeM1Cover(self, id_data):
        self.assert_enabled("closeM1Cover")
        if self.m1CoversClosing:
            return
        if self.m1CoversOpening:
            self._openM1CoversTask.cancel()
        self._closeM1CoversTask = asyncio.ensure_future(self.closeM1Covers())

    def do_closeMasterAirSupply(self, id_data):
        self.assert_enabled("closeMasterAirSupply")
        self.evt_mainValveState.set_put(
            state=SALPY_ATPneumatics.ATPneumatics_shared_AirValveState_ValveClosedState,
        )

    def do_m1CloseAirValve(self, id_data):
        self.assert_enabled("m1CloseAirValve")
        self.evt_m1State.set_put(
            state=SALPY_ATPneumatics.ATPneumatics_shared_AirValveState_ValveClosedState,
        )

    def do_m1SetPressure(self, id_data):
        self.assert_enabled("m1SetPressure")
        self.cmd_m1_pressure = id_data.data.pressure

    def do_m2CloseAirValve(self, id_data):
        self.assert_enabled("m2CloseAirValve")
        self.evt_m2State.set_put(
            state=SALPY_ATPneumatics.ATPneumatics_shared_AirValveState_ValveClosedState,
        )

    def do_m1OpenAirValve(self, id_data):
        self.assert_enabled("m1OpenAirValve")
        self.evt_m1State.set_put(
            state=SALPY_ATPneumatics.ATPneumatics_shared_AirValveState_ValveOpenedState,
        )

    def do_m2OpenAirValve(self, id_data):
        self.assert_enabled("m2OpenAirValve")
        self.evt_m2State.set_put(
            state=SALPY_ATPneumatics.ATPneumatics_shared_AirValveState_ValveOpenedState,
        )

    def do_m2SetPressure(self, id_data):
        self.assert_enabled("m2SetPressure")
        self.cmd_m2_pressure = id_data.data.pressure

    def do_openInstrumentAirValve(self, id_data):
        self.assert_enabled("openInstrumentAirValve")
        self.evt_instrumentState.set_put(
            state=SALPY_ATPneumatics.ATPneumatics_shared_AirValveState_ValveOpenedState,
        )

    def do_openM1CellVents(self, id_data):
        self.assert_enabled("openCellVents")
        if self.m1VentsClosing:
            self._closeCellVentsTask.cancel()
        if self.m1VentsOpening:
            return
        self._openCellVentsTask = asyncio.ensure_future(self.openCellVents())

    def do_openM1Cover(self, id_data):
        self.assert_enabled("openM1Cover")
        if self.m1CoversClosing:
            self._closeM1CoversTask.cancel()
        if self.m1CoversOpening:
            return
        self._openM1CoversTask = asyncio.ensure_future(self.openM1Covers())

    def do_openMasterAirSupply(self, id_data):
        self.assert_enabled("openMasterAirSupply")
        self.evt_mainValveState.set_put(
            state=SALPY_ATPneumatics.ATPneumatics_shared_AirValveState_ValveOpenedState,
        )

    @property
    def m1CoversClosing(self):
        """Are the M1 covers closing?"""
        return self._closeM1CoversTask is not None and not self._closeM1CoversTask.done()

    @property
    def m1CoversOpening(self):
        """Are the M1 covers opening?"""
        return self._openM1CoversTask is not None and not self._openM1CoversTask.done()

    @property
    def m1VentsClosing(self):
        """Are the M1 vents closing?"""
        return self._closeCellVentsTask is not None and not self._closeCellVentsTask.done()

    @property
    def m1VentsOpening(self):
        """Are the M1 vents opening?"""
        return self._openCellVentsTask is not None and not self._openCellVentsTask.done()

    async def closeM1Covers(self):
        """Close the M1 covers."""
        if self.evt_m1CoverPosition.data.position != \
                SALPY_ATPneumatics.ATPneumatics_shared_CoverPosition_Closed:
            self.set_m1_cover_events(closed=False, opened=False)
            await asyncio.sleep(self.m1_covers_close_time)
        self.set_m1_cover_events(closed=True, opened=False)

    async def closeCellVents(self):
        """Close the M1 vents."""
        if self.evt_m1VentsPosition.data.position != \
                SALPY_ATPneumatics.ATPneumatics_shared_VentsPosition_Closed:
            self.set_cell_vents_events(closed=False, opened=False)
            await asyncio.sleep(self.cell_vents_close_time)
        self.set_cell_vents_events(closed=True, opened=False)

    async def openM1Covers(self):
        """Open the M1 covers."""
        if self.evt_m1CoverPosition.data.position != \
                SALPY_ATPneumatics.ATPneumatics_shared_CoverPosition_Opened:
            self.set_m1_cover_events(closed=False, opened=False)
            await asyncio.sleep(self.m1_covers_open_time)
        self.set_m1_cover_events(closed=False, opened=True)

    async def openCellVents(self):
        """Open the M1 vents."""
        if self.evt_m1VentsPosition.data.position != \
                SALPY_ATPneumatics.ATPneumatics_shared_VentsPosition_Opened:
            self.set_cell_vents_events(closed=False, opened=False)
            await asyncio.sleep(self.cell_vents_open_time)
        self.set_cell_vents_events(closed=False, opened=True)

    async def implement_simulation_mode(self, simulation_mode):
        if simulation_mode != 1:
            raise salobj.ExpectedError(
                f"This CSC only supports simulation; simulation_mode={simulation_mode} but must be 1")

    def report_summary_state(self):
        super().report_summary_state()
        if self.summary_state in (salobj.State.DISABLED, salobj.State.ENABLED):
            asyncio.ensure_future(self.telemetry_loop())

    def set_cell_vents_events(self, closed, opened):
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
            self.evt_cellVentsState.set_put(
                state=SALPY_ATPneumatics.ATPneumatics_shared_CellVentState_InMotionState,
            )

        self.evt_m1VentsLimitSwitches.set_put(
            ventsClosedActive=closed,
            ventsOpenedActive=opened,
        )
        if opened:
            self.evt_m1VentsPosition.set_put(
                position=SALPY_ATPneumatics.ATPneumatics_shared_VentsPosition_Opened,
            )
            self.evt_cellVentsState.set_put(
                state=SALPY_ATPneumatics.ATPneumatics_shared_CellVentState_CellVentsOpenedState,
            )
        elif closed:
            self.evt_m1VentsPosition.set_put(
                position=SALPY_ATPneumatics.ATPneumatics_shared_VentsPosition_Closed,
            )
            self.evt_cellVentsState.set_put(
                state=SALPY_ATPneumatics.ATPneumatics_shared_CellVentState_CellVentsClosedState,
            )
        else:
            self.evt_m1VentsPosition.set_put(
                position=SALPY_ATPneumatics.ATPneumatics_shared_VentsPosition_PartiallyOpened,
            )

    def set_m1_cover_events(self, closed, opened):
        """Set m1CoverLimitSwitches, m1CoverPosition and m1CoverState events.

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
            self.evt_m1CoverState.set_put(
                state=SALPY_ATPneumatics.ATPneumatics_shared_MirrorCoverState_InMotionState,
            )

        self.evt_m1CoverLimitSwitches.set_put(
            cover1ClosedActive=closed,
            cover2ClosedActive=closed,
            cover3ClosedActive=closed,
            cover4ClosedActive=closed,
            cover1OpenedActive=opened,
            cover2OpenedActive=opened,
            cover3OpenedActive=opened,
            cover4OpenedActive=opened,
        )
        if opened:
            self.evt_m1CoverPosition.set_put(
                position=SALPY_ATPneumatics.ATPneumatics_shared_CoverPosition_Opened,
            )
            self.evt_m1CoverState.set_put(
                state=SALPY_ATPneumatics.ATPneumatics_shared_MirrorCoverState_MirrorCoversOpenedState,
            )
        elif closed:
            self.evt_m1CoverPosition.set_put(
                position=SALPY_ATPneumatics.ATPneumatics_shared_CoverPosition_Closed,
            )
            self.evt_m1CoverState.set_put(
                state=SALPY_ATPneumatics.ATPneumatics_shared_MirrorCoverState_MirrorCoversClosedState,
            )
        else:
            self.evt_m1CoverPosition.set_put(
                position=SALPY_ATPneumatics.ATPneumatics_shared_CoverPosition_PartiallyOpened,
            )

    async def telemetry_loop(self):
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
        while self.summary_state == salobj.State.ENABLED:
            self.tel_m1AirPressure.set_put(pressure=self.cmd_m1_pressure)
            self.tel_m2AirPressure.set_put(pressure=self.cmd_m2_pressure)
            self.tel_mainAirSourcePressure.set_put(pressure=self.main_pressure)
            self.tel_loadCell.set_put(cellLoad=self.cell_load)
            await asyncio.sleep(self.telemetry_interval)
