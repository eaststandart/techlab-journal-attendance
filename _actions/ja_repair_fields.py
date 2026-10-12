#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  ja_repair_fields.py
@about   Подмодуль инспекции и чистки текстовых полей учащихся
@purpose Очистка от мусора строк направлений, имен учеников и тегов платформы
@author  TechLab
@version 1.0.0
"""

import json
from ja_repair_normalizer import clean_field

def repair_fields_line(line, filename):
    """Проверяет и исправляет синтаксис полей учеников строго по логике оригинала."""
    is_modified = False

    electronics_letters = ["э", "Э", "е", "Е", "e", "E"]
    joinery_letters = ["с", "С", "c", "C"]

    # 1. Проверка направления (direction)
    if line.startswith("      direction:"):
        raw_val = line.split(":", 1)[1].replace('"', '').replace("'", '').strip()
        clean_val = clean_field(raw_val)
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
            print(f"[КУРС] {filename}: {raw_val!r} -> {repaired_val!r}", flush=True)
            line = repaired_line
            is_modified = True

    # 2. Проверка имени ученика (- name)
    if line.startswith("    - name:"):
        old_raw_val = line.split(":", 1)[1].strip()
        clean_val = old_raw_val.strip('"').strip("'").strip()
        clean_val = clean_field(clean_val)
        repaired_line = f'    - name: {json.dumps(clean_val, ensure_ascii=False)}\n'
        if repaired_line != line:
            print(f"[ИМЯ] {filename}: {old_raw_val!r} -> {clean_val!r}", flush=True)
            line = repaired_line
            is_modified = True

    # 3. Проверка тега платформы (tag)
    if line.startswith("      tag:"):
        raw_val = line.split(":", 1)[1].replace('"', '').replace("'", '').strip()
        clean_val = clean_field(raw_val, allowed_extra="#@-")
        repaired_line = f'      tag: {json.dumps(clean_val, ensure_ascii=False)}\n'
        if repaired_line != line:
            print(f"[ТЕГ] {filename}: {raw_val!r} -> {clean_val!r}", flush=True)
            line = repaired_line
            is_modified = True

    return line, is_modified
