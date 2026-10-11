#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  ja_repair_engine.py
@about   Движок проверки и построчного исправления файла расписания
@purpose Построчный разбор YAML, чистка полей и физическое сохранение файла
@author  TechLab
@version 1.0.0
"""

import re
import os
import json
from ja_repair_normalizer import normalize_time, normalize_weekday, clean_field

def repair_yaml_file(file_path):
    """Проверяет и исправляет один файл расписания."""
    filename = os.path.basename(file_path)
    print(f"[ПРОВЕРКА] Файл: {filename}", flush=True)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"[ОШИБКА] {filename}: чтение файла: {e}", flush=True)
        return False

    is_modified = has_errors = False
    repaired_lines = []

    electronics_letters = ["э", "Э", "е", "Е", "e", "E"]
    joinery_letters = ["с", "С", "c", "C"]

    for line in lines:
        original_line = line
        stripped = line.strip()

        if stripped.endswith(":") and stripped and not line.startswith((" ", "\t")):
            raw_day = stripped[:-1].strip().strip("\"'").strip()
            clean_day = normalize_weekday(raw_day)
            if clean_day is not None:
                repaired_line = f"{clean_day}:\n"
                if repaired_line != line:
                    print(f"[ДЕНЬ] {filename}: {raw_day!r} -> {clean_day!r}", flush=True)
                    line = repaired_line
                    is_modified = True
                    stripped = line.strip()

        if line.startswith("  ") and not line.startswith("    ") and stripped.endswith(":"):

            # --- ЛОГ 1: Сырая строка из файла ---
            print(f"[ДИАГНОСТИКА ЛОГ 1] Сырая строка из YAML: {stripped!r}", flush=True)
            
            raw_time = stripped[:-1].replace('"', "").replace("'", "").strip()

            # --- ЛОГ 2: Строка после первичной очистки ---
            print(f"[ДИАГНОСТИКА ЛОГ 2] После очистки кавычек: {raw_time!r}", flush=True)
            
            if not re.match(r"^\d", raw_time):
                print(f"[ДИАГНОСТИКА] Строка пропущена (это текст): {raw_time!r}", flush=True)
                repaired_lines.append(line)
                continue

            clean_time = normalize_time(raw_time)

            # --- ЛОГ 3: Результат парсера ---
            print(f"[ДИАГНОСТИКА ЛОГ 3] Функция normalize_time вернула: {clean_time!r}", flush=True)
            
            if clean_time is None:
                print(f"[ОШИБКА ВРЕМЕНИ] {filename}: недопустимое значение {raw_time!r}", flush=True)
                has_errors = True
            else:
                repaired_line = f'  "{clean_time}":\n'
                if repaired_line != line:
                    print(f"[ВРЕМЯ] {filename}: {stripped!r} -> {repaired_line.strip()!r}", flush=True)
                    line = repaired_line
                    is_modified = True

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

        if line.startswith("    - name:"):
            old_raw_val = line.split(":", 1)[1].strip()
            clean_val = old_raw_val.strip('"').strip("'").strip()
            clean_val = clean_field(clean_val)
            repaired_line = f'    - name: {json.dumps(clean_val, ensure_ascii=False)}\n'
            if repaired_line != line:
                print(f"[ИМЯ] {filename}: {old_raw_val!r} -> {clean_val!r}", flush=True)
                line = repaired_line
                is_modified = True

        if line.startswith("      tag:"):
            raw_val = line.split(":", 1)[1].replace('"', '').replace("'", '').strip()
            clean_val = clean_field(raw_val, allowed_extra="#@-")
            repaired_line = f'      tag: {json.dumps(clean_val, ensure_ascii=False)}\n'
            if repaired_line != line:
                print(f"[ТЕГ] {filename}: {raw_val!r} -> {clean_val!r}", flush=True)
                line = repaired_line
                is_modified = True

        if line != original_line:
            is_modified = True
        repaired_lines.append(line)

    if has_errors:
        print(f"[ОШИБКА] {filename}: найдены недопустимые значения времени.", flush=True)
        return False

    if is_modified:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(repaired_lines)
            print(f"[ИТОГ] {filename}: исправления сохранены.", flush=True)
        except Exception as e:
            print(f"[ОШИБКА] {filename}: запись файла: {e}", flush=True)
            return False
    else:
        print(f"[ИТОГ] {filename}: исправления не требуются.", flush=True)

    return True
