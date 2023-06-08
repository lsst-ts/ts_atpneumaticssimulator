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

__all__ = [
    "LoadCell",
    "M1AirPressure",
    "M1CoverLimitSwitches",
    "M1VentsLimitSwitches",
    "M2AirPressure",
    "MainAirSourcePressure",
    "PowerStatus",
]

from dataclasses import dataclass


def one_hundred_zeros() -> list[float]:
    """Return a list of 100 zeros."""
    return [0.0] * 100


@dataclass
class LoadCell:
    """Dataclass holding load cell value (from M1 hardpoint) data.

    Attributes
    ----------
    cellLoad : float
        Load cell measurement [kg].
    """

    cellLoad: float = 0.0


@dataclass
class M1AirPressure:
    """Dataclass holding measured pressure in air line to M1 pneumatic
    actuators data.

    Attributes
    ----------
    pressure : float
        Measured pressure of M1 air line [Ps].
    """

    pressure: float = 0.0


@dataclass
class M1CoverLimitSwitches:
    """Dataclass holding state of each of the 4 M1 mirror cover petals data.

    Attributes
    ----------
    cover1ClosedActive : bool
        True if cover/petal 1 closed.
    cover2ClosedActive : bool
        True if cover/petal 2 closed.
    cover3ClosedActive : bool
        True if cover/petal 3 closed.
    cover4ClosedActive : bool
        True if cover/petal 4 closed.
    cover1OpenedActive : bool
        True if cover/petal 1 open.
    cover2OpenedActive : bool
        True if cover/petal 2 open.
    cover3OpenedActive : bool
        True if cover/petal 3 open.
    cover4OpenedActive : bool
        True if cover/petal 4 open.
    """

    cover1ClosedActive: bool = False
    cover2ClosedActive: bool = False
    cover3ClosedActive: bool = False
    cover4ClosedActive: bool = False
    cover1OpenedActive: bool = False
    cover2OpenedActive: bool = False
    cover3OpenedActive: bool = False
    cover4OpenedActive: bool = False


@dataclass
class M1VentsLimitSwitches:
    """Dataclass holding M1 vents open/closed data.

    Attributes
    ----------
    ventsClosedActive : bool
        True if M1 vents closed.
    ventsOpenedActive : bool
        True if M1 vents open.
    """

    ventsClosedActive: bool = False
    ventsOpenedActive: bool = False


@dataclass
class M2AirPressure:
    """Dataclass holding measured pressure in air line to M2 pneumatic
    actuators data.

    Attributes
    ----------
    pressure : float
        Measured pressure of M2 air line [Ps].
    """

    pressure: float = 0.0


@dataclass
class MainAirSourcePressure:
    """Dataclass holding measured pressure in main supply line from compressor
     data.

    Attributes
    ----------
    pressure : float
        Measured pressure of main air supply line [Ps].
    """

    pressure: float = 0.0


@dataclass
class PowerStatus:
    """Dataclass holding state of circuit breakers for ATMCS drives data.

    Attributes
    ----------
    powerOnL1 : bool
        Status Power line 1, Azimuth motors 1 and 2.
    powerOnL1 : bool
        Status Power line 2, Elevation and M3 rotator.
    powerOnL1 : bool
        Status Power line 3, Nasmyth ports 1 and 2.
    """

    powerOnL1: bool = False
    powerOnL2: bool = False
    powerOnL3: bool = False
