#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  journal-analyzer.py
@about   Изолированный модуль проверки комплектности журналов.
@purpose Группировка файлов по датам и дням недели, сверка с YAML-расписанием и перенос первого готового комплекта.
@author TechLab
@version 9.0.0
"""

import os
import json
import re
import sys
import yaml
import shutil

def analyze_and_move_bundle():
    print("\n=== [МОДУЛЬ JOURNAL-ANALYZER] АНАЛИЗ ПАПКИ _INPUT ===")

    input_dir = os.path.join(os.getcwd(), "_input")
    output_dir = os.path.join(os.getcwd(), "_output")
    data_dir = os.path.join(os.getcwd(), "_data")

    if not os.path.exists(input_dir) or not os.path.exists(output_dir) or not os.path.exists(data_dir):
        print("[АНАЛИЗАТОР] ❌ Ошибка: Целевые директории не найдены.")
        return "ERROR_DIR_NOT_FOUND"

    # Защита от начала нового комплекта, если папка Выход занята
    output_json_files = sorted(f for f in os.listdir(output_dir) if f.endswith(".json"))
    if output_json_files:
        print(f"[АНАЛИЗАТОР] Папка _output занята: {len(output_json_files)} JSON-файл(ов). Новый комплект не переносим.")
        return "OUTPUT_BUSY"

    all_files = sorted(os.listdir(input_dir))
    json_files = [f for f in all_files if "-journal-attendance-" in f and f.endswith(".json")]

    if not json_files:
        print("[АНАЛИЗАТОР] В директории _input файлы JSON отсутствуют.")
        return "NO_FILES"

    # Сбор списка активных преподавателей по алфавиту
    active_teachers = []
    for f in sorted(os.listdir(data_dir)):
        if f.startswith("journal-attendance-") and f.endswith(".yml"):
            login = f.replace("journal-attendance-", "").replace(".yml", "").strip().lower()
            if login:
                active_teachers.append(login)
    active_teachers.sort()

    # Детерминированный поиск первого готового комплекта
    for teacher_login in active_teachers:
        teacher_files = sorted(f for f in json_files if f.lower().endswith(f"-journal-attendance-{teacher_login}.json"))
        if not teacher_files:
            continue

        # Группировка файлов преподавателя по календарным датам
        date_groups = {}
        for file_name in teacher_files:
            file_path = os.path.join(input_dir, file_name)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    file_data = json.load(f)
                file_date = str(file_data.get("date", "")).strip()
                file_day = str(file_data.get("day", "")).strip().lower()

                if not file_date or not file_day:
                    continue

                if file_date not in date_groups:
                    date_groups[file_date] = {"day_name": file_day, "files": []}
                date_groups[file_date]["files"].append(file_name)
            except Exception as e:
                print(f"[АНАЛИЗАТОР] Ошибка чтения '{file_name}': {str(e)}")
                continue

        # Перебор дат в строгом хронологическом порядке
        for target_date in sorted(date_groups.keys()):
            group_data = date_groups[target_date]
            target_day = group_data["day_name"]
            bundle_files = sorted(group_data["files"])

            yaml_path = os.path.join(data_dir, f"journal-attendance-{teacher_login}.yml")
            if not os.path.exists(yaml_path):
                continue

            # Вызываем наш отдельный модуль для исправления опечаток на диске до старта PyYAML
            journal_data_repair.fix_local_yaml_file(yaml_path)

            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    yaml_data = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"[АНАЛИЗАТОР] Ошибка парсинга YAML '{yaml_path}': {str(e)}")
                continue

            # Сбор структуры расписания групп из YAML
            students_data = {}
            for key, value in yaml_data.items():
                if key == "config":
                    continue
                day_name = str(key).lower().strip()
                students_data[day_name] = {}
                if isinstance(value, dict):
                    for raw_time, kids_list in value.items():
                        clean_time_str = str(raw_time).strip()
                        match_time = re.search(r"(\d{1,2})\D*(\d{2})", clean_time_str)
                        if match_time:
                            normalized_time = f"{match_time.group(1)}:{match_time.group(2)}"
                            students_data[day_name][normalized_time] = kids_list if isinstance(kids_list, list) else []
                        else:
                            students_data[day_name][clean_time_str] = kids_list if isinstance(kids_list, list) else []

            schedule_groups = sorted(list(students_data.get(target_day, {}).keys()))

            # Сверка комплектности с планом расписания
            if len(bundle_files) < len(schedule_groups):
                continue

            # РЕАЛЬНЫЙ ПРОЦЕСС №1: ФИКСАЦИЯ ОБНАРУЖЕНИЯ КОМПЛЕКТА В ПАМЯТИ
            day_short = target_day[:2]
            print(f"[АНАЛИЗАТОР] Обнаружен комплект файлов JSON '{teacher_login}' за '{target_date} ({day_short})': {len(bundle_files)} шт.")
            
            # РЕАЛЬНЫЙ ПРОЦЕСС №2: ОФИЦИАЛЬНАЯ ОСТАНОВКА ЦИКЛА ПОИСКА
            print("[АНАЛИЗАТОР] Поиск завершен. Анализ директории _input остановлен.")

            # Повторная проверка перед переносом
            if sorted(f for f in os.listdir(output_dir) if f.endswith(".json")):
                return "OUTPUT_BUSY"

            # РЕАЛЬНЫЙ ПРОЦЕСС №3: ФИЗИЧЕСКИЙ ПЕРЕНОС ФАЙЛОВ С ЛОГОМ ПО ФАКТУ ОПЕРАЦИИ
            for file_name in bundle_files:
                old_file_path = os.path.join(input_dir, file_name)
                new_file_path = os.path.join(output_dir, file_name)
                
                shutil.move(old_file_path, new_file_path)
                
                if os.path.exists(new_file_path):
                    print(f"[АНАЛИЗАТОР] Перемещаем комплект файлов JSON '{teacher_login}' за '{target_date} ({day_short})' [{len(bundle_files)} из {len(schedule_groups)}].")

            status = f"SUCCESS_{teacher_login}"
            if "GITHUB_ENV" in os.environ:
                with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as env_file:
                    env_file.write(f"ANALYZER_STATUS={status}\n")

            print(f"[АНАЛИЗАТОР] Финальный статус работы модуля: {status}")
            return status

    print("[АНАЛИЗАТОР] Комплекты для переноса отсутствуют.")
    if "GITHUB_ENV" in os.environ:
        with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as env_file:
            env_file.write("ANALYZER_STATUS=NO_BUNDLE_READY\n")
    return "NO_BUNDLE_READY"

if __name__ == "__main__":
    status = analyze_and_move_bundle()
