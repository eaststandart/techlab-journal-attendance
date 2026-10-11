#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  journal_data_repair.py
@about   Главный диспетчер проверки, исправления и модерации расписания
@purpose Прием входящих сигналов, управление светофором и вызов модулей TechLab
@author  TechLab
@version 1.0.0
"""

import os
import sys
import json
from datetime import datetime, timezone

# Импортируем наши автономные модули TechLab
from ja_repair_normalizer import write_status
from ja_repair_engine import repair_yaml_file
from ja_repair_delete import delete_students_from_yaml

# ==============================================================================
# НАСТРОЙКИ
# ==============================================================================
DATA_DIR = "_data"
SIGNAL_FILE = os.path.join(DATA_DIR, "signal-repair.json")


def main():
    # Проверяем наличие папки данных и входящего сигнала
    if not os.path.isdir(DATA_DIR) or not os.path.isfile(SIGNAL_FILE):
        print("[ОШИБКА] Папка _data или входящий сигнал не найдены.", flush=True)
        sys.exit(1)

    try:
        with open(SIGNAL_FILE, "r", encoding="utf-8") as f:
            signal_data = json.load(f)

        target_teacher = signal_data.get("teacher_login", "")
        if not isinstance(target_teacher, str):
            raise ValueError("teacher_login должен быть строкой")

        target_teacher = target_teacher.strip()
        if (
            not target_teacher
            or target_teacher in {".", ".."}
            or "/" in target_teacher
            or "\\" in target_teacher
        ):
            raise ValueError("teacher_login отсутствует или содержит недопустимый путь")

    except Exception as e:
        print(f"[ОШИБКА] Некорректный сигнал: {e}", flush=True)
        try:
            write_status("error")
        except Exception as status_error:
            print(f"[ОШИБКА] Не удалось сохранить статус: {status_error}", flush=True)
        sys.exit(1)

    filename = f"journal-attendance-{target_teacher}.yml"
    file_path = os.path.join(DATA_DIR, filename)

    print(f"[СИГНАЛ] Преподаватель: {target_teacher}", flush=True)
    print(f"[СИГНАЛ] Целевой файл: {filename}", flush=True)

    if not os.path.isfile(file_path):
        print(f"[ОШИБКА] Файл {filename} не найден.", flush=True)
        try:
            write_status("error")
        except Exception as e:
            print(f"[ОШИБКА] Не удалось сохранить статус: {e}", flush=True)
        sys.exit(1)

    success = True

    # =========================================================================
    # 💥 ИСПОЛНИТЕЛЬНЫЙ КОНВЕЙЕР МОДЕРАЦИИ И РЕМОНТА БАЗЫ
    # =========================================================================
    
    # 1. Проверяем, пришел ли запрос на удаление учеников
    students_to_delete = signal_data.get("delete")
    if isinstance(students_to_delete, list) and len(students_to_delete) > 0:
        target_day = signal_data.get("day", "")
        target_time = signal_data.get("time", "")
        
        # Запускаем лазерное вырезание указанных учеников по координатам группы
        success = delete_students_from_yaml(file_path, target_day, target_time, students_to_delete)

    # 2. Если удаление прошло успешно, запускаем общую гигиеническую нормализацию оставшегося YAML
    if success:
        try:
            success = repair_yaml_file(file_path)
        except Exception as e:
            print(f"[КРИТИЧЕСКИЙ СБОЙ] Нормализация {filename}: {e}", flush=True)
            success = False

    # Фиксируем финальный статус для светофора Obsidian фронтенда
    if not success:
        try:
            write_status("error")
        except Exception as e:
            print(f"[ОШИБКА] Не удалось сохранить статус: {e}", flush=True)
        sys.exit(1)

    try:
        write_status("on")
    except Exception as e:
        print(f"[ОШИБКА] Не удалось сохранить статус: {e}", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
