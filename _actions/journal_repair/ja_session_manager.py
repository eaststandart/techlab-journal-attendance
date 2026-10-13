#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  ja_session_manager.py
@about   Модуль контроля жизненного цикла сессий и статусов робота TechLab
@purpose Расчет Unix-секунд коммитов Git, управление шлагбаумом оптимизации и светофором
@author  TechLab
@version 1.0.0
"""

import os
import json
import subprocess
from datetime import datetime, timezone

STATUS_FILE = os.path.join("_data", "repair-status.json")

def get_file_commit_seconds(file_path):
    """Запрашивает у Git точное число секунд Unix последнего коммита конкретного файла расписания."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", file_path],
            capture_output=True, text=True, check=True
        )
        out = result.stdout.strip()
        if out.isdigit():
            return int(out)
    except Exception as e:
        print(f"[ОПТИМИЗАЦИЯ] Сбой запроса секунд файла расписания: {e}", flush=True)
    return 0

def get_last_robot_commit_seconds():
    """Запрашивает у Git точное число секунд Unix прошлого успешного коммита закрытия сессии роботом."""
    try:
        result = subprocess.run(
            ["git", "log", "--grep=подтверждение завершения исправления", "-1", "--format=%ct"],
            capture_output=True, text=True, check=True
        )
        out = result.stdout.strip()
        if out.isdigit():
            return int(out)
    except Exception as e:
        print(f"[ОПТИМИЗАЦИЯ] Сбой запроса секунд коммита робота: {e}", flush=True)
    return 0

def write_status(status, mode=""):
    """Сохраняет текущий статус обработки и маркер режима (Сквозная версия сессионного контура)."""
    payload = {
        "status": status,
        "mode": mode,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"[СТАТУС] {status} (mode: {mode})", flush=True)
  
