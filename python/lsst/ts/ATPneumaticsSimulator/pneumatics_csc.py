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
from lsst.ts.idl.enums import ATPneumatics


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
    * eStop
    * instrumentState
    * m1CoverLimitSwitches
    * m1CoverState
    * m1State
    * m1VentsLimitSwitches
    * m1VentsPosition
    * m2State
    * mainValveState
    * powerStatus
    """
    def __init__(self, initial_state=salobj.State.STANDBY, initial_simulation_mode=1):
        super().__init__(name="ATPneumatics", index=0, initial_state=initial_state,
                         initial_simulation_mode=initial_simulation_mode)
        self.telemetry_interval = 1.0
        """Interval between telemetry updates (sec)"""
        self._closeM1CoversTask = salobj.make_done_future()
        self._openM1CoversTask = salobj.make_done_future()
        self._closeCellVentsTask = salobj.make_done_future()
        self._openCellVentsTask = salobj.make_done_future()
        self.configure()
        self.initialize()

    async def close_tasks(self):
        await super().close_tasks()
        self._closeM1CoversTask.cancel()
        self._openM1CoversTask.cancel()
        self._closeCellVentsTask.cancel()
        self._openCellVentsTask.cancel()

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
        self.evt_m1SetPressure.set_put(pressure=m1_pressure)
        self.evt_m2SetPressure.set_put(pressure=m2_pressure)
        self.main_pressure = main_pressure
        self.cell_load = cell_load

    def initialize(self):
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
        self.evt_eStop.set_put(triggered=False)
        self.set_cell_vents_events(closed=True, opened=False)
        self.set_m1_cover_events(closed=True, opened=False)
        self.evt_instrumentState.set_put(
            state=ATPneumatics.AirValveState.OPENED,
        )
        self.evt_m1State.set_put(
            state=ATPneumatics.AirValveState.OPENED,
        )
        self.evt_m2State.set_put(
            state=ATPneumatics.AirValveState.OPENED,
        )
        self.evt_mainValveState.set_put(
            state=ATPneumatics.AirValveState.OPENED,
        )
        self.evt_powerStatus.set_put(
            powerOnL1=True,
            powerOnL2=True,
            powerOnL3=True,
        )

    def do_closeInstrumentAirValve(self, data):
        self.assert_enabled("closeInstrumentAirValve")
        self.evt_instrumentState.set_put(
            state=ATPneumatics.AirValveState.CLOSED,
        )

    def do_closeM1CellVents(self, data):
        self.assert_enabled("closeM1CellVents")
        self._openCellVentsTask.cancel()
        if self.m1VentsClosing:
            return
        self._closeCellVentsTask = asyncio.ensure_future(self.closeCellVents())

    def do_closeM1Cover(self, data):
        self.assert_enabled("closeM1Cover")
        if self.m1CoversClosing:
            return
        self._openM1CoversTask.cancel()
        self._closeM1CoversTask = asyncio.ensure_future(self.closeM1Covers())

    def do_closeMasterAirSupply(self, data):
        self.assert_enabled("closeMasterAirSupply")
        self.evt_mainValveState.set_put(
            state=ATPneumatics.AirValveState.CLOSED,
        )

    def do_m1CloseAirValve(self, data):
        self.assert_enabled("m1CloseAirValve")
        self.evt_m1State.set_put(
            state=ATPneumatics.AirValveState.CLOSED,
        )

    def do_m1SetPressure(self, data):
        self.assert_enabled("m1SetPressure")
        self.evt_m1SetPressure.set_put(pressure=data.pressure)

    def do_m2CloseAirValve(self, data):
        self.assert_enabled("m2CloseAirValve")
        self.evt_m2State.set_put(
            state=ATPneumatics.AirValveState.CLOSED,
        )

    def do_m1OpenAirValve(self, data):
        self.assert_enabled("m1OpenAirValve")
        self.evt_m1State.set_put(
            state=ATPneumatics.AirValveState.OPENED,
        )

    def do_m2OpenAirValve(self, data):
        self.assert_enabled("m2OpenAirValve")
        self.evt_m2State.set_put(
            state=ATPneumatics.AirValveState.OPENED,
        )

    def do_m2SetPressure(self, data):
        self.assert_enabled("m2SetPressure")
        self.evt_m2SetPressure.set_put(pressure=data.pressure)

    def do_openInstrumentAirValve(self, data):
        self.assert_enabled("openInstrumentAirValve")
        self.evt_instrumentState.set_put(
            state=ATPneumatics.AirValveState.OPENED,
        )

    def do_openM1CellVents(self, data):
        self.assert_enabled("openCellVents")
        self._closeCellVentsTask.cancel()
        if self.m1VentsOpening:
            return
        self._openCellVentsTask = asyncio.ensure_future(self.openCellVents())

    def do_openM1Cover(self, data):
        self.assert_enabled("openM1Cover")
        self._closeM1CoversTask.cancel()
        if self.m1CoversOpening:
            return
        self._openM1CoversTask = asyncio.ensure_future(self.openM1Covers())

    def do_openMasterAirSupply(self, data):
        self.assert_enabled("openMasterAirSupply")
        self.evt_mainValveState.set_put(
            state=ATPneumatics.AirValveState.OPENED,
        )

    @property
    def m1CoversClosing(self):
        """Are the M1 covers closing?"""
        return not self._closeM1CoversTask.done()

    @property
    def m1CoversOpening(self):
        """Are the M1 covers opening?"""
        return not self._openM1CoversTask.done()

    @property
    def m1VentsClosing(self):
        """Are the M1 vents closing?"""
        return not self._closeCellVentsTask.done()

    @property
    def m1VentsOpening(self):
        """Are the M1 vents opening?"""
        return not self._openCellVentsTask.done()

    async def closeM1Covers(self):
        """Close the M1 covers."""
        if self.evt_m1CoverState.data.state != \
                ATPneumatics.MirrorCoverState.CLOSED:
            self.set_m1_cover_events(closed=False, opened=False)
            await asyncio.sleep(self.m1_covers_close_time)
        self.set_m1_cover_events(closed=True, opened=False)

    async def closeCellVents(self):
        """Close the M1 vents."""
        if self.evt_m1VentsPosition.data.position != \
                ATPneumatics.VentsPosition.CLOSED:
            self.set_cell_vents_events(closed=False, opened=False)
            await asyncio.sleep(self.cell_vents_close_time)
        self.set_cell_vents_events(closed=True, opened=False)

    async def openM1Covers(self):
        """Open the M1 covers."""
        if self.evt_m1CoverState.data.state != \
                ATPneumatics.MirrorCoverState.OPENED:
            self.set_m1_cover_events(closed=False, opened=False)
            await asyncio.sleep(self.m1_covers_open_time)
        self.set_m1_cover_events(closed=False, opened=True)

    async def openCellVents(self):
        """Open the M1 vents."""
        if self.evt_m1VentsPosition.data.position != \
                ATPneumatics.VentsPosition.OPENED:
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
                state=ATPneumatics.CellVentState.INMOTION,
            )

        self.evt_m1VentsLimitSwitches.set_put(
            ventsClosedActive=closed,
            ventsOpenedActive=opened,
        )
        if opened:
            self.evt_m1VentsPosition.set_put(
                position=ATPneumatics.VentsPosition.OPENED,
            )
            self.evt_cellVentsState.set_put(
                state=ATPneumatics.CellVentState.OPENED,
            )
        elif closed:
            self.evt_m1VentsPosition.set_put(
                position=ATPneumatics.VentsPosition.CLOSED,
            )
            self.evt_cellVentsState.set_put(
                state=ATPneumatics.CellVentState.CLOSED,
            )
        else:
            self.evt_m1VentsPosition.set_put(
                position=ATPneumatics.VentsPosition.PARTIALLYOPENED,
            )

    def set_m1_cover_events(self, closed, opened):
        """Set m1CoverLimitSwitches and m1CoverState events.

        Output any changes.

        Parameters
        ----------
        closed : `bool`
            Are the closed switches active?
        opened : `bool`
            Are the opened switches active?
        """
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
        if opened and closed:
            self.evt_m1CoverState.set_put(
                state=ATPneumatics.MirrorCoverState.INVALID,
            )
        elif opened:
            self.evt_m1CoverState.set_put(
                state=ATPneumatics.MirrorCoverState.OPENED,
            )
        elif closed:
            self.evt_m1CoverState.set_put(
                state=ATPneumatics.MirrorCoverState.CLOSED,
            )
        else:
            self.evt_m1CoverState.set_put(
                state=ATPneumatics.MirrorCoverState.INMOTION,
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
            opened_state = ATPneumatics.AirValveState.OPENED
            main_valve_open = self.evt_mainValveState.data.state == opened_state

            if main_valve_open and self.evt_m1State.data.state == opened_state:
                m1_pressure = self.evt_m1SetPressure.data.pressure
            else:
                m1_pressure = 0

            if main_valve_open and self.evt_m2State.data.state == opened_state:
                m2_pressure = self.evt_m2SetPressure.data.pressure
            else:
                m2_pressure = 0

            self.tel_m1AirPressure.set_put(pressure=m1_pressure)
            self.tel_m2AirPressure.set_put(pressure=m2_pressure)
            self.tel_mainAirSourcePressure.set_put(pressure=self.main_pressure if main_valve_open else 0)
            self.tel_loadCell.set_put(cellLoad=self.cell_load)
            await asyncio.sleep(self.telemetry_interval)
