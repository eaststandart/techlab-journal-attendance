#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module journal-notify.py
@about Умный шлюзовой будильник TechLab Journal Attendance
@purpose Логика буферного шлюза (_input -> _output) с защитой от гонки сигналов
@version 3.0.0
"""

import os
import json
import re
import sys
import yaml
import requests
import shutil

def run_notifier():
    print("\n=== [МОДУЛЬ JOURNAL_NOTIFY] ЗАПУСК БУФЕРНОГО ШЛЮЗА ===")
    
    # Инициализируем пути ко всем трем изолированным папкам
    input_dir = os.path.join(os.getcwd(), '_input')
    output_dir = os.path.join(os.getcwd(), '_output')
    data_dir = os.path.join(os.getcwd(), '_data') # Здесь лежат только YML расписания
    
    # Проверяем физическое наличие папок на сервере
    for folder in [input_dir, output_dir, data_dir]:
        if not os.path.exists(folder):
            print(f"[ШЛЮЗ] ❌ КРИТИЧЕСКАЯ ОШИБКА: Папка не найдена на диске: {folder}")
            return

    # === ШАГ А: ЖЕСТКАЯ ПРОВЕРКА ЗАНЯТОСТИ ЧИСТОЙ ЗОНЫ ВЫВОДА (_output) ===
    print("[ШЛЮЗ] ЛОГ ШАГА А: Проверяем состояние шлюза вывода _output...")
    
    all_output_files = os.listdir(output_dir)
    # Игнорируем технический файл-заглушку .gitkeep при подсчете
    live_output_json = [f for f in all_output_files if f.endswith('.json')]
    
    if live_output_json:
        print(f"[ШЛЮЗ] ⛔ ШЛЮЗ ЗАНЯТ! В папке _output обнаружены обрабатываемые файлы ({len(live_output_json)} шт.):")
        print(f"[ШЛЮЗ] ⛔ Список занятых файлов: {live_output_json}")
        print("[ШЛЮЗ] ℹ️ Лог: Предыдущий отчёт ещё собирается на сайте. Новые файлы остаются ждать в _input.")
        print("[ШЛЮЗ] 🛑 Отмена запуска. Сетевой сигнал dispatches на сайт заблокирован.")
        return

    print("[ШЛЮЗ] ЛОГ ШАГА А: 🟢 Шлюз вывода _output идеально чист! Проверка занятости успешна.")

    # === ШАГ Б: РАЗВЕДКА В ПРИЁМНОЙ ЗОНЕ (_input) ===
    print("\n[ШЛЮЗ] ЛОГ ШАГА Б: Сканируем приёмный покой _input на наличие сырых JSON...")
    
    all_input_files = os.listdir(input_dir)
    json_files = [f for f in all_input_files if '-journal-attendance-' in f and f.endswith('.json')]
    
    if not json_files:
        print("[ШЛЮЗ] ℹ️ Лог: В папке _input нет ни одного временного файла JSON. Отмена.")
        return

    print(f"[ШЛЮЗ] ЛОГ ШАГА Б: Всего в приёмнике обнаружено сырых файлов JSON: {len(json_files)} шт.")

    # Вытаскиваем список активных учителей по файлам расписаний из папки _data
    active_teachers = []
    for f in os.listdir(data_dir):
        if f.startswith('journal-attendance-') and f.endswith('.yml'):
            login = f.replace('journal-attendance-', '').replace('.yml', '').strip().lower()
            if login:
                active_teachers.append(login)

    print(f"[ШЛЮЗ] ЛОГ ШАГА Б: Обнаружено активных расписаний учителей в базе: {active_teachers}")

    # Заводим флаг, который покажет, удалось ли собрать хотя бы один полный комплект
    any_bundle_copied = False
    copied_teacher_login = None

    # ЗАПУСКАЕМ ПЕРЕБОР КУЧЕК ПРЕПОДАВАТЕЛЕЙ
    for teacher_login in active_teachers:
        # Отбираем файлы из папки _input строго для текущего учителя
        teacher_json_files = [f for f in json_files if f.lower().endswith(f"-journal-attendance-{teacher_login}.json")]
        
        if not teacher_json_files:
            continue

        print(f"\n👉 [ШЛЮЗ ЦИКЛА] Анализируем прилетевшие файлы для: '{teacher_login}' ({len(teacher_json_files)} шт.)")

        # Читаем день недели из первого попавшегося файла этого конкретного учителя
        sample_path = os.path.join(input_dir, teacher_json_files[0])
        try:
            with open(sample_path, 'r', encoding='utf-8') as f:
                sample_data = json.load(f)
            target_day = sample_data.get('day', '').strip().lower()
            teacher_username = sample_data.get('teacher_username', 'Преподаватель')
        except Exception as e:
            print(f"[ШЛЮЗ] ⚠️ Ошибка чтения файла {teacher_json_files[0]}: {str(e)}")
            continue

        if not target_day:
            print(f"[ШЛЮЗ] ⚠️ Ошибка: В файле {teacher_json_files[0]} не найден день недели day.")
            continue

        # Читаем YAML расписание этого учителя строго из папки _data
        yaml_path = os.path.join(data_dir, f"journal-attendance-{teacher_login}.yml")
        if not os.path.exists(yaml_path):
            print(f"[ШЛЮЗ] ⚠️ Расписание не найдено в _data: {yaml_path}. Пропуск.")
            continue

        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"[ШЛЮЗ] ⚠️ Ошибка парсинга YAML для {teacher_login}: {str(e)}")
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
        print(f"[ШЛЮЗ] 👤 Учитель: '{teacher_username}' ({teacher_login}), День: '{target_day}'")
        print(f"[ШЛЮЗ] План по расписанию YML: {schedule_groups} (Всего: {len(schedule_groups)})")

        # ПРОВЕРКА КОМПЛЕКТНОСТИ ДЛЯ ТЕКУЩЕГО УЧИТЕЛЯ В ПАПКЕ _input
        if len(teacher_json_files) < len(schedule_groups):
            print(f"[ШЛЮЗ] ⏳ КОМПЛЕКТ НЕ СОБРАН: Готово только {len(teacher_json_files)} из {len(schedule_groups)} групп. Оставляем лежать в _input.")
            continue

        # ЕСЛИ ПОЛНЫЙ КОМПЛЕКТ НАЙДЕН — ФИЗИЧЕСКИ ПЕРЕМЕЩАЕМ В _output!
        print(f"[ШЛЮЗ] 🔥 ПОЛНЫЙ КОМПЛЕКТ СОБРАН ДЛЯ '{teacher_login}' ({len(teacher_json_files)} из {len(schedule_groups)})!")
        print(f"[ШЛЮЗ] Перемещаем файлы этого учителя из _input в чистую зону _output...")
        
        for file_name in teacher_json_files:
            old_file_path = os.path.join(input_dir, file_name)
            new_file_path = os.path.join(output_dir, file_name)
            shutil.move(old_file_path, new_file_path)
            print(f"[ШЛЮЗ] 📦 Файл перемещён: '{file_name}' ➔ _output/")

        any_bundle_copied = True
        copied_teacher_login = teacher_login
        # Прерываем цикл по учителям на сегодня: за раз переносим и запускаем строго одну готовую смену!
        break

    # === ШАГ В: ОДИНОЧНЫЙ ВЫСТРЕЛ БУДИЛЬНИКА ===
    if not any_bundle_copied:
        print("\n[ШЛЮЗ] ЛОГ ШАГА В: Ни одного готового комплекта в папке _input не собрано. Робот сайта отдыхает.")
        return

    fine_token = os.environ.get("MY_FINE_TOKEN")
    if not fine_token:
        print(f"[ШЛЮЗ] ❌ КРИТИЧЕСКАЯ ОШИБКА: Авторизационный ключ MY_FINE_TOKEN не найден в секретах!")
        return

    print(f"\n[ШЛЮЗ] ЛОГ ШАГА В: Чистая зона _output успешно заряжена отчётом '{copied_teacher_login}'.")
    print("[ШЛЮЗ] Отправляем ровно 1 точечный POST импульс dispatches на основной сайт...")
    
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
            print(f"[ШЛЮЗ] 🚀 [УСПЕХ] Будильник сработал! Сайт вызван для обработки отчёта '{copied_teacher_login}' строго в один поток.")
        else:
            print(f"[ШЛЮЗ] ⚠️ Гитхаб принял запрос, но статус не 204: {response.status_code}")
            
    except Exception as err:
        print(f"[ШЛЮЗ] ❌ Исключение при отправке dispatches на сайт: {str(err)}")

# ТОЧКА ТРИГГЕРА ВХОДА ДЛЯ ЗАПУСКА СЕРВЕРОМ ЖУРНАЛА
if __name__ == "__main__":
    run_notifier()
