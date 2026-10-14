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

        repaired_lines = []
        is_modified = False
        inside_target_day = False
        
        # Стандартизируем паттерны поиска строк для точного совпадения
        day_marker = f"{target_day.lower()}:"
        old_time_marker = f'"{old_time}":'

        for line in lines:
            stripped = line.strip()
            indent = len(line) - len(line.lstrip(' '))

            # 1. Фиксируем вход в нужную секцию дня недели (отступ строго 0)
            if indent == 0 and stripped.lower() == day_marker:
                inside_target_day = True
                repaired_lines.append(line)
                continue

            # 2. Если вышли из секции дня (встретили другой день на отступе 0), гасим флаг
            if indent == 0 and stripped.endswith(":") and stripped.lower() != day_marker:
                inside_target_day = False
                print(f"[ОТЛАДКА МОДИФИКАТОРА] Вышли из дня! Флаг inside_target_day = False", flush=True)

            # Печатаем посимвольный разбор абсолютно каждой строки с двоеточием внутри целевого дня
            if inside_target_day and stripped.endswith(':'):
                print(f"--- [ИНСПЕКЦИЯ СТРОКИ] inside_target_day={inside_target_day} ---", flush=True)
                print(f"Сырая строка из файла: {line!r}", flush=True)
                print(f"Вычисленный indent: {indent} | Вычисленный .strip(): {stripped!r}", flush=True)
                print(f"Искомый старый маркер: {old_time_marker!r}", flush=True)
                print(f"Результат проверки (old_time_marker in stripped): {old_time_marker in stripped}", flush=True)

            # 3. Находим целевую строку времени внутри нужного дня
            if inside_target_day and old_time_marker in stripped:
                # Извлекаем оригинальные кавычки и двоеточие, заменяя только начинку
                repaired_line = line.replace(old_time, new_time)
                if repaired_line != line:
                    print(f"[МОДИФИКАЦИЯ] Успех: в секции '{target_day}' заменено {old_time!r} -> {new_time!r}", flush=True)
                    line = repaired_line
                    is_modified = True
                    # Сразу гасим флаг дня, так как задача выполнена
                    inside_target_day = False

            repaired_lines.append(line)

        if is_modified:
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(repaired_lines)
            return True
        else:
            print(f"[МОДИФИКАЦИЯ] Предупреждение: строка времени '{old_time}' в секции '{target_day}' не найдена.", flush=True)
            return False

    except Exception as e:
        print(f"[МОДИФИКАЦИЯ] Критический сбой при обработке файла: {e}", flush=True)
        return False
