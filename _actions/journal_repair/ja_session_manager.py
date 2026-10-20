#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  ja_session_manager.py
@about   Модуль контроля жизненного цикла сессий и статусов.
@purpose Запрос Unix-времени коммитов Git для защиты от конфликтов и запись текущих состояний в JSON-файлы.
@author  TechLab
@version 1.0.0
"""

import os
import json
import subprocess
from datetime import datetime, timezone

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

def write_status(status, mode="", teacher_login="", **kwargs):
    """Сохраняет текущий статус обработки и маркер режима (Сквозная версия сессионного контура)."""
    if not teacher_login:
        print("[КРИТИЧЕСКИЙ СБОЙ СТАТУСА] Вызов write_status произведен без указания teacher_login!", flush=True)
        return

    status_filename = f"repair-status-{teacher_login.strip()}.json"
    status_filepath = os.path.join("_data", status_filename)
    payload = {
        "status": status,
        "mode": mode,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Автоматически упаковываем любые новые входящие параметры (включая errorDetails) в JSON-файл
    if kwargs:
        payload.update(kwargs)

    with open(status_filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    
    # Выводим в лог сервера состояние ключевых маркеров сессии
    details_log = f" | errorDetails: {kwargs['errorDetails']}" if 'errorDetails' in kwargs else ""
    print(f"[СТАТУС ПРЕПОДАВАТЕЛЯ: {teacher_login}] {status} (mode: {mode}){details_log}", flush=True) 
