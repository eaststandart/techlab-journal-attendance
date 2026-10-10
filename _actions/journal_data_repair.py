#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  journal_data_repair.py
@about   Проверка и исправление файлов расписания
@purpose Приведение времени и направлений к единому стандарту базы данных
@author TechLab
@version 1.0.0
"""

import os
import sys
import json
from datetime import datetime

def repair_yaml_file(file_path):
    print(f"🔍 Чтение файла расписания: {file_path}", flush=True)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        # Аппаратный перехват отсутствия файла (ошибка 404 / FileNotFoundError)
        print(f"❌ Ошибка чтения файла: {e}", flush=True)
        return False

    is_modified = False
    repaired_lines = []

    # Белые списки символов для полноценной замены направлений
    electronics_letters = ["э", "Э", "е", "Е", "e", "E"]
    joinery_letters = ["с", "С", "c", "C"]

    for line in lines:
        stripped = line.strip()
        
        # 1. Исправление и нормализация времени группы (отступ 2 пространства)
        if line.startswith("  ") and not line.startswith("    ") and stripped.endswith(":"):
            raw_time = stripped[:-1].replace('"', '').replace("'", '').strip()
            digits = "".join([c for c in raw_time if c.isdigit()])
            if len(digits) == 4:
                clean_time = f"{digits[0:2]}:{digits[2:4]}"
                repaired_line = f"  \"{clean_time}\":\n"
                if repaired_line != line:
                    print(f"  [ВРЕМЯ] Изменение формата: {stripped} ➔ \"{clean_time}\":", flush=True)
                    line = repaired_line
                    is_modified = True

        # 2. Исправление и замена полей направлений (отступ 6 пространств)
        if line.startswith("      direction:"):
            raw_val = line.split(":", 1)[1].replace('"', '').replace("'", '').strip()
            clean_val = "".join([c for c in raw_val if c not in ["[", "]", "\\", "/", ";"]]).strip()
            
            repaired_val = clean_val
            if clean_val in electronics_letters or "электрон" in clean_val.lower():
                repaired_val = "электронное конструирование"
            elif clean_val in joinery_letters or "столяр" in clean_val.lower():
                repaired_val = "столярное дело"

            repaired_val = " ".join(repaired_val.split()).strip()
            repaired_line = f"      direction: \"{repaired_val}\"\n"
            if repaired_line != line:
                print(f"  [КУРС] Изменение направления: '{raw_val}' ➔ '{repaired_val}'", flush=True)
                line = repaired_line
                is_modified = True

        # 3. Очистка мусора из полей имён (отступ 4 пространства)
        if line.startswith("    - name:"):
            # Сохраняем исходное грязное значение для честного вывода в логи
            old_raw_val = line.split(":", 1)[1].strip()
            
            # Проводим глубокую очистку от всех запрещенных знаков и кавычек
            clean_val = "".join([c for c in old_raw_val if c not in ["[", "]", "\\", "/", ";", '"', "'"]]).strip()
            
            clean_val = " ".join(clean_val.split()).strip()
            repaired_line = f"    - name: \"{clean_val}\"\n"
            if repaired_line != line:
                # Очищаем кавычки в отображении старого имени, чтобы лог был аккуратным
                print(f"  [ИМЯ] Очистка запрещенных знаков: '{old_raw_val}' ➔ '{clean_val}'", flush=True)
                line = repaired_line
                is_modified = True

        # 4. Проверка и очистка хэштегов (отступ 6 пространств)
        if line.startswith("      tag:"):
            raw_val = line.split(":", 1)[1].replace('"', '').replace("'", '').strip()
            clean_val = raw_val
            if clean_val.startswith("#techlab-") or clean_val.startswith("@"):
                while clean_val and clean_val[-1] in ["!", ".", ",", ";", "\"", "'"]:
                    clean_val = clean_val[:-1]
            clean_val = " ".join(clean_val.split()).strip()
            repaired_line = f"      tag: \"{clean_val}\"\n"
            if repaired_line != line:
                print(f"  [ТЕГ] Удаление опечаток в конце строки: '{raw_val}' ➔ '{clean_val}'", flush=True)
                line = repaired_line
                is_modified = True

        repaired_lines.append(line)

    if is_modified:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(repaired_lines)
            print(f"🟢 Файл {file_path} успешно исправлен и сохранен.", flush=True)
            return True
        except Exception as e:
            print(f"❌ Ошибка записи файла YAML: {e}", flush=True)
            raise e
    return False

def main():
    data_dir = "_data"
    signal_file = os.path.join(data_dir, "signal-repair.json")
    status_file = os.path.join(data_dir, "repair-status.json")
    
    if not os.path.exists(data_dir):
        print(f"❌ Папка данных {data_dir} не найдена.", flush=True)
        sys.exit(0)

    target_teacher = ""
    
    # Шаг 1: Извлекаем параметры целевого преподавателя из входящего сигнала JSON
    if os.path.exists(signal_file):
        try:
            with open(signal_file, "r", encoding="utf-8") as sf:
                signal_data = json.load(sf)
                target_teacher = signal_data.get("teacher_login", "").strip()
            print(f"🎯 Получен адресный сигнал на проверку расписания преподавателя: '{target_teacher}'", flush=True)
        except Exception as e:
            print(f"⚠️ Ошибка чтения параметров входящего сигнала: {e}", flush=True)

    any_file_fixed = False
    has_critical_error = False

    if target_teacher:
        # Вычисляем строго один целевой файл расписания
        target_filename = f"journal-attendance-{target_teacher}.yml"
        full_path = os.path.join(data_dir, target_filename)
        
        if os.path.exists(full_path):
            try:
                if repair_yaml_file(full_path):
                    any_file_fixed = True
            except Exception as e:
                print(f"💥 Критический сбой обработки файла {target_filename}: {e}", flush=True)
                has_critical_error = True
        else:
            print(f"❌ Файл расписания {target_filename} физически не найден в папке _data", flush=True)
            has_critical_error = True
    else:
        # Если сигнал пустой или пришёл ручной пуш, сканируем всю папку в режиме предохранителя
        for root, _, files in os.walk(data_dir):
            for file in files:
                if (file.endswith(".yml") or file.endswith(".yaml")) and not file.startswith("repair-status"):
                    full_path = os.path.join(root, file)
                    try:
                        if repair_yaml_file(full_path):
                            any_file_fixed = True
                    except Exception as e:
                        print(f"💥 Критический сбой обработки файла {file}: {e}", flush=True)
                        has_critical_error = True

    # Шаг 2: Запись итогового флага светофора строго после всех физических сохранений
    final_status = "error" if has_critical_error else "off"
    status_payload = {
        "status": final_status,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    try:
        with open(status_file, "w", encoding="utf-8") as stf:
            json.dump(status_payload, stf, indent=2, ensure_ascii=False)
        print(f"📶 Переключатель статуса сервера успешно переведён в: '{final_status}'", flush=True)
    except Exception as e:
        print(f"❌ Не удалось обновить файл статуса repair-status.json: {e}", flush=True)

if __name__ == "__main__":
    main()

