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

def repair_yaml_file(file_path):
    print(f"🔍 Чтение файла расписания: {file_path}", flush=True)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
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
            # Убираем любые мусорные разделители из времени (10-00, 10=00)
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
            # Вытаскиваем сырое значение курса из строки
            raw_val = line.split(":", 1)[1].replace('"', '').replace("'", '').strip()
            
            # Очищаем от ломающих символов: [ ] \ / ;
            clean_val = "".join([c for c in raw_val if c not in ["[", "]", "\\", "/", ";"]]).strip()
            
            repaired_val = clean_val
            # Полноценное посимвольное сопоставление курса
            if clean_val in electronics_letters or "электрон" in clean_val.lower():
                repaired_val = "электронное конструирование"
            elif clean_val in joinery_letters or "столяр" in clean_val.lower():
                repaired_val = "столярное дело"

            repaired_line = f"      direction: \"{repaired_val}\"\n"
            if repaired_line != line:
                print(f"  [КУРС] Изменение направления: '{raw_val}' ➔ '{repaired_val}'", flush=True)
                line = repaired_line
                is_modified = True

        # 3. Очистка мусора из полей имён (отступ 4 пространства)
        if line.startswith("    - name:"):
            raw_val = line.split(":", 1)[1].replace('"', '').replace("'", '').strip()
            clean_val = "".join([c for c in raw_val if c not in ["[", "]", "\\", "/", ";"]]).strip()
            repaired_line = f"    - name: \"{clean_val}\"\n"
            if repaired_line != line:
                print(f"  [ИМЯ] Очистка запрещенных знаков: '{raw_val}' ➔ '{clean_val}'", flush=True)
                line = repaired_line
                is_modified = True

        # 4. Проверка и очистка тегов (отступ 6 пространств)
        if line.startswith("      tag:"):
            raw_val = line.split(":", 1)[1].replace('"', '').replace("'", '').strip()
            
            # Удаление случайных знаков препинания строго с конца тега
            clean_val = raw_val
            if clean_val.startswith("#techlab-") or clean_val.startswith("@"):
                while clean_val and clean_val[-1] in ["!", ".", ",", ";", "\"", "'"]:
                    clean_val = clean_val[:-1]
            repaired_line = f"      tag: \"{clean_val}\"\n"
            if repaired_line != line:
                print(f"  [ТЕГ] Удаление опечаток: '{raw_val}' ➔ '{clean_val}'", flush=True)
                line = repaired_line
                is_modified = True

        repaired_lines.append(line)

    if is_modified:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(repaired_lines)
            print(f"🟢 Файл {file_path} успешно исправлен и сохранен в репозиторий.", flush=True)
            return True
        except Exception as e:
            print(f"❌ Ошибка записи файла YAML: {e}", flush=True)
            return False
    else:
        print(f"✨ Файл {file_path} соответствует стандарту расписания.", flush=True)
        return False

def main():
    data_dir = "_data"
    status_file = os.path.join(data_dir, "repair-status.json")
    
    if not os.path.exists(data_dir):
        print(f"❌ Папка данных {data_dir} не найдена.", flush=True)
        sys.exit(0)

    any_file_fixed = False
    has_critical_error = False

    # Сканируем и исправляем файлы расписаний
    for root, _, files in os.walk(data_dir):
        for file in files:
            if (file.endswith(".yml") or file.endswith(".yaml")) and file != "repair-status.json":
                full_path = os.path.join(root, file)
                try:
                    if repair_yaml_file(full_path):
                        any_file_fixed = True
                except Exception as e:
                    print(f"💥 Фатальный сбой обработки файла {file}: {e}", flush=True)
                    has_critical_error = True

    # СТРОГО ПОСЛЕ ВСЕХ РАБОТ И СОХРАНЕНИЙ ОБНОВЛЯЕМ ФАЙЛ СВЕТОФОРА
    # Определяем финальный статус на основе результатов работы робота
    final_status = "error" if has_critical_error else "off"
    
    import json
    from datetime import datetime
    
    status_payload = {
        "status": final_status,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    try:
        with open(status_file, "w", encoding="utf-8") as sf:
            json.dump(status_payload, sf, indent=2, ensure_ascii=False)
        print(f"📶 Переключатель статуса сервера успешно переведён в: '{final_status}'", flush=True)
    except Exception as e:
        print(f"❌ Не удалось обновить файл статуса repair-status.json: {e}", flush=True)

    if any_file_fixed:
        print("🚀 Все файлы расписаний успешно приведены к регламентированному стандарту.", flush=True)
    else:
        print("✅ Проверка завершена. Дополнительных изменений в структуре не потребовалось.", flush=True)

if __name__ == "__main__":
    main()
