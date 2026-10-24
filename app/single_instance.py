"""Single-instance guard built on QLocalServer."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstance(QObject):
    activated = Signal()

    def __init__(self, key: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.key = key
        self.server: QLocalServer | None = None

    def acquire(self) -> bool:
        """Return True when this process owns the instance; False if another one runs."""
        probe = QLocalSocket()
        probe.connectToServer(self.key)
        if probe.waitForConnected(250):
            probe.write(b"show")
            probe.flush()
            probe.waitForBytesWritten(400)
            probe.disconnectFromServer()
            return False

        QLocalServer.removeServer(self.key)
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._on_connection)
        if not self.server.listen(self.key):
            # A stale pipe should have been removed; failing to listen is not fatal.
            return True
        return True

    def _on_connection(self) -> None:
        if self.server is None:
            return
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            if socket is None:
                continue
            socket.readyRead.connect(lambda s=socket: self._read(s))
            socket.disconnected.connect(socket.deleteLater)
            if socket.bytesAvailable():
                self._read(socket)

    def _read(self, socket: QLocalSocket) -> None:
        data = bytes(socket.readAll())
        if b"show" in data:
            self.activated.emit()
