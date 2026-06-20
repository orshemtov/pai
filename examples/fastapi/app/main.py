import threading
import time
from typing import Protocol

from app.orders import load_order, serialize_order
from fastapi import FastAPI


class ShutdownControl(Protocol):
    def request_shutdown(self) -> None: ...


class AppHandlers:
    def __init__(self, shutdown_control: ShutdownControl | None) -> None:
        self.shutdown_control = shutdown_control

    def health(self) -> dict[str, str]:
        return {"status": "ok"}

    def get_order(self, order_id: int) -> dict[str, object]:
        order = load_order(order_id)
        return serialize_order(order)

    def trigger_thread_crash(self) -> dict[str, str]:
        payload: dict[str, object] = {
            "request_id": "demo-thread-crash",
        }
        thread = threading.Thread(target=crash_in_background, args=(payload,))
        thread.start()
        return {"status": "started"}

    def shutdown(self) -> dict[str, str]:
        if not self.shutdown_control:
            return {"status": "unavailable"}

        self.shutdown_control.request_shutdown()
        return {"status": "stopping"}


def crash_in_background(payload: dict[str, object]) -> None:
    time.sleep(0.05)
    missing = payload["required_key"]
    print(missing)


def create_app(shutdown_control: ShutdownControl | None = None) -> FastAPI:
    app = FastAPI()
    handlers = AppHandlers(shutdown_control=shutdown_control)

    app.add_api_route("/health", handlers.health, methods=["GET"])
    app.add_api_route("/orders/{order_id}", handlers.get_order, methods=["GET"])
    app.add_api_route("/debug/thread-crash", handlers.trigger_thread_crash, methods=["POST"])
    app.add_api_route("/debug/shutdown", handlers.shutdown, methods=["POST"])

    return app


app = create_app()
