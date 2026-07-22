# -*- coding: utf-8 -*-
"""
app.py â€” (W) Manpower Map backend

à¸§à¸´à¸˜à¸µà¸£à¸±à¸™ (à¸žà¸±à¸’à¸™à¸²/à¸—à¸”à¸ªà¸­à¸šà¹ƒà¸™à¹€à¸„à¸£à¸·à¹ˆà¸­à¸‡):
    pip install -r requirements.txt
    set FLASK_SECRET_KEY=<random string à¸¢à¸²à¸§à¹†>      (Windows: set, macOS/Linux: export)
    set COOKIE_SECURE=0                              (à¹ƒà¸ªà¹ˆà¹€à¸‰à¸žà¸²à¸°à¸•à¸­à¸™à¸—à¸”à¸ªà¸­à¸šà¸œà¹ˆà¸²à¸™ http:// à¹€à¸—à¹ˆà¸²à¸™à¸±à¹‰à¸™)
    python app.py
    à¹€à¸›à¸´à¸” http://127.0.0.1:5000/

à¸§à¸´à¸˜à¸µà¸£à¸±à¸™à¸ˆà¸£à¸´à¸‡ (production):
    - à¸•à¹‰à¸­à¸‡à¸•à¸±à¹‰à¸‡à¸„à¹ˆà¸² FLASK_SECRET_KEY à¹€à¸›à¹‡à¸™à¸„à¹ˆà¸²à¸ªà¸¸à¹ˆà¸¡à¸—à¸µà¹ˆà¸„à¸²à¸”à¹€à¸”à¸²à¹„à¸¡à¹ˆà¹„à¸”à¹‰ (à¸«à¹‰à¸²à¸¡à¹ƒà¸Šà¹‰à¸„à¹ˆà¸² default)
    - à¸•à¹‰à¸­à¸‡à¸£à¸±à¸™à¸œà¹ˆà¸²à¸™ HTTPS à¹€à¸—à¹ˆà¸²à¸™à¸±à¹‰à¸™ (à¹€à¸Šà¹ˆà¸™à¸œà¹ˆà¸²à¸™ reverse proxy à¸­à¸¢à¹ˆà¸²à¸‡ nginx + certbot)
    - à¸­à¸¢à¹ˆà¸²à¸£à¸±à¸™à¸”à¹‰à¸§à¸¢ `python app.py` à¸•à¸£à¸‡à¹† à¹ƒà¸«à¹‰à¹ƒà¸Šà¹‰ WSGI server à¹€à¸Šà¹ˆà¸™:
        gunicorn -w 4 -b 0.0.0.0:8000 app:app
    - à¸•à¹‰à¸­à¸‡à¸£à¸±à¸™ migrate_db.py à¸à¹ˆà¸­à¸™à¹ƒà¸Šà¹‰à¸‡à¸²à¸™à¸„à¸£à¸±à¹‰à¸‡à¹à¸£à¸ à¹€à¸žà¸·à¹ˆà¸­à¸ªà¸£à¹‰à¸²à¸‡à¸•à¸²à¸£à¸²à¸‡ staff / manpower_nodes

à¸à¹ˆà¸­à¸™à¸£à¸±à¸™à¸•à¹‰à¸­à¸‡à¸¡à¸µà¹„à¸Ÿà¸¥à¹Œà¹€à¸«à¸¥à¹ˆà¸²à¸™à¸µà¹‰à¸­à¸¢à¸¹à¹ˆà¹‚à¸Ÿà¸¥à¹€à¸”à¸­à¸£à¹Œà¹€à¸”à¸µà¸¢à¸§à¸à¸±à¸™:
    app.py, login.html, main.html, manpower_map.db (à¸œà¹ˆà¸²à¸™ migrate_db.py à¹à¸¥à¹‰à¸§)
"""

import os
import sys

def _safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        try:
            text = kwargs.get('sep', ' ').join(str(a) for a in args)
            end = kwargs.get('end', '\n')
            sys.stdout.buffer.write((text + end).encode('utf-8'))
        except Exception:
            try:
                # last resort: ascii-only fallback
                ascii_text = ' '.join(str(a).encode('ascii', errors='replace').decode('ascii') for a in args)
                sys.stdout.write(ascii_text + kwargs.get('end', '\n'))
            except Exception:
                pass
import re
import json 
import sqlite3
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, request, jsonify, g, send_from_directory, session, abort, make_response
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.realpath(os.path.join(BASE_DIR, "manpower_map.db"))
IMG_DIR = os.path.realpath(os.path.join(BASE_DIR, "img"))

# à¸žà¸´à¸¡à¸žà¹Œ path à¹€à¸•à¹‡à¸¡à¸‚à¸­à¸‡à¹„à¸Ÿà¸¥à¹Œ DB à¸•à¸­à¸™à¹€à¸£à¸´à¹ˆà¸¡à¹‚à¸›à¸£à¹à¸à¸£à¸¡ à¹€à¸žà¸·à¹ˆà¸­à¹ƒà¸«à¹‰à¹€à¸Šà¹‡à¸„à¸‡à¹ˆà¸²à¸¢à¹† à¸§à¹ˆà¸²
# à¹„à¸Ÿà¸¥à¹Œà¸—à¸µà¹ˆ app.py à¹ƒà¸Šà¹‰à¸ˆà¸£à¸´à¸‡ à¸•à¸£à¸‡à¸à¸±à¸šà¹„à¸Ÿà¸¥à¹Œà¸—à¸µà¹ˆà¹€à¸£à¸²à¸à¸³à¸¥à¸±à¸‡à¹€à¸›à¸´à¸”à¸”à¸¹/à¸•à¸£à¸§à¸ˆà¸ªà¸­à¸šà¸­à¸¢à¸¹à¹ˆà¸«à¸£à¸·à¸­à¹„à¸¡à¹ˆ
# (à¸ªà¸²à¹€à¸«à¸•à¸¸à¸—à¸µà¹ˆà¸žà¸šà¸šà¹ˆà¸­à¸¢à¸—à¸µà¹ˆà¸ªà¸¸à¸”à¸‚à¸­à¸‡ "à¸ªà¸¡à¸±à¸„à¸£à¹à¸¥à¹‰à¸§à¸”à¸¹à¹€à¸«à¸¡à¸·à¸­à¸™à¸ªà¸³à¹€à¸£à¹‡à¸ˆà¹à¸•à¹ˆà¹„à¸¡à¹ˆà¸¡à¸µà¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¹ƒà¸™ DB"
#  à¸„à¸·à¸­à¸¡à¸µà¹„à¸Ÿà¸¥à¹Œ manpower_map.db à¸‹à¹‰à¸³à¸à¸±à¸™à¸«à¸¥à¸²à¸¢à¸—à¸µà¹ˆà¹ƒà¸™à¹€à¸„à¸£à¸·à¹ˆà¸­à¸‡ à¹à¸¥à¹‰à¸§à¹„à¸›à¹€à¸›à¸´à¸”à¸”à¸¹à¸œà¸´à¸”à¹„à¸Ÿà¸¥à¹Œ)
def _safe_print_db_info():
    try:
        print("=" * 70)
        print(f"[DB] à¹„à¸Ÿà¸¥à¹Œà¸à¸²à¸™à¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¸—à¸µà¹ˆ app.py à¸ˆà¸°à¹ƒà¸Šà¹‰à¸‡à¸²à¸™à¸ˆà¸£à¸´à¸‡ (path à¹€à¸•à¹‡à¸¡): {DB_PATH}")
        print(f"[DB] à¹„à¸Ÿà¸¥à¹Œà¸™à¸µà¹‰à¸¡à¸µà¸­à¸¢à¸¹à¹ˆà¸ˆà¸£à¸´à¸‡à¸«à¸£à¸·à¸­à¹„à¸¡à¹ˆà¸•à¸­à¸™à¹€à¸£à¸´à¹ˆà¸¡à¹‚à¸›à¸£à¹à¸à¸£à¸¡: {os.path.exists(DB_PATH)}")
        print("=" * 70)
    except UnicodeEncodeError:
        # stdout may not support these characters on some Windows consoles (cp1252)
        try:
            out = sys.stdout.buffer
            out.write(("=" * 70 + "\n").encode("utf-8"))
            out.write((f"[DB] à¹„à¸Ÿà¸¥à¹Œà¸à¸²à¸™à¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¸—à¸µà¹ˆ app.py à¸ˆà¸°à¹ƒà¸Šà¹‰à¸‡à¸²à¸™à¸ˆà¸£à¸´à¸‡ (path à¹€à¸•à¹‡à¸¡): {DB_PATH}\n").encode("utf-8"))
            out.write((f"[DB] à¹„à¸Ÿà¸¥à¹Œà¸™à¸µà¹‰à¸¡à¸µà¸­à¸¢à¸¹à¹ˆà¸ˆà¸£à¸´à¸‡à¸«à¸£à¸·à¸­à¹„à¸¡à¹ˆà¸•à¸­à¸™à¹€à¸£à¸´à¹ˆà¸¡à¹‚à¸›à¸£à¹à¸à¸£à¸¡: {os.path.exists(DB_PATH)}\n").encode("utf-8"))
            out.write(("=" * 70 + "\n").encode("utf-8"))
        except Exception:
            # final fallback: ASCII-only
            print("[DB] PATH:", DB_PATH)
            print("[DB] EXISTS:", os.path.exists(DB_PATH))


_safe_print_db_info()

