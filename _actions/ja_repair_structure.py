#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  ja_repair_structure.py
@about   Серверный модуль контроля целостности и геометрии YAML TechLab
@purpose Построчная проверка легитимности полей через флаг совпадения и выставление отступов
@author  TechLab
@version 5.0.0
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
    is_inside_config = False  # Зрячий предохранитель секции конфигурации

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

        # АВТОНОМНЫЙ ТЕСТ: День недели (на нулевом отступе оканчивается на двоеточие)
        check_days = ["понедельник:", "вторник:", "среда:", "четверг:", "пятница:", "суббота:", "воскресенье:"]
        if stripped.lower() in check_days and not line.startswith((" ", "\t")):
            is_inside_config = False  # Робот вышел из настроек, началось расписание!
            repaired_line = f"{stripped.lower()}\n"
            if repaired_line != original_line:
                is_modified = True
            repaired_lines.append(repaired_line)
            continue

        # ХАРД-ЛОК: Если мы летим внутри секции config:, проверки синтаксиса полностью ИГНОРИРУЮТСЯ!
        if is_inside_config:
            repaired_lines.append(original_line)
            continue

        # =========================================================================
        # 🛑 СИТО ТЕСТОВ ДЛЯ СЕКЦИИ РАСПИСАНИЯ (РАБОТАЕТ С ФЛАГОМ СОВПАДЕНИЯ)
        # =========================================================================
        is_line_valid = False

        # 1. ТЕСТ: Время группы (Плоский автономный разбор регулярным выражением ЧЧ:ММ)
        raw_time = stripped.replace(":", "").replace('"', '').replace("'", '').strip()
        if re.fullmatch(r"\d{3,4}", raw_time) and stripped.endswith(":"):
            # Форматируем в красивый стандарт ЧЧ:ММ
            if len(raw_time) == 3:
                clean_time = f"0{raw_time[0]}:{raw_time[1:]}"
            else:
                clean_time = f"{raw_time[:2]}:{raw_time[2:]}"
                
            repaired_line = f'  "{clean_time}":\n'
            if repaired_line != original_line:
                is_modified = True
            repaired_lines.append(repaired_line)
            is_line_valid = True
            continue

        # 2. ТЕСТ: Имя ученика (Штампуем жесткий отступ 4 пробела)
        if stripped.startswith("- name:"):
            repaired_line = f"    {stripped}\n"
            if repaired_line != original_line:
                is_modified = True
            repaired_lines.append(repaired_line)
            is_line_valid = True
            continue

        # 3. ТЕСТ: Параметры ученика (Штампуем жесткий отступ 6 пробелов)
        if stripped.startswith("direction:") or stripped.startswith("tag:"):
            repaired_line = f"      {stripped}\n"
            if repaired_line != original_line:
                is_modified = True
            repaired_lines.append(repaired_line)
            is_line_valid = True
            continue

        # --- МОМЕНТАЛЬНЫЙ СТОП-СИГНАЛ ---
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
    
