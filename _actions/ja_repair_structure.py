#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  ja_repair_structure.py
@about   Серверный модуль контроля целостности и геометрии YAML TechLab
@purpose Построчная проверка легитимности полей через точное совпадение и выставление отступов
@author  TechLab
@version 6.1.0
"""

import os
import re

def repair_yaml_structure(file_path):
    """Построчно проверяет текст по белому списку расписания и выставляет эталонные отступы."""
    filename = os.path.basename(file_path)
    print(f"[СТРУКТУРА] Контроль целостности и геометрии по белому списку для файла: {filename}", flush=True)

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

        # =========================================================================
        # 🛑 БЕЛАЯ МАТРИЦА ТОЧНЫХ СОВПАДЕНИЙ РАСПИСАНИЯ TECHLAB
        # =========================================================================

        # 1. ТЕСТ: День недели (Отступ любой на входе, точное совпадение слова, отступ 0 на выходе)
        raw_day = stripped.replace(":", "").replace('"', '').replace("'", '').strip().lower()
        structure_days = {"понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"}
        
        if raw_day in structure_days and stripped.endswith(":"):
            # Штампуем жесткий отступ 0 пробелов для дня недели на выходе
            repaired_line = f"{raw_day}:\n"
            if repaired_line != original_line:
                is_modified = True
            repaired_lines.append(repaired_line)
            continue

        # 2. ТЕСТ: Время группы (Отступ любой на входе, штампуем ровно 2 пробела на выходе)
        raw_time = stripped.replace(":", "").replace('"', '').replace("'", '').strip()
        if re.fullmatch(r"\d{3,4}", raw_time) and stripped.endswith(":"):
            if len(raw_time) == 3:
                clean_time = f"0{raw_time[:1]}:{raw_time[1:]}"
            else:
                clean_time = f"{raw_time[:2]}:{raw_time[2:]}"
            repaired_line = f'  "{clean_time}":\n'
            if repaired_line != original_line:
                is_modified = True
            repaired_lines.append(repaired_line)
            continue

        # 3. ТЕСТ: Имя ученика (Штампуем ровно 4 пробела на выходе)
        if stripped.startswith("- name:"):
            repaired_line = f"    {stripped}\n"
            if repaired_line != original_line:
                is_modified = True
            repaired_lines.append(repaired_line)
            continue

        # 4. ТЕСТ: Параметры ученика (Штампуем ровно 6 пробелов на выходе)
        if stripped.startswith("direction:") or stripped.startswith("tag:"):
            repaired_line = f"      {stripped}\n"
            if repaired_line != original_line:
                is_modified = True
            repaired_lines.append(repaired_line)
            continue

        # --- БЕЗОПАСНЫЙ АВТОНОМНЫЙ ПРОПУСК (БЛОК CONFIG И ВСЕ НАСТРОЙКИ) ---
        # Если строка не совпала со списком расписания — она легитимно летит дальше без изменений!
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