MAX_FAILED_ATTEMPTS = 5          # à¸¥à¹‡à¸­à¸à¸šà¸±à¸à¸Šà¸µà¸Šà¸±à¹ˆà¸§à¸„à¸£à¸²à¸§à¸–à¹‰à¸²à¹ƒà¸ªà¹ˆà¸£à¸«à¸±à¸ªà¸œà¸´à¸”à¹€à¸à¸´à¸™à¸ˆà¸³à¸™à¸§à¸™à¸™à¸µà¹‰
SESSION_HOURS = 8
SESSION_HOURS_REMEMBER = 24 * 30
LOGIN_RATE_LIMIT = 10            # à¸ˆà¸³à¸™à¸§à¸™à¸„à¸£à¸±à¹‰à¸‡à¸—à¸µà¹ˆà¸¢à¸­à¸¡à¹ƒà¸«à¹‰à¸¥à¸­à¸‡ login à¸•à¹ˆà¸­ IP
LOGIN_RATE_WINDOW_SECONDS = 300  # à¸•à¹ˆà¸­à¸Šà¹ˆà¸§à¸‡à¹€à¸§à¸¥à¸² 5 à¸™à¸²à¸—à¸µ
REGISTER_RATE_LIMIT = 5          # à¸ˆà¸³à¸™à¸§à¸™à¸„à¸£à¸±à¹‰à¸‡à¸—à¸µà¹ˆà¸¢à¸­à¸¡à¹ƒà¸«à¹‰à¸ªà¸¡à¸±à¸„à¸£à¸šà¸±à¸à¸Šà¸µà¸•à¹ˆà¸­ IP
REGISTER_RATE_WINDOW_SECONDS = 600  # à¸•à¹ˆà¸­à¸Šà¹ˆà¸§à¸‡à¹€à¸§à¸¥à¸² 10 à¸™à¸²à¸—à¸µ
# à¸ªà¸´à¸—à¸˜à¸´à¹Œà¹à¸à¹‰à¹„à¸‚à¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¸•à¹‰à¸­à¸‡à¸žà¸´à¸ˆà¸²à¸£à¸“à¸²à¸—à¸±à¹‰à¸‡à¸•à¸³à¹à¸«à¸™à¹ˆà¸‡à¹à¸¥à¸°à¸à¹ˆà¸²à¸¢à¸ˆà¸²à¸à¸à¸²à¸™à¸‚à¹‰à¸­à¸¡à¸¹à¸¥ à¹„à¸¡à¹ˆà¹€à¸Šà¸·à¹ˆà¸­à¸„à¹ˆà¸²
# à¹ƒà¸™ session/cookie à¹€à¸žà¸£à¸²à¸°à¸ªà¸²à¸¡à¸²à¸£à¸–à¹€à¸à¹ˆà¸² à¸«à¸£à¸·à¸­à¸–à¸¹à¸à¹à¸à¹‰à¹„à¸‚à¹„à¸”à¹‰à¸ˆà¸²à¸à¸à¸±à¹ˆà¸‡ browser
#
# à¹ƒà¸«à¹‰à¸ªà¸´à¸—à¸˜à¸´à¹Œà¹€à¸‰à¸žà¸²à¸°à¸•à¸³à¹à¸«à¸™à¹ˆà¸‡à¸—à¸µà¹ˆà¹„à¸”à¹‰à¸£à¸±à¸šà¸¡à¸­à¸šà¸«à¸¡à¸²à¸¢à¹€à¸—à¹ˆà¸²à¸™à¸±à¹‰à¸™:
# - à¸žà¸™à¸±à¸à¸‡à¸²à¸™à¸à¹ˆà¸²à¸¢ IT
# - à¸«à¸±à¸§à¸«à¸™à¹‰à¸²à¸‡à¸²à¸™
# - à¹€à¸ˆà¹‰à¸²à¸«à¸™à¹‰à¸²à¸—à¸µà¹ˆà¸à¹ˆà¸²à¸¢à¸šà¸¸à¸„à¸„à¸¥
# - à¸à¹ˆà¸²à¸¢ ES
# - à¸«à¸±à¸§à¸«à¸™à¹‰à¸²à¸à¹ˆà¸²à¸¢ IT
#
# à¹€à¸à¹‡à¸šà¸•à¸³à¹à¸«à¸™à¹ˆà¸‡à¹à¸¥à¸°à¸à¹ˆà¸²à¸¢à¹à¸¢à¸à¸à¸±à¸™ à¸ˆà¸¶à¸‡à¸•à¸£à¸§à¸ˆà¹€à¸›à¹‡à¸™à¸„à¸¹à¹ˆà¹€à¸žà¸·à¹ˆà¸­à¹„à¸¡à¹ˆà¹ƒà¸«à¹‰ "à¸žà¸™à¸±à¸à¸‡à¸²à¸™" à¸‚à¸­à¸‡à¸à¹ˆà¸²à¸¢à¸­à¸·à¹ˆà¸™
# à¹„à¸”à¹‰à¸ªà¸´à¸—à¸˜à¸´à¹Œà¹„à¸›à¸”à¹‰à¸§à¸¢à¹‚à¸”à¸¢à¹„à¸¡à¹ˆà¹„à¸”à¹‰à¸•à¸±à¹‰à¸‡à¹ƒà¸ˆ
IT_DEPARTMENT = "à¸à¹ˆà¸²à¸¢ IT"
HR_DEPARTMENT = "à¸à¹ˆà¸²à¸¢à¸—à¸£à¸±à¸žà¸¢à¸²à¸à¸£à¸šà¸¸à¸„à¸„à¸¥"
ES_DEPARTMENT = "à¸à¹ˆà¸²à¸¢ ES"
EDITABLE_ROLES = ("à¸«à¸±à¸§à¸«à¸™à¹‰à¸²à¸‡à¸²à¸™", "à¹€à¸ˆà¹‰à¸²à¸«à¸™à¹‰à¸²à¸—à¸µà¹ˆà¸à¹ˆà¸²à¸¢à¸šà¸¸à¸„à¸„à¸¥", "à¸à¹ˆà¸²à¸¢ ES", "à¸«à¸±à¸§à¸«à¸™à¹‰à¸²à¸à¹ˆà¸²à¸¢ IT")
EDITABLE_DEPARTMENTS = (IT_DEPARTMENT, HR_DEPARTMENT, ES_DEPARTMENT)
EDITABLE_ROLE_DEPARTMENT_PAIRS = frozenset({
    ("à¸žà¸™à¸±à¸à¸‡à¸²à¸™", IT_DEPARTMENT),
    # à¸£à¸°à¸šà¸šà¹€à¸”à¸´à¸¡à¸šà¸±à¸™à¸—à¸¶à¸à¹€à¸ˆà¹‰à¸²à¸«à¸™à¹‰à¸²à¸—à¸µà¹ˆà¸à¹ˆà¸²à¸¢à¸šà¸¸à¸„à¸„à¸¥à¹à¸¥à¸°à¸à¹ˆà¸²à¸¢ ES à¹€à¸›à¹‡à¸™ role "à¸žà¸™à¸±à¸à¸‡à¸²à¸™"
    # à¸£à¹ˆà¸§à¸¡à¸à¸±à¸šà¸Šà¸·à¹ˆà¸­à¸à¹ˆà¸²à¸¢ à¸ˆà¸¶à¸‡à¸£à¸­à¸‡à¸£à¸±à¸šà¸£à¸¹à¸›à¹à¸šà¸šà¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¸™à¸µà¹‰à¸”à¹‰à¸§à¸¢
    ("à¸žà¸™à¸±à¸à¸‡à¸²à¸™", HR_DEPARTMENT),
    ("à¸žà¸™à¸±à¸à¸‡à¸²à¸™", ES_DEPARTMENT),
    ("à¹€à¸ˆà¹‰à¸²à¸«à¸™à¹‰à¸²à¸—à¸µà¹ˆà¸à¹ˆà¸²à¸¢à¸šà¸¸à¸„à¸„à¸¥", HR_DEPARTMENT),
    ("à¸à¹ˆà¸²à¸¢ ES", ES_DEPARTMENT),
    ("à¸«à¸±à¸§à¸«à¸™à¹‰à¸²à¸à¹ˆà¸²à¸¢ IT", IT_DEPARTMENT),
})
MIN_PASSWORD_LENGTH = 8


def can_edit_manpower(user):
    """Return whether a database user may edit manpower data.

    Permissions are deliberately allow-listed.  A department on its own never
    grants edit access: the user's job role must be one of the assigned roles.
    """
    if not user:
        return False
    role = user.get("role")
    department = user.get("dept_name")

    # à¸«à¸±à¸§à¸«à¸™à¹‰à¸²à¸‡à¸²à¸™à¹„à¸”à¹‰à¸£à¸±à¸šà¸ªà¸´à¸—à¸˜à¸´à¹Œà¸•à¸²à¸¡à¸•à¸³à¹à¸«à¸™à¹ˆà¸‡ à¹‚à¸”à¸¢à¹„à¸¡à¹ˆà¸ˆà¸³à¸à¸±à¸”à¸à¹ˆà¸²à¸¢
    if role == "à¸«à¸±à¸§à¸«à¸™à¹‰à¸²à¸‡à¸²à¸™":
        return True

    return (role, department) in EDITABLE_ROLE_DEPARTMENT_PAIRS

# â”€â”€ à¸•à¹‰à¸­à¸‡à¸•à¸±à¹‰à¸‡à¸„à¹ˆà¸²à¸ˆà¸£à¸´à¸‡à¸œà¹ˆà¸²à¸™ environment variable à¹€à¸ªà¸¡à¸­à¹ƒà¸™ production â”€â”€
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
if not SECRET_KEY:
    # à¹‚à¸«à¸¡à¸”à¸žà¸±à¸’à¸™à¸²/à¹€à¸”à¹‚à¸¡à¹€à¸—à¹ˆà¸²à¸™à¸±à¹‰à¸™: à¸ªà¸¸à¹ˆà¸¡à¸„à¸µà¸¢à¹Œà¹ƒà¸«à¸¡à¹ˆà¸—à¸¸à¸à¸„à¸£à¸±à¹‰à¸‡à¸—à¸µà¹ˆà¸£à¸µà¸ªà¸•à¸²à¸£à¹Œà¸— (à¸œà¸¹à¹‰à¹ƒà¸Šà¹‰à¸ˆà¸°à¸«à¸¥à¸¸à¸” session à¸—à¸¸à¸à¸„à¸£à¸±à¹‰à¸‡à¸—à¸µà¹ˆà¸£à¸µà¸ªà¸•à¸²à¸£à¹Œà¸—)
    # à¸«à¹‰à¸²à¸¡à¸›à¸¥à¹ˆà¸­à¸¢à¹à¸šà¸šà¸™à¸µà¹‰à¹„à¸›à¹ƒà¸Šà¹‰à¸‡à¸²à¸™à¸ˆà¸£à¸´à¸‡ â€” à¹ƒà¸«à¹‰à¸•à¸±à¹‰à¸‡ FLASK_SECRET_KEY à¹€à¸›à¹‡à¸™à¸„à¹ˆà¸²à¸„à¸‡à¸—à¸µà¹ˆà¸—à¸µà¹ˆà¸ªà¸¸à¹ˆà¸¡à¹„à¸§à¹‰à¸¥à¹ˆà¸§à¸‡à¸«à¸™à¹‰à¸²
    _safe_print("[à¸„à¸³à¹€à¸•à¸·à¸­à¸™] à¹„à¸¡à¹ˆà¸žà¸š FLASK_SECRET_KEY à¹ƒà¸™ environment â€” à¹ƒà¸Šà¹‰à¸„à¸µà¸¢à¹Œà¸ªà¸¸à¹ˆà¸¡à¸Šà¸±à¹ˆà¸§à¸„à¸£à¸²à¸§ (à¸«à¹‰à¸²à¸¡à¹ƒà¸Šà¹‰à¹ƒà¸™ production)")
    SECRET_KEY = secrets.token_hex(32)

COOKIE_SECURE_ENV = os.environ.get("COOKIE_SECURE")
if COOKIE_SECURE_ENV is None:
    # à¸–à¹‰à¸²à¹„à¸¡à¹ˆà¹„à¸”à¹‰à¸•à¸±à¹‰à¸‡à¸„à¹ˆà¸²à¸•à¸±à¸§à¹à¸›à¸£ COOKIE_SECURE à¹„à¸§à¹‰ à¹à¸¥à¸°à¸à¸³à¸¥à¸±à¸‡à¸£à¸±à¸™à¹ƒà¸™à¹‚à¸«à¸¡à¸”à¸—à¸”à¸ªà¸­à¸š/à¸žà¸±à¸’à¸™à¸²
    # à¸ˆà¸°à¹ƒà¸Šà¹‰ session cookie à¹à¸šà¸š non-secure à¹€à¸žà¸·à¹ˆà¸­à¹ƒà¸«à¹‰à¹à¸­à¸›à¸—à¸³à¸‡à¸²à¸™à¸œà¹ˆà¸²à¸™ HTTP à¸šà¸™ localhost à¹„à¸”à¹‰
    COOKIE_SECURE = False
    _safe_print("[INFO] COOKIE_SECURE à¹„à¸¡à¹ˆà¹„à¸”à¹‰à¸•à¸±à¹‰à¸‡à¸„à¹ˆà¸²à¹„à¸§à¹‰ â€” à¹ƒà¸Šà¹‰ session cookie à¹à¸šà¸š non-secure à¸ªà¸³à¸«à¸£à¸±à¸šà¸à¸²à¸£à¸žà¸±à¸’à¸™à¸² HTTP à¸—à¹‰à¸­à¸‡à¸–à¸´à¹ˆà¸™")
else:
    COOKIE_SECURE = COOKIE_SECURE_ENV != "0"

app = Flask(__name__)
app.config.update(
    SECRET_KEY=SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,        # à¸à¸±à¸™ JavaScript à¸­à¹ˆà¸²à¸™ cookie (à¸à¸±à¸™ XSS à¸‚à¹‚à¸¡à¸¢ session)
    SESSION_COOKIE_SAMESITE="Lax",       # à¸à¸±à¸™ CSRF à¸‚à¹‰à¸²à¸¡à¹€à¸§à¹‡à¸šà¹„à¸‹à¸•à¹Œà¹€à¸šà¸·à¹‰à¸­à¸‡à¸•à¹‰à¸™
    SESSION_COOKIE_SECURE=COOKIE_SECURE, # à¸ªà¹ˆà¸‡ cookie à¹€à¸‰à¸žà¸²à¸°à¸œà¹ˆà¸²à¸™ HTTPS (à¸›à¸´à¸”à¹„à¸”à¹‰à¹€à¸‰à¸žà¸²à¸°à¸•à¸­à¸™ dev à¸œà¹ˆà¸²à¸™ http)
    PERMANENT_SESSION_LIFETIME=timedelta(hours=SESSION_HOURS),
    JSON_SORT_KEYS=False,
)

# static_folder=None à¹‚à¸”à¸¢à¸•à¸±à¹‰à¸‡à¹ƒà¸ˆ: à¸–à¹‰à¸²à¹€à¸›à¸´à¸”à¹„à¸§à¹‰à¸žà¸£à¹‰à¸­à¸¡ static_folder=BASE_DIR à¸ˆà¸°à¸—à¸³à¹ƒà¸«à¹‰à¸—à¸¸à¸à¹„à¸Ÿà¸¥à¹Œà¹ƒà¸™à¹‚à¸Ÿà¸¥à¹€à¸”à¸­à¸£à¹Œà¸™à¸µà¹‰
# (app.py, manpower_map.db à¸¯à¸¥à¸¯) à¸–à¸¹à¸à¹€à¸‚à¹‰à¸²à¸–à¸¶à¸‡à¸œà¹ˆà¸²à¸™ URL à¹„à¸”à¹‰à¹‚à¸”à¸¢à¸•à¸£à¸‡ à¹€à¸£à¸²à¸ˆà¸¶à¸‡à¹€à¸›à¸´à¸”à¹€à¸‰à¸žà¸²à¸°à¹„à¸Ÿà¸¥à¹Œà¸—à¸µà¹ˆà¸•à¸±à¹‰à¸‡à¹ƒà¸ˆà¸œà¹ˆà¸²à¸™ route à¸”à¹‰à¸²à¸™à¸¥à¹ˆà¸²à¸‡


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def log_attempt(db, emp_id, success):
    db.execute(
        "INSERT INTO login_logs (emp_id, success, ip_address, user_agent) VALUES (?, ?, ?, ?)",
        (emp_id, 1 if success else 0, request.remote_addr, request.headers.get("User-Agent", "")[:255]),
    )
    db.commit()


