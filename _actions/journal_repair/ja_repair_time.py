#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  ja_repair_time.py
@about   Модуль форматирования синтаксиса времени групп.
@purpose Автоматическое приведение любых ломаных разделителей времени строго к каноническому формату ЧЧ:ММ.
@author  TechLab
@version 1.0.0
"""

import re

def normalize_time_internal(raw_time):
    """Внутренний автономный парсер структуры времени."""
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
    """Приводит ломаные разделители времени строго к канону ЧЧ:ММ без валидации суток."""
    stripped = line.strip()
    is_modified = False
    has_errors = False

    content_inside = stripped.replace('"', "").replace("'", "").strip().rstrip(":")
    if stripped.endswith(":") and re.match(r"^\d{1,2}\s*[:\\/.\=–—-]?\s*\d{2}$", content_inside):
        raw_time = content_inside
        clean_time = normalize_time_internal(raw_time)
            
        if clean_time is None:
            print(f"[СИНТАКСИС ВРЕМЕНИ] {filename}: строка не распознана как время {raw_time!r}", flush=True)
            has_errors = True
        else:
            repaired_line = f'  "{clean_time}":\n'
            if repaired_line != line:
                print(f"[ГЕОМЕТРИЯ ВРЕМЕНИ] {filename}: {stripped!r} -> {repaired_line.strip()!r}", flush=True)
                line = repaired_line
                is_modified = True

    return line, is_modified, has_errors
