#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  ja_repair_time.py
@about   Подмодуль инспекции и форматирования синтаксиса времени групп
@purpose Контроль формата ЧЧ:ММ и автоматическое оборачивание в кавычки с обходом конфига
@author  TechLab
@version 1.0.0
"""

import re

def normalize_time_internal(raw_time):
    """Внутренний автономный парсер времени из старого ja_repair_normalizer.py."""
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

def repair_time_line(line, filename, signal_data=None):
    """Проверяет и исправляет синтаксис времени групп строго по логике оригинала с зрячим щитом."""
    stripped = line.strip()
    is_modified = False
    has_errors = False

    # Твой оригинальный рабочий код обхода конфиг-блока
    content_inside = stripped.replace('"', "").replace("'", "").strip().rstrip(":")
    if stripped.endswith(":") and re.match(r"^\d{1,2}\s*[:\\/.\=–—-]?\s*\d{2}$", content_inside):
        raw_time = content_inside
            
        clean_time = normalize_time_internal(raw_time)
        
        if clean_time is None:
            # ЗРЯЧИЙ ЩИТ ИНДУЛЬГЕНЦИИ TECHLAB ПО ТВОЕМУ СЦЕНАРИЮ
            # Если парсер вернул None из-за границ суток, принудительно собираем ЧЧ:ММ для сверки
            digits_only = "".join(c for c in raw_time if c.isdigit())
            repaired_format = f"{digits_only[:2]}:{digits_only[2:]}" if len(digits_only) in {3, 4} else ""
            
            # Проверяем реальность нового времени суток из сигнала
            signal_new_time = signal_data.get("modify_time", "") if isinstance(signal_data, dict) else ""
            is_new_time_valid = normalize_time_internal(signal_new_time) is not None

            is_being_fixed = (
                isinstance(signal_data, dict)
                and signal_data.get("command") == "modify"
                and signal_data.get("time") == repaired_format
                and is_new_time_valid
            )
            
            if is_being_fixed:
                print(f"[ИНДУЛЬГЕНЦИЯ] Брак {raw_time!r} пропущен для исправления модификатором, синтаксис сохранен.", flush=True)
                clean_time = repaired_format
            
        # Финальный вывод эталона в файл на твоих оригинальных рельсах
        if clean_time is None:
            print(f"[ОШИБКА ВРЕМЕНИ] {filename}: недопустимое значение {raw_time!r}", flush=True)
            has_errors = True
        else:
            repaired_line = f'  "{clean_time}":\n'
            if repaired_line != line:
                print(f"[ВРЕМЯ] {filename}: {stripped!r} -> {repaired_line.strip()!r}", flush=True)
                line = repaired_line
                is_modified = True

    return line, is_modified, has_errors