# ---------------------------------------------------------------------------
# à¸›à¹‰à¸­à¸‡à¸à¸±à¸™à¸à¸²à¸£à¸¢à¸´à¸‡à¸¥à¸­à¸‡ login à¸–à¸µà¹ˆà¹† (brute force) à¹à¸šà¸šà¸‡à¹ˆà¸²à¸¢ à¹† à¸•à¹ˆà¸­ IP â€” à¹€à¸ªà¸£à¸´à¸¡à¸ˆà¸²à¸à¸•à¸±à¸§à¸¥à¹‡à¸­à¸à¸šà¸±à¸à¸Šà¸µà¹ƒà¸™ DB
# à¸«à¸¡à¸²à¸¢à¹€à¸«à¸•à¸¸: à¸–à¹‰à¸² deploy à¸«à¸¥à¸²à¸¢ process/à¸«à¸¥à¸²à¸¢à¹€à¸„à¸£à¸·à¹ˆà¸­à¸‡ à¹ƒà¸«à¹‰à¹€à¸›à¸¥à¸µà¹ˆà¸¢à¸™à¹„à¸›à¹ƒà¸Šà¹‰ Redis à¹à¸—à¸™ dict à¹ƒà¸™à¸«à¸™à¹ˆà¸§à¸¢à¸„à¸§à¸²à¸¡à¸ˆà¸³à¸™à¸µà¹‰
# ---------------------------------------------------------------------------
_login_attempts_by_ip = defaultdict(deque)
_register_attempts_by_ip = defaultdict(deque)


def _rate_limited(bucket, ip, limit, window_seconds):
    now = time.time()
    dq = bucket[ip]
    while dq and now - dq[0] > window_seconds:
        dq.popleft()
    if len(dq) >= limit:
        return True
    dq.append(now)
    return False


def rate_limited(ip):
    return _rate_limited(_login_attempts_by_ip, ip, LOGIN_RATE_LIMIT, LOGIN_RATE_WINDOW_SECONDS)


def register_rate_limited(ip):
    return _rate_limited(_register_attempts_by_ip, ip, REGISTER_RATE_LIMIT, REGISTER_RATE_WINDOW_SECONDS)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def create_session(db, emp_id, role, full_name, remember):
    token = secrets.token_hex(32)
    hours = SESSION_HOURS_REMEMBER if remember else SESSION_HOURS
    expires = datetime.utcnow() + timedelta(hours=hours)
    db.execute(
        "INSERT INTO sessions (session_token, emp_id, expires_at) VALUES (?, ?, ?)",
        (token, emp_id, expires.isoformat()),
    )
    db.commit()

    session.clear()
    session.permanent = True
    app.permanent_session_lifetime = timedelta(hours=hours)
    session["emp_id"] = emp_id
    session["token"] = token
    session["role"] = role
    session["name"] = full_name


def destroy_session(db):
    token = session.get("token")
    if token:
        db.execute("DELETE FROM sessions WHERE session_token = ?", (token,))
        db.commit()
    session.clear()


def current_user():
    """à¸„à¸·à¸™à¸„à¹ˆà¸² dict à¸œà¸¹à¹‰à¹ƒà¸Šà¹‰à¸›à¸±à¸ˆà¸ˆà¸¸à¸šà¸±à¸™à¸–à¹‰à¸² session à¸¢à¸±à¸‡à¹ƒà¸Šà¹‰à¹„à¸”à¹‰à¸ˆà¸£à¸´à¸‡ (à¸•à¸£à¸§à¸ˆà¸à¸±à¸šà¸•à¸²à¸£à¸²à¸‡ sessions à¸—à¸¸à¸à¸„à¸£à¸±à¹‰à¸‡
    à¹€à¸žà¸·à¹ˆà¸­à¹ƒà¸«à¹‰ revoke/à¸«à¸¡à¸”à¸­à¸²à¸¢à¸¸à¹„à¸”à¹‰à¸ˆà¸£à¸´à¸‡à¸à¸±à¹ˆà¸‡ server à¹„à¸¡à¹ˆà¹ƒà¸Šà¹ˆà¹€à¸Šà¸·à¹ˆà¸­ cookie à¹€à¸žà¸µà¸¢à¸‡à¸­à¸¢à¹ˆà¸²à¸‡à¹€à¸”à¸µà¸¢à¸§), à¸„à¸·à¸™ None à¸–à¹‰à¸²à¹„à¸¡à¹ˆà¹ƒà¸Šà¹ˆ
    """
    emp_id = session.get("emp_id")
    token = session.get("token")
    if not emp_id or not token:
        return None

    db = get_db()
    row = db.execute(
        """SELECT s.emp_id, s.expires_at, e.full_name, e.role, e.dept_id,
                  d.dept_name
           FROM sessions s
           JOIN employees e ON e.emp_id = s.emp_id
           LEFT JOIN departments d ON d.dept_id = e.dept_id
           WHERE s.session_token = ? AND s.emp_id = ?""",
        (token, emp_id),
    ).fetchone()
    if row is None:
        session.clear()
        return None

    if datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
        db.execute("DELETE FROM sessions WHERE session_token = ?", (token,))
        db.commit()
        session.clear()
        return None

    # à¸­à¹ˆà¸²à¸™ role/department à¹ƒà¸«à¸¡à¹ˆà¸ˆà¸²à¸ DB à¸—à¸¸à¸ request à¹€à¸žà¸·à¹ˆà¸­à¹ƒà¸«à¹‰à¸à¸²à¸£à¹€à¸›à¸¥à¸µà¹ˆà¸¢à¸™à¸ªà¸´à¸—à¸˜à¸´à¹Œà¸¡à¸µà¸œà¸¥à¸—à¸±à¸™à¸—à¸µ
    return {
        "emp_id": emp_id,
        "role": row["role"],
        "name": row["full_name"],
        "dept_id": row["dept_id"],
        "dept_name": row["dept_name"],
    }


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if user is None:
            return jsonify(success=False, message="à¸à¸£à¸¸à¸“à¸²à¹€à¸‚à¹‰à¸²à¸ªà¸¹à¹ˆà¸£à¸°à¸šà¸šà¸à¹ˆà¸­à¸™à¹ƒà¸Šà¹‰à¸‡à¸²à¸™"), 401
        g.current_user = user
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = getattr(g, "current_user", None) or current_user()
            if user is None:
                return jsonify(success=False, message="à¸à¸£à¸¸à¸“à¸²à¹€à¸‚à¹‰à¸²à¸ªà¸¹à¹ˆà¸£à¸°à¸šà¸šà¸à¹ˆà¸­à¸™à¹ƒà¸Šà¹‰à¸‡à¸²à¸™"), 401
            if user["role"] not in roles:
                return jsonify(success=False, message="à¸„à¸¸à¸“à¹„à¸¡à¹ˆà¸¡à¸µà¸ªà¸´à¸—à¸˜à¸´à¹Œà¸—à¸³à¸£à¸²à¸¢à¸à¸²à¸£à¸™à¸µà¹‰"), 403
            g.current_user = user
            return view(*args, **kwargs)
        return wrapped
    return decorator


def edit_permission_required(view):
    """à¸­à¸™à¸¸à¸à¸²à¸•à¹ƒà¸«à¹‰à¹à¸à¹‰à¹„à¸‚à¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¹€à¸‰à¸žà¸²à¸°à¸•à¸³à¹à¸«à¸™à¹ˆà¸‡à¸—à¸µà¹ˆà¹„à¸”à¹‰à¸£à¸±à¸šà¸ªà¸´à¸—à¸˜à¸´à¹Œà¹€à¸—à¹ˆà¸²à¸™à¸±à¹‰à¸™."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = getattr(g, "current_user", None) or current_user()
        if user is None:
            return jsonify(success=False, message="à¸à¸£à¸¸à¸“à¸²à¹€à¸‚à¹‰à¸²à¸ªà¸¹à¹ˆà¸£à¸°à¸šà¸šà¸à¹ˆà¸­à¸™à¹ƒà¸Šà¹‰à¸‡à¸²à¸™"), 401
        if not can_edit_manpower(user):
            return jsonify(
                success=False,
                message="à¸„à¸¸à¸“à¹„à¸¡à¹ˆà¸¡à¸µà¸ªà¸´à¸—à¸˜à¸´à¹Œà¹à¸à¹‰à¹„à¸‚à¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¸žà¸™à¸±à¸à¸‡à¸²à¸™à¸ªà¸³à¸«à¸£à¸±à¸šà¸•à¸³à¹à¸«à¸™à¹ˆà¸‡à¸‚à¸­à¸‡à¸„à¸¸à¸“",
            ), 403
        g.current_user = user
        return view(*args, **kwargs)
    return wrapped


def require_ajax(view):
    """à¹€à¸Šà¹‡à¸„ header à¹à¸šà¸šà¸‡à¹ˆà¸²à¸¢à¹† à¹€à¸žà¸·à¹ˆà¸­à¸¥à¸”à¸„à¸§à¸²à¸¡à¹€à¸ªà¸µà¹ˆà¸¢à¸‡ CSRF à¸ªà¸³à¸«à¸£à¸±à¸š endpoint à¸—à¸µà¹ˆà¹à¸à¹‰à¹„à¸‚à¸‚à¹‰à¸­à¸¡à¸¹à¸¥
    (à¹ƒà¸Šà¹‰à¸£à¹ˆà¸§à¸¡à¸à¸±à¸š SameSite=Lax cookie à¹à¸¥à¸° Content-Type: application/json à¸—à¸µà¹ˆà¸šà¸±à¸‡à¸„à¸±à¸š CORS preflight à¸­à¸¢à¸¹à¹ˆà¹à¸¥à¹‰à¸§)
    """
    @wraps(view)
    def wrapped(*args, **kwargs):
        if request.headers.get("X-Requested-With") != "XMLHttpRequest":
            return jsonify(success=False, message="à¸„à¸³à¸‚à¸­à¹„à¸¡à¹ˆà¸–à¸¹à¸à¸•à¹‰à¸­à¸‡"), 403
        return view(*args, **kwargs)
    return wrapped


# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------

EMP_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,32}$")
# Newcomer is recorded together with the shift they belong to.  Keeping this
# in the existing shift column avoids requiring a database migration.
ALLOWED_SHIFTS = ("White", "Yellow", "Day", "Newcomer", "Newcomer-White", "Newcomer-Yellow", "")
ALLOWED_NODE_TYPES = ("staff", "object")
# à¸›à¸£à¸°à¹€à¸ à¸—à¸à¸²à¸£à¸‚à¸²à¸”à¸‡à¸²à¸™/à¸¥à¸² à¸•à¹‰à¸­à¸‡à¸•à¸£à¸‡à¸à¸±à¸š CHECK constraint à¹ƒà¸™à¸•à¸²à¸£à¸²à¸‡ attendance (migrate_attendance.py) à¹€à¸›à¹Šà¸° à¹†
ALLOWED_ATTENDANCE_TYPES = ("à¸‚à¸²à¸”à¸‡à¸²à¸™", "à¸¥à¸²à¸›à¹ˆà¸§à¸¢", "à¸¥à¸²à¸à¸´à¸ˆ", "à¸¥à¸²à¸žà¸±à¸à¸£à¹‰à¸­à¸™", "à¸¡à¸²à¸ªà¸²à¸¢", "à¸­à¸·à¹ˆà¸™à¹†")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# à¸£à¸²à¸¢à¸Šà¸·à¹ˆà¸­ Process à¸•à¹‰à¸­à¸‡à¸•à¸£à¸‡à¸à¸±à¸šà¸›à¸¸à¹ˆà¸¡à¸à¸£à¸­à¸‡à¹ƒà¸™ main.html (#processSelector) à¹€à¸›à¹Šà¸° à¹† à¹€à¸žà¸·à¹ˆà¸­à¹ƒà¸«à¹‰à¸žà¸™à¸±à¸à¸‡à¸²à¸™à¸—à¸µà¹ˆà¸ªà¸¡à¸±à¸„à¸£
# à¸œà¹ˆà¸²à¸™à¸«à¸™à¹‰à¸²à¸™à¸µà¹‰à¸–à¸¹à¸à¸ˆà¸±à¸”à¸à¸¥à¸¸à¹ˆà¸¡/à¸à¸£à¸­à¸‡à¸–à¸¹à¸à¸•à¹‰à¸­à¸‡à¸—à¸±à¸™à¸—à¸µà¹ƒà¸™à¸«à¸™à¹‰à¸²à¸£à¸²à¸¢à¸Šà¸·à¹ˆà¸­à¸žà¸™à¸±à¸à¸‡à¸²à¸™à¹à¸¥à¸°à¹à¸œà¸™à¸œà¸±à¸‡à¹‚à¸£à¸‡à¸‡à¸²à¸™
PROCESS_NAMES = (
    "CAB3 and Fr. Floor",
    "Rr. Floor",
    "Side Menber",
    "Deck",
    "Slat",
    "Shell3",
    "Shell3 Roller Hem",
    "Logistics",
    "Inspection",
)


def clean_text(value, max_len=255):
    if value is None:
        return ""
    text = str(value).strip()[:max_len]
    # à¸•à¸±à¸”à¸­à¸±à¸à¸‚à¸£à¸°à¸—à¸µà¹ˆà¹ƒà¸Šà¹‰à¸à¸±à¸‡ HTML/script à¸­à¸­à¸à¸•à¸±à¹‰à¸‡à¹à¸•à¹ˆà¸à¸±à¹ˆà¸‡ server (defense-in-depth, front-end escape à¸”à¹‰à¸§à¸¢à¹à¸¥à¹‰à¸§)
    text = re.sub(r"[<>]", "", text)
    return text


# ---------------------------------------------------------------------------
# Page routes â€” à¹€à¸›à¸´à¸”à¹€à¸‰à¸žà¸²à¸°à¹„à¸Ÿà¸¥à¹Œà¸—à¸µà¹ˆà¸•à¸±à¹‰à¸‡à¹ƒà¸ˆà¹€à¸—à¹ˆà¸²à¸™à¸±à¹‰à¸™ à¹„à¸¡à¹ˆà¹€à¸›à¸´à¸”à¸—à¸±à¹‰à¸‡à¹‚à¸Ÿà¸¥à¹€à¸”à¸­à¸£à¹Œ
# ---------------------------------------------------------------------------

@app.after_request
def set_security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    return resp


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "login.html")


@app.route("/login.html")
def serve_login_page():
    return send_from_directory(BASE_DIR, "login.html")


@app.route("/main.html")
def serve_main_page():
    return send_from_directory(BASE_DIR, "main.html")


@app.route("/register.html")
def serve_register_page():
    return send_from_directory(BASE_DIR, "register.html")


@app.route("/attendance.html")
def serve_attendance_page():
    return send_from_directory(BASE_DIR, "attendance.html")


@app.route("/img/<path:filename>")
def serve_image(filename):
    """à¹€à¸ªà¸´à¸£à¹Œà¸Ÿà¸£à¸¹à¸›à¹à¸œà¸™à¸œà¸±à¸‡à¹‚à¸£à¸‡à¸‡à¸²à¸™/à¹‚à¸‹à¸™à¸•à¹ˆà¸²à¸‡à¹† à¹ƒà¸«à¹‰ main.html
    à¸–à¹‰à¸²à¹„à¸¡à¹ˆà¸¡à¸µà¹„à¸Ÿà¸¥à¹Œà¸ à¸²à¸žà¸ˆà¸£à¸´à¸‡ à¸ˆà¸°à¸„à¸·à¸™ SVG placeholder à¹€à¸žà¸·à¹ˆà¸­à¹ƒà¸«à¹‰à¸•à¸­à¸™à¸—à¸”à¸ªà¸­à¸šà¸¢à¸±à¸‡à¹€à¸«à¹‡à¸™à¹à¸œà¸™à¸œà¸±à¸‡à¹„à¸”à¹‰
    """
    os.makedirs(IMG_DIR, exist_ok=True)

    full_path = os.path.realpath(os.path.join(IMG_DIR, filename))
    if os.path.commonpath([IMG_DIR, full_path]) != IMG_DIR:
        abort(404)

    if os.path.isfile(full_path):
        return send_from_directory(IMG_DIR, filename)

    label = os.path.splitext(os.path.basename(filename))[0] or "layout"
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='1600' height='900' viewBox='0 0 1600 900'>
      <rect width='1600' height='900' fill='#f8fafc'/>
      <rect x='30' y='30' width='1540' height='840' rx='24' fill='#ffffff' stroke='#cbd5e1' stroke-width='3'/>
      <rect x='70' y='70' width='1460' height='120' rx='16' fill='#800000' opacity='0.08'/>
      <text x='800' y='430' text-anchor='middle' font-family='Segoe UI, Arial, sans-serif' font-size='48' font-weight='700' fill='#800000'>{label}</text>
      <text x='800' y='490' text-anchor='middle' font-family='Segoe UI, Arial, sans-serif' font-size='24' fill='#64748b'>à¸ à¸²à¸žà¹à¸œà¸™à¸œà¸±à¸‡à¸ˆà¸°à¸–à¸¹à¸à¹à¸ªà¸”à¸‡à¸—à¸µà¹ˆà¸™à¸µà¹ˆà¹€à¸¡à¸·à¹ˆà¸­à¸¡à¸µà¹„à¸Ÿà¸¥à¹Œà¸ˆà¸£à¸´à¸‡</text>
      <text x='800' y='535' text-anchor='middle' font-family='Segoe UI, Arial, sans-serif' font-size='20' fill='#94a3b8'>à¸£à¸°à¸šà¸šà¸à¸³à¸¥à¸±à¸‡à¹ƒà¸Šà¹‰ placeholder à¹à¸šà¸šà¸­à¸±à¸•à¹‚à¸™à¸¡à¸±à¸•à¸´</text>
    </svg>"""
    return make_response(svg, 200, {"Content-Type": "image/svg+xml"})


