#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  journal_repair.py
@about   Главный диспетчер проверки, исправления и модерации расписания
@purpose Прием входящих сигналов, управление светофором и вызов модулей TechLab
@author  TechLab
@version 1.0.0
"""

import os
import sys
import json
import subprocess
from datetime import datetime

# ПОДКЛЮЧАЕМ АВТОНОМНЫЙ МЕНЕДЖЕР СЕССИЙ И СТАТУСОВ TECHLAB
from ja_session_manager import write_status, get_file_commit_seconds, get_last_robot_commit_seconds

# ПОДКЛЮЧАЕМ СИНТАКСИЧЕСКИЕ ПОДМОДУЛИ ПРОВЕРКИ РАСПИСАНИЯ
from ja_repair_day import repair_day_line
from ja_repair_time import repair_time_line
from ja_repair_fields import repair_fields_line
from ja_repair_delete import delete_students_from_yaml
from ja_repair_structure import repair_yaml_structure

# ==============================================================================
# НАСТРОЙКИ
# ==============================================================================
DATA_DIR = "_data"
SIGNAL_FILE = os.path.join(DATA_DIR, "signal-repair.json")
STATUS_FILE = os.path.join(DATA_DIR, "repair-status.json")

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

    # --- МОНОЛИТНЫЙ БУЛЕВЫЙ ШЛАГБАУМ ОПТИМИЗАЦИИ Unix-СЕКУНД TECHLAB ---
    force_full_run = True  # По умолчанию - полная безопасность
    
    try:
        if os.path.isfile(STATUS_FILE):
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                status_data = json.load(f)
            
            status_mode = status_data.get("mode", "").strip()
            
            # Аппаратно извлекаем чистые секунды Unix напрямую из истории Git
            commit_seconds = get_file_commit_seconds(file_path)
            robot_seconds = get_last_robot_commit_seconds()
            
            print(f"[ОТЛАДКА СЕКУНД] Unix-время файла расписания: {commit_seconds}", flush=True)
            print(f"[ОТЛАДКА СЕКУНД] Unix-время прошлого ухода робота: {robot_seconds}", flush=True)
            print(f"[ОТЛАДКА СЕКУНД] Текущий маркер режима с сайта: '{status_mode}'", flush=True)
            
            # ТВОЯ СЖАТАЯ МОНОЛИТНАЯ ФОРМУЛА ПРИНЯТИЯ РЕШЕНИЙ:
            # Полная проверка запускается ТОЛЬКО если есть свежий коммит ИЛИ взведен режим repair
            if commit_seconds > robot_seconds or status_mode == "repair":
                print(f"[ОПТИМИЗАЦИЯ] Условия выполнены (Новый коммит: {commit_seconds > robot_seconds}, Режим: {status_mode == 'repair'}). Полный запуск.", flush=True)
                force_full_run = True
            else:
                # ИНАЧЕ - коммитов нет, режим пустой -> МГНОВЕННЫЙ ФИНИШ БЕЗ ИЗБЫТОЧНЫХ ПРОВЕРОК
                print(f"[ОПТИМИЗАЦИЯ] Новых коммитов расписания нет, принудительных команд нет. Мгновенный финиш.", flush=True)
                force_full_run = False
    except Exception as opt_err:
        print(f"[ПРЕДОХРАНИТЕЛЬ] Сбой булевого оптимизатора (переход в безопасный режим полной проверки): {opt_err}", flush=True)
        force_full_run = True

    # ИСПОЛНЕНИЕ РЕШЕНИЯ АВТОМАТА
    if not force_full_run:
        try:
            # Изменений нет: за 0.01 сек тушим светофор в off, очищаем mode и удаляем сигнал
            with open(STATUS_FILE, "w", encoding="utf-8") as f:
                json.dump({"status": "off", "mode": "", "timestamp": datetime.now().isoformat()}, f, indent=2, ensure_ascii=False)
            
            if os.path.isfile(SIGNAL_FILE):
                os.remove(SIGNAL_FILE)
                
            print("[УСПЕХ] Оптимизатор сработал. Светофор погашен в off, сигнал зачищен. Выход.", flush=True)
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

    # 2. Общая нормализация расписания (Подмодуль №1: Дни недели)
    if success:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            is_modified = False
            has_errors = False  # Оригинальный аварийный флаг времени
            repaired_lines = []

            for line in lines:
                stripped = line.strip()

                if not stripped or stripped.startswith('#'):
                    repaired_lines.append(line)
                    continue

                # 1. Подмодуль дней недели
                line, day_mod = repair_day_line(line, filename)
                if day_mod:
                    is_modified = True

                # 2. Подмодуль времени групп
                line, time_mod, time_err = repair_time_line(line, filename)
                if time_mod:
                    is_modified = True
                if time_err:
                    has_errors = True

                # 3. Подмодуль текстовых полей учащихся (курсы, имена, теги)
                line, fields_mod = repair_fields_line(line, filename)
                if fields_mod:
                    is_modified = True

                repaired_lines.append(line)

            # Если найдены недопустимые значения времени — прерываемся
            if has_errors:
                print(f"[ОШИБКА] {filename}: найдены недопустимые значения времени.", flush=True)
                return False

            if is_modified:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(repaired_lines)
                print(f"[ИТОГ] {filename}: синтаксические исправления сохранены.", flush=True)
            else:
                print(f"[ИТОГ] {filename}: синтаксических исправлений текста не требуется.", flush=True)

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
