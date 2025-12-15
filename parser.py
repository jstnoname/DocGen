import os.path
import re
from dataclasses import dataclass, field
from typing import NamedTuple

FUNC_PATTERN = re.compile(r'^def (\w+)')
CLASS_PATTERN = re.compile(r'^class (\w+)')
DECORATOR_PATTERN = re.compile(r'^@.*')


class ClassOrFunc(NamedTuple):  # хз как назвать по-другому
    """NamedTuple для отображения классов и функций: path - полный путь, pos - позиция в строке"""

    path: str
    pos: int


@dataclass
class Position:
    """Класс для отображения позиции: start_line, end_line - строки (с нуля), pos - позиция в строке"""

    start_line: int
    pos: int
    end_line: int = 0

    def __repr__(self) -> str:
        """Отображение в виде (lines:X-Y, offset:Z)"""
        return f"(lines:{self.start_line}-{self.end_line}, offset:{self.pos})"


@dataclass
class PosWithBody:
    position: Position
    body: list[str] = field(default_factory=list)


class Parser:
    """
    Парсер. Он парсит файл
    _dictionary: словарь, в который мы добавляем классы/функции и их позиции
    _stack: стек для отслеживания вложенности
    _path_to_current_file: путь к последнему прочитанному файлу
    """

    def __init__(self) -> None:
        self._dictionary: dict[str, PosWithBody] = {}
        self._stack: list[ClassOrFunc] = []
        self._path_to_current_file = ""

    def parse_from_file(self, filename: str) -> dict[str, PosWithBody]:
        """Основная функция - считывает файл"""
        with open(filename, 'r', encoding='utf-8-sig') as f:
            self._path_to_current_file = os.path.realpath(filename)
            lines = f.readlines()
        return self._parse(lines)

    def parse_generated_from_file(self, filename: str) -> dict[str, PosWithBody]:
        """Ищет функции и классы, которые были сгенерированы"""
        if len(self._dictionary) == 0:
            self.parse_from_file(filename)
        result = {}
        for path, pos_with_body in self._dictionary.items():
            for line in pos_with_body.body[1:]:
                if "def" in line or "class" in line:
                    break
                if "\"\"\"" in line:
                    if "\u200c" in line:
                        result[path] = pos_with_body
                    break
        return result

    def _parse(self, lines: list[str]) -> dict[str, PosWithBody]:
        """Ищет функции и классы в списке строк"""
        decorator_counter = 0
        last_offset = 0
        for i, line in enumerate(lines):
            stripped = line.lstrip()
            offset = len(line) - len(stripped)
            if offset == 1:  # пустая строка
                continue
            if offset <= last_offset and not stripped.startswith(
                ')'
            ):  # обработка случая функций/классов с длинным началом
                self._update_previous(offset, i, lines)
            if re.match(DECORATOR_PATTERN, stripped):
                decorator_counter += 1
            if self._check_match(FUNC_PATTERN, stripped, i - decorator_counter, offset) or self._check_match(
                CLASS_PATTERN, stripped, i - decorator_counter, offset
            ):
                decorator_counter = 0
                last_offset = offset

        self._update_previous(0, len(lines) + 1, lines)
        return self._dictionary

    def _update_previous(self, offset: int, line_num: int, lines: list[str]) -> None:
        """Указывает конец уже добавленных в словарь классов и функций"""
        for prev in reversed(self._stack):
            if prev.pos < offset or self._dictionary[prev.path].position.end_line > 0:
                continue
            start, end = self._dictionary[prev.path].position.start_line, line_num - 1
            self._dictionary[prev.path].position.end_line = end
            self._dictionary[prev.path].body = lines[start:end]

    def _check_match(self, pattern: re.Pattern[str], line: str, line_num: int, offset: int) -> bool:
        """Проверяет, является ли строка функцией/классом, если да - добавляет её"""
        match = re.match(pattern, line)
        if match:
            self._add(match.group(1), line_num, offset)
            return True
        return False

    def _add(self, func_name: str, line_num: int, pos: int) -> None:
        """Добавляет функции и классы в словарь и стэк"""
        if pos == 0 and len(self._stack) != 0:
            self._stack.clear()
        if len(self._stack) == 0:
            class_or_func = ClassOrFunc(f"{self._path_to_current_file}/{func_name}", pos)
        else:
            previous = self._stack[-1]
            while previous.pos >= pos:
                self._stack.pop()
                previous = self._stack[-1]
            class_or_func = ClassOrFunc(f"{previous.path}/{func_name}", pos)
        self._stack.append(class_or_func)
        self._dictionary[class_or_func.path] = PosWithBody(Position(line_num, pos))
