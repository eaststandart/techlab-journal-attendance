#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  ja_repair_delete.py
@about   Автономный модуль удаления учеников из базы данных расписания
@purpose Точечное вырезание блоков строк учащихся по координатам дня и времени
@author  TechLab
@version 2.0.0
"""

import os

def delete_students_from_yaml(file_path, target_day, target_time, students_to_delete):
    """Ищет день, группу и вырезает указанных учеников вместе со всеми их полями по чистым координатам."""
    if not students_to_delete:
        return True

    filename = os.path.basename(file_path)

    # Диспетчер передает координаты уже чистыми (в нижнем регистре и без мусора)
    clean_day = target_day
    clean_time = target_time

    print(f"[УДАЛЕНИЕ] Цель: {filename} -> {clean_day} в {clean_time}. Список: {students_to_delete}", flush=True)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"[УДАЛЕНИЕ] Ошибка чтения {filename}: {e}", flush=True)
        return False

    repaired_lines = []
    is_modified = False
    
    inside_target_day = False
    inside_target_group = False
    skip_student_block = False

    for line in lines:
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(' '))

        # 1. СВЕРКА ДНЕЙ НЕДЕЛИ: файл уже гарантированно нормализован в нижний регистр силами ja_repair_day.py
        if indent == 0 and stripped.endswith(':'):
            current_day = stripped[:-1]  # Просто срезаем двоеточие. Регистр уже маленький!
            inside_target_day = (current_day == clean_day)
            inside_target_group = False
            skip_student_block = False

        # 2. СВЕРКА ВРЕМЕНИ ГРУПП: файл уже гарантированно обернут в кавычки силами ja_repair_time.py
        elif inside_target_day and indent == 2 and stripped.endswith(':'):
            current_time = stripped[:-1].replace('"', '').replace("'", "")  # Убираем кавычки стандарта и двоеточие
            inside_target_group = (current_time == clean_time)
            skip_student_block = False

        # 3. СВЕРКА ИМЕНИ УЧЕНИКА
        elif inside_target_day and inside_target_group and line.startswith("    - name:"):
            raw_name = stripped.split(":", 1)[1].replace('"', '').replace("'", '').strip()
            
            if any(raw_name == name.strip() for name in students_to_delete):
                print(f"[УДАЛЕНИЕ] {filename}: Вырезан ученик {raw_name!r}", flush=True)
                skip_student_block = True
                is_modified = True
                continue
            else:
                skip_student_block = False

        # 4. ПРОПУСК ПОЛЕЙ УДАЛЕННОГО УЧЕНИКА
        elif inside_target_day and inside_target_group and skip_student_block:
            if line.startswith("      direction:") or line.startswith("      tag:"):
                continue
            else:
                skip_student_block = False

        repaired_lines.append(line)

    if is_modified:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(repaired_lines)
            print(f"[УДАЛЕНИЕ] {filename}: Изменения успешно зафиксированы на диске.", flush=True)
        except Exception as e:
            print(f"[УДАЛЕНИЕ] Ошибка записи {filename}: {e}", flush=True)
            return False
    else:
        print(f"[УДАЛЕНИЕ] {filename}: Указанные ученики не найдены в этой группе.", flush=True)

    return True