# ---------------------------------------------------------------------------
# Auth API
# ---------------------------------------------------------------------------

@app.route("/api/login", methods=["POST"])
def api_login():
    ip = request.remote_addr or "unknown"
    if rate_limited(ip):
        return jsonify(success=False, message="à¸žà¸¢à¸²à¸¢à¸²à¸¡à¹€à¸‚à¹‰à¸²à¸ªà¸¹à¹ˆà¸£à¸°à¸šà¸šà¸–à¸µà¹ˆà¹€à¸à¸´à¸™à¹„à¸› à¸à¸£à¸¸à¸“à¸²à¸£à¸­à¸ªà¸±à¸à¸„à¸£à¸¹à¹ˆà¹à¸¥à¹‰à¸§à¸¥à¸­à¸‡à¹ƒà¸«à¸¡à¹ˆ"), 429

    data = request.get_json(silent=True) or {}
    emp_id = (data.get("Emp_ID") or "").strip()
    password = data.get("password") or ""
    remember = bool(data.get("remember"))

    if not emp_id or not password:
        return jsonify(success=False, message="à¸à¸£à¸¸à¸“à¸²à¸à¸£à¸­à¸à¸£à¸«à¸±à¸ªà¸žà¸™à¸±à¸à¸‡à¸²à¸™à¹à¸¥à¸°à¸£à¸«à¸±à¸ªà¸œà¹ˆà¸²à¸™à¹ƒà¸«à¹‰à¸„à¸£à¸šà¸–à¹‰à¸§à¸™"), 400

    db = get_db()
    row = db.execute("SELECT * FROM employees WHERE emp_id = ?", (emp_id,)).fetchone()

    # à¹„à¸¡à¹ˆà¸žà¸šà¸œà¸¹à¹‰à¹ƒà¸Šà¹‰ -> à¸•à¸­à¸šà¸‚à¹‰à¸­à¸„à¸§à¸²à¸¡à¸à¸¥à¸²à¸‡ à¹† à¹€à¸žà¸·à¹ˆà¸­à¹„à¸¡à¹ˆà¹ƒà¸«à¹‰à¹€à¸”à¸²à¸£à¸«à¸±à¸ªà¸žà¸™à¸±à¸à¸‡à¸²à¸™à¹„à¸”à¹‰ (à¸›à¹‰à¸­à¸‡à¸à¸±à¸™ user enumeration)
    if row is None:
        log_attempt(db, emp_id, success=False)
        return jsonify(success=False, message="à¸£à¸«à¸±à¸ªà¸žà¸™à¸±à¸à¸‡à¸²à¸™à¸«à¸£à¸·à¸­à¸£à¸«à¸±à¸ªà¸œà¹ˆà¸²à¸™à¹„à¸¡à¹ˆà¸–à¸¹à¸à¸•à¹‰à¸­à¸‡"), 401

    if row["status"] == "locked":
        log_attempt(db, emp_id, success=False)
        return jsonify(success=False, message="à¸šà¸±à¸à¸Šà¸µà¸™à¸µà¹‰à¸–à¸¹à¸à¸¥à¹‡à¸­à¸ à¸à¸£à¸¸à¸“à¸²à¸•à¸´à¸”à¸•à¹ˆà¸­à¸à¹ˆà¸²à¸¢ IT"), 403

    if row["status"] == "inactive":
        log_attempt(db, emp_id, success=False)
        return jsonify(success=False, message="à¸šà¸±à¸à¸Šà¸µà¸™à¸µà¹‰à¸–à¸¹à¸à¸£à¸°à¸‡à¸±à¸šà¸à¸²à¸£à¹ƒà¸Šà¹‰à¸‡à¸²à¸™"), 403

    if not check_password_hash(row["password_hash"], password):
        new_failed = row["failed_attempts"] + 1
        new_status = "locked" if new_failed >= MAX_FAILED_ATTEMPTS else row["status"]
        db.execute(
            "UPDATE employees SET failed_attempts = ?, status = ? WHERE emp_id = ?",
            (new_failed, new_status, emp_id),
        )
        db.commit()
        log_attempt(db, emp_id, success=False)
        return jsonify(success=False, message="à¸£à¸«à¸±à¸ªà¸žà¸™à¸±à¸à¸‡à¸²à¸™à¸«à¸£à¸·à¸­à¸£à¸«à¸±à¸ªà¸œà¹ˆà¸²à¸™à¹„à¸¡à¹ˆà¸–à¸¹à¸à¸•à¹‰à¸­à¸‡"), 401

    # à¸¥à¹‡à¸­à¸à¸­à¸´à¸™à¸ªà¸³à¹€à¸£à¹‡à¸ˆ: à¸£à¸µà¹€à¸‹à¹‡à¸•à¸•à¸±à¸§à¸™à¸±à¸š, à¸šà¸±à¸™à¸—à¸¶à¸à¹€à¸§à¸¥à¸², à¸ªà¸£à¹‰à¸²à¸‡ session (server-side, httpOnly cookie)
    db.execute(
        "UPDATE employees SET failed_attempts = 0, last_login_at = ? WHERE emp_id = ?",
        (datetime.utcnow().isoformat(), emp_id),
    )
    db.commit()
    create_session(db, row["emp_id"], row["role"], row["full_name"], remember)
    log_attempt(db, emp_id, success=True)

    return jsonify(
        success=True,
        redirect="main.html",
        user={"empId": row["emp_id"], "name": row["full_name"], "role": row["role"]},
    )


@app.route("/api/logout", methods=["POST"])
@login_required
def api_logout():
    destroy_session(get_db())
    return jsonify(success=True)


@app.route("/api/session", methods=["GET"])
def api_session():
    """à¹ƒà¸«à¹‰ main.html à¹ƒà¸Šà¹‰à¸•à¸£à¸§à¸ˆà¸ªà¸­à¸šà¸ªà¸–à¸²à¸™à¸° login à¸à¸±à¸š server à¸ˆà¸£à¸´à¸‡ à¹à¸—à¸™à¸à¸²à¸£à¹€à¸Šà¸·à¹ˆà¸­ localStorage à¸­à¸¢à¹ˆà¸²à¸‡à¹€à¸”à¸µà¸¢à¸§"""
    user = current_user()
    if user is None:
        return jsonify(success=False), 401
    can_edit = can_edit_manpower(user)
    return jsonify(
        success=True,
        user={
            "empId": user["emp_id"],
            "name": user["name"],
            "role": user["role"],
            "department": user["dept_name"],
            "canEdit": can_edit,
        },
    )


@app.route("/api/departments", methods=["GET"])
def api_departments():
    """à¸£à¸²à¸¢à¸Šà¸·à¹ˆà¸­à¹à¸œà¸™à¸ â€” à¹ƒà¸Šà¹‰à¹à¸ªà¸”à¸‡à¹ƒà¸™ dropdown à¸•à¸­à¸™à¸ªà¸¡à¸±à¸„à¸£à¸šà¸±à¸à¸Šà¸µ (à¹„à¸¡à¹ˆà¸•à¹‰à¸­à¸‡ login à¹€à¸žà¸£à¸²à¸°à¹€à¸›à¹‡à¸™à¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¸—à¸±à¹ˆà¸§à¹„à¸› à¹„à¸¡à¹ˆà¸à¸£à¸°à¸—à¸šà¸„à¸§à¸²à¸¡à¸›à¸¥à¸­à¸”à¸ à¸±à¸¢)"""
    db = get_db()
    rows = db.execute("SELECT dept_id, dept_name FROM departments ORDER BY dept_name").fetchall()
    return jsonify(success=True, departments=[{"deptId": r["dept_id"], "deptName": r["dept_name"]} for r in rows])


@app.route("/api/processes", methods=["GET"])
def api_processes():
    """à¸£à¸²à¸¢à¸Šà¸·à¹ˆà¸­ Process à¸—à¸±à¹‰à¸‡à¸«à¸¡à¸” (à¸•à¸£à¸‡à¸à¸±à¸šà¸•à¸±à¸§à¸à¸£à¸­à¸‡à¹ƒà¸™ main.html) â€” à¹ƒà¸Šà¹‰à¹à¸ªà¸”à¸‡à¹ƒà¸™ dropdown à¸•à¸­à¸™à¸ªà¸¡à¸±à¸„à¸£à¸šà¸±à¸à¸Šà¸µ"""
    return jsonify(success=True, processes=list(PROCESS_NAMES))


