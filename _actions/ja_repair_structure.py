#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  ja_repair_structure.py
@about   Серверный модуль контроля целостности и геометрии YAML TechLab
@purpose Построчная проверка легитимности полей через флаг совпадения и выставление отступов
@author  TechLab
@version 4.6.0
"""

import os
import re
from ja_repair_day import repair_day_line
from ja_repair_time import repair_time_line

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

        # Сквозной вызов автономного подмодуля дней недели
        repaired_line, day_mod = repair_day_line(original_line, filename)
        if day_mod or (repaired_line.strip().endswith(":") and not repaired_line.startswith(" ")):
            # Проверяем, что это реальный день из нашего словаря синонимов
            check_days = ["понедельник:", "вторник:", "среда:", "четверг:", "пятница:", "суббота:", "воскресенье:"]
            if repaired_line.strip().lower() in check_days:
                is_inside_config = False  # Робот вышел из настроек, началось расписание!
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

        # 1. ТЕСТ: Время группы (Сквозной вызов автономного подмодуля времени)
        # Искусственно подставляем отступ в 2 пробела для корректной симуляции инспектора
        sim_line = f"  {stripped}\n" if not original_line.startswith("  ") else original_line
        repaired_time_line_str, time_mod, time_err = repair_time_line(sim_line, filename)
        
        if (time_mod or repaired_time_line_str.strip().startswith('"')) and repaired_time_line_str.strip().endswith(':'):
            if repaired_time_line_str != original_line:
                is_modified = True
            repaired_lines.append(repaired_time_line_str)
            is_line_valid = True
            continue

        # 2. ТЕСТ: Имя ученика
        if stripped.startswith("- name:"):
            repaired_line = f"    {stripped}\n"
            if repaired_line != original_line:
                is_modified = True
            repaired_lines.append(repaired_line)
            is_line_valid = True
            continue

        # 3. ТЕСТ: Параметры ученика
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
