#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module journal-notify.py
@about Управляющий диспетчер буферного шлюза
@purpose Управление блокировками, фиксация папок через Git и контроль очистки шлюза
@version 5.0.0
"""

import os
import sys
import time
import requests
import subprocess

# ==============================================================================
# УПРАВЛЯЮЩИЙ ТУМБЛЕР РЕЖИМА ПРОВЕРКИ ОЧИСТКИ ШЛЮЗА: "CONTENTS" ИЛИ "COMMIT"
# ==============================================================================
CHECK_MODE = "CONTENTS"

def run_control_pipeline():
    print("\n=== [МОДУЛЬ JOURNAL_NOTIFY] ЗАПУСК УПРАВЛЯЮЩЕГО ДИСПЕТЧЕРА ===")
    
    output_dir = os.path.join(os.getcwd(), '_output')
    if not os.path.exists(output_dir):
        print(f"[ДИСПЕТЧЕР] ❌ Ошибка: Директория вывода не найдена: {output_dir}")
        return

    # 1. ПРОВЕРКА СОСТОЯНИЯ ДИРЕКТОРИИ _output НА СТАРТЕ
    live_output_json = [f for f in os.listdir(output_dir) if f.endswith('.json')]
    if live_output_json:
        print(f"[ДИСПЕТЧЕР] Директория _output содержит файлы ({len(live_output_json)} шт.). Работа конвейера остановлена.")
        return

    print("[ДИСПЕТЧЕР] Директория _output чистая. Конвейер готов к работе.")

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
            subprocess.run(["git", "commit", "-m", f"chore: фиксация переноса комплекта для {teacher_login} в папку выход"], check=True)
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

    site_api_url = "https://api.github.com/repos/eaststandart/eaststandart.github.io/dispatches"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {fine_token}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    payload = {"event_type": "journal-notify"}

    try:
        response = requests.post(site_api_url, json=payload, headers=headers)
        if response.status_code != 204:
            print(f"[ДИСПЕТЧЕР] ⚠️ Ошибка отправки сигнала. Код ответа сервера: {response.status_code}")
            return
        print(f"[ДИСПЕТЧЕР] Одиночный сигнал успешно отправлен. Робот сайта вызван.")
    except Exception as err:
        print(f"[ДИСПЕТЧЕР] ❌ Исключение при отправке сигнала: {str(err)}")
        return

    # 5. ЦИКЛИЧЕСКОЕ ЕЖЕМИНУТНОЕ ОЖИДАНИЕ ОЧИСТКИ ШЛЮЗА
    print(f"[ДИСПЕТЧЕР] Включение режима ожидания очистки шлюза для '{teacher_login}'. Интервал: 60 секунд.")
    print(f"[ДИСПЕТЧЕР] Активный режим контроля: '{CHECK_MODE}'")

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
        print(f"\n[ДИСПЕТЧЕР] Круг проверки №{check_counter} (Прошло времени: {int(time.time() - start_time)} сек.)")

        # РЕЖИМ КОНТРОЛЯ ПО СОДЕРЖИМОМУ ДИРЕКТОРИИ
        if CHECK_MODE == "CONTENTS":
            check_url = "https://api.github.com/repos/eaststandart/techlab-journal-attendance/contents/_output"
            try:
                check_res = requests.get(check_url, headers=headers_check)
                if check_res.status_code == 200:
                    output_contents = check_res.json()
                    live_files = [item["name"] for item in output_contents if item["name"].endswith('.json')]
                    if not live_files:
                        print("[ДИСПЕТЧЕР] Директория вывода опустела.")
                        break
                    else:
                        print(f"[ДИСПЕТЧЕР] Директория содержит файлы ({len(live_files)} шт.): {live_files}")
                elif check_res.status_code == 404:
                    print("[ДИСПЕТЧЕР] Код ответа 404. Директория вывода удалена (очищена).")
                    break
            except Exception as check_err:
                print(f"[ДИСПЕТЧЕР] Ошибка запроса к API директории: {str(check_err)}")

        # РЕЗЕРВНЫЙ РЕЖИМ КОНТРОЛЯ ПО ТЕКСТУ КОММИТОВ ИСТОРИИ ИЗМЕНЕНИЙ
        elif CHECK_MODE == "COMMIT":
            commits_url = "https://api.github.com/repos/eaststandart/techlab-journal-attendance/commits"
            try:
                commits_res = requests.get(commits_url, headers=headers_check)
                if commits_res.status_code == 200:
                    last_commit = commits_res.json()[0]
                    commit_message = last_commit.get("commit", {}).get("message", "")
                    print(f"[ДИСПЕТЧЕР] Текст последнего коммита в истории: '{commit_message}'")
                    
                    if "cleanup" in commit_message.lower() or "удаление" in commit_message.lower():
                        print("[ДИСПЕТЧЕР] Обнаружен коммит очистки репозитория.")
                        break
                    else:
                        print("[ДИСПЕТЧЕР] Коммит очистки репозитория в истории пока отсутствует.")
            except Exception as commit_err:
                print(f"[ДИСПЕТЧЕР] Ошибка запроса к API истории коммитов: {str(commit_err)}")

        time.sleep(60)

    # 6. УСПЕШНОЕ РАЗБЛОКИРОВАНИЕ
    print("\n[ДИСПЕТЧЕР] Работа управляющего конвейера успешно завершена.")

if __name__ == "__main__":
    run_control_pipeline()
