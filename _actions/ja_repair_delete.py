#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  ja_repair_delete.py
@about   Автономный модуль удаления учеников из базы данных расписания
@purpose Точечное вырезание блоков строк учащихся по координатам дня и времени
@author  TechLab
@version 1.0.0
"""

import os
from ja_repair_normalizer import normalize_time, normalize_weekday

def delete_students_from_yaml(file_path, target_day, target_time, students_to_delete):
    """Ищет день, группу и вырезает указанных учеников вместе со всеми их полями."""
    if not students_to_delete:
        return True

    filename = os.path.basename(file_path)
    clean_day = normalize_weekday(target_day)
    clean_time = normalize_time(target_time)

    if not clean_day or not clean_time:
        print(f"[УДАЛЕНИЕ] Ошибка: Кривые координаты day={target_day!r}, time={target_time!r}", flush=True)
        return False

    print(f"[УДАЛЕНИЕ] Цель: {filename} -> {clean_day} в {clean_time}. Список: {students_to_delete}", flush=True)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"[УДАЛЕНИЕ] Ошибка чтения {filename}: {e}", flush=True)
        return False

    repaired_lines = []
    is_modified = False
    
    # Системные маркеры состояния нашего конвейера
    inside_target_day = False
    inside_target_group = False
    skip_student_block = False

    for line in lines:
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(' '))

        # Отслеживаем глобальную смену дней недели (отступ 0, двоеточие на конце)
        if indent == 0 and stripped.endswith(':'):
            current_day = normalize_weekday(stripped[:-1])
            inside_target_day = (current_day == clean_day)
            inside_target_group = False # Сбрасываем группу при переходе на новый день
            skip_student_block = False

        # Отслеживаем смену групп внутри текущего целевого дня (отступ 2, двоеточие на конце)
        elif inside_target_day and indent == 2 and stripped.endswith(':'):
            current_time = normalize_time(stripped[:-1])
            inside_target_group = (current_time == clean_time)
            skip_student_block = False

        # Анализируем блок учеников внутри целевой группы (отступ 4, начинается на - name:)
        elif inside_target_day and inside_target_group and line.startswith("    - name:"):
            raw_name = stripped.split(":", 1)[1].replace('"', '').replace("'", '').strip()
            
            # Если имя совпало со списком на удаление, взводим флаг пропуска строк
            if any(raw_name == name.strip() for name in students_to_delete):
                print(f"[УДАЛЕНИЕ] {filename}: Вырезан ученик {raw_name!r}", flush=True)
                skip_student_block = True
                is_modified = True
                continue # Эту строку с именем не записываем
            else:
                skip_student_block = False

        # Гасим флаг пропуска, если внутри целевой группы наткнулись на любые другие параметры
        elif inside_target_day and inside_target_group and skip_student_block:
            if line.startswith("      direction:") or line.startswith("      tag:"):
                continue # Пропускаем (вырезаем) вложенные свойства удаленного ребенка
            else:
                skip_student_block = False # Смежные данные чужих блоков не трогаем

        repaired_lines.append(line)

    # Если база была физически изменена, перезаписываем файл расписания
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
