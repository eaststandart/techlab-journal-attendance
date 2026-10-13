#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  ja_repair_structure.py
@about   Серверный module контроля целостности и геометрии YAML TechLab
@purpose Построчная проверка легитимности полей через флаг совпадения и выставление отступов
@author  TechLab
@version 5.3.0
"""

import os
import re

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

    repaired_lines = []
    is_modified = False
    is_inside_config = False  # Жесткий предохранитель секции конфигурации

    # Построчно перебираем весь текст файла расписания
    for i, line in enumerate(lines):
        original_line = line
        stripped = line.strip()

        # Законные пустые строки и комментарии пропускаем без проверок
        if not stripped or stripped.startswith("#"):
            repaired_lines.append(original_line)
            continue

        # Перехват входа в секцию конфигурации config:
        if stripped.lower() == "config:":
            is_inside_config = True
            repaired_lines.append(original_line)
            continue

        # АВТОНОМНЫЙ ПЕРЕХВАТ ГРАНИЦЫ: Выход из config:, если пошла любая строка дня на нулевом отступе
        if stripped.endswith(":") and not line.startswith((" ", "\t")):
            is_inside_config = False

        # ХАРД-ЛОК CONFIG: Если мы внутри настроек, любые внутренние строки YAML пропускаются легитимно!
        if is_inside_config:
            repaired_lines.append(original_line)
            continue

        # =========================================================================
        # 🛑 СИТО ТЕСТОВ ДЛЯ СЕКЦИИ РАСПИСАНИЯ (РАБОТАЕТ С ФЛАГОМ СОВПАДЕНИЯ)
        # =========================================================================
        is_line_valid = False

        # 1. ТЕСТ: День недели (Плоский автономный аналог)
        raw_day = stripped.replace(":", "").replace('"', '').replace("'", '').strip().lower()
        structure_days = {"понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"}
        
        if raw_day in structure_days and stripped.endswith(":"):
            repaired_line = f"{stripped}\n"
            if repaired_line != original_line:
                is_modified = True
            repaired_lines.append(repaired_line)
            is_line_valid = True
            continue

        # 2. ТЕСТ: Время группы (Плоский автономный аналог)
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

        # --- МОМЕНТАЛЬНЫЙ СТОП-СИГНАЛ (Флаг остался False во внешней базе расписания) ---
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
