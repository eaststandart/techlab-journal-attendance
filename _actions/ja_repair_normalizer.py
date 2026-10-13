#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  ja_repair_normalizer.py
@about   Утилиты фильтрации строк и управления файлом статуса светофора
@purpose Извлечение чистого времени, дней недели, букв и фиксация repair-status.json
@author  TechLab
@version 1.0.0
"""

import re
import os
import json
from datetime import datetime, timezone

STATUS_FILE = os.path.join("_data", "repair-status.json")

def normalize_time(raw_time):
    """Возвращает HH:MM для допустимого времени, иначе None."""
    value = raw_time.strip().strip("\"'").strip()
    hour = minute = None

    if re.fullmatch(r"\d{3,4}", value):
        if len(value) == 3:
            hour, minute = int(value[0]), int(value[1:])
        else:
            hour, minute = int(value[:2]), int(value[2:])
    else:
        match = re.fullmatch(r"(\d{1,2})\s*[:\\/.\=–—-]\s*(\d{2})", value)
        if not match:
            match = re.fullmatch(r"(\d{1,2})\s+(\d{2})", value)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))

    if hour is None or minute is None or not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return f"{hour:02d}:{minute:02d}"

def normalize_weekday(raw_day):
    """[ОТКЛЮЧЕНО TECHLAB] Старая функция закомментирована во избежание дублирования."""
    # value = raw_day.strip().strip("\"'").strip().lower()
    # value = re.sub(r"^[\s\-–—]+|[\s\-–—]+$", "", value).rstrip(".").strip()
    # weekdays = {
    #     "понедельник": "Понедельник", "пн": "Понедельник",
    #     "вторник": "Вторник", "вт": "Вторник",
    #     "среда": "Среда", "ср": "Среда",
    #     "четверг": "Черверг", "чт": "Четверг",
    #     "пятница": "Пятница", "пт": "Пятница",
    #     "суббота": "Суббота", "сб": "Суббота",
    #     "воскресенье": "Воскресенье", "вс": "Воскресенье",
    # }
    # return weekdays.get(value)
    return None

def clean_field(value, allowed_extra=""):
    """Оставляет только русские и английские буквы, пробелы и разрешённые знаки."""
    allowed = set(
        "abcdefghijklmnopqrstuvwxyz" "ABCDEFGHIJKLMNOPQRSTUVWXYZ "
        "абвгдеёжзийклмнопрстуфхцчшщъыьэюя" "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
        + allowed_extra
    )
    cleaned = "".join(c for c in value if c in allowed)
    return " ".join(cleaned.split()).strip()

def write_status(status, mode=""):
    """Сохраняет текущий статус обработки и маркер режима."""
    payload = {
        "status": status,
        "mode": mode,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"[СТАТУС] {status} (mode: {mode})", flush=True)

