import threading
import time
from datetime import datetime, timezone

from models.database import get_config, record_alert_history
from models.get import monitorar


class MonitorService:
    def __init__(self):
        self._lock = threading.Lock()
        self._wake_event = threading.Event()
        self._stop_event = threading.Event()
        self._run_now_event = threading.Event()
        self._thread = None
        self._state = {
            "running": False,
            "last_run_started_at": None,
            "last_run_finished_at": None,
            "last_duration_seconds": None,
            "last_result": None,
            "last_error": None,
        }

    def start(self):
        with self._lock:
            if self._thread and self._thread.is_alive():
                return

            self._stop_event.clear()
            self._wake_event.clear()
            self._thread = threading.Thread(target=self._loop, daemon=True, name="sefaz-monitor")
            self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._wake_event.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=5)

    def reload(self):
        self._wake_event.set()

    def run_now(self):
        self._run_now_event.set()
        self._wake_event.set()

    def get_status(self):
        with self._lock:
            snapshot = dict(self._state)

        config = get_config()
        snapshot["config"] = {
            "monitor_enabled": config["monitor_enabled"],
            "telegram_enabled": config["telegram_enabled"],
            "webhook_enabled": config["webhook_enabled"],
            "check_interval_seconds": config["check_interval_seconds"],
        }
        snapshot["thread_alive"] = bool(self._thread and self._thread.is_alive())
        return snapshot

    def _loop(self):
        next_run_at = time.monotonic()

        while not self._stop_event.is_set():
            config = get_config()

            if not config["monitor_enabled"]:
                self._wake_event.wait(timeout=1)
                self._wake_event.clear()
                continue

            should_run_now = self._run_now_event.is_set()
            current_time = time.monotonic()
            if should_run_now or current_time >= next_run_at:
                self._run_now_event.clear()
                self._execute_cycle(config)
                next_run_at = time.monotonic() + config["check_interval_seconds"]
                continue

            timeout = max(0.5, min(next_run_at - current_time, 1.0))
            self._wake_event.wait(timeout=timeout)
            self._wake_event.clear()

    def _execute_cycle(self, config: dict):
        started_at = datetime.now(timezone.utc)
        self._update_state(
            running=True,
            last_run_started_at=started_at.isoformat(),
            last_error=None,
        )

        try:
            result = monitorar(config)
            for delivery in result.get("deliveries", []):
                record_alert_history(delivery)
            finished_at = datetime.now(timezone.utc)
            self._update_state(
                running=False,
                last_run_finished_at=finished_at.isoformat(),
                last_duration_seconds=round((finished_at - started_at).total_seconds(), 3),
                last_result=result,
                last_error=None,
            )
        except Exception as exc:
            finished_at = datetime.now(timezone.utc)
            self._update_state(
                running=False,
                last_run_finished_at=finished_at.isoformat(),
                last_duration_seconds=round((finished_at - started_at).total_seconds(), 3),
                last_error=str(exc),
            )

    def _update_state(self, **kwargs):
        with self._lock:
            self._state.update(kwargs)