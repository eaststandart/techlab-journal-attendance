#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  ja_repair_structure.py
@about   Серверный модуль контроля целостности и геометрии YAML TechLab
@purpose Построчная проверка легитимности полей через флаг совпадения и выставление отступов
@author  TechLab
@version 1.0.0
"""

import os
import re
from ja_repair_normalizer import normalize_weekday, normalize_time

def repair_yaml_structure(file_path):
    """Построчно проверяет легитимность текста по флагу совпадения и штампует отступы."""
    filename = os.path.basename(file_path)
    print(f"[СТРУКТУРА] Контроль целостности по флагу совпадения для файла: {filename}", flush=True)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"[СТРУКТУРА] Ошибка чтения {filename}: {e}", flush=True)
        return False

    valid_days = {"Понедельник:", "Вторник:", "Среда:", "Четверг:", "Пятница:", "Суббота:", "Воскресенье:"}
    allowed_config = {"config:", "project_category_name:", "tg_public_notify:", "publish_as_bot: true"}
    
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

        # Жесткий маркер валидности текущей строки расписания
        is_line_valid = False

        # 1. ТЕСТ: День недели (Пробуем нормализовать текст)
        raw_day = stripped.replace(":", "").replace('"', '').replace("'", '').strip()
        clean_day = normalize_weekday(raw_day)
        if clean_day:
            repaired_line = f"{clean_day}:\n"
            if repaired_line != original_line:
                is_modified = True
            repaired_lines.append(repaired_line)
            is_line_valid = True
            continue

        # 2. ТЕСТ: Время группы (Пробуем нормализовать текст)
        raw_time = stripped.replace(":", "").replace('"', '').replace("'", '').strip()
        clean_time = normalize_time(raw_time)
        if clean_time and stripped.endswith(":"):
            repaired_line = f'  "{clean_time}":\n'
            if repaired_line != original_line:
                is_modified = True
            repaired_lines.append(repaired_line)
            is_line_valid = True
            continue

        # 3. ТЕСТ: Имя ученика
        if stripped.startswith("- name:"):
            repaired_line = f"    {stripped}\n"
            if repaired_line != original_line:
                is_modified = True
            repaired_lines.append(repaired_line)
            is_line_valid = True
            continue

        # 4. ТЕСТ: Параметры ученика
        if stripped.startswith("direction:") or stripped.startswith("tag:"):
            repaired_line = f"      {stripped}\n"
            if repaired_line != original_line:
                is_modified = True
            repaired_lines.append(repaired_line)
            is_line_valid = True
            continue

        # 5. ТЕСТ: Служебные поля секции config
        if stripped in allowed_config:
            repaired_lines.append(original_line)
            is_line_valid = True
            continue

        # --- МОМЕНТАЛЬНЫЙ СТОП-СИГНАЛ (Флаг остался False) ---
        if not is_line_valid:
            print(f"[КРИТИЧЕСКИЙ СБОЙ] {filename} (Строка {i+1}): Обнаружено неразрешенное или разорванное поле: {stripped!r}", flush=True)
            print("[ИНСТРУКЦИЯ] Сборка заблокирована. Пожалуйста, исправьте эту опечатку вручную на GitHub.", flush=True)
            return False

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
