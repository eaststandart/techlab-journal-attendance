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

    # Построчно перебираем весь текст файла расписания в плоском режиме
    for i, line in enumerate(lines):
        original_line = line
        stripped = line.strip()

        # Законные пустые строки и комментарии пропускаем без провевок
        if not stripped or stripped.startswith("#"):
            repaired_lines.append(original_line)
            continue

        # 1. ТЕСТ ГЕОМЕТРИИ: Узлы дней недели (или config:) на нулевом отступе
        if stripped.endswith(":") and not line.startswith((" ", "\t")):
            repaired_line = f"{stripped.lower()}\n"
            if repaired_line != original_line:
                is_modified = True
            repaired_lines.append(repaired_line)
            continue

        # Внутренние строки конфигурации обходят сито тестов автоматически,
        # так как не имеют префиксов расписания (- name, direction, tag) и не являются временем ЧЧ:ММ.
        is_line_valid = False

        # 2. ТЕСТ ГЕОМЕТРИИ: Время группы (Определяем плоско по наличию стартовой цифры и двоеточия)
        raw_time = stripped.replace(":", "").replace('"', '').replace("'", '').strip()
        if re.fullmatch(r"\d{3,4}", raw_time) and stripped.endswith(":"):
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

        # 3. ТЕСТ ГЕОМЕТРИИ: Имя ученика (Штампуем жесткий отступ 4 пробела)
        if stripped.startswith("- name:"):
            repaired_line = f"    {stripped}\n"
            if repaired_line != original_line:
                is_modified = True
            repaired_lines.append(repaired_line)
            is_line_valid = True
            continue

        # 4. ТЕСТ ГЕОМЕТРИИ: Параметры ученика (Штампуем жесткий отступ 6 пробелов)
        if stripped.startswith("direction:") or stripped.startswith("tag:"):
            repaired_line = f"      {stripped}\n"
            if repaired_line != original_line:
                is_modified = True
            repaired_lines.append(repaired_line)
            is_line_valid = True
            continue

        # 5. ТЕСТ ГЕОМЕТРИИ: Пропуск служебных строк конфигурации (tg_public_notify, channel_id и т.д.)
        # Если строка имеет отступ и не относится к расписанию, она легитимно пропускается
        if line.startswith((" ", "\t")) and not stripped.startswith(("- name:", "direction:", "tag:")) and not re.match(r"^\d", raw_time):
            repaired_lines.append(original_line)
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
