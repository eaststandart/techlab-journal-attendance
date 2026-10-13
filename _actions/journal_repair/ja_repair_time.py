#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  ja_repair_time.py
@about   Подмодуль инспекции и форматирования синтаксиса времени групп
@purpose Контроль формата ЧЧ:ММ и автоматическое оборачивание в кавычки
@author  TechLab
@version 2.0.0
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

def repair_time_line(line, filename):
    """Проверяет и исправляет синтаксис времени групп строго по логике оригинала."""
    stripped = line.strip()
    is_modified = False
    has_errors = False

    # Зряче ловим время по смыслу (3-4 цифры с разделителем или без), игнорируя любые начальные пробелы
    content_inside = stripped.replace('"', "").replace("'", "").strip().rstrip(":")
    if stripped.endswith(":") and re.match(r"^\d{1,2}\s*[:\\/.\=–—-]?\s*\d{2}$", content_inside):
        raw_time = content_inside
            
        clean_time = normalize_time_internal(raw_time)
        
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
    
