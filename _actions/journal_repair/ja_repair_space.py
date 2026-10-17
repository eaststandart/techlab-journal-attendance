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
    Обрабатывает пробелы внутри значений полей YAML без нарушения отступов геометрии
    """
    stripped = line.strip()
    
    # ИГНОРИРУЕМ: Пустые строки и любые строки комментариев платформы со значком '#'
    if not stripped or stripped.startswith('#'):
        return line, False

    # Считываем геометрию оригинального начального отступа YAML-строки
    indent_len = len(line) - len(line.lstrip())
    indent_spaces = line[:indent_len]
    
    is_modified = False
    
    # Регулярное выражение для поиска ключей полей со значениями внутри кавычек или без них
    match_field = re.match(r'^([a-zA-Z0-9_\-]+)\s*:\s*(.*)$', stripped)
    
    if match_field:
        field_key = match_field.group(1).strip()
        field_value = match_field.group(2).strip()
        
        # Снимаем внешние кавычки для чистого анализа текста, если они есть
        has_quotes = False
        quote_char = '"'
        if (field_value.startswith('"') and field_value.endswith('"')) or (field_value.startswith("'") and field_value.endswith("'")):
            has_quotes = True
            quote_char = field_value
            field_value = field_value[1:-1]

        # СЦЕНАРИЙ А: Поле тега — выжигаем абсолютно все пробелы внутри под ноль
        if field_key == "tag":
            clean_value = field_value.replace(" ", "")
            if clean_value != field_value:
                field_value = clean_value
                is_modified = True
                
        # СЦЕНАРИЙ Б: Все остальные поля (name, direction, config и т.д.) — схлопываем множественные пробелы в один
        else:
            clean_value = re.sub(r' {2,}', ' ', field_value)
            if clean_value != field_value:
                field_value = clean_value
                is_modified = True

        # Собираем строку обратно, возвращая исходные кавычки и правильное двоеточие
        if is_modified:
            if has_quotes:
                new_line = f"{indent_spaces}{field_key}: {quote_char}{field_value}{quote_char}\n"
            else:
                new_line = f"{indent_spaces}{field_key}: {field_value}\n"
            
            # КАНОНИЧЕСКОЕ ЗРЯЧЕЕ ЛОГИРОВАНИЕ TECHLAB: Выводим исходную сырую строку из файла до очистки
            print(f"[ПРОБЕЛЫ ПОЛЕЙ] {filename}: {line.strip()!r} -> {new_line.strip()!r}", flush=True)
            return new_line, True

    # СЦЕНАРИЙ В: Строка списка (например, - "Галерея" или - name: "Вася")
    elif stripped.startswith('-'):
        # Если это элемент списка со словарем (например, - name: "Вася")
        if ":" in stripped:
            sub_line = stripped[1:].lstrip()
            sub_line_repaired, sub_mod = repair_space_line(sub_line, filename)
            if sub_mod:
                # ЖЕЛЕЗНЫЙ КАНОНИЧЕСКИЙ ПРОБЕЛ ПОСЛЕ ДЕФИСА ДЛЯ ИСКЛЮЧЕНИЯ СЛИПАНИЯ СТРОК
                return f"{indent_spaces}- {sub_line_repaired.lstrip()}", True
        else:
            # Если это простой плоский элемент списка строк (например, в блоке project_category_name)
            content = stripped[1:].strip()
            has_quotes = False
            quote_char = '"'
            if (content.startswith('"') and content.endswith('"')) or (content.startswith("'") and content.endswith("'")):
                has_quotes = True
                quote_char = content[0]
                content = content[1:-1].strip()
                
            clean_content = re.sub(r' {2,}', ' ', content)
            if clean_content != content:
                if has_quotes:
                    new_line = f"{indent_spaces}- {quote_char}{clean_content}{quote_char}\n"
                else:
                    new_line = f"{indent_spaces}- {clean_content}\n"
                
                print(f"[ПРОБЕЛЫ СПИСКА] {filename}: {stripped!r} -> {new_line.strip()!r}", flush=True)
                return new_line, True

    # ИНСПЕКТОР ВЫХОДА МОДУЛЯ
    print(f"[ВЫХОД НАШЕГО МОДУЛЯ] {filename}: {line.strip()!r}", flush=True)
    return line, False

