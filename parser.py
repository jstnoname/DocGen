import os.path
import re
from typing import NamedTuple

FUNC_PATTERN = re.compile(r'^def (\w+)\(.*\)')
CLASS_PATTERN = re.compile(r'^class (\w+).*:')


class ClassOrFunc(NamedTuple):  # хз как назвать по-другому
    """NamedTuple для отображения классов и функций: path - полный путь, pos - позиция в строке"""

    path: str
    pos: int


class Position(NamedTuple):
    """NamedTuple для отображения позиции: line - номер строки (с нуля), pos - позиция в строке"""

    line: int
    pos: int

    def __repr__(self) -> str:
        """Отображение в виде (x,y)"""
        return f"({self.line},{self.pos})"


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
        for i, line in enumerate(lines):
            stripped = line.lstrip()
            func_match = re.match(FUNC_PATTERN, stripped)
            if func_match:
                self._add(func_match.group(1), i, len(line) - len(stripped))
                continue
            class_match = re.match(CLASS_PATTERN, stripped)
            if class_match:
                self._add(class_match.group(1), i, len(line) - len(stripped))
        return self._dictionary

    def _add(self, func_name: str, line: int, pos: int) -> None:
        """Добавляет функции и классы в словарь и стак"""
        if pos == 0:
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
        self._dictionary[class_or_func.path] = Position(line, pos)


# пример использования
if __name__ == '__main__':
    parser = Parser()
    result = parser.parse_from_file('example.py')
    for path in result:
        print(path, result[path])
