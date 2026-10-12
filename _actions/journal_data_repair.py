#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  journal_data_repair.py
@about   Главный диспетчер проверки, исправления и модерации расписания
@purpose Прием входящих сигналов, управление светофором и вызов модулей TechLab
@author  TechLab
@version 2.0.0
"""

import os
import sys
import json
import subprocess
from datetime import datetime

from ja_repair_normalizer import write_status
from ja_repair_engine import repair_yaml_file
from ja_repair_delete import delete_students_from_yaml
from ja_repair_structure import repair_yaml_structure

# ==============================================================================
# НАСТРОЙКИ
# ==============================================================================
DATA_DIR = "_data"
SIGNAL_FILE = os.path.join(DATA_DIR, "signal-repair.json")


def get_file_commit_date_utc(file_path):
    """Аппаратно запрашивает у Git точную ISO-UTC дату последнего коммита конкретного файла."""
    try:
        # Запрашиваем дату последнего коммита строго в международном формате ISO 8601 (UTC)
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--", file_path],
            capture_output=True, text=True, check=True
        )
        date_str = result.stdout.strip()
        if date_str:
            # Превращаем в живой объект datetime для математического сравнения
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception as e:
        print(f"[ОПТИМИЗАЦИЯ] Не удалось получить дату коммита через Git: {e}", flush=True)
    return None

def main():
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

    if not os.path.isfile(file_path):
        print(f"[ОШИБКА] Файл {filename} не найден.", flush=True)
        try:
            write_status("error")
        except Exception as e:
            print(f"[ОШИБКА] Не удалось сохранить статус: {e}", flush=True)
        sys.exit(1)

    STATUS_FILE = os.path.join(DATA_DIR, "repair-status.json")
    print(f"[СИГНАЛ] Преподаватель: {target_teacher}", flush=True)
    print(f"[СИГНАЛ] Целевой файл: {filename}", flush=True)

    # --- ЗРЯЧИЙ ИЕРАРХИЧЕСКИЙ ШЛАГБАУМ ОПТИМИЗАЦИИ ВРЕМЕНИ TECHLAB ---
    force_full_run = True  # По умолчанию - полная безопасность при любых сбоях чтения
    
    try:
        if os.path.isfile(STATUS_FILE):
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                status_data = json.load(f)
            
            status_mode = status_data.get("mode", "")
            timestamp_str = status_data.get("timestamp", "")
            
            # Извлекаем дату последнего коммита персонального YML-файла из истории Git
            file_commit_date = get_file_commit_date_utc(file_path)
            
            if timestamp_str and file_commit_date:
                # Приводим timestamp светофора к единому ISO-формату UTC
                status_timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                
                # ТВОЯ ИСТИННАЯ МАТРИЦА УСЛОВИЙ:
                # 1. Если файл изменен руками в репозитории позже, чем был подан сигнал
                if file_commit_date > status_timestamp:
                    print(f"[ОПТИМИЗАЦИЯ] Обнаружен новый ручной коммит файла {filename}. Запуск полной проверки.", flush=True)
                    force_full_run = True
                # 2. Если коммит старый, но взведен режим готовящихся изменений
                elif status_mode == "repair":
                    print(f"[ОПТИМИЗАЦИЯ] Режим готовящихся изменений 'repair' (удаление/ремонт). Запуск полной проверки.", flush=True)
                    force_full_run = True
                # 3. ИНАЧЕ - коммитов по расписанию нет, режим пустой -> МГНОВЕННОЕ ЗАВЕРШЕНИЕ СЕССИИ
                else:
                    print(f"[ОПТИМИЗАЦИЯ] Файл {filename} не менялся, принудительных команд нет. Мгновенный финиш.", flush=True)
                    force_full_run = False
    except Exception as opt_err:
        print(f"[ПРЕДОХРАНИТЕЛЬ] Сбой оптимизатора (переход в безопасный режим полной проверки): {opt_err}", flush=True)
        force_full_run = True

    # ИСПОЛНЕНИЕ РЕШЕНИЯ АВТОМАТА
    if not force_full_run:
        try:
            # Изменений нет: за 0.01 сек гасим светофор в off и очищаем mode
            with open(STATUS_FILE, "w", encoding="utf-8") as f:
                json.dump({"status": "off", "mode": "", "timestamp": datetime.now().isoformat()}, f, indent=2, ensure_ascii=False)
            
            # Аппаратно счищаем файл сигнала с диска. Git увидит удаление, и коммит завершится успехом!
            if os.path.isfile(SIGNAL_FILE):
                os.remove(SIGNAL_FILE)
                
            print("[УСПЕХ] Оптимизатор сработал. Светофор погашен, сигнал зачищен. Выход.", flush=True)
        except Exception as e:
            print(f"[ОШИБКА] Не удалось завершить оптимизацию: {e}", flush=True)
        sys.exit(0)

    # ИНАЧЕ - РАБОТАЕМ ПО ПОЛНОЙ ПРОГРАММЕ КАК И РАНЬШЕ
    success = True

    # 1. Проверяем наличие массива на удаление
    students_to_delete = signal_data.get("delete")
    if isinstance(students_to_delete, list) and len(students_to_delete) > 0:
        target_day = signal_data.get("day", "")
        target_time = signal_data.get("time", "")
        success = delete_students_from_yaml(file_path, target_day, target_time, students_to_delete)

    # 2. Общая гигиеническая нормализация оставшегося расписания
    if success:
        try:
            success = repair_yaml_file(file_path)
        except Exception as e:
            print(f"[КРИТИЧЕСКИЙ СБОЙ] Нормализация {filename}: {e}", flush=True)
            success = False

    # 3. Принудительное выравнивание геометрии отступов (0, 2, 4, 6 пробелов)
    if success:
        try:
            success = repair_yaml_structure(file_path)
        except Exception as e:
            print(f"[КРИТИЧЕСКИЙ СБОЙ] Геометрия отступов {filename}: {e}", flush=True)
            success = False
    
    if not success:
        try:
            write_status("error", mode="")
        except Exception as e:
            print(f"[ОШИБКА] Не удалось сохранить статус: {e}", flush=True)
        sys.exit(1)

    try:
        # Успешный финал полной работы: гасим светофор в off и очищаем mode в пустоту
        write_status("off", mode="")
    except Exception as e:
        print(f"[ОШИБКА] Не удалось сохранить статус: {e}", flush=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
