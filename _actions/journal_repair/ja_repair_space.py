#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  ja_repair_space.py
@about   Модуль удаления лишних пробелов
@purpose Удаление множественных пробелов в именах/курсах и удаление пробелов в тегах
@author  TechLab
@version 1.0.0
"""

import re

def repair_space_line(line, filename=""):
    """
    Зряче сжимает множественные пробелы внутри значений полей YAML,
    сохраняя исходные комментарии, кавычки и геометрию отступов.
    """
    stripped = line.strip()
    
    # ИГНОРИРУЕМ: Пустые строки и любые строки комментариев платформы со значком '#'
    if not stripped or stripped.startswith('#'):
        return line, False

    # 1. Извлекаем и сохраняем оригинальную левую геометрию (отступы и дефисы)
    match_indent = re.match(r'^(\s*(?:-\s+)?)(.*)$', line.rstrip('\n'))
    if not match_indent:
        return line, False
        
    indent_prefix = match_indent.group(1)  # Сохраняет всё: "    " или "    - "
    content_part = match_indent.group(2)   # Текстовая часть: "name: \"  Баранова  Лиза\""
    
    # 2. Проверяем, является ли строка парой Ключ: Значение
    match_field = re.match(r'^([a-zA-Z0-9_\-]+)\s*:\s*(.*)$', content_part)
    if not match_field:
        return line, False
        
    field_key = match_field.group(1).strip()
    field_value = match_field.group(2).strip()
    
    # Игнорируем строки, если значение пустое
    if not field_value:
        return line, False
        
    # 3. Зряче определяем и снимаем внешние кавычки значения
    has_quotes = False
    quote_char = '"'
    if (field_value.startswith('"') and field_value.endswith('"')) or (field_value.startswith("'") and field_value.endswith("'")):
        has_quotes = True
        quote_char = field_value[0]
        field_value = field_value[1:-1] # Оставляем живые внутренние пробелы

    is_modified = False
    
    # СЦЕНАРИЙ А: Поле системного тега — полностью выжигаем любые пробелы внутри значения под ноль
    if field_key == "tag":
        clean_value = field_value.replace(" ", "")
        if clean_value != field_value:
            field_value = clean_value
            is_modified = True
            
    # СЦЕНАРИЙ Б: Все остальные текстовые поля — строго схлопываем множественные пробелы (2 и более) в один
    else:
        clean_value = re.sub(r' {2,}', ' ', field_value)
        if clean_value != field_value:
            field_value = clean_value
            is_modified = True

    # 4. Собираем строку обратно в канонический вид без разрушения структуры
    if is_modified:
        if has_quotes:
            new_line = f"{indent_prefix}{field_key}: {quote_char}{field_value}{quote_char}\n"
        else:
            new_line = f"{indent_prefix}{field_key}: {field_value}\n"
            
        # ПЕЧАТАЕМ ЧИСТЫЙ ЛОГ ТЕCHLAB ИЗ СВЕЖЕЙ СТРОКИ ДО И ПОСЛЕ ИЗМЕНЕНИЯ
        print(f"[ПРОБЕЛЫ ПОЛЕЙ] {filename}: {line.strip()!r} -> {new_line.strip()!r}", flush=True)
        return new_line, True

    return line, False
