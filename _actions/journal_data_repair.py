#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  journal_data_repair.py
@about   Локальный модуль предочистки и защиты синтаксиса YAML Журнала
@purpose Лечение слэшей времени и опечаток кавычек электроники на диске раннера
@author TechLab
@version 1.0.0
"""

import os
import re

def fix_local_yaml_file(yaml_path):
    if not os.path.exists(yaml_path):
        return False

    try:
        # 1. Читаем сырой текст файла прямо с диска виртуальной машины Журнала
        with open(yaml_path, 'r', encoding='utf-8') as f:
            yaml_text_orig = f.read()

        repaired_yaml_text = yaml_text_orig
        teacher_login = os.path.basename(yaml_path).replace('journal-attendance-', '').replace('.yml', '').strip()

        # ЗОНА №1: Лечение времени со слэшем между цифрами (например, 11\00 или 12/00 -> 11:00)
        raw_slash_matches = re.findall(r'\d{1,2}\\\d{2}|\d{1,2}/\d{2}', repaired_yaml_text)
        if raw_slash_matches:
            for bad_time_str in raw_slash_matches:
                good_time_str = bad_time_str.replace('\\', ':').replace('/', ':')
                print(f"[ЩИТ ЖУРНАЛА] ⏰ Найдена локальная опечатка слэша во времени: '{bad_time_str}' -> Исправляем на '{good_time_str}'")
            
            repaired_yaml_text = re.sub(r'(\d{1,2})\\(\d{2})', r'\1:\2', repaired_yaml_text)
            repaired_yaml_text = re.sub(r'(\d{1,2})/(\d{2})', r'\1:\2', repaired_yaml_text)

        # ЗОНА №2: Лечение направлений электроники (маленькие буквы, заглавные и кривые скобки)
        bad_chars_matches = re.findall(r'\[([eеЕЭ])\]', repaired_yaml_text)
        if bad_chars_matches:
            for char in bad_chars_matches:
                print(f"[ЩИТ ЖУРНАЛА] 🔤 Найдена опечатка раскладки букв направления для {teacher_login}: '[{char}]' -> Исправляем на '[э]'")
            repaired_yaml_text = re.sub(r'\[[eеЕЭ]\]', '[э]', repaired_yaml_text)

        # Лечение ложных одиначных или двойных кавычек внутри квадратных скобок ['], ["]
        bad_quotes_matches = re.findall(r'(\[\'\]|\[\"\])', repaired_yaml_text)
        if bad_quotes_matches:
            for quote_item in bad_quotes_matches:
                print(f"[ЩИТ ЖУРНАЛА] 🛑 Найдена опечатка ложных кавычек в скобках: '{quote_item}' -> Исправляем на '[э]'")
            repaired_yaml_text = re.sub(r'\[[\'\"]\]', '[э]', repaired_yaml_text)

        # Лечение критического бага трипл-кавычек двойная-одиночная-двойная '"' (разрушает PyYAML)
        if '\"\'\"' in repaired_yaml_text:
            count_triple = repaired_yaml_text.count('\"\'\"')
            print(f"[ЩИТ ЖУРНАЛА] 💥 Найдена критическая опечатка тройных кавычек '\"'\"' ({count_triple} шт.) -> Исправляем на '[э]'")
            repaired_yaml_text = repaired_yaml_text.replace('\"\'\"', '[э]')

        # 2. Сохраняем вылеченный синтаксически идеальный текст обратно на локальный диск Журнала
        if repaired_yaml_text != yaml_text_orig:
            with open(yaml_path, 'w', encoding='utf-8') as f:
                f.write(repaired_yaml_text)
            print(f"[ЩИТ ЖУРНАЛА] 🟢 Локальный файл расписания для '{teacher_login}' успешно вылечен на диске раннера!")
            return True

    except Exception as e:
        print(f"[ЩИТ ЖУРНАЛА] ❌ Ошибка при локальном лечении файла YAML: {str(e)}")
        
    return False
