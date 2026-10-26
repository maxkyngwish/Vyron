"""Local, offline account storage for VYRON.

Accounts are stored in the user's home directory. Passwords are never stored in
clear text: each one is hashed with PBKDF2-HMAC-SHA256 and a random salt.
"""
import base64
import hashlib
import json
import os
import re
import secrets
import time

STORE = os.path.join(os.path.expanduser("~"), ".vyron_accounts.json")
USERNAME_MIN = 3
USERNAME_MAX = 24
USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")
ITERATIONS = 200_000
MAX_GAMES = 20
# Names kept for the project itself. Blocked silently: the public message is
# the same as a duplicate, so the reservation is never advertised.
RESERVED = {"maxkingwish", "vyron"}


def _is_reserved(username):
    compact = re.sub(r"[^a-z0-9]", "", (username or "").lower())
    return compact in RESERVED


def game_name(path):
    """Human-friendly game name derived from an executable path."""
    base = os.path.splitext(os.path.basename(path or ""))[0]
    cleaned = base.replace("_", " ").replace("-", " ").strip()
    return cleaned or (path or "Game")


def _hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return base64.b64encode(salt).decode(), base64.b64encode(digest).decode()


class AccountStore:
    def __init__(self, path=STORE):
        self.path = path
        self.data = self._load()

    # ------------------------------------------------------------------ storage
    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("users"), dict):
                return data
        except Exception:
            pass
        return {"users": {}}

    def _save(self):
        try:
            folder = os.path.dirname(self.path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, self.path)
            return True
        except Exception:
            return False

    @staticmethod
    def _key(username):
        return (username or "").strip().lower()

    @staticmethod
    def _public(user):
        if not user:
            return None
        return {k: v for k, v in user.items() if k not in ("salt", "hash")}

    def _user(self, username):
        return self.data["users"].get(self._key(username))

    # ------------------------------------------------------------------ accounts
    def profile(self, username):
        return self._public(self._user(username))

    def create(self, username, password, display_name=""):
        username = (username or "").strip()
        if not username or not password:
            return False, "empty_fields"
        if len(username) < USERNAME_MIN:
            return False, "username_short"
        if len(username) > USERNAME_MAX:
            return False, "username_long"
        if not USERNAME_RE.match(username):
            return False, "username_chars"
        if _is_reserved(username):
            return False, "username_taken"
        if self._key(username) in self.data["users"]:
            return False, "username_taken"
        if len(password) < 6:
            return False, "password_short"
        salt, digest = _hash_password(password)
        user = {
            "username": username,
            "display": (display_name or "").strip() or username,
            "salt": salt,
            "hash": digest,
            "iterations": ITERATIONS,
            "created": int(time.time()),
            "games": [],
            "launches": 0,
            "last_played": 0,
        }
        self.data["users"][self._key(username)] = user
        if not self._save():
            self.data["users"].pop(self._key(username), None)
            return False, "save_error"
        return True, self._public(user)

    def authenticate(self, username, password):
        user = self._user(username)
        if not user:
            return False, "user_not_found"
        if not password:
            return False, "empty_fields"
        try:
            salt = base64.b64decode(user.get("salt", ""))
            expected = user.get("hash", "")
            iterations = int(user.get("iterations", ITERATIONS))
        except Exception:
            return False, "wrong_password"
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        candidate = base64.b64encode(digest).decode()
        if not secrets.compare_digest(candidate, expected):
            return False, "wrong_password"
        return True, self._public(user)

    def change_password(self, username, current, new):
        user = self._user(username)
        if not user:
            return False, "user_not_found"
        ok, _ = self.authenticate(username, current)
        if not ok:
            return False, "wrong_password"
        if not new or len(new) < 6:
            return False, "password_short"
        salt, digest = _hash_password(new)
        user["salt"] = salt
        user["hash"] = digest
        user["iterations"] = ITERATIONS
        if not self._save():
            return False, "save_error"
        return True, self._public(user)

    def delete(self, username, password):
        ok, code = self.authenticate(username, password)
        if not ok:
            return False, code
        self.data["users"].pop(self._key(username), None)
        return (True, None) if self._save() else (False, "save_error")

    # ------------------------------------------------------------------ library
    def add_game(self, username, path, name=None):
        user = self._user(username)
        if not user:
            return None
        path = os.path.abspath(path)
        games = user.setdefault("games", [])
        for game in games:
            if os.path.normcase(game.get("path", "")) == os.path.normcase(path):
                return self._public(user)
        games.insert(0, {"name": name or game_name(path), "path": path, "added": int(time.time())})
        del games[MAX_GAMES:]
        self._save()
        return self._public(user)

    def remove_game(self, username, path):
        user = self._user(username)
        if not user:
            return None
        games = user.setdefault("games", [])
        user["games"] = [
            game for game in games
            if os.path.normcase(game.get("path", "")) != os.path.normcase(os.path.abspath(path))
        ]
        self._save()
        return self._public(user)

    def record_launch(self, username, path):
        user = self._user(username)
        if not user:
            return None
        user["launches"] = int(user.get("launches", 0)) + 1
        user["last_played"] = int(time.time())
        self._save()
        return self._public(user)
