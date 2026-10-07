#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module journal-notify.py
@about Главный управляющий диспетчер и часовой буферного шлюза
@purpose Управление заморозкой, фиксация папок через Git и контроль очистки шлюза сайтом
@author  TechLab
@version 1.0.0
"""

import os
import sys
import time
import requests
import subprocess

def run_control_pipeline():
    print("\n=== [МОДУЛЬ JOURNAL_NOTIFY] ЗАПУСК УПРАВЛЯЮЩЕГО ДИСПЕТЧЕРА ===")
    
    output_dir = os.path.join(os.getcwd(), '_output')
    if not os.path.exists(output_dir):
        print(f"[ДИСПЕТЧЕР] ❌ КРИТИЧЕСКАЯ ОШИБКА: Директория вывода не найдена: {output_dir}")
        return

    # === ЭТАП 1: ВХОДНОЙ ЗАЩИТНЫЙ ЩИТ ЗАНЯТОСТИ ШЛЮЗА ===
    print("[ДИСПЕТЧЕР] ЛОГ ЭТАПА 1: Проверка текущего состояния папки _output...")
    live_output_json = [f for f in os.listdir(output_dir) if f.endswith('.json')]
    
    if live_output_json:
        print(f"[ДИСПЕТЧЕР] ⛔ ШЛЮЗ ЗАНЯТ! В папке _output обнаружены файлы в обработке ({len(live_output_json)} шт.).")
        print("[ДИСПЕТЧЕР] ℹ️ Лог: Предыдущая сборка ещё не завершена сайтом. Новые файлы ждут в приёмнике.")
        print("[ДИСПЕТЧЕР] 🛑 Отмена запуска. Конвейер принудительно остановлен на входе.")
        return

    print("[ДИСПЕТЧЕР] ЛОГ ЭТАПА 1: 🟢 Папка Выход идеально чиста. Шлюз свободен для новой сборки.")

    # === ЭТАП 2: ЗАПУСК ИЗОЛИРОВАННОГО МАТЕМАТИЧЕСКОГО МОДУЛЯ АНАЛИЗА ===
    print("[ДИСПЕТЧЕР] ЛОГ ЭТАПА 2: Запуск изолированного модуля 'journal-analyzer.py'...")
    
    # Запускаем скрипт-анализатор как отдельный процесс, чтобы он выполнил математику над файлами
    result = subprocess.run(["python", "_actions/journal-analyzer.py"], capture_output=True, text=True)
    print(result.stdout) # Печатаем логи математика в общую консоль
    
    # Читаем статус, который математик передал через файл окружения или вытаскиваем его из лога
    analyzer_status = os.environ.get("ANALYZER_STATUS", "NO_BUNDLE_READY")
    
    # Если файл окружения недоступен локально, парсим финальную строчку вывода
    for line in result.stdout.split('\n'):
        if "Финальный статус работы модуля:" in line:
            analyzer_status = line.split(":")[-1].strip()

    if not analyzer_status.startswith("SUCCESS_"):
        print(f"[ДИСПЕТЧЕР] ЛОГ ЭТАПА 2: Модуль анализа не выявил готовых комплектов. Статус: {analyzer_status}")
        print("[ДИСПЕТЧЕР] ℹ️ Лог: Робот сайта отдыхает. Работа конвейера успешно завершена.")
        return

    teacher_login = analyzer_status.replace("SUCCESS_", "").strip()
    print(f"[ДИСПЕТЧЕР] ЛОГ ЭТАПА 2: 🔥 ОБНАРУЖЕН ГОТОВЫЙ КОМПЛЕКТ ДЛЯ УЧИТЕЛЯ: '{teacher_login}'")
    print("[ДИСПЕТЧЕР] 🛑 ТОТАЛЬНОЕ ЗАМИРАНИЕ: Дальнейший анализ папки Вход полностью остановлен.")

    # === ЭТАП 3: РЕАЛЬНАЯ ФИКСАЦИЯ ПЕРЕНОСА ФАЙЛОВ НА ГИТХАБЕ (GIT PUSH) ===
    print("\n[ДИСПЕТЧЕР] ЛОГ ЭТАПА 3: Начинаем процесс жесткой фиксации папок на сервере GitHub...")
    try:
        # Настраиваем параметры системного бота Git перед коммитом
        subprocess.run(["git", "config", "--global", "user.name", "TechLab Notifier Bot"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "notifier@techlab.local"], check=True)
        
        # Индексируем изменения в приёмнике и шлюзе вывода
        subprocess.run(["git", "add", "_input/", "_output/"], check=True)
        
        # Проверяем, зафиксировал ли Git реальные изменения на диске
        diff_check = subprocess.run(["git", "diff", "--cached", "--quiet"])
        if diff_check.returncode != 0:
            print("[ДИСПЕТЧЕР] [GIT] Перенос файлов подтвержден. Сохраняем изменения в репозиторий...")
            subprocess.run(["git", "commit", "-m", f"chore: фиксация переноса комплекта для {teacher_login} в папку выход"], check=True)
            subprocess.run(["git", "push", "origin", "main"], check=True)
            print("[ДИСПЕТЧЕР] 🟢 [GIT PUSH УСПЕШЕН] Изменения папок официально записаны в историю Гитхаба!")
        else:
            print("[ДИСПЕТЧЕР] ⚠️ [GIT] Предупреждение: Локальный перенос выполнен, но Git не зафиксировал изменений истории.")
            print("[ДИСПЕТЧЕР] 🛑 Отмена отправки сигнала. Шлюз безопасности заблокирован.")
            return
            
    except Exception as err:
        print(f"[ДИСПЕТЧЕР] ❌ КРИТИЧЕСКАЯ ОШИБКА выполнения команд Git: {str(err)}")
        return

    # === ЭТАП 4: ОТПРАВКА ОДИНОЧНОГО СИГНАЛА НА САЙТ (CURL DISPATCHES) ===
    fine_token = os.environ.get("MY_FINE_TOKEN")
    if not fine_token:
        print("[ДИСПЕТЧЕР] ❌ КРИТИЧЕСКАЯ ОШИБКА: Ключ MY_FINE_TOKEN не найден в переменных окружения!")
        return

    print(f"\n[ДИСПЕТЧЕР] ЛОГ ЭТАПА 4: Готовим точечный вызов REST API для сайта...")
    
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
        
        if response.status_code != 204:
            print(f"[ДИСПЕТЧЕР] ⚠️ Сервер вернул код {response.status_code}. Отмена заморозки.")
            return
            
        print(f"[ДИСПЕТЧЕР] 🚀 [УСПЕХ] Одиночный сигнал отправлен! Робот сайта успешно вызван.")
        
    except Exception as err:
        print(f"[ДИСПЕТЧЕР] ❌ Исключение при отправке dispatches: {str(err)}")
        return

    # === ЭТАП 5: РЕЖИМ ТОТАЛЬНОЙ ЗАМОРОЗКИ И ЦИКЛИЧЕСКОЕ ОЖИДАНИЕ (КАЖДУЮ 1 МИНУТУ) ===
    print(f"\n[ДИСПЕТЧЕР] ЛОГ ЭТАПА 5: Включение режима заморозки конвейера для '{teacher_login}'...")
    print("[ДИСПЕТЧЕР] ⏳ Робот замер. Ожидаем, пока основной сайт обработает отчёт и очистит папку Выход.")
    print("[ДИСПЕТЧЕР] ℹ️ Проверка состояния шлюза будет выполняться строго каждые 60 секунд.")

    start_time = time.time()
    check_counter = 0

    while True:
        check_counter += 1
        print(f"\n[ДИСПЕТЧЕР] ОЖИДАНИЕ: Круг проверки №{check_counter} (Прошло времени: {int(time.time() - start_time)} сек.)")
        print(f"[ДИСПЕТЧЕР] Делаем запрос к API репозитория Журнала...")

        # Запрашиваем актуальное содержимое папки Выход напрямую с серверов GitHub API
        # Чтобы исключить локальное кэширование виртуальной машины
        check_url = f"https://github.com"
        
        try:
            check_res = requests.get(check_url, headers={"Authorization": f"token {fine_token}"})
            
            if check_res.status_code == 200:
                output_contents = check_res.json()
                # Считаем только файлы JSON, игнорируя системную заглушку .gitkeep
                live_files = [item["name"] for item in output_contents if item["name"].endswith('.json')]
                
                if not live_files:
                    print("[ДИСПЕТЧЕР] 🔥 [ШЛЮЗ СВОБОДЕН] Папка Выход _output РЕАЛЬНО ОПУСТЕЛА на сервере!")
                    print("[ДИСПЕТЧЕР] ЛОГ: Робот сайта полностью стёр отработанные файлы через REST API.")
                    break
                else:
                    print(f"[ДИСПЕТЧЕР] ⏳ Папка Выход ещё содержит файлы ({len(live_files)} шт.): {live_files}")
                    print("[ДИСПЕТЧЕР] Конвейер остаётся замороженным. Ждём завершения работы сайта...")
            
            elif check_res.status_code == 404:
                # Если папка вообще физически удалена сайтом — это тоже означает полную очистку
                print("[ДИСПЕТЧЕР] 🔥 [ШЛЮЗ СВОБОДЕН] Директория Вывода не найдена на сервере (очищена).")
                break
            else:
                print(f"[ДИСПЕТЧЕР] ⚠️ Не удалось проверить состояние папки, код API: {check_res.status_code}")
                
        except Exception as check_err:
            print(f"[ДИСПЕТЧЕР] ⚠️ Ошибка сети при проверке шлюза: {str(check_err)}")

        # Жесткая минутная пауза между кругами сканирования (60 секунд)
        time.sleep(60)

    # === ЭТАП 6: ПОЛНОЕ РАЗМОРОЖИВАНИЕ И УСПЕШНЫЙ ВЫХОД ===
    print("\n[ДИСПЕТЧЕР] ЛОГ ЭТАПА 6: 🟢 Шлюз разблокирован. Процесс полностью размораживается.")
    print("=== УПРАВЛЯЮЩИЙ КОНВЕЙЕР УСПЕШНО ЗАВЕРШИЛ СВОЮ РАБОТУ В ОДИН ПОТОК ===")

if __name__ == "__main__":
    run_control_pipeline()
