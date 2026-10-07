#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module journal-notify.py
@about Управляющий диспетчер буферного шлюза
@purpose Управление блокировками, фиксация папок через Git и контроль очистки шлюза
@author TechLab
@version 7.0.0
"""

import os
import sys
import time
import requests
import subprocess

# ==============================================================================
# КОНФИГУРАЦИЯ ВНЕШНИХ ИНТЕРНЕТ-АДРЕСОВ GITHUB API
# ==============================================================================
SITE_API_URL = "https://api.github.com/repos/eaststandart/eaststandart.github.io/dispatches"
CHECK_URL = "https://api.github.com/repos/eaststandart/techlab-journal-attendance/contents/_output"

def run_control_pipeline():
    print("\n=== [МОДУЛЬ JOURNAL-NOTIFY] ЗАПУСК УПРАВЛЯЮЩЕГО ДИСПЕТЧЕРА ===")
    
    output_dir = os.path.join(os.getcwd(), '_output')
    if not os.path.exists(output_dir):
        print(f"[ДИСПЕТЧЕР] ❌ Ошибка: Директория вывода не найдена: {output_dir}")
        return

    # 1. ПРОВЕРКА НАЛИЧИЯ ФАЙЛОВ JSON В ДИРЕКТОРИИ _output НА СТАРТЕ
    live_output_json = [f for f in os.listdir(output_dir) if f.endswith('.json')]
    if live_output_json:
        print(f"[ДИСПЕТЧЕР] В _output файлы: {live_output_json}. К поиску в _input не переходим.")
        return

    print("[ДИСПЕТЧЕР] В директории _output пусто. Переходим к анализу.")

    # 2. ЗАПУСК ИЗОЛИРОВАННОГО МОДУЛЯ АНАЛИЗА ФАЙЛОВ
    print("[ДИСПЕТЧЕР] Запуск модуля 'journal-analyzer.py'...")
    result = subprocess.run(["python", "_actions/journal-analyzer.py"], capture_output=True, text=True)
    print(result.stdout)
    
    analyzer_status = "NO_BUNDLE_READY"
    for line in result.stdout.split('\n'):
        if "Финальный статус работы модуля:" in line:
            analyzer_status = line.split(":")[-1].strip()

    if not analyzer_status.startswith("SUCCESS_"):
        print(f"[ДИСПЕТЧЕР] Модуль анализа не выявил готовых комплектов. Статус: {analyzer_status}")
        return

    teacher_login = analyzer_status.replace("SUCCESS_", "").strip()
    print(f"[ДИСПЕТЧЕР] Обнаружен готовый комплект для преподавателя: '{teacher_login}'")

    # 3. ФИКСАЦИЯ ИЗМЕНЕНИЙ ПАПОК В РЕПОЗИТОРИИ (GIT PUSH)
    try:
        subprocess.run(["git", "config", "--global", "user.name", "TechLab Notifier Bot"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "notifier@techlab.local"], check=True)
        subprocess.run(["git", "add", "_input/", "_output/"], check=True)
        
        diff_check = subprocess.run(["git", "diff", "--cached", "--quiet"])
        if diff_check.returncode != 0:
            subprocess.run(["git", "commit", "-m", f"Фиксация: перенос комплекта для {teacher_login} в _output"], check=True)
            # ОБНОВЛЕНИЕ ИСТОРИИ ПЕРЕД ПУШЕМ ДЛЯ ИСКЛЮЧЕНИЯ ОТКАЗА [rejected]
            subprocess.run(["git", "pull", "origin", "main", "--rebase"], check=True)
            subprocess.run(["git", "push", "origin", "main"], check=True)
            print("[ДИСПЕТЧЕР] Изменения папок записаны в историю Гитхаба.")
        else:
            print("[ДИСПЕТЧЕР] Изменений в репозитории не обнаружено. Отмена отправки сигнала.")
            return
            
    except Exception as err:
        print(f"[ДИСПЕТЧЕР] ❌ Ошибка выполнения команд Git: {str(err)}")
        return

    # 4. ОТПРАВКА СИГНАЛА НА ОСНОВНОЙ САЙТ ЧЕРЕЗ GITHUB REST API
    fine_token = os.environ.get("MY_FINE_TOKEN")
    if not fine_token:
        print("[ДИСПЕТЧЕР] ❌ Ошибка: Ключ MY_FINE_TOKEN не найден в секретах репозитория.")
        return

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {fine_token}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    payload = {"event_type": "journal-notify"}

    try:
        response = requests.post(SITE_API_URL, json=payload, headers=headers)
        if response.status_code != 204:
            print(f"[ДИСПЕТЧЕР] ⚠️ Ошибка отправки сигнала. Код ответа сервера: {response.status_code}")
            return
        print("[ДИСПЕТЧЕР] Сигнал передан в репозиторий eaststandart.github.io.")
    except Exception as err:
        print(f"[ДИСПЕТЧЕР] ❌ Исключение при отправке сигнала: {str(err)}")
        return

    # 5. ЦИКЛИЧЕСКОЕ ОЖИДАНИЕ ОЧИСТКИ ШЛЮЗА С АВАРИЙНОЙ ПАУЗОЙ НА 1 ЧАС
    print(f"[ДИСПЕТЧЕР] Ожидание удаления файлов из _output для '{teacher_login}'. Интервал: 60 сек.")

    start_time = time.time()
    check_counter = 0
    
    headers_check = {
        "Authorization": f"token {fine_token}",
        "Accept": "application/vnd.github+json",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }

    while True:
        check_counter += 1
        print(f"\n[ДИСПЕТЧЕР] Проверка №{check_counter} (Время: {int(time.time() - start_time)} сек.)")
        print("[ДИСПЕТЧЕР] Делаем запрос к API techlab-journal-attendance для проверки удаления файлов.")

        try:
            response_check = requests.get(CHECK_URL, headers=headers_check)
            
            if response_check.status_code >= 500:
                print(f"[ДИСПЕТЧЕР] ❌ Ошибка сервера GitHub API: {response_check.status_code}. Пауза 1 час.")
                time.sleep(3600)
                continue

            if response_check.status_code == 200:
                output_contents = response_check.json()
                live_files = [item["name"] for item in output_contents if item["name"].endswith('.json')]
                if not live_files:
                    print("[ДИСПЕТЧЕР] Папка _output опустела.")
                    break
                else:
                    print(f"[ДИСПЕТЧЕР] Директория содержит файлы ({len(live_files)} шт.): {live_files}")
            elif response_check.status_code == 404:
                print("[ДИСПЕТЧЕР] Ответ API: 404. Директория вывода очищена.")
                break
            else:
                print(f"[ДИСПЕТЧЕР] ⚠️ Нетипичный ответ API: {response_check.status_code}. Пауза 1 час.")
                time.sleep(3600)
                continue

        except Exception as check_err:
            print(f"[ДИСПЕТЧЕР] ❌ Сетевой сбой API: {str(check_err)}. Пауза 1 час.")
            time.sleep(3600)
            continue

        time.sleep(60)

    # 6. УСПЕШНОЕ ЗАВЕРШЕНИЕ
    print("\n[ДИСПЕТЧЕР] Процесс контроля успешно завершён.")

if __name__ == "__main__":
    run_control_pipeline()
