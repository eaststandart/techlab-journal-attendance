#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  ja_repair_structure.py
@about   Серверный модуль контроля целостности и геометрии YAML TechLab
@purpose Построчная проверка легитимности полей через флаг совпадения и выставление отступов
@author  TechLab
@version 5.4.0
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
    is_schedule_zone = False  # Твое плоское правило управления зоной расписания

    # Построчно перебираем весь текст файла расписания
    for i, line in enumerate(lines):
        original_line = line
        stripped = line.strip()

        # Законные пустые строки и комментарии пропускаем без проверок
        if not stripped or stripped.startswith("#"):
            repaired_lines.append(original_line)
            continue

        # --- ТВОЁ НОВОЕ ПЛОСКОЕ ПРАВИЛО УПРАВЛЕНИЯ ЗОНОЙ НАСТРОЕК И РАСПИСАНИЯ ---
        if stripped.endswith(":") and not line.startswith((" ", "\t")):
            raw_day = stripped.replace(":", "").replace('"', '').replace("'", '').strip().lower()
            # Учитываем текущие изменения системы: дни теперь строго в нижнем регистре
            structure_days = {"понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"}
            
            if raw_day in structure_days:
                is_schedule_zone = True  # Это день недели, включаем жесткий контроль расписания
                repaired_line = f"{stripped}\n"
                if repaired_line != original_line:
                    is_modified = True
                repaired_lines.append(repaired_line)
                continue
            else:
                is_schedule_zone = False  # Это не день расписания (например config:), выключаем сито тестов
                repaired_lines.append(original_line)
                continue

        # АВТОНОМНЫЙ ПРОПУСК БЛОКА КОНФИГУРАЦИИ:
        # Если мы находимся вне зоны расписания, любые внутренние строки настроек пропускаются легитимно
        if not is_schedule_zone:
            repaired_lines.append(original_line)
            continue

        # =========================================================================
        # 🛑 ТВОЕ ОРИГИНАЛЬНОЕ СИТО ТЕСТОВ (ВКЛЮЧАЕТСЯ СТРОГО ВНУТРИ РАСПИСАНИЯ)
        # =========================================================================
        is_line_valid = False

        # 2. ТЕСТ: Время группы (Плоский автономный аналог без внешних импортов)
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

        # 3. ТЕСТ: Имя ученика (Твой оригинальный код 1 в 1)
        if stripped.startswith("- name:"):
            repaired_line = f"    {stripped}\n"
            if repaired_line != original_line:
                is_modified = True
            repaired_lines.append(repaired_line)
            is_line_valid = True
            continue

        # 4. ТЕСТ: Параметры ученика (Твой оригинальный код 1 в 1)
        if stripped.startswith("direction:") or stripped.startswith("tag:"):
            repaired_line = f"      {stripped}\n"
            if repaired_line != original_line:
                is_modified = True
            repaired_lines.append(repaired_line)
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
