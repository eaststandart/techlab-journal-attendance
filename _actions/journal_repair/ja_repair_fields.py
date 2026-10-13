#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  ja_repair_fields.py
@about   Подмодуль инспекции и чистки текстовых полей учащихся
@purpose Очистка от мусора строк имен, направлений и тегов
@author  TechLab
@version 1.0.0
"""

import json

def clean_field_internal(value, allowed_extra=""):
    """Внутренняя автономная прачечная очистки букв из старого ja_repair_normalizer.py."""
    allowed = set(
        "abcdefghijklmnopqrstuvwxyz" "ABCDEFGHIJKLMNOPQRSTUVWXYZ "
        "абвгдеёжзийклмнопрстуфхцчшщъыьэюя" "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
        + allowed_extra
    )
    cleaned = "".join(c for c in value if c in allowed)
    return " ".join(cleaned.split()).strip()

def repair_fields_line(line, filename):
    """Проверяет и исправляет синтаксис полей учеников строго по логике оригинала."""
    is_modified = False

    electronics_letters = ["э", "Э", "е", "Е", "e", "E"]
    joinery_letters = ["с", "С", "c", "C"]

    # 1. Проверка направления (direction)
    if line.startswith("      direction:"):
        raw_val = line.split(":", 1)[1].replace('"', '').replace("'", '').strip()
        clean_val = clean_field_internal(raw_val)
        value_lower = clean_val.lower()

        if value_lower in electronics_letters or "электрон" in value_lower:
            repaired_val = "электронное конструирование"
        elif value_lower in joinery_letters or "столяр" in value_lower:
            repaired_val = "столярное дело"
        else:
            repaired_val = clean_val

        repaired_val = " ".join(repaired_val.split()).strip()
        repaired_line = f'      direction: {json.dumps(repaired_val, ensure_ascii=False)}\n'
        if repaired_line != line:
            print(f"[СИНТАКСИС КУРСА] {filename}: {raw_val!r} -> {repaired_val!r}", flush=True)
            line = repaired_line
            is_modified = True

    # 2. Проверка имени ученика (- name)
    if line.startswith("    - name:"):
        old_raw_val = line.split(":", 1)[1].strip()
        clean_val = old_raw_val.strip('"').strip("'").strip()
        clean_val = clean_field_internal(clean_val)
        repaired_line = f'    - name: {json.dumps(clean_val, ensure_ascii=False)}\n'
        if repaired_line != line:
            print(f"[СИНТАКСИС ИМЕНИ] {filename}: {old_raw_val!r} -> {clean_val!r}", flush=True)
            line = repaired_line
            is_modified = True

    # 3. Проверка тега платформы (tag)
    if line.startswith("      tag:"):
        raw_val = line.split(":", 1)[1].replace('"', '').replace("'", '').strip()
        clean_val = clean_field_internal(raw_val, allowed_extra="#@-")
        repaired_line = f'      tag: {json.dumps(clean_val, ensure_ascii=False)}\n'
        if repaired_line != line:
            print(f"[СИНТАКСИС ТЕГА] {filename}: {raw_val!r} -> {clean_val!r}", flush=True)
            line = repaired_line
            is_modified = True

    return line, is_modified
    
