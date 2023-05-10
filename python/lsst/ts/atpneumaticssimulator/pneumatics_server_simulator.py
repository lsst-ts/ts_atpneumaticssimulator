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
import logging
import typing

from lsst.ts import tcpip

__all__ = ["PneumaticsServerSimulator"]


class PneumaticsServerSimulator(tcpip.OneClientReadLoopServer):
    """An implementation of OneClientJsonServer that simulates a Pneumatics
     server.

    Parameters
    ----------
    host : `str` or `None`
        IP address for this server; typically `LOCALHOST_IPV4` for IPV4
        or `LOCALHOST_IPV6` for IPV6. If `None` then bind to all network
        interfaces (e.g. listen on an IPv4 socket and an IPv6 socket).
        None can cause trouble with port=0;
        see ``port`` in the Attributes section for more information.
    port : `int`
        IP port for this server. If 0 then randomly pick an available port
        (or ports, if listening on multiple sockets).
        0 is strongly recommended for unit tests.
    log : `logging.Logger`
        Logger.
    dispatch_callback : `callable`
        Asynchronous function to call when data are read and dispatched.
    connect_callback : `callable` or `None`, optional
        Asynchronous or (deprecated) synchronous function to call when
        when a client connects or disconnects.
        If the other end (client) closes the connection, it may take
        ``monitor_connection_interval`` seconds or longer to notice.
        The function receives one argument: this `OneClientServer`.
    name : `str`, optional
        Name used for log messages, e.g. "Commands" or "Telemetry".
    **kwargs : `dict` [`str`, `typing.Any`]
        Additional keyword arguments for `asyncio.start_server`,
        beyond host and port.
    """

    def __init__(
        self,
        host: str | None,
        port: int | None,
        log: logging.Logger,
        dispatch_callback: tcpip.ConnectCallbackType,
        connect_callback: tcpip.ConnectCallbackType | None = None,
        name: str = "",
        **kwargs: typing.Any,
    ) -> None:
        super().__init__(
            host=host,
            port=port,
            log=log,
            connect_callback=connect_callback,
            name=name,
            **kwargs,
        )
        self.dispatch_callback = dispatch_callback
        self.start_event = asyncio.Event()

    async def start(self, **kwargs: typing.Any) -> None:
        """Start the TCP/IP server.

        This is called automatically by the constructor,
        and is not intended to be called by the user.
        It is a public method so that subclasses can override it.

        After calling the super start method, an async event is set so clients
        can be ensured that the server has been started.

        Parameters
        ----------
        **kwargs : `dict` [`str`, `typing.Any`]
            Additional keyword arguments for `asyncio.start_server`,
            beyond host and port.

        Raises
        ------
        `RuntimeError`
            If start has already been called and has successfully constructed
            a server.
        """
        await super().start(**kwargs)
        self.start_event.set()

    async def close(self) -> None:
        """Close socket server and client socket, and set done_task done.

        Call connect_callback if a client was connected.

        Always safe to call.

        After calling the super stop method, an async event is cleared so
        clients can be ensured that the server has been closed.
        """
        await super().close()
        self.start_event.clear()

    async def read_and_dispatch(self) -> None:
        data = await self.read_json()
        await self.dispatch_callback(data=data)