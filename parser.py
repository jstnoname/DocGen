import os.path
import re
from dataclasses import dataclass
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


class Parser:
    """
    Парсер. Он парсит файл
    _dictionary: словарь, в который мы добавляем классы/функции и их позиции
    _stack: стек для отслеживания вложенности
    _path_to_current_file: путь к последнему прочитанному файлу
    """

    def __init__(self) -> None:
        self._dictionary: dict[str, Position] = {}
        self._stack: list[ClassOrFunc] = []
        self._path_to_current_file = ""

    def parse_from_file(self, filename: str) -> dict[str, Position]:
        """Основная функция - считывает файл"""
        with open(filename, 'r') as f:
            self._path_to_current_file = os.path.realpath(filename)
            lines = f.readlines()
        return self._parse(lines)

    def _parse(self, lines: list[str]) -> dict[str, Position]:
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
                self._update_previous(offset, i)
            if re.match(DECORATOR_PATTERN, stripped):
                decorator_counter += 1
            if self._check_match(FUNC_PATTERN, stripped, i - decorator_counter, offset) or self._check_match(
                CLASS_PATTERN, stripped, i - decorator_counter, offset
            ):
                decorator_counter = 0
                last_offset = offset

        self._update_previous(0, len(lines) + 1)
        return self._dictionary

    def _update_previous(self, offset: int, line_num: int) -> None:
        """Указывает конец уже добавленных в словарь классов и функций"""
        for prev in reversed(self._stack):
            if prev.pos < offset or self._dictionary[prev.path].end_line > 0:
                return
            self._dictionary[prev.path].end_line = line_num - 1

    def _check_match(self, pattern: re.Pattern[str], line: str, line_num: int, offset: int) -> bool:
        """Проверяет, является ли строка функцией/классом, если да - добавляет её"""
        match = re.match(pattern, line)
        if match:
            self._add(match.group(1), line_num, offset)
            return True
        return False

    def _add(self, func_name: str, line_num: int, pos: int) -> None:
        """Добавляет функции и классы в словарь и стак"""
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
        self._dictionary[class_or_func.path] = Position(line_num, pos)


# пример использования
if __name__ == '__main__':
    parser = Parser()
    result = parser.parse_from_file('example.py')
    for path in result:
        print(path, result[path])
