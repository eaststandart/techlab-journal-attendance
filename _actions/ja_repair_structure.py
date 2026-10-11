#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  ja_repair_structure.py
@about   Серверный модуль тотального выравнивания геометрии структуры YAML
@purpose Принудительное приведение отступов дней (0), групп (2) и учеников (4/6) к эталону
@author  TechLab
@version 1.0.0
"""

import os
import re

def repair_yaml_structure(file_path):
    """Построчно пересобирает YAML, выставляя жесткие эталонные отступы по Белому списку."""
    filename = os.path.basename(file_path)
    print(f"[СТРУКТУРА] Сканирование геометрии файла: {filename}", flush=True)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"[СТРУКТУРА] Ошибка чтения {filename}: {e}", flush=True)
        return False

    # Белый список дней недели с Заглавной буквы строго по новому стандарту базы
    valid_days = {
        "понедельник:", "вторник:", "среда:", "четверг:", 
        "пятница:", "суббота:", "воскресенье:"
    }

    repaired_lines = []
    is_modified = False

    for line in lines:
        original_line = line
        stripped = line.strip()

        # Пропускаем системные комментарии и пустые строки без изменений
        if not stripped or stripped.startswith("#"):
            repaired_lines.append(original_line)
            continue

        # --- АППАРАТНЫЙ ПЕРЕХВАТ НАРУШЕНИЯ ЦЕЛОСТНОСТИ СИСТЕМНЫХ ПОЛЕЙ ---
        # Ловим разорванные пробелами или искалеченные ключевые слова YAML
        collapsed = stripped.replace(" ", "")
        if (
            ("name:" in collapsed and not stripped.startswith("- name:")) or
            ("direction:" in collapsed and not stripped.startswith("direction:")) or
            ("tag:" in collapsed and not stripped.startswith("tag:")) or
            (stripped.startswith("-") and "name" in stripped and not stripped.startswith("- name:"))
        ):
            print(f"[КРИТИЧЕСКИЙ СБОЙ] {filename}: Нарушена целостность системного поля! Обнаружена опечатка в ключевой строке: {stripped!r}", flush=True)
            return False

        # 1. Выравнивание Дней недели (Строго 0 пробелов, проверка по белому списку без учета регистра)
        if stripped.lower() in valid_days:
            # Приводим к правильному регистру (Заглавная буква на старте)
            clean_day = stripped.capitalize()
            repaired_line = f"{clean_day}\n"
            if repaired_line != original_line:
                print(f"[ГЕОМЕТРИЯ] {filename}: Выровнен день '{clean_day.strip()}' -> отступ 0", flush=True)
                is_modified = True
            repaired_lines.append(repaired_line)

        # 2. Выравнивание Времени групп (Строго 2 пробела)
        elif stripped.endswith(":") and re.match(r'^"\d{2}:\d{2}":$', stripped):
            repaired_line = f"  {stripped}\n"
            if repaired_line != original_line:
                print(f"[ГЕОМЕТРИЯ] {filename}: Выровнена группа {stripped} -> отступ 2", flush=True)
                is_modified = True
            repaired_lines.append(repaired_line)

        # 3. Выравнивание Имени ученика (Строго 4 пробела)
        elif stripped.startswith("- name:"):
            repaired_line = f"    {stripped}\n"
            if repaired_line != original_line:
                print(f"[ГЕОМЕТРИЯ] {filename}: Выровнено имя ученика -> отступ 4", flush=True)
                is_modified = True
            repaired_lines.append(repaired_line)

        # 4. Выравнивание Параметров ученика (Строго 6 пробелов)
        elif stripped.startswith("direction:") or stripped.startswith("tag:"):
            repaired_line = f"      {stripped}\n"
            if repaired_line != original_line:
                is_modified = True
            repaired_lines.append(repaired_line)

        # Все остальные легитимные строки расписания (например, внутри config:) оставляем как есть
        else:
            repaired_lines.append(original_line)

    # Записываем изменения на диск, если геометрия была нарушена
    if is_modified:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(repaired_lines)
            print(f"[ИТОГ СТРУКТУРЫ] {filename}: Геометрия отступов успешно приведена к стандарту.", flush=True)
        except Exception as e:
            print(f"[СТРУКТУРА] Ошибка записи {filename}: {e}", flush=True)
            return False
    else:
        print(f"[ИТОГ СТРУКТУРЫ] {filename}: Ошибок геометрии отступов не обнаружено.", flush=True)

    return True
