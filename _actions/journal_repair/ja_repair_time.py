#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  ja_repair_time.py
@about   Подмодуль инспекции и форматирования синтаксиса времени групп
@purpose Преобразование к стандарту ЧЧ:ММ на одном этапе и зрячая отбраковка
@author  TechLab
@version 2.1.0
"""

import re

def normalize_time_internal(raw_time):
    """Преобразует любые кривые знаки разделителей строго к стандарту ЧЧ:ММ."""
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

    if hour is None or minute is None:
        return None
        
    return f"{hour:02d}:{minute:02d}"

def repair_time_line(line, filename, signal_data=None):
    """Штатно нормализует формат времени строк и делает зрячую отбраковку суток."""
    stripped = line.strip()
    is_modified = False
    has_errors = False

    # Ловим время по смыслу строки, игнорируя любые начальные пробелы
    content_inside = stripped.replace('"', "").replace("'", "").strip().rstrip(":")
    if stripped.endswith(":") and re.match(r"^\d{1,2}\s*[:\\/.\=–—-]?\s*\d{2}$", content_inside):
        raw_time = content_inside
        
        # ЭТАП №1: Абсолютно любое время сначала преобразуется к стандарту ЧЧ:ММ!
        clean_time = normalize_time_internal(raw_time)
        
        if clean_time is None:
            print(f"[ОШИБКА ВРЕМЕНИ] {filename}: критически битый синтаксис {raw_time!r}", flush=True)
            has_errors = True
            return line, is_modified, has_errors

        # ЭТАП №2: Отбраковка реальности суток над уже готовым стандартом ЧЧ:ММ
        hour_val = int(clean_time.split(":")[0])
        minute_val = int(clean_time.split(":")[1])
        
        if not (0 <= hour_val <= 23 and 0 <= minute_val <= 59):
            # Проверяем наличие зрячего сигнала модификации из кэша
            is_being_fixed = (
                isinstance(signal_data, dict)
                and signal_data.get("command") == "modify"
                and signal_data.get("time") == clean_time
            )
            
            if is_being_fixed:
                print(f"[ИНДУЛЬГЕНЦИЯ] Брак {clean_time!r} пропущен для последующего исправления модификатором.", flush=True)
            else:
                print(f"[ОШИБКА СУТОК] {filename}: несуществующее время суток {clean_time!r}", flush=True)
                has_errors = True
                return line, is_modified, has_errors

        # ЭТАП №3: Вывод эталонной нормализованной по синтаксису строки в YML
        repaired_line = f'  "{clean_time}":\n'
        if repaired_line != line:
            print(f"[ВРЕМЯ] {filename}: {stripped!r} -> {repaired_line.strip()!r}", flush=True)
            line = repaired_line
            is_modified = True

    return line, is_modified, has_errors
