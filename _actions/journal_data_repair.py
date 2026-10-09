#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  journal_data_repair.py
@about   Проверка и исправление файлов расписания
@purpose Приведение времени и направлений к единому стандарту базы данных
@author TechLab
@version 10.0.0
"""

import os
import re
import sys
import yaml

def clean_text_field(text_str):
    if not text_str or not isinstance(text_str, str):
        return ""
    # Удаление запрещенных символов из текста: [ ] ' " \ / ;
    cleaned = re.sub(r"[\[\]'\"\\/;]", "", text_str)
    # Схлопывание множественных пробелов до одного
    return " ".join(cleaned.split()).strip()

def clean_tag_field(tag_str):
    if not tag_str or not isinstance(tag_str, str):
        return ""
    tag_clean = tag_str.strip()
    # Удаление знаков препинания на конце системных интернет-тегов
    if tag_clean.startswith("#techlab-") or tag_clean.startswith("@"):
        tag_clean = re.sub(r"[!.,;\"']+$", "", tag_clean)
    return tag_clean.strip()

def normalize_time_str(time_str):
    if not time_str or not isinstance(time_str, str):
        return str(time_str)
    raw_time = time_str.strip()
    # Извлечение цифр часов и минут через универсальный текстовый разделитель
    match = re.search(r"(\d{1,2})\D*(\d{2})", raw_time)
    if match:
        return f"{int(match.group(1)):02d}:{match.group(2)}"
    return raw_time

def normalize_direction(dir_str):
    if not dir_str or not isinstance(dir_str, str):
        return ""
    
    cleaned = clean_text_field(dir_str).strip()    
    
    electronics_letters = ["э", "Э", "е", "Е", "e", "E"]
    
    joinery_letters = ["с", "С", "c", "C"]
    
    if cleaned in electronics_letters or "электрон" in cleaned.lower() or "электр" in cleaned.lower():
        return "электронное конструирование"
        
    if cleaned in joinery_letters or "столяр" in cleaned.lower() or "стол" in cleaned.lower():
        return "столярное дело"

    return cleaned

def repair_yaml_file(file_path):
    print(f"🔍 Чтение файла расписания: {file_path}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"❌ Ошибка чтения формата YAML: {e}")
        return False

    is_modified = False
    repaired_data = {}

    # Построчная проверка структуры данных расписания
    for day, groups in data.items():
        if day == "config":
            repaired_data[day] = groups
            continue

        clean_day = day.strip().lower()
        if clean_day != day:
            is_modified = True

        repaired_data[clean_day] = {}

        if not isinstance(groups, dict):
            repaired_data[clean_day] = groups
            continue

        for time_key, kids_list in groups.items():
            # Проверка и исправление формата времени группы
            repaired_time = normalize_time_str(time_key)
            if repaired_time != time_key:
                print(f"  [ВРЕМЯ] Изменение формата: {time_key} ➔ {repaired_time}")
                is_modified = True

            repaired_data[clean_day][repaired_time] = []

            if not isinstance(kids_list, list):
                continue

            for kid in kids_list:
                if not isinstance(kid, dict):
                    continue

                # Проверка и исправление текстовых полей ученика
                old_name = kid.get("name", "")
                old_dir = kid.get("direction", "")
                old_tag = kid.get("tag", "")

                repaired_name = clean_text_field(old_name)
                repaired_dir = normalize_direction(old_dir)
                repaired_tag = clean_tag_field(old_tag)

                if repaired_name != old_name or repaired_dir != old_dir or repaired_tag != old_tag:
                    print(f"  [УЧЕНИК] Обнаружены опечатки у: '{old_name}'", flush=True)
                    if repaired_name != old_name:
                        print(f"          ИМЯ:  '{old_name}' ➔ '{repaired_name}'", flush=True)
                    if repaired_dir != old_dir:
                        print(f"          КУРС: '{old_dir}' ➔ '{repaired_dir}'", flush=True)
                    if repaired_tag != old_tag:
                        print(f"          ТЕГ:  '{old_tag}' ➔ '{repaired_tag}'", flush=True)
                    is_modified = True

                new_kid_obj = {
                    "name": repaired_name,
                    "direction": repaired_dir
                }
                if repaired_tag:
                    new_kid_obj["tag"] = repaired_tag

                repaired_data[clean_day][repaired_time].append(new_kid_obj)

    if is_modified:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(repaired_data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
            print(f"🟢 Файл {file_path} успешно исправлен и перезаписан.")
            return True
        except Exception as e:
            print(f"❌ Ошибка записи исправленного файла YAML: {e}")
            return False
    else:
        print(f"✨ Файл {file_path} соответствует стандарту расписания.")
        return False

def main():
    data_dir = "_data"
    if not os.path.exists(data_dir):
        print(f"❌ Папка данных {data_dir} не найдена.")
        sys.exit(0)

    any_file_fixed = False
    for root, _, files in os.walk(data_dir):
        for file in files:
            if file.endswith(".yml") or file.endswith(".yaml"):
                full_path = os.path.join(root, file)
                if repair_yaml_file(full_path):
                    any_file_fixed = True

    if any_file_fixed:
        print("🚀 Файлы расписаний успешно приведены к регламентированному стандарту.")
    else:
        print("✅ Проверка завершена. Ошибок в файлах расписаний не обнаружено.")

if __name__ == "__main__":
    main()
