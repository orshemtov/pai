from urllib.request import Request, urlopen

URL = "http://127.0.0.1:8765/debug/thread-crash"


def main() -> None:
    request = Request(URL, method="POST")
    with urlopen(request) as response:
        body = response.read().decode("utf-8")

    print(body)


if __name__ == "__main__":
    main()
