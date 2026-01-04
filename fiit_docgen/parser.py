import os.path
import re

from fiit_docgen.code_changer import CodeChanger
from fiit_docgen.records import ClassOrFunc, Position, PosWithBody


class Parser:
    """
    Парсер. Он парсит файл
    _dictionary: словарь, в который мы добавляем классы/функции и их позиции
    _stack: стек для отслеживания вложенности
    _path_to_current_file: путь к последнему прочитанному файлу
    """

    FUNC_PATTERN = re.compile(r'^(?:async )?def (\w+)')
    CLASS_PATTERN = re.compile(r'^class (\w+)')
    DECORATOR_PATTERN = re.compile(r'^@.*')

    def __init__(self, path_to_file: str) -> None:
        self._stack: list[ClassOrFunc] = []
        self._path_to_current_file = path_to_file
        self._file: list[str] = []
        self._dictionary: dict[str, PosWithBody] = {}

        self._dictionary = self._parse_all_from_file(self._path_to_current_file)

    @property
    def objects_length(self) -> int:
        return len(self._dictionary)

    def _parse_all_from_file(self, filename: str) -> dict[str, PosWithBody]:
        """Основная функция - считывает файл"""
        with open(filename, 'r', encoding='utf-8-sig') as f:
            self._path_to_current_file = os.path.realpath(filename)
            self._file = f.readlines()
        return self._parse(self._file)

    def parse_from_file(self, filename: str) -> dict[str, PosWithBody]:
        if len(self._dictionary) == 0:
            self._parse_all_from_file(filename)
        result = {}
        for path, pos_with_body in self._dictionary.items():
            if not CodeChanger.has_existing_docstring(self._file, pos_with_body.position):
                result[path] = pos_with_body
        return result

    def parse_generated_from_file(self, filename: str) -> dict[str, PosWithBody]:
        """Ищет функции и классы, которые были сгенерированы"""
        if len(self._dictionary) == 0:
            self._parse_all_from_file(filename)
        result = {}
        for path, pos_with_body in self._dictionary.items():
            if CodeChanger.is_generated_docstring(self._file, pos_with_body.position):
                result[path] = pos_with_body
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
            if re.match(self.DECORATOR_PATTERN, stripped):
                decorator_counter += 1
            if self._check_match(self.FUNC_PATTERN, stripped, i, decorator_counter, offset) or self._check_match(
                self.CLASS_PATTERN, stripped, i, decorator_counter, offset
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
            self._dictionary[prev.path].position.end_line = line_num - 1
            self._dictionary[prev.path].body = CodeChanger.remove_docstring(
                lines, self._dictionary[prev.path].position, False
            )
            self._dictionary[prev.path].position.start_line += self._dictionary[prev.path].position.decorators

    def _check_match(
        self, pattern: re.Pattern[str], line: str, line_num: int, decorator_counter: int, offset: int
    ) -> bool:
        """Проверяет, является ли строка функцией/классом, если да - добавляет её"""
        match = re.match(pattern, line)
        if match:
            self._add(match.group(1), line_num, decorator_counter, offset)
            return True
        return False

    def _add(self, func_name: str, line_num: int, decorator_counter: int, pos: int) -> None:
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
        self._dictionary[class_or_func.path] = PosWithBody(
            Position(line_num - decorator_counter, pos, decorators=decorator_counter)
        )
