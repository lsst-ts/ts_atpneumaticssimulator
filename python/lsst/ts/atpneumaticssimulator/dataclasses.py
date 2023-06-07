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

__all__ = ["LoadCell", "M1AirPressure", "M2AirPressure", "MainAirSourcePressure"]

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