@app.route("/api/register", methods=["POST"])
@require_ajax
def api_register():
    """à¸ªà¸¡à¸±à¸„à¸£à¸šà¸±à¸à¸Šà¸µà¸žà¸™à¸±à¸à¸‡à¸²à¸™à¹ƒà¸«à¸¡à¹ˆà¸”à¹‰à¸§à¸¢à¸•à¸±à¸§à¹€à¸­à¸‡ (à¸ªà¸³à¸«à¸£à¸±à¸šà¸—à¸”à¸ªà¸­à¸š/à¹ƒà¸Šà¹‰à¸‡à¸²à¸™à¸ˆà¸£à¸´à¸‡à¹€à¸šà¸·à¹‰à¸­à¸‡à¸•à¹‰à¸™)

    à¸‚à¹‰à¸­à¸„à¸§à¸£à¸£à¸°à¸§à¸±à¸‡à¸”à¹‰à¸²à¸™à¸„à¸§à¸²à¸¡à¸›à¸¥à¸­à¸”à¸ à¸±à¸¢à¸—à¸µà¹ˆà¸•à¸±à¹‰à¸‡à¹ƒà¸ˆà¹„à¸§à¹‰:
    - à¸¢à¸­à¸¡à¸£à¸±à¸šà¹€à¸‰à¸žà¸²à¸° role à¸ˆà¸²à¸à¸Ÿà¸­à¸£à¹Œà¸¡à¸ªà¸¡à¸±à¸„à¸£à¸—à¸µà¹ˆà¹€à¸›à¹‡à¸™ 'à¸žà¸™à¸±à¸à¸‡à¸²à¸™' à¸«à¸£à¸·à¸­ 'à¸«à¸±à¸§à¸«à¸™à¹‰à¸²à¸‡à¸²à¸™'
      à¹€à¸žà¸·à¹ˆà¸­à¸›à¹‰à¸­à¸‡à¸à¸±à¸™à¸à¸²à¸£à¸•à¸±à¹‰à¸‡à¸ªà¸´à¸—à¸˜à¸´à¹Œà¸ªà¸¹à¸‡à¸à¸§à¹ˆà¸²à¸—à¸µà¹ˆà¸­à¸™à¸¸à¸à¸²à¸•
    - à¸ˆà¸³à¸à¸±à¸”à¸ˆà¸³à¸™à¸§à¸™à¸„à¸£à¸±à¹‰à¸‡à¸à¸²à¸£à¸ªà¸¡à¸±à¸„à¸£à¸•à¹ˆà¸­ IP à¸à¸±à¸™à¸ªà¹à¸›à¸¡/à¸ªà¸„à¸£à¸´à¸›à¸•à¹Œà¸¢à¸´à¸‡à¸ªà¸¡à¸±à¸„à¸£à¸£à¸±à¸§ à¹†
    - à¸•à¸£à¸§à¸ˆà¸£à¸¹à¸›à¹à¸šà¸šà¸£à¸«à¸±à¸ªà¸žà¸™à¸±à¸à¸‡à¸²à¸™à¹à¸¥à¸°à¸„à¸§à¸²à¸¡à¸¢à¸²à¸§à¸£à¸«à¸±à¸ªà¸œà¹ˆà¸²à¸™à¸‚à¸±à¹‰à¸™à¸•à¹ˆà¸³à¸à¸±à¹ˆà¸‡ server à¹€à¸ªà¸¡à¸­ (à¹„à¸¡à¹ˆà¹€à¸Šà¸·à¹ˆà¸­à¸à¸±à¹ˆà¸‡ client à¸­à¸¢à¹ˆà¸²à¸‡à¹€à¸”à¸µà¸¢à¸§)
    - à¹à¸ˆà¹‰à¸‡à¸‚à¹‰à¸­à¸„à¸§à¸²à¸¡à¸à¸¥à¸²à¸‡ à¹† à¸–à¹‰à¸²à¸£à¸«à¸±à¸ªà¸žà¸™à¸±à¸à¸‡à¸²à¸™à¸‹à¹‰à¸³ (à¹„à¸¡à¹ˆà¸šà¸­à¸à¸£à¸²à¸¢à¸¥à¸°à¹€à¸­à¸µà¸¢à¸”à¹€à¸à¸´à¸™à¸ˆà¸³à¹€à¸›à¹‡à¸™)
    """
    ip = request.remote_addr or "unknown"
    if register_rate_limited(ip):
        return jsonify(success=False, message="à¸žà¸¢à¸²à¸¢à¸²à¸¡à¸ªà¸¡à¸±à¸„à¸£à¸šà¸±à¸à¸Šà¸µà¸–à¸µà¹ˆà¹€à¸à¸´à¸™à¹„à¸› à¸à¸£à¸¸à¸“à¸²à¸£à¸­à¸ªà¸±à¸à¸„à¸£à¸¹à¹ˆà¹à¸¥à¹‰à¸§à¸¥à¸­à¸‡à¹ƒà¸«à¸¡à¹ˆ"), 429

    data = request.get_json(silent=True) or {}
    emp_id = (data.get("Emp_ID") or "").strip()
    full_name = clean_text(data.get("FullName"), 100)
    password = data.get("password") or ""
    confirm_password = data.get("confirmPassword") or ""
    role_name = (data.get("Role") or "").strip() or "à¸žà¸™à¸±à¸à¸‡à¸²à¸™"
    dept_id = data.get("DeptId")
    process_name = (data.get("ProcessName") or "").strip()

    if not emp_id or not full_name or not password:
        return jsonify(success=False, message="à¸à¸£à¸¸à¸“à¸²à¸à¸£à¸­à¸à¸£à¸«à¸±à¸ªà¸žà¸™à¸±à¸à¸‡à¸²à¸™ à¸Šà¸·à¹ˆà¸­-à¸™à¸²à¸¡à¸ªà¸à¸¸à¸¥ à¹à¸¥à¸°à¸£à¸«à¸±à¸ªà¸œà¹ˆà¸²à¸™à¹ƒà¸«à¹‰à¸„à¸£à¸šà¸–à¹‰à¸§à¸™"), 400

    if not EMP_ID_RE.match(emp_id):
        return jsonify(success=False, message="à¸£à¸«à¸±à¸ªà¸žà¸™à¸±à¸à¸‡à¸²à¸™à¸•à¹‰à¸­à¸‡à¹€à¸›à¹‡à¸™à¸•à¸±à¸§à¸­à¸±à¸à¸©à¸£/à¸•à¸±à¸§à¹€à¸¥à¸‚ à¸„à¸§à¸²à¸¡à¸¢à¸²à¸§à¹„à¸¡à¹ˆà¹€à¸à¸´à¸™ 32 à¸•à¸±à¸§à¸­à¸±à¸à¸©à¸£"), 400

    if len(password) < MIN_PASSWORD_LENGTH:
        return jsonify(success=False, message=f"à¸£à¸«à¸±à¸ªà¸œà¹ˆà¸²à¸™à¸•à¹‰à¸­à¸‡à¸¡à¸µà¸„à¸§à¸²à¸¡à¸¢à¸²à¸§à¸­à¸¢à¹ˆà¸²à¸‡à¸™à¹‰à¸­à¸¢ {MIN_PASSWORD_LENGTH} à¸•à¸±à¸§à¸­à¸±à¸à¸©à¸£"), 400

    if password != confirm_password:
        return jsonify(success=False, message="à¸£à¸«à¸±à¸ªà¸œà¹ˆà¸²à¸™à¸—à¸±à¹‰à¸‡à¸ªà¸­à¸‡à¸Šà¹ˆà¸­à¸‡à¹„à¸¡à¹ˆà¸•à¸£à¸‡à¸à¸±à¸™"), 400

    if role_name not in ("à¸žà¸™à¸±à¸à¸‡à¸²à¸™", "à¸«à¸±à¸§à¸«à¸™à¹‰à¸²à¸‡à¸²à¸™"):
        return jsonify(success=False, message="à¸•à¸³à¹à¸«à¸™à¹ˆà¸‡à¸—à¸µà¹ˆà¹€à¸¥à¸·à¸­à¸à¹„à¸¡à¹ˆà¸–à¸¹à¸à¸•à¹‰à¸­à¸‡"), 400

    # Process à¹€à¸›à¹‡à¸™à¸—à¸²à¸‡à¹€à¸¥à¸·à¸­à¸ à¹à¸•à¹ˆà¸–à¹‰à¸²à¸ªà¹ˆà¸‡à¸¡à¸²à¸•à¹‰à¸­à¸‡à¸•à¸£à¸‡à¸à¸±à¸šà¸£à¸²à¸¢à¸Šà¸·à¹ˆà¸­ Process à¸—à¸µà¹ˆà¸¡à¸µà¸ˆà¸£à¸´à¸‡à¹€à¸—à¹ˆà¸²à¸™à¸±à¹‰à¸™ (à¸›à¹‰à¸­à¸‡à¸à¸±à¸™à¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¸¡à¸±à¹ˆà¸§/à¹à¸›à¸¥à¸à¸›à¸¥à¸­à¸¡)
    if process_name and process_name not in PROCESS_NAMES:
        return jsonify(success=False, message="Process à¸—à¸µà¹ˆà¹€à¸¥à¸·à¸­à¸à¹„à¸¡à¹ˆà¸–à¸¹à¸à¸•à¹‰à¸­à¸‡"), 400

    # dept_id à¹€à¸›à¹‡à¸™à¸—à¸²à¸‡à¹€à¸¥à¸·à¸­à¸ à¹à¸•à¹ˆà¸–à¹‰à¸²à¸ªà¹ˆà¸‡à¸¡à¸²à¸•à¹‰à¸­à¸‡à¹€à¸›à¹‡à¸™à¹à¸œà¸™à¸à¸—à¸µà¹ˆà¸¡à¸µà¸­à¸¢à¸¹à¹ˆà¸ˆà¸£à¸´à¸‡à¹€à¸—à¹ˆà¸²à¸™à¸±à¹‰à¸™
    clean_dept_id = None
    if dept_id not in (None, "", "null"):
        try:
            clean_dept_id = int(dept_id)
        except (TypeError, ValueError):
            return jsonify(success=False, message="à¹à¸œà¸™à¸à¸—à¸µà¹ˆà¹€à¸¥à¸·à¸­à¸à¹„à¸¡à¹ˆà¸–à¸¹à¸à¸•à¹‰à¸­à¸‡"), 400

    db = get_db()

    if clean_dept_id is not None:
        dept_row = db.execute("SELECT dept_id FROM departments WHERE dept_id = ?", (clean_dept_id,)).fetchone()
        if dept_row is None:
            return jsonify(success=False, message="à¹à¸œà¸™à¸à¸—à¸µà¹ˆà¹€à¸¥à¸·à¸­à¸à¹„à¸¡à¹ˆà¸–à¸¹à¸à¸•à¹‰à¸­à¸‡"), 400

    existing = db.execute("SELECT emp_id FROM employees WHERE emp_id = ?", (emp_id,)).fetchone()
    if existing is not None:
        return jsonify(success=False, message="à¸¡à¸µà¸£à¸«à¸±à¸ªà¸žà¸™à¸±à¸à¸‡à¸²à¸™à¸™à¸µà¹‰à¹ƒà¸™à¸£à¸°à¸šà¸šà¸­à¸¢à¸¹à¹ˆà¹à¸¥à¹‰à¸§ à¸à¸£à¸¸à¸“à¸²à¹ƒà¸Šà¹‰à¸£à¸«à¸±à¸ªà¸žà¸™à¸±à¸à¸‡à¸²à¸™à¸­à¸·à¹ˆà¸™à¸«à¸£à¸·à¸­à¹€à¸‚à¹‰à¸²à¸ªà¸¹à¹ˆà¸£à¸°à¸šà¸š"), 409

    # role à¸¢à¸­à¸¡à¸£à¸±à¸šà¹€à¸‰à¸žà¸²à¸° 'à¸žà¸™à¸±à¸à¸‡à¸²à¸™' à¸«à¸£à¸·à¸­ 'à¸«à¸±à¸§à¸«à¸™à¹‰à¸²à¸‡à¸²à¸™' à¸—à¸µà¹ˆà¹€à¸¥à¸·à¸­à¸à¹„à¸”à¹‰à¸ˆà¸²à¸à¸Ÿà¸­à¸£à¹Œà¸¡à¸ªà¸¡à¸±à¸„à¸£
    password_hash = generate_password_hash(password)
    try:
        db.execute("BEGIN")
        db.execute(
            """INSERT INTO employees (emp_id, full_name, password_hash, role, dept_id, status)
               VALUES (?, ?, ?, ?, ?, 'active')""",
            (emp_id, full_name, password_hash, role_name, clean_dept_id),
        )
        db.commit()
    except sqlite3.Error as e:
        db.rollback()
        _safe_print(f"[REGISTER][à¸œà¸´à¸”à¸žà¸¥à¸²à¸”] emp_id={emp_id} à¸¥à¸‡à¸—à¸°à¹€à¸šà¸µà¸¢à¸™à¹„à¸¡à¹ˆà¸ªà¸³à¹€à¸£à¹‡à¸ˆ: {e}")
        return jsonify(success=False, message="à¸ªà¸¡à¸±à¸„à¸£à¸šà¸±à¸à¸Šà¸µà¹„à¸¡à¹ˆà¸ªà¸³à¹€à¸£à¹‡à¸ˆ à¸à¸£à¸¸à¸“à¸²à¸¥à¸­à¸‡à¹ƒà¸«à¸¡à¹ˆà¸­à¸µà¸à¸„à¸£à¸±à¹‰à¸‡"), 500

    # à¸¢à¸·à¸™à¸¢à¸±à¸™à¸‹à¹‰à¸³à¸­à¸µà¸à¸„à¸£à¸±à¹‰à¸‡à¸«à¸¥à¸±à¸‡ commit à¸§à¹ˆà¸²à¹à¸–à¸§à¸–à¸¹à¸à¹€à¸‚à¸µà¸¢à¸™à¸¥à¸‡à¹„à¸Ÿà¸¥à¹Œ DB à¸ˆà¸£à¸´à¸‡à¹† à¸à¹ˆà¸­à¸™à¸šà¸­à¸à¸§à¹ˆà¸²à¸ªà¸³à¹€à¸£à¹‡à¸ˆ
    # (à¸à¸±à¸™à¸à¸£à¸“à¸µà¸ªà¸±à¸šà¸ªà¸™à¹„à¸Ÿà¸¥à¹Œ DB à¸„à¸™à¸¥à¸°à¹„à¸Ÿà¸¥à¹Œ à¸«à¸£à¸·à¸­ silent failure à¸­à¸·à¹ˆà¸™à¹† à¸—à¸µà¹ˆà¹„à¸¡à¹ˆ throw exception)
    check_row = db.execute("SELECT emp_id FROM employees WHERE emp_id = ?", (emp_id,)).fetchone()
    if check_row is None:
        _safe_print(f"[REGISTER][à¸œà¸´à¸”à¸žà¸¥à¸²à¸”] emp_id={emp_id} commit à¹à¸¥à¹‰à¸§à¹à¸•à¹ˆà¸«à¸²à¹à¸–à¸§à¹„à¸¡à¹ˆà¹€à¸ˆà¸­ â€” à¹€à¸Šà¹‡à¸„à¸§à¹ˆà¸²à¹„à¸Ÿà¸¥à¹Œ DB à¸–à¸¹à¸à¸•à¹‰à¸­à¸‡à¸«à¸£à¸·à¸­à¹„à¸¡à¹ˆ: {DB_PATH}")
        return jsonify(success=False, message="à¸ªà¸¡à¸±à¸„à¸£à¸šà¸±à¸à¸Šà¸µà¹„à¸¡à¹ˆà¸ªà¸³à¹€à¸£à¹‡à¸ˆ à¸à¸£à¸¸à¸“à¸²à¸¥à¸­à¸‡à¹ƒà¸«à¸¡à¹ˆà¸­à¸µà¸à¸„à¸£à¸±à¹‰à¸‡ (à¸šà¸±à¸™à¸—à¸¶à¸à¸¥à¸‡ DB à¹„à¸¡à¹ˆà¸ªà¸³à¹€à¸£à¹‡à¸ˆ)"), 500

    _safe_print(f"[REGISTER][à¸ªà¸³à¹€à¸£à¹‡à¸ˆ] emp_id={emp_id} full_name={full_name!r} à¸šà¸±à¸™à¸—à¸¶à¸à¸¥à¸‡ {DB_PATH} à¹€à¸£à¸µà¸¢à¸šà¸£à¹‰à¸­à¸¢à¹à¸¥à¹‰à¸§")
    return jsonify(success=True, message="à¸ªà¸¡à¸±à¸„à¸£à¸šà¸±à¸à¸Šà¸µà¸ªà¸³à¹€à¸£à¹‡à¸ˆ à¸à¸£à¸¸à¸“à¸²à¹€à¸‚à¹‰à¸²à¸ªà¸¹à¹ˆà¸£à¸°à¸šà¸š")


