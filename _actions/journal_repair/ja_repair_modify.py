#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  ja_repair_modify.py
@about   Подмодуль точечной модификации структуры расписания TechLab
@purpose Построчный поиск секции дня и хирургическая замена ломаного времени на эталонное
@author  TechLab
@version 1.0.0
"""

import os

def modify_time_in_yaml(file_path, target_day, old_time, new_time):
    """Находит нужный день недели и заменяет строку старого времени на новое."""
    if not os.path.isfile(file_path):
        print(f"[МОДИФИКАЦИЯ] Ошибка: файл {file_path} не существует.", flush=True)
        return False

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # СПИСОК ВСЕХ ВАЛИДНЫХ ДНЕЙ НЕДЕЛИ TECHLAB ДЛЯ СНАЙПЕРСКОЙ СВЕРКИ ГРАНИЦ
        valid_days = {"понедельник:", "вторник:", "среда:", "четверг:", "пятница:", "суббота:", "воскресенье:"}
        
        day_start_idx = None
        day_end_idx = len(lines)
        day_marker = f"{target_day.lower()}:"

        # Шаг А: Снайперски находим Точку Старта и Точку Финиша секции дня
        for idx, line in enumerate(lines):
            stripped = line.strip().lower()
            indent = len(line) - len(line.lstrip(' '))
            
            if indent == 0 and stripped in valid_days:
                if stripped == day_marker:
                    day_start_idx = idx
                elif day_start_idx is not None and day_end_idx == len(lines):
                    day_end_idx = idx
                    break

        if day_start_idx is None:
            print(f"[МОДИФИКАЦИЯ] Ошибка: секция дня '{target_day}' физически не найдена в YML-файле.", flush=True)
            return False

        # Шаг Б: Работаем строго внутри изолированных границ целевого дня
        is_modified = False
        clean_target_digits = old_time.replace(':', '').strip()

        for idx in range(day_start_idx + 1, day_end_idx):
            line = lines[idx]
            stripped = line.strip()
            
            # Извлекаем чистые цифры времени текущей строки расписания
            clean_line_digits = stripped.replace('"', '').replace("'", "").replace(':', '').strip()
            
            if stripped.endswith(":") and clean_line_digits == clean_target_digits:
                # Нашли! Заменяем старое время на новое
                indent_str = " " * (len(line) - len(line.lstrip(' ')))
                if not indent_str: indent_str = "  "
                
                lines[idx] = f'{indent_str}"{new_time}":\n'
                print(f"[МОДИФИКАЦИЯ] УСПЕХ: В секции '{target_day}' на строке №{idx+1} время измененно на '{new_time}'", flush=True)
                is_modified = True
                break  # Цель достигнута, экстренно останавливаем контур поиска

        if is_modified:
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            return True
        else:
            print(f"[МОДИФИКАЦИЯ] Предупреждение: строка времени '{old_time}' в секции '{target_day}' не найдена.", flush=True)
            return False

    except Exception as e:
        print(f"[МОДИФИКАЦИЯ] Критический сбой при обработке файла: {e}", flush=True)
        return False
