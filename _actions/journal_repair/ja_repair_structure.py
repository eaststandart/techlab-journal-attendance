#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  ja_repair_structure.py
@about   Модуль контроля целостности и геометрии YAML.
@purpose Построчная проверка строк по белому списку расписания и принудительное выравнивание отступов блоков.
@author  TechLab
@version 1.0.0
"""

import os
import re

def repair_yaml_structure(file_path):
    """Построчно проверяет текст по белому списку расписания, выставляет отступы и выводит детальные логи."""
    filename = os.path.basename(file_path)
    print(f"[СТРУКТУРА] Контроль целостности и геометрии для: {filename}", flush=True)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"[СТРУКТУРА] Ошибка чтения {filename}: {e}", flush=True)
        return False

    repaired_lines = []
    is_modified = False

    # Построчно перебираем весь текст файла расписания
    for i, line in enumerate(lines):
        original_line = line
        stripped = line.strip()

        # Законные пустые строки и комментарии пропускаем без проверок
        if not stripped or stripped.startswith("#"):
            repaired_lines.append(original_line)
            continue

        # 1. ТЕСТ: День недели (Отступ любой на входе -> отступ 0 на выходе)
        raw_day = stripped.replace(":", "").replace('"', '').replace("'", '').strip().lower()
        structure_days = {"понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"}
        
        if raw_day in structure_days and stripped.endswith(":"):
            repaired_line = f"{raw_day}:\n"
            if repaired_line != original_line:
                print(f"[ГЕОМЕТРИЯ ДНЯ] Строка {i+1}: {original_line.rstrip()!r} -> {repaired_line.rstrip()!r}", flush=True)
                is_modified = True
            repaired_lines.append(repaired_line)
            continue

        # 2. ТЕСТ: Время группы (Отступ любой на входе -> ровно 2 пробела на выходе)
        raw_time = stripped.replace(":", "").replace('"', '').replace("'", '').strip()
        if re.fullmatch(r"\d{3,4}", raw_time) and stripped.endswith(":"):
            if len(raw_time) == 3:
                clean_time = f"0{raw_time[:1]}:{raw_time[1:]}"
            else:
                clean_time = f"{raw_time[:2]}:{raw_time[2:]}"
            repaired_line = f'  "{clean_time}":\n'
            if repaired_line != original_line:
                print(f"[ГЕОМЕТРИЯ ВРЕМЕНИ] Строка {i+1}: {original_line.rstrip()!r} -> {repaired_line.rstrip()!r}", flush=True)
                is_modified = True
            repaired_lines.append(repaired_line)
            continue

        # 3. ТЕСТ: Имя ученика (Штампуем ровно 4 пробела на выходе)
        if stripped.startswith("- name:"):
            repaired_line = f"    {stripped}\n"
            if repaired_line != original_line:
                print(f"[ГЕОМЕТРИЯ ИМЕНИ] Строка {i+1}: {original_line.rstrip()!r} -> {repaired_line.rstrip()!r}", flush=True)
                is_modified = True
            repaired_lines.append(repaired_line)
            continue

        # 4. ТЕСТ: Параметры ученика (Штампуем ровно 6 пробелов на выходе)
        if stripped.startswith("direction:") or stripped.startswith("tag:"):
            repaired_line = f"      {stripped}\n"
            if repaired_line != original_line:
                print(f"[ГЕОМЕТРИЯ ПОЛЯ] Строка {i+1}: {original_line.rstrip()!r} -> {repaired_line.rstrip()!r}", flush=True)
                is_modified = True
            repaired_lines.append(repaired_line)
            continue

        # --- БЕЗОПАСНЫЙ АВТОНОМНЫЙ ПРОПУСК (БЛОК CONFIG И ВСЕ НАСТРОЙКИ) ---
        repaired_lines.append(original_line)

    # Физически сохраняем исправленные отступы, только если проход завершился успехом
    if is_modified:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(repaired_lines)
            print(f"[ИТОГ] {filename}: Геометрия отступов успешно нормализована.", flush=True)
        except Exception as e:
            print(f"[СТРУКТУРА] Ошибка записи {filename}: {e}", flush=True)
            return False
    else:
        print(f"[ИТОГ] {filename}: Нарушений целостности и геометрии не найдено.", flush=True)

    return True
