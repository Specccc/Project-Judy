from datetime import datetime


def _timestamp():
    return datetime.now().strftime("%H:%M:%S")


def info(message):
    print(f"[{_timestamp()}] [INFO] {message}")


def success(message):
    print(f"[{_timestamp()}] [SUCCESS] {message}")


def warning(message):
    print(f"[{_timestamp()}] [WARNING] {message}")


def error(message):
    print(f"[{_timestamp()}] [ERROR] {message}")
