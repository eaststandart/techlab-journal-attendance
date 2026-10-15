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

# ПОДКЛЮЧАЕМ МЕНЕДЖЕР СЕССИЙ И СТАТУСОВ
from journal_repair.ja_session_manager import write_status

# ПОДКЛЮЧАЕМ ПОДМОДУЛИ ПРОВЕРКИ РАСПИСАНИЯ
from journal_repair.ja_repair_day import repair_day_line
from journal_repair.ja_repair_time import repair_time_line, normalize_time_internal
from journal_repair.ja_repair_fields import repair_fields_line
from journal_repair.ja_repair_structure import repair_yaml_structure
from journal_repair.ja_repair_delete import delete_students_from_yaml
from journal_repair.ja_repair_modify import modify_time_in_yaml

# ==============================================================================
# НАСТРОЙКИ
# ==============================================================================
DATA_DIR = "_data"

def main():
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
            write_status("error", teacher_login=cmd_teacher if 'cmd_teacher' in locals() else "unknown")
        except Exception as status_error:
            print(f"[ОШИБКА] Не удалось сохранить статус: {status_error}", flush=True)
        sys.exit(1)

    filename = f"journal-attendance-{target_teacher}.yml"
    file_path = os.path.join(DATA_DIR, filename)

    if not os.path.isfile(file_path):
        print(f"[ОШИБКА] Файл {filename} не найден.", flush=True)
        try:
            write_status("error", teacher_login=target_teacher)
        except Exception as e:
            print(f"[ОШИБКА] Не удалось сохранить статус: {e}", flush=True)
        sys.exit(1)

    print(f"[СИГНАЛ] Преподаватель: {target_teacher}", flush=True)
    print(f"[СИГНАЛ] Целевой файл: {filename}", flush=True)

    success = True

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
                line, time_mod, time_err = repair_time_line(line, filename, signal_data)
                if time_mod:
                    is_modified = True

                if time_err:
                    has_errors = True

                # 3. Подмодуль текстовых полей учащихся (курсы, имена, теги)
                line, fields_mod = repair_fields_line(line, filename)
                if fields_mod:
                    is_modified = True

                repaired_lines.append(line)

            # Если найдены недопустимые значения времени — завершаем процесс с ошибкой для GitHub Actions.
            if has_errors:
                print(
                    f"[ОШИБКА] {filename}: найдены недопустимые значения времени.",
                    flush=True,
                )
                try:
                    write_status("error", mode="", teacher_login=target_teacher)
                except Exception as status_error:
                    print(
                        f"[ОШИБКА] Не удалось сохранить статус: {status_error}",
                        flush=True,
                    )
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
                write_status("error", mode="repair", teacher_login=target_teacher, errorDetails=err_msg)
            except Exception as status_error:
                print(f"[ОШИБКА] Не удалось сохранить статус: {status_error}", flush=True)
            sys.exit(1)

    # 3. Принудительное выравнивание геометрии отступов (0, 2, 4, 6 пробелов)
    if success:
        try:
            success = repair_yaml_structure(file_path)
        except Exception as e:
            err_msg = f"[КРИТИЧЕСКИЙ СБОЙ] Геометрия отступов {filename}: {e}"
            print(err_msg, flush=True)
            try:
                write_status("error", mode="repair", teacher_login=target_teacher, errorDetails=err_msg)
            except Exception as status_error:
                print(f"[ОШИБКА] Не удалось сохранить статус: {status_error}", flush=True)
            sys.exit(1)

    # 4. Выполнение команд модификации базы данных из однотипного сигнала
    if success:
        cmd_type = signal_data.get("command", "").strip().lower()
        
        # Контур А: Удаление учеников из полностью нормализованной базы
        if cmd_type == "delete":
            students_to_delete = signal_data.get("delete")
            if isinstance(students_to_delete, list) and len(students_to_delete) > 0:
                target_day = signal_data.get("day", "")
                target_time = signal_data.get("time", "")
            
            # Нормализуем координаты прямо перед вызовом удаления силами новых ядер TechLab
            sim_day_line, _ = repair_day_line(f"{target_day}:\n", filename)
            clean_day = sim_day_line.replace(":", "").strip()
            clean_time = normalize_time_internal(target_time)
            
            try:
                success = delete_students_from_yaml(file_path, clean_day, clean_time, students_to_delete)
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
                sim_day_line, _ = repair_day_line(f"{target_day}:\n", filename)
                clean_day = sim_day_line.replace(":", "").strip()
                
                # Старое время принудительно приводим к ЧЧ:ММ без суточной отбраковки
                digits_old = "".join(c for c in old_time if c.isdigit())
                clean_old_time = f"{digits_old[:2]}:{digits_old[2:]}" if len(digits_old) in {3, 4} else ""
                
                # Новое целевое время проверяем по полной строгости закона суток
                clean_new_time = normalize_time_internal(new_time)

                if clean_old_time and clean_new_time:
                    try:
                        # СВЕРХТОЧНЫЙ ИЗМЕРИТЕЛЬНЫЙ ЗОНД TECHLAB ПОСЛЕ ШАГА №3
                        print(f"[ОТЛАДКА ПЕРЕЧИТЫВАНИЯ] Ищем день: {clean_day!r}, старое время: {clean_old_time!r}", flush=True)
                        try:
                            with open(file_path, "r", encoding="utf-8") as f_fresh:
                                fresh_lines = f_fresh.readlines()
                            
                            print(f"[ОТЛАДКА С ДИСКА] Файл успешно перечитан заново. Всего строк: {len(fresh_lines)}", flush=True)
                            
                            test_inside_day = False
                            test_target_str = f'"{clean_old_time}":'
                            
                            for idx, line in enumerate(fresh_lines):
                                trimmed = line.strip()
                                
                                # Моделируем логику фиксации дня из твоего подмодуля modify_time_in_yaml
                                if not line.startswith(' ') and trimmed.endswith(':'):
                                    check_day_name = trimmed.replace(':', '').lower().strip()
                                    test_inside_day = (check_day_name == clean_day.lower().strip())
                                    if test_inside_day:
                                        print(f"[ОТЛАДКА ЗОНДА] Найдена строка дня №{idx+1}: {line!r} -> Взведён флаг test_inside_day = True", flush=True)
                                
                                # Печатаем лог для абсолютно всех строк с двоеточием, пока взведён флаг дня
                                if test_inside_day and trimmed.endswith(':'):
                                    print(f"--- Проверка строки №{idx+1} inside_day={test_inside_day} ---", flush=True)
                                    print(f"Сырой текст в YML: {line!r}", flush=True)
                                    print(f"Результат line.startswith(' '): {line.startswith(' ')}", flush=True)
                                    print(f"Результат trimmed: {trimmed!r}", flush=True)
                                    print(f"Сравниваем с ожидаемым: {test_target_str!r}", flush=True)
                                    print(f"Результат совпадения (trimmed == target): {trimmed == test_target_str}", flush=True)
                                    
                                    # Симулируем повторную проверку дня на строке времени, как в подмодуле
                                    if not line.startswith(' '):
                                        print(f"[ВНИМАНИЕ ОШИБКА] Строка №{idx+1} НЕ начинается с пробела! Вызов повторной проверки дня сбросит флаг в False!", flush=True)
                        except Exception as log_err:
                            print(f"[ОТЛАДКА ОШИБКА] Сбой измерительного зонда: {log_err}", flush=True)

                        success = modify_time_in_yaml(file_path, clean_day, clean_old_time, clean_new_time)
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
            write_status("error", mode="repair", teacher_login=target_teacher, errorDetails="Отказ выполнения конвейера модерации базы данных расписания.")
        except Exception as e:
            print(f"[ОШИБКА] Не удалось сохранить статус: {e}", flush=True)
        sys.exit(1)

    try:
        # Успешный финал полной работы: гасим светофор в off и очищаем mode в пустоту
        write_status("off", mode="", teacher_login=target_teacher)
    except Exception as e:
        print(f"[ОШИБКА] Не удалось сохранить статус: {e}", flush=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
