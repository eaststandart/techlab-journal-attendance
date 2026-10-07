#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module journal-analyzer.py
@about Изолированный модуль проверки комплектности журналов
@purpose Группировка файлов по датам и дням недели, сверка с YAML-расписанием
@author TechLab
@version 1.0.0
"""

import os
import json
import re
import sys
import yaml
import shutil

def analyze_and_move_bundle():
    print("\n=== [МОДУЛЬ JOURNAL-ANALYZER] АНАЛИЗ ПАПКИ _INPUT ===")
    
    input_dir = os.path.join(os.getcwd(), '_input')
    output_dir = os.path.join(os.getcwd(), '_output')
    data_dir = os.path.join(os.getcwd(), '_data')
    
    if not os.path.exists(input_dir):
        print(f"[АНАЛИЗАТОР] ❌ Ошибка: Директория не найдена: {input_dir}")
        return "ERROR_NO_INPUT_DIR"

    all_files = os.listdir(input_dir)
    json_files = [f for f in all_files if '-journal-attendance-' in f and f.endswith('.json')]
    
    if not json_files:
        print("[АНАЛИЗАТОР] В директории _input файлы JSON отсутствуют.")
        return "NO_FILES"

    print(f"[АНАЛИЗАТОР] Обнаружено файлов JSON в _input: {len(json_files)} шт.")

    # Сбор списка активных преподавателей по файлам расписаний
    active_teachers = []
    for f in os.listdir(data_dir):
        if f.startswith('journal-attendance-') and f.endswith('.yml'):
            login = f.replace('journal-attendance-', '').replace('.yml', '').strip().lower()
            if login:
                active_teachers.append(login)

    # Группировка файлов по преподавателям и календарным датам
    for teacher_login in active_teachers:
        teacher_files = [f for f in json_files if f.lower().endswith(f"-journal-attendance-{teacher_login}.json")]
        
        if not teacher_files:
            continue

        date_groups = {}
        for file_name in teacher_files:
            file_path = os.path.join(input_dir, file_name)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                
                file_date = file_data.get('date', '').strip()
                file_day = file_data.get('day', '').strip().lower()
                
                if not file_date or not file_day:
                    continue
                    
                if file_date not in date_groups:
                    date_groups[file_date] = {"day_name": file_day, "files": []}
                date_groups[file_date]["files"].append(file_name)
                
            except Exception as e:
                print(f"[АНАЛИЗАТОР] ❌ Ошибка чтения файла {file_name}: {str(e)}")
                continue

        # Проверка комплектности каждой изолированной даты
        for target_date, group_data in date_groups.items():
            target_day = group_data["day_name"]
            bundle_files = group_data["files"]
            
            yaml_path = os.path.join(data_dir, f"journal-attendance-{teacher_login}.yml")
            if not os.path.exists(yaml_path):
                continue

            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    yaml_data = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"[АНАЛИЗАТОР] ❌ Ошибка парсинга YAML: {str(e)}")
                continue

            students_data = {}
            for key, value in yaml_data.items():
                if key == 'config':
                    continue
                day_name = str(key).lower().strip()
                students_data[day_name] = {}
                if isinstance(value, dict):
                    for raw_time, kids_list in value.items():
                        clean_time_str = str(raw_time).strip()
                        match_time = re.search(r'(\d{1,2})\D*(\d{2})', clean_time_str)
                        if match_time:
                            normalized_time = f"{match_time.group(1)}:{match_time.group(2)}"
                            students_data[day_name][normalized_time] = kids_list if isinstance(kids_list, list) else []
                        else:
                            students_data[day_name][clean_time_str] = kids_list if isinstance(kids_list, list) else []

            schedule_groups = sorted(list(students_data.get(target_day, {}).keys()))

            if len(bundle_files) < len(schedule_groups):
                print(f"[АНАЛИЗАТОР] Для даты '{target_date}' готово {len(bundle_files)} из {len(schedule_groups)} групп. Комплект не собран.")
                continue
            
            day_short = target_day[:3]
            print(f"[АНАЛИЗАТОР] Обнаружен комплект файлов JSON '{teacher_login}' за '{target_date} ({day_short})': {len(bundle_files)} шт.")
            print(f"[АНАЛИЗАТОР] Поиск завершен. Анализ директории _input остановлен.")
            print(f"[АНАЛИЗАТОР] Перемещаем комплект файлов JSON '{teacher_login}' за '{target_date} ({day_short})' [{len(bundle_files)} из {len(schedule_groups)}].")
            
            for file_name in bundle_files:
                old_file_path = os.path.join(input_dir, file_name)
                new_file_path = os.path.join(output_dir, file_name)
                
                # Физическое перемещение файла на диске
                shutil.move(old_file_path, new_file_path)
                
                # Лог пишется строго по факту успешного переноса
                if os.path.exists(new_file_path):
                    print(f"[АНАЛИЗАТОР] Перемещён: '{file_name}' ➔ _output/")

            # Жесткая запись статуса успеха в файл окружения GitHub Actions
            if "GITHUB_ENV" in os.environ:
                with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as env_file:
                    env_file.write(f"ANALYZER_STATUS=SUCCESS_{teacher_login}\n")
            
            print(f"[АНАЛИЗАТОР] Финальный статус работы модуля: SUCCESS_{teacher_login}")
            return f"SUCCESS_{teacher_login}"

    print("[АНАЛИЗАТОР] Готовых комплектов журналов не обнаружено.")
    
    # Запись статуса отсутствия комплектов в файл окружения GitHub Actions
    if "GITHUB_ENV" in os.environ:
        with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as env_file:
            env_file.write("ANALYZER_STATUS=NO_BUNDLE_READY\n")
            
    return "NO_BUNDLE_READY"

if __name__ == "__main__":
    status = analyze_and_move_bundle()
    if "GITHUB_ENV" in os.environ:
        with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as env_file:
            env_file.write(f"ANALYZER_STATUS={status}\n")