# ---------------------------------------------------------------------------
# Manpower map node API (à¸•à¸³à¹à¸«à¸™à¹ˆà¸‡à¸«à¸¡à¸¸à¸”à¸šà¸™à¸œà¸±à¸‡à¹‚à¸£à¸‡à¸‡à¸²à¸™)
# ---------------------------------------------------------------------------

@app.route("/api/get_manpower", methods=["GET"])
@login_required
def api_get_manpower():
    db = get_db()
    rows = db.execute("SELECT node_id, x, y, type, staff_id, staff_name, zone_id FROM manpower_nodes").fetchall()
    result = [
        {
            "id": r["node_id"],
            "x": r["x"],
            "y": r["y"],
            "type": r["type"],
            "staffId": r["staff_id"],
            "staffName": r["staff_name"],
            "zoneId": r["zone_id"],
        }
        for r in rows
    ]
    revision = db.execute(
        "SELECT COUNT(*) AS count, COALESCE(MAX(rowid), 0) AS last_rowid FROM manpower_nodes"
    ).fetchone()
    response = jsonify(result)
    response.headers["X-Manpower-Revision"] = f"{revision['last_rowid']}:{revision['count']}"
    return response


@app.route("/api/manpower_revision", methods=["GET"])
@login_required
def api_manpower_revision():
    """Small polling endpoint used to refresh the shared map for other users."""
    db = get_db()
    row = db.execute(
        "SELECT COUNT(*) AS count, COALESCE(MAX(rowid), 0) AS last_rowid FROM manpower_nodes"
    ).fetchone()
    return jsonify(revision=f"{row['last_rowid']}:{row['count']}")


@app.route("/api/manpower_summary", methods=["GET"])
@login_required
def api_manpower_summary():
    db = get_db()
    # A placed marker is the source of truth for the map count.  Do not filter
    # by process_name: newly added staff may not have a process yet, but their
    # marker still has to remain visible in the shared real-time total.
    placed_row = db.execute(
        "SELECT COUNT(*) AS cnt FROM manpower_nodes WHERE type = 'staff'"
    ).fetchone()
    # Total: count distinct staff who have a non-empty process_name
    total_row = db.execute(
        "SELECT COUNT(DISTINCT emp_id) AS cnt FROM staff WHERE COALESCE(process_name, '') != ''"
    ).fetchone()
    return jsonify(
        success=True,
        placed_count=int(placed_row["cnt"] if placed_row else 0),
        total_count=int(total_row["cnt"] if total_row else 0),
    )


@app.route("/api/manpower_shift_summary", methods=["GET"])
@login_required
def api_manpower_shift_summary():
    """à¸„à¸·à¸™à¸„à¹ˆà¸²à¸ˆà¸³à¸™à¸§à¸™à¸žà¸™à¸±à¸à¸‡à¸²à¸™à¸šà¸™à¹à¸œà¸™à¸—à¸µà¹ˆà¹à¸¥à¸°à¸ˆà¸³à¸™à¸§à¸™à¸žà¸™à¸±à¸à¸‡à¸²à¸™à¹ƒà¸™à¸£à¸°à¸šà¸š à¹à¸¢à¸à¸•à¸²à¸¡à¸à¸° (shift)
    Response example:
    {
      "success": true,
      "placed_by_shift": {"White": 5, "Yellow": 3, "": 2},
      "staff_by_shift": {"White": 12, "Yellow": 8, "Newcomer": 1, "": 0},
      "white_yellow_total": 20
    }
    """
    db = get_db()
    # placed nodes grouped by shift (join manpower_nodes -> staff)
    rows = db.execute(
        "SELECT COALESCE(s.shift, '') AS shift, COUNT(*) AS cnt"
        " FROM manpower_nodes m JOIN staff s ON m.staff_id = s.emp_id"
        " WHERE m.type = 'staff' AND COALESCE(s.process_name, '') != '' GROUP BY COALESCE(s.shift, '')"
    ).fetchall()
    placed_by_shift = {r["shift"]: int(r["cnt"]) for r in rows}

    # total staff in system grouped by shift (merge employees + staff similar to api_get_employee_list)
    # Count only staff entries that have a process assigned
    rows2 = db.execute(
        "SELECT COALESCE(shift, '') AS shift, COUNT(DISTINCT emp_id) AS cnt "
        "FROM staff WHERE COALESCE(process_name, '') != '' GROUP BY COALESCE(shift, '')"
    ).fetchall()
    staff_by_shift = {r["shift"]: int(r["cnt"]) for r in rows2}

    # Always expose both keys so clients can render a stable White/Yellow summary
    # while all employees remain in the same staff table.
    placed_by_shift = {
        "White": placed_by_shift.get("White", 0),
        "Yellow": placed_by_shift.get("Yellow", 0),
        **{key: value for key, value in placed_by_shift.items() if key not in ("White", "Yellow")},
    }
    staff_by_shift = {
        "White": staff_by_shift.get("White", 0),
        "Yellow": staff_by_shift.get("Yellow", 0),
        **{key: value for key, value in staff_by_shift.items() if key not in ("White", "Yellow")},
    }
    white_yellow_total = staff_by_shift["White"] + staff_by_shift["Yellow"]

    return jsonify(
        success=True,
        placed_by_shift=placed_by_shift,
        staff_by_shift=staff_by_shift,
        white_yellow_total=white_yellow_total,
    )


@app.route("/api/save_manpower", methods=["POST"])
@login_required
@edit_permission_required
def api_save_manpower():
    data = None
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        data = request.get_json(silent=True)
    else:
        # request à¸ˆà¸²à¸ sendBeacon à¸­à¸²à¸ˆà¹„à¸¡à¹ˆà¸¡à¸µ header à¹à¸šà¸š AJAX
        try:
            data = json.loads(request.get_data(as_text=True) or "null")
        except json.JSONDecodeError:
            data = None

    if not isinstance(data, list):
        return jsonify(success=False, message="à¸£à¸¹à¸›à¹à¸šà¸šà¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¹„à¸¡à¹ˆà¸–à¸¹à¸à¸•à¹‰à¸­à¸‡"), 400
    if len(data) > 5000:
        return jsonify(success=False, message="à¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¸¡à¸²à¸à¹€à¸à¸´à¸™à¹„à¸›"), 400

    cleaned = []
    placed_staff_ids = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        node_id = clean_text(item.get("id"), 64)
        node_type = item.get("type") if item.get("type") in ALLOWED_NODE_TYPES else "staff"
        try:
            x = float(item.get("x"))
            y = float(item.get("y"))
        except (TypeError, ValueError):
            continue
        if not node_id:
            continue
        staff_id = clean_text(item.get("staffId"), 32)
        if node_type == "staff" and staff_id:
            if staff_id in placed_staff_ids:
                return jsonify(
                    success=False,
                    message=f"à¸žà¸™à¸±à¸à¸‡à¸²à¸™à¸£à¸«à¸±à¸ª '{staff_id}' à¸–à¸¹à¸à¸§à¸²à¸‡à¸‹à¹‰à¸³à¹ƒà¸™à¹à¸œà¸™à¸œà¸±à¸‡à¹à¸¥à¹‰à¸§",
                ), 409
            placed_staff_ids.add(staff_id)
        cleaned.append((
            node_id, x, y, node_type,
            staff_id or None,
            clean_text(item.get("staffName"), 100) or None,
            clean_text(item.get("zoneId"), 100) or None,
            g.current_user["emp_id"],
        ))

    db = get_db()
    try:
        db.execute("BEGIN")
        db.execute("DELETE FROM manpower_nodes")
        db.executemany(
            "INSERT INTO manpower_nodes (node_id, x, y, type, staff_id, staff_name, zone_id, updated_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            cleaned,
        )
        db.commit()
    except sqlite3.Error as e:
        db.rollback()
        return jsonify(success=False, message=f"à¸šà¸±à¸™à¸—à¸¶à¸à¹„à¸¡à¹ˆà¸ªà¸³à¹€à¸£à¹‡à¸ˆ: {e}"), 500

    revision = db.execute(
        "SELECT COUNT(*) AS count, COALESCE(MAX(rowid), 0) AS last_rowid FROM manpower_nodes"
    ).fetchone()
    return jsonify(success=True, saved=len(cleaned), revision=f"{revision['last_rowid']}:{revision['count']}")


# ---------------------------------------------------------------------------
# Staff list API (à¸£à¸²à¸¢à¸Šà¸·à¹ˆà¸­à¸žà¸™à¸±à¸à¸‡à¸²à¸™)
# ---------------------------------------------------------------------------

def row_to_staff_dict(r):
    return {
        "Emp_ID": r["emp_id"],
        "TM_Name": r["tm_name"],
        "Process_Name": r["process_name"],
        "Han_TM": r["han_tm"],
        "Process_Rank_S": r["process_rank_s"],
        "Process_Rank_Q": r["process_rank_q"],
        "Process_Rank_P": r["process_rank_p"],
        "Current_Skill": r["current_skill"],
        "Shift": r["shift"],
        "StartDate": r["start_date"],
        "Remark": r["remark"],
    }


