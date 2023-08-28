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

__all__ = ["ATPneumaticsCsc", "run_atpneumatics_simulator"]

import asyncio

from lsst.ts import attcpip, salobj

from . import __version__
from .config_schema import CONFIG_SCHEMA
from .enums import Command
from .pneumatics_simulator import PneumaticsSimulator


class ATPneumaticsCsc(attcpip.AtTcpipCsc):
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

    # TODO DM-39357 Remove these lines.
    # Append "-sim" to avoid confusion with the real ATPneumatics CSC.
    version = f"{__version__}-sim"

    def __init__(
        self,
        config_dir: str | None = None,
        initial_state: salobj.State = salobj.State.STANDBY,
    ) -> None:
        super().__init__(
            name="ATPneumatics",
            index=0,
            config_schema=CONFIG_SCHEMA,
            config_dir=config_dir,
            initial_state=initial_state,
            simulation_mode=1,
        )

        # PenumaticsSimulator for simulation_mode == 1.
        self.simulator: PneumaticsSimulator | None = None

    async def start_clients(self) -> None:
        if self.simulator is None:
            self.simulator = PneumaticsSimulator(
                host=self.config.host,
                cmd_evt_port=self.config.cmd_evt_port,
                telemetry_port=self.config.telemetry_port,
            )
        await super().start_clients()

    async def do_closeInstrumentAirValve(self, data: salobj.BaseMsgType) -> None:
        self.assert_enabled("closeInstrumentAirValve")
        command_issued = await self.write_command(
            command=Command.CLOSE_INSTRUMENT_AIR_VALE
        )
        await command_issued.done

    async def do_closeM1CellVents(self, data: salobj.BaseMsgType) -> None:
        self.assert_enabled("closeM1CellVents")
        command_issued = await self.write_command(command=Command.CLOSE_M1_CELL_VENTS)
        await command_issued.done

    async def do_closeM1Cover(self, data: salobj.BaseMsgType) -> None:
        self.assert_enabled("closeM1Cover")
        command_issued = await self.write_command(command=Command.CLOSE_M1_COVER)
        await command_issued.done

    async def do_closeMasterAirSupply(self, data: salobj.BaseMsgType) -> None:
        self.assert_enabled("closeMasterAirSupply")
        command_issued = await self.write_command(
            command=Command.CLOSE_MASTER_AIR_SUPPLY
        )
        await command_issued.done

    async def do_m1CloseAirValve(self, data: salobj.BaseMsgType) -> None:
        self.assert_enabled("m1CloseAirValve")
        command_issued = await self.write_command(command=Command.M1_CLOSE_AIR_VALVE)
        await command_issued.done

    async def do_m1SetPressure(self, data: salobj.BaseMsgType) -> None:
        self.assert_enabled("m1SetPressure")
        command_issued = await self.write_command(
            command=Command.M1_SET_PRESSURE, pressure=data.pressure
        )
        await command_issued.done

    async def do_m2CloseAirValve(self, data: salobj.BaseMsgType) -> None:
        self.assert_enabled("m2CloseAirValve")
        command_issued = await self.write_command(command=Command.M2_CLOSE_AIR_VALVE)
        await command_issued.done

    async def do_m1OpenAirValve(self, data: salobj.BaseMsgType) -> None:
        self.assert_enabled("m1OpenAirValve")
        command_issued = await self.write_command(command=Command.M1_OPEN_AIR_VALVE)
        await command_issued.done

    async def do_m2OpenAirValve(self, data: salobj.BaseMsgType) -> None:
        self.assert_enabled("m2OpenAirValve")
        command_issued = await self.write_command(command=Command.M2_OPEN_AIR_VALVE)
        await command_issued.done

    async def do_m2SetPressure(self, data: salobj.BaseMsgType) -> None:
        self.assert_enabled("m2SetPressure")
        command_issued = await self.write_command(
            command=Command.M2_SET_PRESSURE, pressure=data.pressure
        )
        await command_issued.done

    async def do_openInstrumentAirValve(self, data: salobj.BaseMsgType) -> None:
        self.assert_enabled("openInstrumentAirValve")
        command_issued = await self.write_command(
            command=Command.OPEN_INSTRUMENT_AIR_VALVE
        )
        await command_issued.done

    async def do_openM1CellVents(self, data: salobj.BaseMsgType) -> None:
        self.assert_enabled("openM1CellVents")
        command_issued = await self.write_command(command=Command.OPEN_M1_CELL_VENTS)
        await command_issued.done

    async def do_openM1Cover(self, data: salobj.BaseMsgType) -> None:
        self.assert_enabled("openM1Cover")
        command_issued = await self.write_command(command=Command.OPEN_M1_COVER)
        await command_issued.done

    async def do_openMasterAirSupply(self, data: salobj.BaseMsgType) -> None:
        self.assert_enabled("openMasterAirSupply")
        command_issued = await self.write_command(
            command=Command.OPEN_MASTER_AIR_SUPPLY
        )
        await command_issued.done


def run_atpneumatics_simulator() -> None:
    """Run the ATPneumatics CSC simulator."""
    asyncio.run(ATPneumaticsCsc.amain(index=None))
