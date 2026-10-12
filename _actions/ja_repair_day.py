#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  ja_repair_day.py
@about   Подмодуль инспекции и исправления синтаксиса дней недели
@purpose Построчный поиск узлов дней и нормализация их текстовых названий
@author  TechLab
@version 1.0.0
"""

from ja_repair_normalizer import normalize_weekday

def repair_day_line(line, filename):
    """Проверяет и исправляет синтаксис дней недели строго по логике оригинала."""
    stripped = line.strip()
    is_modified = False

    if stripped.endswith(":") and stripped and not line.startswith((" ", "\t")):
        raw_day = stripped[:-1].strip().strip("\"'").strip()
        clean_day = normalize_weekday(raw_day)
        if clean_day is not None:
            repaired_line = f"{clean_day}:\n"
            if repaired_line != line:
                print(f"[ДЕНЬ] {filename}: {raw_day!r} -> {clean_day!r}", flush=True)
                line = repaired_line
                is_modified = True
                
    return line, is_modified
