#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  journal_repair.py
@about   Модуль исправления базы данных.
@purpose Построчная нормализация текста расписания, контроль геометрии YAML и выполнение команд удаления или модификации данных по сигналу.
@author  TechLab
@version 1.0.0
"""

import os
import sys
import json
import subprocess
from datetime import datetime

# ==============================================================================
# НАСТРОЙКИ
# ==============================================================================
DATA_DIR = os.path.join(os.getcwd(), '_data')

def main():
    # Прописываем пути к локальной папке диспетчера, чтобы модули импортировались без сбоев
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.append(current_dir)

    # ПОДКЛЮЧАЕМ МЕНЕДЖЕР СЕССИЙ И СТАТУСОВ
    import ja_session_manager
     
    # ПОДКЛЮЧАЕМ ПОДМОДУЛИ ПРОВЕРКИ РАСПИСАНИЯ
    import ja_repair_space
    import ja_repair_day
    import ja_repair_time
    import ja_repair_fields
    import ja_repair_structure
    import ja_repair_delete
    import ja_repair_modify
     
    # Проверяем, что воркфлоу передал обязательный аргумент логина преподавателя
    if len(sys.argv) < 2:
        print("[ОШИБКА] Запуск диспетчера произведен без указания логина преподавателя в аргументах.", flush=True)
        sys.exit(1)
        
    cmd_teacher = sys.argv[1].strip()
    SIGNAL_FILE = os.path.join(DATA_DIR, f"signal-repair-{cmd_teacher}.json")

    if not os.path.isdir(DATA_DIR) or not os.path.isfile(SIGNAL_FILE):
        print(f"[ОШИБКА] Папка _data или персональный входящий сигнал {os.path.basename(SIGNAL_FILE)} не найдены.", flush=True)
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
            ja_session_manager.write_status("error", teacher_login=cmd_teacher if 'cmd_teacher' in locals() else "unknown")
        except Exception as status_error:
            print(f"[ОШИБКА] Не удалось сохранить статус: {status_error}", flush=True)
        sys.exit(1)

    filename = f"journal-attendance-{target_teacher}.yml"
    file_path = os.path.join(DATA_DIR, filename)

    if not os.path.isfile(file_path):
        print(f"[ОШИБКА] Файл {filename} не найден.", flush=True)
        try:
            ja_session_manager.write_status("error", teacher_login=target_teacher)
        except Exception as e:
            print(f"[ОШИБКА] Не удалось сохранить статус: {e}", flush=True)
        sys.exit(1)

    print(f"[СИГНАЛ] Преподаватель: {target_teacher}", flush=True)
    print(f"[СИГНАЛ] Целевой файл: {filename}", flush=True)

    success = True

    # 1. Общая нормализация расписания
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

                # 0. Подмодуль точечного исправления и сжатия пробелов (включая config)
                line, space_mod = ja_repair_space.repair_space_line(line, filename)
                if space_mod:
                    is_modified = True

                # 1. Подмодуль дней недели
                line, day_mod = ja_repair_day.repair_day_line(line, filename)
                if day_mod:
                    is_modified = True

                # 2. Подмодуль времени групп
                line, time_mod, time_err = ja_repair_time.repair_time_line(line, filename, signal_data)
                if time_mod:
                    is_modified = True

                if time_err:
                    has_errors = True

                # 3. Подмодуль текстовых полей учащихся (курсы, имена, теги)
                line, fields_mod = ja_repair_fields.repair_fields_line(line, filename)
                if fields_mod:
                    is_modified = True

                repaired_lines.append(line)

            # Если найдены критические синтаксические ошибки времени — передаем лог на Красный экран сайта
            if has_errors:
                err_msg = f"[СИНТАКСИС] {filename}: обнаружены некорректные или нераспознанные строки времени групп."
                print(err_msg, flush=True)
                try:
                    ja_session_manager.write_status("error", mode="repair", teacher_login=target_teacher, errorDetails=err_msg)
                except Exception as status_error:
                    print(f"[ОШИБКА] Не удалось сохранить статус: {status_error}", flush=True)
                sys.exit(1)

            if is_modified:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(repaired_lines)
                print(f"[ИТОГ] {filename}: синтаксические исправления сохранены.", flush=True)
            else:
                print(f"[ИТОГ] {filename}: синтаксических исправлений текста не требуется.", flush=True)

        except Exception as e:
            err_msg = f"[КРИТИЧЕСКИЙ СБОЙ] Нормализация {filename}: {e}"
            print(err_msg, flush=True)
            try:
                ja_session_manager.write_status("error", mode="repair", teacher_login=target_teacher, errorDetails=err_msg)
            except Exception as status_error:
                print(f"[ОШИБКА] Не удалось сохранить статус: {status_error}", flush=True)
            sys.exit(1)

    # 2. Принудительное выравнивание геометрии отступов (0, 2, 4, 6 пробелов)
    if success:
        try:
            success = ja_repair_structure.repair_yaml_structure(file_path)
        except Exception as e:
            err_msg = f"[КРИТИЧЕСКИЙ СБОЙ] Геометрия отступов {filename}: {e}"
            print(err_msg, flush=True)
            try:
                ja_session_manager.write_status("error", mode="repair", teacher_login=target_teacher, errorDetails=err_msg)
            except Exception as status_error:
                print(f"[ОШИБКА] Не удалось сохранить статус: {status_error}", flush=True)
            sys.exit(1)

    # 3. Выполнение команд модификации базы данных из однотипного сигнала
    if success:
        cmd_type = signal_data.get("command", "").strip().lower()
        
        # Контур А: Удаление учеников из полностью нормализованной базы
        if cmd_type == "delete":
            students_to_delete = signal_data.get("delete")
            if isinstance(students_to_delete, list) and len(students_to_delete) > 0:
                target_day = signal_data.get("day", "")
                target_time = signal_data.get("time", "")
            
            # Нормализуем координаты прямо перед вызовом удаления силами новых ядер TechLab
            sim_day_line, _ = ja_repair_day.repair_day_line(f"{target_day}:\n", filename)
            clean_day = sim_day_line.replace(":", "").strip()
            clean_time = ja_repair_time.normalize_time_internal(target_time)
            
            try:
                success = ja_repair_delete.delete_students_from_yaml(file_path, clean_day, clean_time, students_to_delete)
            except Exception as e:
                print(f"[КРИТИЧЕСКИЙ СБОЙ] Финальное вырезание учеников {filename}: {e}", flush=True)
                success = False

        # Контур Б: Точечное изменение структуры времени группы в расписании
        elif cmd_type == "modify":
            target_day = signal_data.get("day", "").strip()
            old_time = signal_data.get("time", "").strip()
            new_time = signal_data.get("modify_time", "").strip()

            if target_day and old_time and new_time:
                # Нормализуем координаты силами ядер TechLab перед вызовом замены
                sim_day_line, _ = ja_repair_day.repair_day_line(f"{target_day}:\n", filename)
                clean_day = sim_day_line.replace(":", "").strip()
                
                # Старое время принудительно приводим к ЧЧ:ММ без суточной отбраковки
                digits_old = "".join(c for c in old_time if c.isdigit())
                clean_old_time = f"{digits_old[:2]}:{digits_old[2:]}" if len(digits_old) in {3, 4} else ""
                
                # Новое целевое время проверяем по полной строгости закона суток
                clean_new_time = ja_repair_time.normalize_time_internal(new_time)

                if clean_old_time and clean_new_time:
                    try:
                        success = ja_repair_modify.modify_time_in_yaml(file_path, clean_day, clean_old_time, clean_new_time)
                    except Exception as e:
                        print(f"[КРИТИЧЕСКИЙ СБОЙ] Точечное изменение времени {filename}: {e}", flush=True)
                        success = False
                else:
                    print(f"[ОШИБКА МОДИФИКАЦИИ] Неверный формат времени в сигнале: старое {old_time!r}, новое {new_time!r}", flush=True)
                    success = False
            else:
                print("[ОШИБКА МОДИФИКАЦИИ] Сигнал modify прилетел без обязательных параметров day/time/modify_time", flush=True)
                success = False
    
    if not success:
        try:
            ja_session_manager.write_status("error", mode="repair", teacher_login=target_teacher, errorDetails="Отказ выполнения конвейера модерации базы данных расписания.")
        except Exception as e:
            print(f"[ОШИБКА] Не удалось сохранить статус: {e}", flush=True)
        sys.exit(1)

    try:
        # Успешный финал полной работы: гасим светофор в off и очищаем mode в пустоту
        ja_session_manager.write_status("off", mode="", teacher_login=target_teacher)
    except Exception as e:
        print(f"[ОШИБКА] Не удалось сохранить статус: {e}", flush=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
