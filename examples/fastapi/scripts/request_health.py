from urllib.request import urlopen

URL = "http://127.0.0.1:8765/health"


def main() -> None:
    with urlopen(URL) as response:
        body = response.read().decode("utf-8")

    print(body)


if __name__ == "__main__":
    main()
