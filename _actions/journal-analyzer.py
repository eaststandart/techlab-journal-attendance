#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  media-analyzer.py
@about   Модуль проверки комплектности отчетов и перемещения медиа-пакетов.
@purpose Группировка медиа-файлов по манифестам, контроль даты, флага публикации и перенос готового пакета в исходном виде в _output.
@author  TechLab
@version 1.0.0
"""

import os
import re
import sys
import shutil
from datetime import datetime, timedelta

def get_vladivostok_date():
    """
    Возвращает текущую дату в часовом поясе Владивостока (UTC+10).
    """
    utc_now = datetime.utcnow()
    vladivostok_now = utc_now + timedelta(hours=10)
    return vladivostok_now.date()

def parse_front_matter(file_path):
    """
    Извлекает Front Matter из .md файла в виде словаря.
    """
    meta = {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if match:
            yaml_block = match.group(1)
            for line in yaml_block.splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip().strip('"').strip("'")
                    meta[key] = value
            return meta, content[match.end():]
    except Exception as e:
        print(f"[АНАЛИЗАТОР] ⚠️ Ошибка парсинга Front Matter в '{os.path.basename(file_path)}': {str(e)}")
    return None, None

def analyze_and_process_media():
    print("\n=== [МОДУЛЬ MEDIA-ANALYZER] АНАЛИЗ ПАПКИ _INPUT ===")

    input_dir = os.path.join(os.getcwd(), "_input")
    output_dir = os.path.join(os.getcwd(), "_output")

    if not os.path.exists(input_dir) or not os.path.exists(output_dir):
        print("[АНАЛИЗАТОР] ❌ Ошибка: Целевые директории не найдены.")
        return "ERROR_DIR_NOT_FOUND"

    # Защита от начала нового комплекта строго по расширению .md (как в оригинале Журнала)
    output_files = sorted(f for f in os.listdir(output_dir) if f.endswith(".md"))
    if output_files:
        print(f"[АНАЛИЗАТОР] Папка _output занята: {len(output_files)} .md файл(ов). Новый комплект не переносим.")
        return "OUTPUT_BUSY"

    all_files = sorted(os.listdir(input_dir))
    md_files = [f for f in all_files if f.endswith(".md")]

    if not md_files:
        print("[АНАЛИЗАТОР] В директории _input файлы манифестов (.md) отсутствуют.")
        return "NO_FILES"

    current_vl_date = get_vladivostok_date()
    print(f"[АНАЛИЗАТОР] Текущая дата сервера по Владивостоку: {current_vl_date}")

    # Детерминированный поиск первого полностью готового комплекта
    for md_name in md_files:
        md_path = os.path.join(input_dir, md_name)
        meta, body_text = parse_front_matter(md_path)
        
        if not meta or not body_text:
            continue

        # 1. Контроль флага видимости (published)
        published_val = meta.get("published", "false").lower()
        if published_val != "true":
            print(f"[АНАЛИЗАТОР] Манифест '{md_name}' пропущен: опубликован как черновик (published: false).")
            continue

        # 2. Контроль времени (Отложенная публикация)
        date_str = meta.get("date", "").strip()
        if not date_str:
            print(f"[АНАЛИЗАТОР] ⚠️ Манифест '{md_name}' пропущен: отсутствует поле даты.")
            continue
            
        try:
            packet_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if packet_date > current_vl_date:
                print(f"[АНАЛИЗАТОР] Манифест '{md_name}' отложен: дата публикации ({date_str}) еще не наступила.")
                continue
        except Exception:
            print(f"[АНАЛИЗАТОР] ⚠️ Манифест '{md_name}' пропущен: неверный формат даты '{date_str}'.")
            continue

        # 3. Сбор списка упомянутых вложений регулярными выражениями
        raw_attachments = []
        raw_attachments.extend(re.findall(r"!\[\[(.*?)\]\]", body_text))
        raw_attachments.extend(re.findall(r"!\[.*?\]\((.*?)\)", body_text))

        # Надежная очистка имен от пробелов и обрезка якорей Obsidian (|300)
        attachments = []
        for att in raw_attachments:
            clean_att = att.strip().split("|")[0].strip()
            if clean_att and clean_att not in attachments:
                attachments.append(clean_att)

        # 4. Контроль комплектности файлов на Входе
        bundle_ready = True
        missing_files = []
        for file_name in attachments:
            source_file_path = os.path.join(input_dir, file_name)
            if not os.path.exists(source_file_path):
                bundle_ready = False
                missing_files.append(file_name)

        if not bundle_ready:
            print(f"[АНАЛИЗАТОР] Манифест '{md_name}' не собран. Отсутствуют файлы: {missing_files}. Пропускаем до полной сборки.")
            continue

        # РЕАЛЬНЫЙ ПРОЦЕСС №1: ФИКСАЦИЯ ОБНАРУЖЕНИЯ ГОТОВОГО КОМПЛЕКТА
        teacher = meta.get("teacher", "Unknown").strip()
        print(f"[АНАЛИЗАТОР] 🔥 Обнаружен полностью готовый комплект от '{teacher}'!")
        print("[АНАЛИЗАТОР] Поиск завершен. Анализ директории _input остановлен.")

        # Превентивная локальная проверка перед физическим переносом файлов
        if sorted(f for f in os.listdir(output_dir) if f.endswith(".md")):
            return "OUTPUT_BUSY"

        # РЕАЛЬНЫЙ ПРОЦЕСС №2: ФИЗИЧЕСКИЙ ПЕРЕНОС ФАЙЛОВ С ЛОГОМ ПО ФАКТУ ОПЕРАЦИИ (ПОЛНАЯ АНАЛОГИЯ С ЖУРНАЛОМ)
        # Поочередно перемещаем все медиафайлы комплекта "как есть" через shutil.move
        for file_name in attachments:
            old_file_path = os.path.join(input_dir, file_name)
            new_file_path = os.path.join(output_dir, file_name)
            
            shutil.move(old_file_path, new_file_path)
            print(f"[АНАЛИЗАТОР] Перемещаем медиафайл комплекта '{md_name}': {file_name}")

        # Перемещаем сам файл текстового манифеста .md в папку Выхода
        new_md_path = os.path.join(output_dir, md_name)
        shutil.move(md_path, new_md_path)
        print(f"[АНАЛИЗАТОР] Манифест {md_name} перемещен в _output.")

        # РЕАЛЬНЫЙ ПРОЦЕСС №3: ОФИЦИАЛЬНАЯ ФИКСАЦИЯ СТАТУСА УСПЕХА В GITHUB_ENV
        status = f"SUCCESS_{teacher}"
        if "GITHUB_ENV" in os.environ:
            with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as env_file:
                env_file.write(f"ANALYZER_STATUS={status}\n")

        print(f"[АНАЛИЗАТОР] Финальный статус работы модуля: {status}")
        return status

    print("[АНАЛИЗАТОР] Готовых или открытых по дате комплектов для переноса не обнаружено.")
    if "GITHUB_ENV" in os.environ:
        with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as env_file:
            env_file.write("ANALYZER_STATUS=NO_BUNDLE_READY\n")
    return "NO_BUNDLE_READY"

if __name__ == "__main__":
    status = analyze_and_process_media()
