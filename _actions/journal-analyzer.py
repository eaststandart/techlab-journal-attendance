#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module journal-analyzer.py
@about Изолированный математический модуль проверки комплектности журналов
@purpose Группировка файлов по датам и дням недели, сверка с YAML-расписанием
@version 1.0.0
"""

import os
import json
import re
import sys
import yaml
import shutil

def analyze_and_move_bundle():
    print("\n=== [МОДУЛЬ JOURNAL_ANALYZER] АНАЛИЗ ПРИЁМНОЙ ПАПКИ ===")
    
    input_dir = os.path.join(os.getcwd(), '_input')
    output_dir = os.path.join(os.getcwd(), '_output')
    data_dir = os.path.join(os.getcwd(), '_data')
    
    # 1. СКАНИРОВАНИЕ ДИРЕКТОРИИ ВХОДНЫХ ДАННЫХ
    if not os.path.exists(input_dir):
        print(f"[АНАЛИЗАТОР] ❌ КРИТИЧЕСКАЯ ОШИБКА: Директория не найдена: {input_dir}")
        return "ERROR_NO_INPUT_DIR"

    all_files = os.listdir(input_dir)
    json_files = [f for f in all_files if '-journal-attendance-' in f and f.endswith('.json')]
    
    if not json_files:
        print("[АНАЛИЗАТОР] ЛОГ: В директории _input отсутствуют временные файлы JSON.")
        return "NO_FILES"

    print(f"[АНАЛИЗАТОР] ЛОГ: Обнаружено файлов JSON в очереди: {len(json_files)} шт.")

    # Сбор списка активных преподавателей по файлам расписаний из папки _data
    active_teachers = []
    for f in os.listdir(data_dir):
        if f.startswith('journal-attendance-') and f.endswith('.yml'):
            login = f.replace('journal-attendance-', '').replace('.yml', '').strip().lower()
            if login:
                active_teachers.append(login)

    # 2. ИЗОЛИРОВАННАЯ ГРУППИРОВКА ФАЙЛОВ ПО ПРЕПОДАВАТЕЛЯМ И КАЛЕНДАРНЫМ ДАТАМ
    for teacher_login in active_teachers:
        teacher_files = [f for f in json_files if f.lower().endswith(f"-journal-attendance-{teacher_login}.json")]
        
        if not teacher_files:
            continue

        # Раскладываем файлы текущего преподавателя по календарным датам
        date_groups = {}
        for file_name in teacher_files:
            file_path = os.path.join(input_dir, file_name)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                
                file_date = file_data.get('date', '').strip()
                file_day = file_data.get('day', '').strip().lower()
                
                if not file_date or not file_day:
                    print(f"[АНАЛИЗАТОР] ⚠️ Предупреждение: В файле {file_name} отсутствуют обязательные поля date или day.")
                    continue
                    
                if file_date not in date_groups:
                    date_groups[file_date] = {
                        "day_name": file_day,
                        "files": []
                    }
                date_groups[file_date]["files"].append(file_name)
                
            except Exception as e:
                print(f"[АНАЛИЗАТОР] ❌ Ошибка чтения файла {file_name}: {str(e)}")
                continue

        print(f"[АНАЛИЗАТОР] ЛОГ: Для преподавателя '{teacher_login}' сформировано изолированных дат: {list(date_groups.keys())}")

        # 3. ПООЧЕРЕДНАЯ ПРОВЕРКА КОМПЛЕКТНОСТИ КАЖДОЙ ИЗОЛИРОВАННОЙ ДАТЫ
        for target_date, group_data in date_groups.items():
            target_day = group_data["day_name"]
            bundle_files = group_data["files"]
            
            print(f"\n[АНАЛИЗАТОР] 👉 Проверка даты '{target_date}' ({target_day}) для '{teacher_login}'. Файлов в кучке: {len(bundle_files)} шт.")

            # Читаем YAML расписание этого учителя строго из папки _data
            yaml_path = os.path.join(data_dir, f"journal-attendance-{teacher_login}.yml")
            if not os.path.exists(yaml_path):
                print(f"[АНАЛИЗАТОР] ⚠️ Расписание не найдено в _data: {yaml_path}. Пропуск даты.")
                continue

            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    yaml_data = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"[АНАЛИЗАТОР] ❌ Ошибка парсинга YAML для {teacher_login}: {str(e)}")
                continue

            # Вычисляем сколько групп запланировано по YAML на этот день недели
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
            print(f"[АНАЛИЗАТОР] План расписания по YAML для '{teacher_login}' на '{target_day}': {schedule_groups} (Всего: {len(schedule_groups)})")

            # ПРОВЕРКА СООТВЕТСТВИЯ КОЛИЧЕСТВА ФАЙЛОВ ПЛАНУ РАСПИСАНИЯ
            if len(bundle_files) < len(schedule_groups):
                print(f"[АНАЛИЗАТОР] ⏳ КОМПЛЕКТ НЕ СОБРАН: Для даты '{target_date}' готово только {len(bundle_files)} из {len(schedule_groups)} групп. Оставляем в _input.")
                continue

            # УСЛОВИЕ УСПЕХА ВЫПОЛНЕНО: ФИЗИЧЕСКИЙ ПЕРЕНОС И ПРЕКРАЩЕНИЕ АНАЛИЗА ВХОДА
            print(f"[АНАЛИЗАТОР] 🔥 ПОЛНЫЙ КОМПЛЕКТ НАЙДЕН ДЛЯ '{teacher_login}' ЗА ДАТУ '{target_date}' ({len(bundle_files)} из {len(schedule_groups)})!")
            print(f"[АНАЛИЗАТОР] Действие: Перемещаем комплект файлов в шлюз вывода _output...")
            
            for file_name in bundle_files:
                old_file_path = os.path.join(input_dir, file_name)
                new_file_path = os.path.join(output_dir, file_name)
                shutil.move(old_file_path, new_file_path)
                print(f"[АНАЛИЗАТОР] 📦 Перемещён: '{file_name}' ➔ _output/")

            print(f"[АНАЛИЗАТОР] 🛑 ТОТАЛЬНОЕ ЗАМИРАНИЕ: Комплект сформирован. Анализ папки Вход принудительно остановлен.")
            # Возвращаем управляющему скрипту строку с логином успешного учителя
            return f"SUCCESS_{teacher_login}"

    print("\n[АНАЛИЗАТОР] ЛОГ: Ни одного полного комплекта журналов среди всех дат и учителей не обнаружено.")
    return "NO_BUNDLE_READY"

if __name__ == "__main__":
    # Вызываем функцию анализа и возвращаем текстовый статус в системную консоль сервера
    status = analyze_and_move_bundle()
    print(f"[АНАЛИЗАТОР] Финальный статус работы модуля: {status}")
    # Передаем статус в файл окружения GitHub Actions для управляющего скрипта
    if "GITHUB_ENV" in os.environ:
        with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as env_file:
            env_file.write(f"ANALYZER_STATUS={status}\n")
