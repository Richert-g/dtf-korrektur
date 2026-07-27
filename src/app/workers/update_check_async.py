"""Asynchroner, nicht-blockierender Update-Check für die Oberfläche.

Bewusst OHNE eigenen Hintergrund-Thread (anders als die übrigen Worker in
diesem Ordner): ein Python-Thread mit einem blockierenden urllib-Aufruf
(siehe core.update.update_check.check_for_update) kollidiert beim schnellen
Schließen der App mit der Interpreter-Terminierung, falls die Anfrage dann
noch läuft - reproduziert als nativer Absturz (Windows: STATUS_STACK_
BUFFER_OVERRUN). QNetworkAccessManager arbeitet dagegen komplett über die
Qt-Ereignisschleife im Hauptthread (kein zweiter, beim Beenden potenziell
noch blockierter OS-Thread), daher kein solches Risiko.
"""
from __future__ import annotations

import json
import logging

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from src.core.update.update_check import (
    GITHUB_RELEASES_LATEST_URL,
    REQUEST_TIMEOUT_SECONDS,
    UpdateCheckResult,
    parse_release_payload,
)

logger = logging.getLogger(__name__)


class AsyncUpdateChecker(QObject):
    finished = Signal(object)  # UpdateCheckResult

    def __init__(
        self,
        current_version: str,
        url: str = GITHUB_RELEASES_LATEST_URL,
        timeout: float = REQUEST_TIMEOUT_SECONDS,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._current_version = current_version
        self._url = url
        self._timeout_ms = int(timeout * 1000)
        self._manager = QNetworkAccessManager(self)
        self._reply: QNetworkReply | None = None

    def start(self) -> None:
        request = QNetworkRequest(QUrl(self._url))
        request.setRawHeader(b"Accept", b"application/vnd.github+json")
        request.setRawHeader(b"User-Agent", b"DTF-Korrektur-UpdateCheck")
        self._reply = self._manager.get(request)
        self._reply.finished.connect(self._on_finished)
        QTimer.singleShot(self._timeout_ms, self._on_timeout)

    def _on_timeout(self) -> None:
        if self._reply is not None and not self._reply.isFinished():
            self._reply.abort()

    def _on_finished(self) -> None:
        reply = self._reply
        if reply is None:
            return
        self._reply = None
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                self.finished.emit(UpdateCheckResult(update_available=False, error=reply.errorString()))
                return
            payload = bytes(reply.readAll().data())
            data = json.loads(payload.decode("utf-8"))
            self.finished.emit(parse_release_payload(data, self._current_version))
        except Exception as exc:  # noqa: BLE001 - Update-Check darf die App nie stoeren
            logger.info("Update-Check-Antwort konnte nicht ausgewertet werden: %s", exc)
            self.finished.emit(UpdateCheckResult(update_available=False, error=str(exc)))
        finally:
            reply.deleteLater()
