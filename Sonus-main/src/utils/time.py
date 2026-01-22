import datetime


def now_iso():
    return datetime.datetime.utcnow().isoformat() + "Z"
