
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@module  journal_data_repair.py
@about   Проверка и исправление файла расписания
@purpose Приведение времени и направлений к единому стандарту базы данных
@author  TechLab
@version 1.0.0
"""

import os
import sys
import json
from datetime import datetime, timezone

# ==============================================================================
# НАСТРОЙКИ
# ==============================================================================

DATA_DIR = "_data"
SIGNAL_FILE = os.path.join(DATA_DIR, "signal-repair.json")
STATUS_FILE = os.path.join(DATA_DIR, "repair-status.json")


def write_status(status):
    """Сохраняет текущий статус обработки."""
    payload = {
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"[СТАТУС] {status}", flush=True)


def repair_yaml_file(file_path):
    """Проверяет и исправляет один файл расписания."""
    filename = os.path.basename(file_path)
    print(f"[ПРОВЕРКА] Файл: {filename}", flush=True)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"[ОШИБКА] {filename}: чтение файла: {e}", flush=True)
        return False

    is_modified = False
    repaired_lines = []

    electronics_letters = ["э", "Э", "е", "Е", "e", "E"]
    joinery_letters = ["с", "С", "c", "C"]

    for line in lines:
        original_line = line
        stripped = line.strip()

        # 1. Нормализация времени группы.
        if (
            line.startswith("  ")
            and not line.startswith("    ")
            and stripped.endswith(":")
        ):
            raw_time = (
                stripped[:-1]
                .replace('"', '')
                .replace("'", '')
                .strip()
            )
            digits = "".join(c for c in raw_time if c.isdigit())

            if len(digits) == 4:
                clean_time = f"{digits[:2]}:{digits[2:4]}"
                repaired_line = f'  "{clean_time}":\n'

                if repaired_line != line:
                    print(
                        f"[ВРЕМЯ] {filename}: "
                        f"{stripped!r} -> {repaired_line.strip()!r}",
                        flush=True
                    )
                    line = repaired_line
                    is_modified = True

        # 2. Нормализация направления.
        if line.startswith("      direction:"):
            raw_val = (
                line.split(":", 1)[1]
                .replace('"', '')
                .replace("'", '')
                .strip()
            )

            clean_val = "".join(
                c for c in raw_val
                if c not in ["[", "]", "\\", "/", ";"]
            ).strip()

            repaired_val = clean_val

            if (
                clean_val in electronics_letters
                or "электрон" in clean_val.lower()
            ):
                repaired_val = "электронное конструирование"
            elif (
                clean_val in joinery_letters
                or "столяр" in clean_val.lower()
            ):
                repaired_val = "столярное дело"

            repaired_val = " ".join(repaired_val.split()).strip()
            repaired_line = f'      direction: "{repaired_val}"\n'

            if repaired_line != line:
                print(
                    f"[КУРС] {filename}: "
                    f"{raw_val!r} -> {repaired_val!r}",
                    flush=True
                )
                line = repaired_line
                is_modified = True

        # 3. Очистка имени.
        if line.startswith("    - name:"):
            old_raw_val = line.split(":", 1)[1].strip()

            clean_val = "".join(
                c for c in old_raw_val
                if c not in ["[", "]", "\\", "/", ";", '"', "'"]
            ).strip()

            clean_val = " ".join(clean_val.split()).strip()
            repaired_line = f'    - name: "{clean_val}"\n'

            if repaired_line != line:
                print(
                    f"[ИМЯ] {filename}: "
                    f"{old_raw_val!r} -> {clean_val!r}",
                    flush=True
                )
                line = repaired_line
                is_modified = True

        # 4. Очистка завершающих знаков тега.
        if line.startswith("      tag:"):
            raw_val = (
                line.split(":", 1)[1]
                .replace('"', '')
                .replace("'", '')
                .strip()
            )
            clean_val = raw_val

            if (
                clean_val.startswith("#techlab-")
                or clean_val.startswith("@")
            ):
                while clean_val and clean_val[-1] in [
                    "!", ".", ",", ";", '"', "'"
                ]:
                    clean_val = clean_val[:-1]

            clean_val = " ".join(clean_val.split()).strip()
            repaired_line = f'      tag: "{clean_val}"\n'

            if repaired_line != line:
                print(
                    f"[ТЕГ] {filename}: "
                    f"{raw_val!r} -> {clean_val!r}",
                    flush=True
                )
                line = repaired_line
                is_modified = True

        if line != original_line:
            is_modified = True

        repaired_lines.append(line)

    if not is_modified:
        print(
            f"[ИТОГ] {filename}: исправления не требуются.",
            flush=True
        )
        return True

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(repaired_lines)

        print(
            f"[ИТОГ] {filename}: исправления сохранены.",
            flush=True
        )
        return True

    except Exception as e:
        print(
            f"[ОШИБКА] {filename}: запись файла: {e}",
            flush=True
        )
        return False


def main():
    # Проверяем наличие папки данных.
    if not os.path.isdir(DATA_DIR):
        print(f"[ОШИБКА] Папка {DATA_DIR} не найдена.", flush=True)
        sys.exit(1)

    # Один запрос должен содержать логин одного преподавателя.
    if not os.path.isfile(SIGNAL_FILE):
        print(
            f"[ОШИБКА] Входящий сигнал {SIGNAL_FILE} не найден.",
            flush=True
        )
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
            raise ValueError(
                "teacher_login отсутствует или содержит недопустимый путь"
            )

    except Exception as e:
        print(f"[ОШИБКА] Некорректный сигнал: {e}", flush=True)
        try:
            write_status("error")
        except Exception as status_error:
            print(
                f"[ОШИБКА] Не удалось сохранить статус: {status_error}",
                flush=True
            )
        sys.exit(1)

    filename = f"journal-attendance-{target_teacher}.yml"
    file_path = os.path.join(DATA_DIR, filename)

    print(f"[СИГНАЛ] Преподаватель: {target_teacher}", flush=True)
    print(f"[СИГНАЛ] Целевой файл: {filename}", flush=True)

    # Обрабатываем исключительно целевой файл.
    if not os.path.isfile(file_path):
        print(f"[ОШИБКА] Файл {filename} не найден.", flush=True)
        try:
            write_status("error")
        except Exception as e:
            print(f"[ОШИБКА] Не удалось сохранить статус: {e}", flush=True)
        sys.exit(1)

    try:
        success = repair_yaml_file(file_path)
    except Exception as e:
        print(f"[ОШИБКА] Критический сбой {filename}: {e}", flush=True)
        success = False

    if not success:
        try:
            write_status("error")
        except Exception as e:
            print(f"[ОШИБКА] Не удалось сохранить статус: {e}", flush=True)
        sys.exit(1)

    # Проверка и обработка завершены успешно.
    # Переход в off выполняется отдельным шагом GitHub Actions.
    try:
        write_status("on")
    except Exception as e:
        print(f"[ОШИБКА] Не удалось сохранить статус: {e}", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
