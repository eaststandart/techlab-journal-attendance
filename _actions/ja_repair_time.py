#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  ja_repair_time.py
@about   Подмодуль инспекции и форматирования синтаксиса времени групп
@purpose Контроль формата ЧЧ:ММ и автоматическое оборачивание в кавычки
@author  TechLab
@version 1.0.0
"""

import re
from ja_repair_normalizer import normalize_time

def repair_time_line(line, filename):
    """Проверяет и исправляет синтаксис времени групп строго по логике оригинала."""
    stripped = line.strip()
    is_modified = False
    has_errors = False

    if line.startswith("  ") and not line.startswith("    ") and stripped.endswith(":"):            
        raw_time = stripped[:-1].replace('"', "").replace("'", "").strip().rstrip(":")           
        if not re.match(r"^\d", raw_time):
            return line, is_modified, has_errors
            
        clean_time = normalize_time(raw_time)
        
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
