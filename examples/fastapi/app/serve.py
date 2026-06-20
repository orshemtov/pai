from dataclasses import dataclass

import uvicorn
from app.main import create_app

HOST = "127.0.0.1"
PORT = 8765


@dataclass
class UvicornShutdownControl:
    server: uvicorn.Server | None = None

    def request_shutdown(self) -> None:
        if self.server:
            self.server.should_exit = True


def main() -> None:
    shutdown_control = UvicornShutdownControl()
    app = create_app(shutdown_control=shutdown_control)
    config = uvicorn.Config(app, host=HOST, port=PORT)
    server = uvicorn.Server(config)
    shutdown_control.server = server

    server.run()


if __name__ == "__main__":
    main()