@app.route("/api/get_staff_list", methods=["GET"])
@login_required
def api_get_staff_list():
    shift = request.args.get("shift", "").strip()
    db = get_db()
    if shift and shift != "All":
        if shift not in ALLOWED_SHIFTS:
            return jsonify([])
        rows = db.execute("SELECT * FROM staff WHERE shift = ?", (shift,)).fetchall()
        return jsonify([row_to_staff_dict(r) for r in rows])
    rows = db.execute("SELECT * FROM staff").fetchall()
    return jsonify([row_to_staff_dict(r) for r in rows])


@app.route("/api/get_employee_list", methods=["GET"])
@login_required
def api_get_employee_list():
    db = get_db()
    # Merge employees + staff rows; include role when available to categorise
    rows = db.execute(
        "SELECT combined.emp_id, combined.full_name, combined.process_name, combined.shift, e.role "
        "FROM ("
        "  SELECT e.emp_id, e.full_name, s.process_name, s.shift, 1 as from_emp "
        "  FROM employees e LEFT JOIN staff s ON e.emp_id = s.emp_id "
        "  UNION ALL "
        "  SELECT s.emp_id, s.tm_name AS full_name, s.process_name, s.shift, 0 as from_emp "
        "  FROM staff s WHERE s.emp_id NOT IN (SELECT emp_id FROM employees)"
        ") AS combined LEFT JOIN employees e ON combined.emp_id = e.emp_id"
        " ORDER BY combined.full_name"
    ).fetchall()

    def category_for(row):
        # If there is a role in employees table, use it; otherwise assume line worker
        role = row["role"]
        if not role or role == "à¸žà¸™à¸±à¸à¸‡à¸²à¸™":
            return "line"
        return "officer"

    return jsonify([
        {
            "Emp_ID": r["emp_id"],
            "TM_Name": r["full_name"],
            "Process_Name": r["process_name"] or "",
            "Shift": r["shift"] or "",
            "Category": category_for(r),
        }
        for r in rows
    ])


@app.route("/api/add_staff", methods=["POST"])
@login_required
@edit_permission_required
@require_ajax
def api_add_staff():
    data = request.get_json(silent=True) or {}

    emp_id = clean_text(data.get("Emp_ID"), 32)
    tm_name = clean_text(data.get("TM_Name"), 150)

    if not emp_id or not tm_name:
        return jsonify(success=False, message="à¸à¸£à¸¸à¸“à¸²à¸à¸£à¸­à¸à¸£à¸«à¸±à¸ªà¸žà¸™à¸±à¸à¸‡à¸²à¸™à¹à¸¥à¸°à¸Šà¸·à¹ˆà¸­"), 400
    if not EMP_ID_RE.match(emp_id):
        return jsonify(success=False, message="à¸£à¸¹à¸›à¹à¸šà¸šà¸£à¸«à¸±à¸ªà¸žà¸™à¸±à¸à¸‡à¸²à¸™à¹„à¸¡à¹ˆà¸–à¸¹à¸à¸•à¹‰à¸­à¸‡"), 400

    shift = data.get("Shift") or ""
    if shift not in ALLOWED_SHIFTS:
        shift = ""

    try:
        current_skill = int(data.get("Current_Skill") or 0)
    except (TypeError, ValueError):
        current_skill = 0
    current_skill = max(0, min(100, current_skill))

    db = get_db()
    exists = db.execute("SELECT 1 FROM staff WHERE emp_id = ?", (emp_id,)).fetchone()
    if exists:
        return jsonify(success=False, message=f"à¸¡à¸µà¸£à¸«à¸±à¸ªà¸žà¸™à¸±à¸à¸‡à¸²à¸™ '{emp_id}' à¸­à¸¢à¸¹à¹ˆà¹ƒà¸™à¸£à¸²à¸¢à¸Šà¸·à¹ˆà¸­à¹à¸¥à¹‰à¸§"), 409

    db.execute(
        "INSERT INTO staff (emp_id, tm_name, process_name, han_tm, process_rank_s, process_rank_q, "
        "process_rank_p, current_skill, shift, start_date, remark, created_by) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            emp_id, tm_name,
            clean_text(data.get("Process_Name"), 100),
            clean_text(data.get("Han_TM"), 100),
            clean_text(data.get("Process_Rank_S"), 20),
            clean_text(data.get("Process_Rank_Q"), 20),
            clean_text(data.get("Process_Rank_P"), 20),
            current_skill,
            shift,
            clean_text(data.get("StartDate"), 20),
            clean_text(data.get("Remark"), 500),
            g.current_user["emp_id"],
        ),
    )
    db.commit()
    return jsonify(success=True)


@app.route("/api/delete_staff", methods=["POST"])
@login_required
@edit_permission_required
@require_ajax
def api_delete_staff():
    data = request.get_json(silent=True) or {}
    emp_id = clean_text(data.get("Emp_ID"), 32)
    if not emp_id:
        return jsonify(success=False, message="à¹„à¸¡à¹ˆà¸žà¸šà¸£à¸«à¸±à¸ªà¸žà¸™à¸±à¸à¸‡à¸²à¸™"), 400

    db = get_db()
    db.execute("BEGIN")
    try:
        # à¸¥à¸šà¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¸—à¸µà¹ˆà¹€à¸à¸µà¹ˆà¸¢à¸§à¸‚à¹‰à¸­à¸‡à¸à¸±à¸šà¸žà¸™à¸±à¸à¸‡à¸²à¸™à¸™à¸µà¹‰à¹ƒà¸«à¹‰à¸«à¸¡à¸” (staff, nodes, sessions, employees)
        # à¹€à¸žà¸´à¹ˆà¸¡à¸¥à¸šà¸•à¸²à¸£à¸²à¸‡à¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¹€à¸ªà¸£à¸´à¸¡ à¹€à¸Šà¹ˆà¸™ attendance à¹à¸¥à¸° login_logs
        staff_deleted = db.execute("DELETE FROM staff WHERE emp_id = ?", (emp_id,)).rowcount
        node_deleted = db.execute("DELETE FROM manpower_nodes WHERE staff_id = ?", (emp_id,)).rowcount
        attendance_deleted = db.execute("DELETE FROM attendance WHERE emp_id = ?", (emp_id,)).rowcount
        login_logs_deleted = db.execute("DELETE FROM login_logs WHERE emp_id = ?", (emp_id,)).rowcount
        session_deleted = db.execute("DELETE FROM sessions WHERE emp_id = ?", (emp_id,)).rowcount
        employee_deleted = db.execute("DELETE FROM employees WHERE emp_id = ?", (emp_id,)).rowcount
        db.commit()
    except sqlite3.Error as e:
        db.rollback()
        print(f"[DELETE][à¸œà¸´à¸”à¸žà¸¥à¸²à¸”] emp_id={emp_id} à¸¥à¸šà¸žà¸™à¸±à¸à¸‡à¸²à¸™à¹„à¸¡à¹ˆà¸ªà¸³à¹€à¸£à¹‡à¸ˆ: {e}")
        return jsonify(success=False, message="à¸¥à¸šà¸žà¸™à¸±à¸à¸‡à¸²à¸™à¹„à¸¡à¹ˆà¸ªà¸³à¹€à¸£à¹‡à¸ˆ à¸à¸£à¸¸à¸“à¸²à¸¥à¸­à¸‡à¹ƒà¸«à¸¡à¹ˆà¸­à¸µà¸à¸„à¸£à¸±à¹‰à¸‡"), 500

    if staff_deleted == 0 and node_deleted == 0 and attendance_deleted == 0 and login_logs_deleted == 0 and session_deleted == 0 and employee_deleted == 0:
        return jsonify(success=False, message="à¹„à¸¡à¹ˆà¸žà¸šà¸žà¸™à¸±à¸à¸‡à¸²à¸™à¸„à¸™à¸™à¸µà¹‰à¹ƒà¸™à¸£à¸°à¸šà¸š"), 404

    return jsonify(success=True, message="à¸¥à¸šà¸žà¸™à¸±à¸à¸‡à¸²à¸™à¸­à¸­à¸à¸ˆà¸²à¸à¸£à¸°à¸šà¸šà¹€à¸£à¸µà¸¢à¸šà¸£à¹‰à¸­à¸¢à¹à¸¥à¹‰à¸§")


@app.route("/api/update_staff", methods=["POST"])
@login_required
@edit_permission_required
@require_ajax
def api_update_staff():
    """à¸­à¸±à¸žà¹€à¸”à¸—à¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¸žà¸™à¸±à¸à¸‡à¸²à¸™à¸šà¸²à¸‡à¸Ÿà¸´à¸¥à¸”à¹Œ à¹€à¸Šà¹ˆà¸™ à¸Šà¸·à¹ˆà¸­, process, shift, skill, remark"""
    data = request.get_json(silent=True) or {}
    emp_id = clean_text(data.get("Emp_ID"), 32)
    if not emp_id or not EMP_ID_RE.match(emp_id):
        return jsonify(success=False, message="à¸£à¸«à¸±à¸ªà¸žà¸™à¸±à¸à¸‡à¸²à¸™à¹„à¸¡à¹ˆà¸–à¸¹à¸à¸•à¹‰à¸­à¸‡"), 400

    # à¸Ÿà¸´à¸¥à¸”à¹Œà¸—à¸µà¹ˆà¸­à¸™à¸¸à¸à¸²à¸•à¹ƒà¸«à¹‰à¹à¸à¹‰à¹„à¸‚
    tm_name = clean_text(data.get("TM_Name"), 200)
    process_name = clean_text(data.get("Process_Name"), 100)
    han_tm = clean_text(data.get("Han_TM"), 100)
    pr_s = clean_text(data.get("Process_Rank_S"), 20)
    pr_q = clean_text(data.get("Process_Rank_Q"), 20)
    pr_p = clean_text(data.get("Process_Rank_P"), 20)
    try:
        current_skill = int(data.get("Current_Skill") or 0)
    except Exception:
        return jsonify(success=False, message="Current_Skill à¸•à¹‰à¸­à¸‡à¹€à¸›à¹‡à¸™à¸•à¸±à¸§à¹€à¸¥à¸‚"), 400
    shift = clean_text(data.get("Shift"), 20)
    start_date = clean_text(data.get("StartDate"), 20)
    remark = clean_text(data.get("Remark"), 500)

    if process_name and process_name not in PROCESS_NAMES:
        return jsonify(success=False, message="Process à¹„à¸¡à¹ˆà¸–à¸¹à¸à¸•à¹‰à¸­à¸‡"), 400
    if shift and shift not in ALLOWED_SHIFTS:
        return jsonify(success=False, message="Shift à¹„à¸¡à¹ˆà¸–à¸¹à¸à¸•à¹‰à¸­à¸‡"), 400

    db = get_db()
    try:
        cur = db.execute(
            "UPDATE staff SET tm_name = ?, process_name = ?, han_tm = ?, process_rank_s = ?, process_rank_q = ?, process_rank_p = ?, current_skill = ?, shift = ?, start_date = ?, remark = ? WHERE emp_id = ?",
            (tm_name, process_name, han_tm, pr_s, pr_q, pr_p, current_skill, shift, start_date, remark, emp_id),
        )
        db.commit()
    except sqlite3.Error as e:
        db.rollback()
        print(f"[UPDATE][à¸œà¸´à¸”à¸žà¸¥à¸²à¸”] emp_id={emp_id} à¸­à¸±à¸žà¹€à¸”à¸—à¹„à¸¡à¹ˆà¸ªà¸³à¹€à¸£à¹‡à¸ˆ: {e}")
        return jsonify(success=False, message="à¸­à¸±à¸žà¹€à¸”à¸—à¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¹„à¸¡à¹ˆà¸ªà¸³à¹€à¸£à¹‡à¸ˆ à¸à¸£à¸¸à¸“à¸²à¸¥à¸­à¸‡à¹ƒà¸«à¸¡à¹ˆ"), 500

    if cur.rowcount == 0:
        return jsonify(success=False, message="à¹„à¸¡à¹ˆà¸žà¸šà¸žà¸™à¸±à¸à¸‡à¸²à¸™à¸—à¸µà¹ˆà¸ˆà¸°à¸­à¸±à¸žà¹€à¸”à¸—"), 404

    # à¸„à¸·à¸™à¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¸¥à¹ˆà¸²à¸ªà¸¸à¸”à¸‚à¸­à¸‡à¸žà¸™à¸±à¸à¸‡à¸²à¸™à¸—à¸µà¹ˆà¸­à¸±à¸žà¹€à¸”à¸—à¹à¸¥à¹‰à¸§
    row = db.execute("SELECT emp_id, tm_name, process_name, han_tm, process_rank_s, process_rank_q, process_rank_p, current_skill, shift, start_date, remark FROM staff WHERE emp_id = ?", (emp_id,)).fetchone()
    result = dict(row) if row else {}
    return jsonify(success=True, staff=result)


# ---------------------------------------------------------------------------
# Attendance API (à¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¸à¸²à¸£à¸‚à¸²à¸”à¸‡à¸²à¸™/à¸¥à¸²/à¸ªà¸²à¸¢ à¸‚à¸­à¸‡à¸žà¸™à¸±à¸à¸‡à¸²à¸™)
# ---------------------------------------------------------------------------

