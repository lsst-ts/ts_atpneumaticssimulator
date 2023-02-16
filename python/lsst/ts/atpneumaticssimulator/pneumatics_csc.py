# This file is part of ts_atpneumaticssimulator.
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

__all__ = ["ATPneumaticsCsc", "run_atpneumatics_simulator"]

import asyncio

from lsst.ts import salobj, utils
from lsst.ts.idl.enums import ATPneumatics

from . import __version__


class ATPneumaticsCsc(salobj.BaseCsc):
    """Simulator for the auxiliary telescope pneumatics controller CSC.

    Parameters
    ----------
    initial_state : `salobj.State` or `int` (optional)
        The initial state of the CSC. This is provided for unit testing,
        as real CSCs should start up in `State.STANDBY`, the default.

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

    valid_simulation_modes = [1]
    # Append "-sim" to avoid confusion with the real ATPneumatics CSC.
    version = f"{__version__}-sim"

    def __init__(self, initial_state=salobj.State.STANDBY):
        super().__init__(
            name="ATPneumatics", index=0, initial_state=initial_state, simulation_mode=1
        )
        # Interval between telemetry updates.
        self.telemetry_interval = 1.0

        # Tasks used to run the methods that simulate
        # opening and closing M1 covers and cell vents.
        self._close_m1_covers_task = utils.make_done_future()
        self._open_m1_covers_task = utils.make_done_future()
        self._close_cell_vents_task = utils.make_done_future()
        self._open_cell_vents_task = utils.make_done_future()

    async def close_tasks(self):
        await super().close_tasks()
        self._close_m1_covers_task.cancel()
        self._open_m1_covers_task.cancel()
        self._close_cell_vents_task.cancel()
        self._open_cell_vents_task.cancel()

    async def start(self):
        await super().start()
        await self.configure()
        await self.initialize()

    async def configure(
        self,
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
        await self.evt_m1SetPressure.set_write(pressure=m1_pressure)
        await self.evt_m2SetPressure.set_write(pressure=m2_pressure)
        self.main_pressure = main_pressure
        self.cell_load = cell_load

    async def initialize(self):
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
        await self.evt_eStop.set_write(triggered=False)
        await self.set_cell_vents_events(closed=True, opened=False)
        await self.set_m1_cover_events(closed=True, opened=False)
        await self.evt_instrumentState.set_write(
            state=ATPneumatics.AirValveState.OPENED,
        )
        await self.evt_m1State.set_write(
            state=ATPneumatics.AirValveState.OPENED,
        )
        await self.evt_m2State.set_write(
            state=ATPneumatics.AirValveState.OPENED,
        )
        await self.evt_mainValveState.set_write(
            state=ATPneumatics.AirValveState.OPENED,
        )
        await self.evt_powerStatus.set_write(
            powerOnL1=True,
            powerOnL2=True,
            powerOnL3=True,
        )

    async def do_closeInstrumentAirValve(self, data):
        self.assert_enabled()
        await self.evt_instrumentState.set_write(
            state=ATPneumatics.AirValveState.CLOSED,
        )

    async def do_closeM1CellVents(self, data):
        self.assert_enabled()
        self._open_cell_vents_task.cancel()
        if self.m1_vents_closing:
            return
        self._close_cell_vents_task = asyncio.ensure_future(self.close_cell_vents())

    async def do_closeM1Cover(self, data):
        self.assert_enabled()
        if self.m1CoversClosing:
            return
        self._open_m1_covers_task.cancel()
        self._close_m1_covers_task = asyncio.ensure_future(self.close_m1_covers())

    async def do_closeMasterAirSupply(self, data):
        self.assert_enabled()
        await self.evt_mainValveState.set_write(
            state=ATPneumatics.AirValveState.CLOSED,
        )

    async def do_m1CloseAirValve(self, data):
        self.assert_enabled()
        await self.evt_m1State.set_write(
            state=ATPneumatics.AirValveState.CLOSED,
        )

    async def do_m1SetPressure(self, data):
        self.assert_enabled()
        await self.evt_m1SetPressure.set_write(pressure=data.pressure)

    async def do_m2CloseAirValve(self, data):
        self.assert_enabled()
        await self.evt_m2State.set_write(
            state=ATPneumatics.AirValveState.CLOSED,
        )

    async def do_m1OpenAirValve(self, data):
        self.assert_enabled()
        await self.evt_m1State.set_write(
            state=ATPneumatics.AirValveState.OPENED,
        )

    async def do_m2OpenAirValve(self, data):
        self.assert_enabled()
        await self.evt_m2State.set_write(
            state=ATPneumatics.AirValveState.OPENED,
        )

    async def do_m2SetPressure(self, data):
        self.assert_enabled()
        await self.evt_m2SetPressure.set_write(pressure=data.pressure)

    async def do_openInstrumentAirValve(self, data):
        self.assert_enabled()
        await self.evt_instrumentState.set_write(
            state=ATPneumatics.AirValveState.OPENED,
        )

    async def do_openM1CellVents(self, data):
        self.assert_enabled()
        self._close_cell_vents_task.cancel()
        if self.m1VentsOpening:
            return
        self._open_cell_vents_task = asyncio.ensure_future(self.open_cell_vents())

    async def do_openM1Cover(self, data):
        self.assert_enabled()
        self._close_m1_covers_task.cancel()
        if self.m1CoversOpening:
            return
        self._open_m1_covers_task = asyncio.ensure_future(self.open_m1_covers())

    async def do_openMasterAirSupply(self, data):
        self.assert_enabled()
        await self.evt_mainValveState.set_write(
            state=ATPneumatics.AirValveState.OPENED,
        )

    @property
    def m1CoversClosing(self):
        """Are the M1 covers closing?"""
        return not self._close_m1_covers_task.done()

    @property
    def m1CoversOpening(self):
        """Are the M1 covers opening?"""
        return not self._open_m1_covers_task.done()

    @property
    def m1_vents_closing(self):
        """Are the M1 vents closing?"""
        return not self._close_cell_vents_task.done()

    @property
    def m1VentsOpening(self):
        """Are the M1 vents opening?"""
        return not self._open_cell_vents_task.done()

    async def close_m1_covers(self):
        """Close the M1 covers."""
        if self.evt_m1CoverState.data.state != ATPneumatics.MirrorCoverState.CLOSED:
            await self.set_m1_cover_events(closed=False, opened=False)
            await asyncio.sleep(self.m1_covers_close_time)
        await self.set_m1_cover_events(closed=True, opened=False)

    async def close_cell_vents(self):
        """Close the M1 vents."""
        if self.evt_m1VentsPosition.data.position != ATPneumatics.VentsPosition.CLOSED:
            await self.set_cell_vents_events(closed=False, opened=False)
            await asyncio.sleep(self.cell_vents_close_time)
        await self.set_cell_vents_events(closed=True, opened=False)

    async def open_m1_covers(self):
        """Open the M1 covers."""
        if self.evt_m1CoverState.data.state != ATPneumatics.MirrorCoverState.OPENED:
            await self.set_m1_cover_events(closed=False, opened=False)
            await asyncio.sleep(self.m1_covers_open_time)
        await self.set_m1_cover_events(closed=False, opened=True)

    async def open_cell_vents(self):
        """Open the M1 vents."""
        if self.evt_m1VentsPosition.data.position != ATPneumatics.VentsPosition.OPENED:
            await self.set_cell_vents_events(closed=False, opened=False)
            await asyncio.sleep(self.cell_vents_open_time)
        await self.set_cell_vents_events(closed=False, opened=True)

    async def handle_summary_state(self):
        await super().handle_summary_state()
        if self.summary_state in (salobj.State.DISABLED, salobj.State.ENABLED):
            asyncio.create_task(self.telemetry_loop())

    async def set_cell_vents_events(self, closed, opened):
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
            await self.evt_cellVentsState.set_write(
                state=ATPneumatics.CellVentState.INMOTION,
            )

        await self.evt_m1VentsLimitSwitches.set_write(
            ventsClosedActive=closed,
            ventsOpenedActive=opened,
        )
        if opened:
            await self.evt_m1VentsPosition.set_write(
                position=ATPneumatics.VentsPosition.OPENED,
            )
            await self.evt_cellVentsState.set_write(
                state=ATPneumatics.CellVentState.OPENED,
            )
        elif closed:
            await self.evt_m1VentsPosition.set_write(
                position=ATPneumatics.VentsPosition.CLOSED,
            )
            await self.evt_cellVentsState.set_write(
                state=ATPneumatics.CellVentState.CLOSED,
            )
        else:
            await self.evt_m1VentsPosition.set_write(
                position=ATPneumatics.VentsPosition.PARTIALLYOPENED,
            )

    async def set_m1_cover_events(self, closed, opened):
        """Set m1CoverLimitSwitches and m1CoverState events.

        Output any changes.

        Parameters
        ----------
        closed : `bool`
            Are the closed switches active?
        opened : `bool`
            Are the opened switches active?
        """
        await self.evt_m1CoverLimitSwitches.set_write(
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
            await self.evt_m1CoverState.set_write(
                state=ATPneumatics.MirrorCoverState.INVALID,
            )
        elif opened:
            await self.evt_m1CoverState.set_write(
                state=ATPneumatics.MirrorCoverState.OPENED,
            )
        elif closed:
            await self.evt_m1CoverState.set_write(
                state=ATPneumatics.MirrorCoverState.CLOSED,
            )
        else:
            await self.evt_m1CoverState.set_write(
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

            await self.tel_m1AirPressure.set_write(pressure=m1_pressure)
            await self.tel_m2AirPressure.set_write(pressure=m2_pressure)
            await self.tel_mainAirSourcePressure.set_write(
                pressure=self.main_pressure if main_valve_open else 0
            )
            await self.tel_loadCell.set_write(cellLoad=self.cell_load)
            await asyncio.sleep(self.telemetry_interval)


def run_atpneumatics_simulator():
    """Run the ATPneumatics CSC simulator."""
    asyncio.run(ATPneumaticsCsc.amain(index=None))
