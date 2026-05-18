"""JSON-backed storage. The whole bot state fits in one file"""
import json
from pathlib import Path

FILE = Path(__file__).resolve().parent / "data.json"

data = {"blacklist": {}, "channels": {}, "notified": {}}


def load():
    if FILE.exists():
        data.update(json.loads(FILE.read_text(encoding="utf-8")))


def save():
    FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def add_blacklisted(user_id, reason, message_id):
    """Returns True if newly added"""
    key = str(user_id)
    if key in data["blacklist"]:
        return False
    data["blacklist"][key] = {"reason": reason, "message_id": message_id}
    save()
    return True


def get_reason(user_id):
    entry = data["blacklist"].get(str(user_id))
    return entry["reason"] if entry else None


def set_channel(guild_id, channel_id):
    data["channels"][str(guild_id)] = channel_id
    save()


def unset_channel(guild_id):
    data["channels"].pop(str(guild_id), None)
    save()


def get_channel(guild_id):
    return data["channels"].get(str(guild_id))


def was_notified(guild_id, user_id):
    return user_id in data["notified"].get(str(guild_id), [])


def mark_notified(guild_id, user_id):
    data["notified"].setdefault(str(guild_id), []).append(user_id)
    save()