def row_to_attendance_dict(r):
    return {
        "AttId": r["att_id"],
        "Emp_ID": r["emp_id"],
        "Date": r["att_date"],
        "Type": r["att_type"],
        "Reason": r["reason"],
        "RecordedBy": r["recorded_by"],
        "CreatedAt": r["created_at"],
    }


@app.route("/api/attendance/types", methods=["GET"])
@login_required
def api_attendance_types():
    """à¸£à¸²à¸¢à¸Šà¸·à¹ˆà¸­à¸›à¸£à¸°à¹€à¸ à¸—à¸à¸²à¸£à¸‚à¸²à¸”/à¸¥à¸² à¸—à¸µà¹ˆà¹ƒà¸Šà¹‰à¸‡à¸²à¸™à¹„à¸”à¹‰ â€” à¹ƒà¸Šà¹‰à¹à¸ªà¸”à¸‡à¹ƒà¸™ dropdown à¸à¸±à¹ˆà¸‡à¸«à¸™à¹‰à¸²à¹€à¸§à¹‡à¸š"""
    return jsonify(success=True, types=list(ALLOWED_ATTENDANCE_TYPES))


@app.route("/api/attendance/list", methods=["GET"])
@login_required
def api_attendance_list():
    """à¸”à¸¶à¸‡à¸£à¸²à¸¢à¸à¸²à¸£à¸‚à¸²à¸”à¸‡à¸²à¸™ à¸à¸£à¸­à¸‡à¹„à¸”à¹‰à¸”à¹‰à¸§à¸¢ emp_id, process, shift, à¸„à¹‰à¸™à¸«à¸² à¹à¸¥à¸°/à¸«à¸£à¸·à¸­à¸Šà¹ˆà¸§à¸‡à¹€à¸”à¸·à¸­à¸™ (YYYY-MM à¸œà¹ˆà¸²à¸™ ?month=)"""
    emp_id = clean_text(request.args.get("emp_id", ""), 32)
    process_name = clean_text(request.args.get("process", ""), 100)
    shift = clean_text(request.args.get("shift", ""), 20)
    query_text = clean_text(request.args.get("q", ""), 100)
    month = clean_text(request.args.get("month", ""), 7)  # à¹€à¸Šà¹ˆà¸™ '2026-07'

    query = "SELECT a.* FROM attendance a"
    query += " LEFT JOIN staff s ON s.emp_id = a.emp_id"
    query += " LEFT JOIN employees e ON e.emp_id = a.emp_id"
    query += " WHERE 1=1"
    params = []
    if emp_id:
        query += " AND a.emp_id = ?"
        params.append(emp_id)
    if process_name:
        query += " AND lower(s.process_name) = lower(?)"
        params.append(process_name)
    if shift:
        if shift not in ALLOWED_SHIFTS:
            return jsonify(success=False, message="Shift à¹„à¸¡à¹ˆà¸–à¸¹à¸à¸•à¹‰à¸­à¸‡"), 400
        query += " AND s.shift = ?"
        params.append(shift)
    if query_text:
        query += " AND (lower(COALESCE(s.tm_name, e.full_name)) LIKE lower(?) OR lower(a.emp_id) LIKE lower(?))"
        like = f"%{query_text}%"
        params.extend([like, like])
    if month and re.match(r"^\d{4}-\d{2}$", month):
        query += " AND substr(a.att_date, 1, 7) = ?"
        params.append(month)
    query += " ORDER BY a.att_date DESC, a.att_id DESC"

    db = get_db()
    rows = db.execute(query, params).fetchall()
    return jsonify(success=True, records=[row_to_attendance_dict(r) for r in rows])


@app.route("/api/attendance/summary", methods=["GET"])
@login_required
def api_attendance_summary():
    """à¸ªà¸£à¸¸à¸›à¸ˆà¸³à¸™à¸§à¸™à¸§à¸±à¸™à¸‚à¸²à¸”/à¸¥à¸² à¹à¸¢à¸à¸•à¸²à¸¡à¸žà¸™à¸±à¸à¸‡à¸²à¸™à¹à¸¥à¸°à¸›à¸£à¸°à¹€à¸ à¸— (à¹ƒà¸Šà¹‰à¹à¸ªà¸”à¸‡à¹€à¸›à¹‡à¸™à¸•à¸²à¸£à¸²à¸‡/à¸à¸£à¸²à¸Ÿà¸ªà¸£à¸¸à¸›)
    à¸£à¸­à¸‡à¸£à¸±à¸šà¸à¸£à¸­à¸‡à¸•à¸²à¸¡ process, shift, à¸„à¹‰à¸™à¸«à¸², à¹€à¸”à¸·à¸­à¸™à¸”à¹‰à¸§à¸¢ ?process=&shift=&q=&month=YYYY-MM
    """
    process_name = clean_text(request.args.get("process", ""), 100)
    shift = clean_text(request.args.get("shift", ""), 20)
    query_text = clean_text(request.args.get("q", ""), 100)
    month = clean_text(request.args.get("month", ""), 7)

    query = """
        SELECT a.emp_id, COALESCE(s.tm_name, e.full_name) AS tm_name,
               COALESCE(s.process_name, '') AS process_name, a.att_type, COUNT(*) as cnt
        FROM attendance a
        LEFT JOIN staff s ON s.emp_id = a.emp_id
        LEFT JOIN employees e ON e.emp_id = a.emp_id
        WHERE 1=1
    """
    params = []
    if process_name:
        query += " AND lower(s.process_name) = lower(?)"
        params.append(process_name)
    if shift:
        if shift not in ALLOWED_SHIFTS:
            return jsonify(success=False, message="Shift à¹„à¸¡à¹ˆà¸–à¸¹à¸à¸•à¹‰à¸­à¸‡"), 400
        query += " AND s.shift = ?"
        params.append(shift)
    if query_text:
        query += " AND (lower(COALESCE(s.tm_name, e.full_name)) LIKE lower(?) OR lower(a.emp_id) LIKE lower(?))"
        like = f"%{query_text}%"
        params.extend([like, like])
    if month and re.match(r"^\d{4}-\d{2}$", month):
        query += " AND substr(a.att_date, 1, 7) = ?"
        params.append(month)
    query += " GROUP BY a.emp_id, a.att_type ORDER BY s.tm_name, a.att_type"

    db = get_db()
    rows = db.execute(query, params).fetchall()

    summary = {}
    for r in rows:
        emp_id = r["emp_id"]
        if emp_id not in summary:
            summary[emp_id] = {
                "empId": emp_id,
                "name": r["tm_name"] or emp_id,
                "processName": r["process_name"],
                "byType": {},
                "total": 0,
            }
        summary[emp_id]["byType"][r["att_type"]] = r["cnt"]
        summary[emp_id]["total"] += r["cnt"]

    result = sorted(summary.values(), key=lambda x: -x["total"])
    return jsonify(success=True, month=month or None, summary=result)


@app.route("/api/attendance/add", methods=["POST"])
@login_required
@edit_permission_required
@require_ajax
def api_attendance_add():
    data = request.get_json(silent=True) or {}

    emp_id = clean_text(data.get("Emp_ID"), 32)
    att_date = clean_text(data.get("Date"), 10)
    att_type = data.get("Type") or "à¸‚à¸²à¸”à¸‡à¸²à¸™"
    reason = clean_text(data.get("Reason"), 500)

    if not emp_id or not att_date:
        return jsonify(success=False, message="à¸à¸£à¸¸à¸“à¸²à¹€à¸¥à¸·à¸­à¸à¸žà¸™à¸±à¸à¸‡à¸²à¸™à¹à¸¥à¸°à¸£à¸°à¸šà¸¸à¸§à¸±à¸™à¸—à¸µà¹ˆ"), 400

    if not DATE_RE.match(att_date):
        return jsonify(success=False, message="à¸£à¸¹à¸›à¹à¸šà¸šà¸§à¸±à¸™à¸—à¸µà¹ˆà¹„à¸¡à¹ˆà¸–à¸¹à¸à¸•à¹‰à¸­à¸‡ (à¸•à¹‰à¸­à¸‡à¹€à¸›à¹‡à¸™ YYYY-MM-DD)"), 400

    if att_type not in ALLOWED_ATTENDANCE_TYPES:
        return jsonify(success=False, message="à¸›à¸£à¸°à¹€à¸ à¸—à¸à¸²à¸£à¸‚à¸²à¸”/à¸¥à¸²à¹„à¸¡à¹ˆà¸–à¸¹à¸à¸•à¹‰à¸­à¸‡"), 400

    db = get_db()
    staff_row = db.execute(
        "SELECT emp_id FROM employees WHERE emp_id = ? UNION SELECT emp_id FROM staff WHERE emp_id = ?",
        (emp_id, emp_id),
    ).fetchone()
    if staff_row is None:
        return jsonify(success=False, message=f"à¹„à¸¡à¹ˆà¸žà¸šà¸£à¸«à¸±à¸ªà¸žà¸™à¸±à¸à¸‡à¸²à¸™ '{emp_id}' à¹ƒà¸™à¸£à¸°à¸šà¸š"), 404

    db.execute(
        "INSERT INTO attendance (emp_id, att_date, att_type, reason, recorded_by) "
        "VALUES (?, ?, ?, ?, ?)",
        (emp_id, att_date, att_type, reason or None, g.current_user["emp_id"]),
    )
    db.commit()
    return jsonify(success=True)


@app.route("/api/attendance/delete", methods=["POST"])
@login_required
@edit_permission_required
@require_ajax
def api_attendance_delete():
    data = request.get_json(silent=True) or {}
    try:
        att_id = int(data.get("AttId"))
    except (TypeError, ValueError):
        return jsonify(success=False, message="à¹„à¸¡à¹ˆà¸žà¸šà¸£à¸²à¸¢à¸à¸²à¸£à¸—à¸µà¹ˆà¸•à¹‰à¸­à¸‡à¸à¸²à¸£à¸¥à¸š"), 400

    db = get_db()
    cur = db.execute("DELETE FROM attendance WHERE att_id = ?", (att_id,))
    db.commit()

    if cur.rowcount == 0:
        return jsonify(success=False, message="à¹„à¸¡à¹ˆà¸žà¸šà¸£à¸²à¸¢à¸à¸²à¸£à¸™à¸µà¹‰"), 404
    return jsonify(success=True)


# ---------------------------------------------------------------------------
# Error handlers â€” à¹„à¸¡à¹ˆà¹‚à¸Šà¸§à¹Œ stack trace / à¸£à¸²à¸¢à¸¥à¸°à¹€à¸­à¸µà¸¢à¸”à¸ à¸²à¸¢à¹ƒà¸™à¹ƒà¸«à¹‰à¸œà¸¹à¹‰à¹ƒà¸Šà¹‰à¹€à¸«à¹‡à¸™
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return jsonify(success=False, message="à¹„à¸¡à¹ˆà¸žà¸šà¸«à¸™à¹‰à¸²à¸—à¸µà¹ˆà¸•à¹‰à¸­à¸‡à¸à¸²à¸£"), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify(success=False, message="à¹€à¸à¸´à¸”à¸‚à¹‰à¸­à¸œà¸´à¸”à¸žà¸¥à¸²à¸”à¸ à¸²à¸¢à¹ƒà¸™à¸£à¸°à¸šà¸š"), 500


    print("=" * 60)
    print(f"à¸à¸³à¸¥à¸±à¸‡à¹ƒà¸Šà¹‰à¸à¸²à¸™à¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¹„à¸Ÿà¸¥à¹Œà¸™à¸µà¹‰: {DB_PATH}")
    print(f"à¹„à¸Ÿà¸¥à¹Œà¸™à¸µà¹‰à¸¡à¸µà¸­à¸¢à¸¹à¹ˆà¸ˆà¸£à¸´à¸‡à¸«à¸£à¸·à¸­à¹„à¸¡à¹ˆ: {os.path.exists(DB_PATH)}")
    if not os.environ.get("FLASK_SECRET_KEY"):
        print("!! à¸¢à¸±à¸‡à¹„à¸¡à¹ˆà¹„à¸”à¹‰à¸•à¸±à¹‰à¸‡à¸„à¹ˆà¸² FLASK_SECRET_KEY â€” à¹‚à¸«à¸¡à¸”à¸™à¸µà¹‰à¹ƒà¸Šà¹‰à¸—à¸”à¸ªà¸­à¸šà¹€à¸—à¹ˆà¸²à¸™à¸±à¹‰à¸™ à¸«à¹‰à¸²à¸¡à¹ƒà¸Šà¹‰à¹ƒà¸™ production !!")
    print("=" * 60)
    # debug=False à¹€à¸ªà¸¡à¸­: à¸«à¹‰à¸²à¸¡à¹€à¸›à¸´à¸” debug mode à¹ƒà¸™ production (à¸ˆà¸°à¹€à¸›à¸´à¸”à¸Šà¹ˆà¸­à¸‡à¹ƒà¸«à¹‰à¸£à¸±à¸™à¹‚à¸„à¹‰à¸”à¸ˆà¸²à¸à¸ à¸²à¸¢à¸™à¸­à¸à¹„à¸”à¹‰à¸œà¹ˆà¸²à¸™ debugger)
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug_mode)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)