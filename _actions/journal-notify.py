#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module journal-notify.py
@about Умный межрепозиторный будильник TechLab Journal Attendance
@purpose Проверка комплектности Журналов посещаемости и отправка точечного сигнала dispatches
@author  TechLab
@version 1.0.0
"""

import os
import json
import re
import sys
import yaml
import requests

def run_notifier():
    print("\n=== [МОДУЛЬ JOURNAL_NOTIFY] ЗАПУСК УМНОГО КАНАЛА СВЯЗИ ===")
    
    data_dir = os.path.join(os.getcwd(), '_data')
    if not os.path.exists(data_dir):
        print(f"[УВЕДОМИТЕЛЬ] ❌ КРИТИЧЕСКАЯ ОШИБКА: Папка с данными не найдена: {data_dir}")
        return

    # 1. СКАНИРУЕМ ПАПКУ И НАХОДИМ ВСЕ JSON ФАЙЛЫ
    all_files = os.listdir(data_dir)
    json_files = [f for f in all_files if '-journal-attendance-' in f and f.endswith('.json')]
    
    if not json_files:
        print("[УВЕДОМИТЕЛЬ] ℹ️ Лог: В папке _data нет ни одного временного файла JSON. Отмена.")
        return

    print(f"[УВЕДОМИТЕЛЬ] ЛОГ ШАГА 1: Найдено временных файлов JSON в очереди: {len(json_files)} шт.")
    print(f"[УВЕДОМИТЕЛЬ] ЛОГ ШАГА 1: Список всех файлов в папке: {json_files}")

    # 2. ОПРЕДЕЛЯЕМ АВТОРА ПО ПОСЛЕДНЕМУ ПРИЛЕТЕВШЕМУ ФАЙЛУ
    sample_file = json_files[0]
    sample_path = os.path.join(data_dir, sample_file)
    
    print(f"[УВЕДОМИТЕЛЬ] ЛОГ ШАГА 2: Читаем структуру файла-образца: '{sample_file}'")
    try:
        with open(sample_path, 'r', encoding='utf-8') as f:
            sample_data = json.load(f)
    except Exception as e:
        print(f"[УВЕДОМИТЕЛЬ] ❌ Ошибка чтения файла {sample_file}: {str(e)}")
        return

    teacher_login = sample_data.get('teacher_login', '').strip().lower()
    teacher_username = sample_data.get('teacher_username', 'Преподаватель')
    target_day = sample_data.get('day', '').strip().lower()

    if not teacher_login or not target_day:
        print("[УВЕДОМИТЕЛЬ] ❌ Ошибка: В JSON-файле отсутствуют поля teacher_login или day!")
        return

    print(f"[УВЕДОМИТЕЛЬ] ЛОГ ШАГА 2: Данные определены успешно.")
    print(f"[УВЕДОМИТЕЛЬ] 👤 Преподаватель: '{teacher_username}' (логин: {teacher_login})")
    print(f"[УВЕДОМИТЕЛЬ] 📅 День недели: '{target_day}'")

    # 3. ОТБИРАЕМ JSON-ФАЙЛЫ СТРОГО ТЕКУЩЕГО ПРЕПОДАВАТЕЛЯ
    teacher_json_files = [f for f in json_files if f.lower().endswith(f"-journal-attendance-{teacher_login}.json")]
    print(f"[УВЕДОМИТЕЛЬ] ЛОГ ШАГА 3: Из общей кучи отобрано файлов для '{teacher_login}': {len(teacher_json_files)} шт.")
    print(f"[УВЕДОМИТЕЛЬ] ЛОГ ШАГА 3: Список файлов учителя: {teacher_json_files}")

    # 4. ЧИТАЕМ YAML РАСПИСАНИЕ И СЧИТАЕМ ПЛАН ГРУПП НА СЕГОДНЯ
    yaml_path = os.path.join(data_dir, f"journal-attendance-{teacher_login}.yml")
    if not os.path.exists(yaml_path):
        print(f"[УВЕДОМИТЕЛЬ] ❌ КРИТИЧЕСКАЯ ОШИБКА: Личный YAML-файл расписания не найден: {yaml_path}")
        return

    print(f"[УВЕДОМИТЕЛЬ] ЛОГ ШАГА 4: Открываем базу расписания '{yaml_path}'...")
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            yaml_data = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"[УВЕДОМИТЕЛЬ] ❌ Ошибка парсинга YAML: {str(e)}")
        return

    # Восстанавливаем структуру расписания, чтобы посчитать количество групп
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

    # Определяем сколько групп запланировано на этот день недели
    schedule_groups = sorted(list(students_data.get(target_day, {}).keys()))
    print(f"[УВЕДОМИТЕЛЬ] ЛОГ ШАГА 4: По плану расписания на день '{target_day}' у учителя {len(schedule_groups)} групп: {schedule_groups}")

    # 5. СРАВНИВАЕМ ПЛАН И ФАКТ (СДЕРЖИВАЮЩИЙ ЩИТ ОТ СПАМА СИГНАЛОВ)
    if len(teacher_json_files) < len(schedule_groups):
        print(f"[УВЕДОМИТЕЛЬ] ⏳ КОМПЛЕКТ НЕ СОБРАН: У учителя '{teacher_login}' готово только {len(teacher_json_files)} из {len(schedule_groups)} групп.")
        print("[УВЕДОМИТЕЛЬ] ℹ️ Лог: Робот сайта отдыхает. Сигнал dispatches блокируется до прилёта остальных файлов.")
        return

    print(f"[УВЕДОМИТЕЛЬ] 🔥 ПОЛНЫЙ КОМПЛЕКТ СОБРАН ({len(teacher_json_files)} из {len(schedule_groups)})! Даём зелёный свет сигналу...")

    # 6. ОТПРАВКА ОДНОКРАТНОГО ТРИГГЕРА НА ОСНОВНОЙ САЙТ ЧЕРЕЗ GITHUB REST API
    fine_token = os.environ.get("MY_FINE_TOKEN")
    if not fine_token:
        print("[УВЕДОМИТЕЛЬ] ❌ КРИТИЧЕСКАЯ ОШИБКА: Авторизационный ключ MY_FINE_TOKEN не найден в секретах Журнала!")
        return

    print(f"[УВЕДОМИТЕЛЬ] ЛОГ ШАГА 6: Готовим точечный POST импульс dispatches на основной сайт...")
    
    # Служебный адрес API роботов для dispatches основного сайта (://github.com)
    site_api_url = "https://api.github.com/repos/eaststandart/eaststandart.github.io/dispatches"
    
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {fine_token}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    payload = {
        "event_type": "journal-notify"
    }

    try:
        response = requests.post(site_api_url, json=payload, headers=headers)
        print("=================== ЛОГ ОТВЕТА СЕРВЕРА GITHUB API ===================")
        print(f"Статус-код ответа API: {response.status_code}")
        if response.text:
            print(f"Текст ответа API: {response.text}")
        print("====================================================================")
        
        if response.status_code == 204:
            print(f"[УВЕДОМИТЕЛЬ] 🚀 [УСПЕХ] Точечный сигнал отправлен! Робот сайта вызван в один поток.")
        else:
            print(f"[УВЕДОМИТЕЛЬ] ⚠️ Гитхаб принял запрос, но статус не 204: {response.status_code}")
            
    except Exception as err:
        print(f"[УВЕДОМИТЕЛЬ] ❌ Исключение при отправке dispatches: {str(err)}")

# ТОЧКА ТРИГГЕРА ВХОДА ДЛЯ ЗАПУСКА СЕРВЕРОМ ЖУРНАЛА
if __name__ == "__main__":
    run_notifier()
