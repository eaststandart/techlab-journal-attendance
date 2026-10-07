#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module journal-notify.py
@about Умный межрепозиторный будильник TechLab (Всеядная группировка)
@purpose Проверка комплектности по каждому учителю отдельно и отправка точечных сигналов
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

    # 1. СКАНИРУЕМ ПАПКУ И НАХОДИМ ВСЕ ЖИВЫЕ YAML РАСПИСАНИЯ
    all_files = os.listdir(data_dir)
    active_teachers = []
    for f in all_files:
        if f.startswith('journal-attendance-') and f.endswith('.yml'):
            login = f.replace('journal-attendance-', '').replace('.yml', '').strip().lower()
            if login:
                active_teachers.append(login)

    print(f"[УВЕДОМИТЕЛЬ] ЛОГ: Список активных учителей из базы YML: {active_teachers}")

    # 2. СОБИРАЕМ ВСЕ ПРИЛЕТЕВШИЕ JSON-ФАЙЛЫ ГРУПП
    json_files = [f for f in all_files if '-journal-attendance-' in f and f.endswith('.json')]
    if not json_files:
        print("[УВЕДОМИТЕЛЬ] ℹ️ Лог: Временные файлы журналов JSON отсутствуют. Отмена.")
        return

    print(f"[УВЕДОМИТЕЛЬ] ЛОГ: Всего в папке обнаружено JSON-файлов: {len(json_files)} шт.")

    # Проверяем наличие токена перед циклом
    fine_token = os.environ.get("MY_FINE_TOKEN")
    if not fine_token:
        print("[УВЕДОМИТЕЛЬ] ❌ КРИТИЧЕСКАЯ ОШИБКА: Ключ MY_FINE_TOKEN не найден в секретах!")
        return

    # 3. ЗАПУСКАЕМ ИЗОЛИРОВАННЫЙ ЦИКЛ ПРОВЕРКИ ДЛЯ КАЖДОГО УЧИТЕЛЯ ОТДЕЛЬНО
    for teacher_login in active_teachers:
        # Отбираем файлы группы строго для текущего учителя
        teacher_json_files = [f for f in json_files if f.lower().endswith(f"-journal-attendance-{teacher_login}.json")]
        
        if not teacher_json_files:
            continue

        print(f"\n👉 [ЦИКЛ ПРОВЕРКИ] Анализируем файлы для учителя: '{teacher_login}' ({len(teacher_json_files)} шт.)")

        # Читаем день недели из первого попавшегося файла этого учителя
        sample_path = os.path.join(data_dir, teacher_json_files[0])
        try:
            with open(sample_path, 'r', encoding='utf-8') as f:
                sample_data = json.load(f)
            target_day = sample_data.get('day', '').strip().lower()
        except Exception as e:
            print(f"[УВЕДОМИТЕЛЬ] ⚠️ Ошибка чтения файла {teacher_json_files[0]}: {str(e)}")
            continue

        if not target_day:
            print(f"[УВЕДОМИТЕЛЬ] ⚠️ Ошибка: В файле {teacher_json_files[0]} не найден день недели day.")
            continue

        # Читаем YAML расписание этого учителя
        yaml_path = os.path.join(data_dir, f"journal-attendance-{teacher_login}.yml")
        if not os.path.exists(yaml_path):
            print(f"[УВЕДОМИТЕЛЬ] ⚠️ Расписание не найдено: {yaml_path}. Пропуск.")
            continue

        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"[УВЕДОМИТЕЛЬ] ⚠️ Ошибка парсинга YAML для {teacher_login}: {str(e)}")
            continue

        # Считаем группы в YAML на этот день недели
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
        print(f"[УВЕДОМИТЕЛЬ] План расписания для '{teacher_login}' на день '{target_day}': {schedule_groups} (Всего: {len(schedule_groups)})")

        # ПРОВЕРКА КОМПЛЕКТНОСТИ ДАННОГО УЧИТЕЛЯ
        if len(teacher_json_files) < len(schedule_groups):
            print(f"[УВЕДОМИТЕЛЬ] ⏳ КОМПЛЕКТ НЕ СОБРАН: У учителя '{teacher_login}' готово {len(teacher_json_files)} из {len(schedule_groups)} групп. Сигнал заблокирован.")
            continue

        # Если комплект собран — отправляем точечный сигнал пробуждения сайта строго для этого шага
        print(f"[УВЕДОМИТЕЛЬ] 🔥 ПОЛНЫЙ КОМПЛЕКТ СОБРАН ДЛЯ '{teacher_login}' ({len(teacher_json_files)} из {len(schedule_groups)})!")
        print(f"[УВЕДОМИТЕЛЬ] Отправляем точечный импульс dispatches на основной сайт...")
        
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
            print(f"[УВЕДОМИТЕЛЬ] Статус-код ответа сервера GitHub API: {response.status_code}")
            if response.status_code == 204:
                print(f"[УВЕДОМИТЕЛЬ] 🚀 [УСПЕХ] Будильник сработал! Сайт вызван для обработки отчётов.")
            else:
                print(f"[УВЕДОМИТЕЛЬ] ⚠️ Ответ сервера: {response.status_code}")
        except Exception as err:
            print(f"[УВЕДОМИТЕЛЬ] ❌ Ошибка сети dispatches: {str(err)}")

if __name__ == "__main__":
    run_notifier()
