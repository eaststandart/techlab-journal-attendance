#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  ja_repair_day.py
@about   Подмодуль инспекции и исправления синтаксиса дней недели
@purpose Построчный поиск узлов дней и нормализация их текстовых названий
@author  TechLab
@version 2.0.0
"""

def repair_day_line(line, filename):
    """Автономно проверяет и исправляет синтаксис и опечатки дней недели."""
    stripped = line.strip()
    is_modified = False

    # Ловим узлы дней на отступе 0
    if stripped.endswith(":") and stripped and not line.startswith((" ", "\t")):
        raw_day = stripped[:-1].strip().strip("\"'").strip()
        
        # Принудительно приводим к нижнему регистру для зрячего сопоставления
        search_day = raw_day.lower()

        # Бронированный внутренний словарь синонимов и частых опечаток TechLab
        day_vocabulary = {
            "понедельник": "понедельник", "понеделнник": "понедельник", "пн": "понедельник",
            "вторник": "вторник", "вт": "вторник",
            "среда": "среда", "ср": "среда",
            "четверг": "четверг", "чт": "четверг",
            "пятница": "пятница", "пт": "пятница",
            "суббота": "суббота", "субота": "суббота", "сб": "суббота",
            "воскресенье": "воскресенье", "вс": "воскресенье"
        }

        clean_day = day_vocabulary.get(search_day)
        
        if clean_day is not None:
            repaired_line = f"{clean_day}:\n"
            if repaired_line != line:
                print(f"[СИНТАКСИС ДНЯ] {filename}: {raw_day!r} -> {clean_day!r}", flush=True)
                line = repaired_line
                is_modified = True
                
    return line, is_modified
