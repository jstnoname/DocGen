from parser import Position
from typing import TypedDict

from ai_requester import PosWithDoc


class Element(TypedDict):
    key: str
    position: Position
    docstring: str


class CodeChanger:
    """Класс для добавления документации в код"""

    """
    на вход: {
        "name_of_file/ClassName": (Position(start_line, pos, end_line), "doc"),
        "name_of_file/func_name": (Position(start_line, pos, end_line), "doc"),
        "name_of_file/ClassName/method_name": (Position(start_line, pos, end_line), "doc")
    }
    """
    GENERATION_MARKER = "\u200c"

    def __init__(self, config: dict[str, str] | None = None, regen: bool = False):
        # config - настройки программы (в будущем)
        self.config = config or {}
        self.regen = regen

    def process_files(self, ai_data: dict[str, PosWithDoc]) -> None:
        """Основной метод для обработки всех файлов"""
        converted_data = self._convert_ai_data(ai_data)
        files_data = self._group_by_files(converted_data)

        for file_path, elements in files_data.items():
            self._process_single_file(file_path, elements)

    @staticmethod
    def _convert_ai_data(ai_data: dict[str, PosWithDoc]) -> dict[str, tuple[Position, str]]:
        """Конвертирует данные из AIRequester в формат, понятный CodeChanger"""
        return {key: (value.Position, value.Documentation) for key, value in ai_data.items()}

    @staticmethod
    def _group_by_files(ai_data: dict[str, tuple[Position, str]]) -> dict[str, list[Element]]:
        """Группирует элементы по файлам"""
        files_data: dict[str, list[Element]] = {}

        for key, (position, docstring) in ai_data.items():
            file_path = key.split('/')[0]

            if file_path not in files_data:
                files_data[file_path] = []

            files_data[file_path].append({'key': key, 'position': position, 'docstring': docstring})

        return files_data

    def _process_single_file(self, file_path: str, elements: list[Element]) -> None:
        """Обрабатывает один файл"""
        try:
            lines = self._read_file(file_path)

            # Сортируем по убыванию start_line (будем вставлять док., начиная с конца файла, чтобы позиция не измен.)
            elements.sort(key=lambda x: x['position'].start_line, reverse=True)

            modified = False
            for element in elements:
                position: Position = element['position']
                docstring: str = element['docstring']

                if self.regen:
                    # Заменяем только сгенерированную документацию и вставляем где ее нет
                    if self._has_existing_docstring(lines, position):
                        if self._is_generated_docstring(lines, position):
                            lines = self._replace_docstring(lines, position, docstring)
                            modified = True
                    else:
                        lines = self._insert_docstring(lines, position, docstring)
                        modified = True
                else:
                    if not self._has_existing_docstring(lines, position):
                        lines = self._insert_docstring(lines, position, docstring)
                        modified = True

            if modified:
                self._write_file(file_path, lines)
                print(f"Документация добавлена в {file_path}")
            else:
                print(f"Файл {file_path} уже содержит документацию")

        except FileNotFoundError:
            print(f"Файл не найден: {file_path}")
        except Exception as e:
            print(f"Ошибка при обработке {file_path}: {e}")

    def _is_generated_docstring(self, lines: list[str], position: Position) -> bool:
        """
        Проверяет, является ли существующий docstring сгенерированным
        (содержит GENERATION_MARKER)
        """
        start_line = position.start_line
        end_line = self._find_end_of_definition(lines, start_line)

        for i in range(end_line + 1, min(end_line + 10, len(lines))):
            line = lines[i].strip()

            if not line or line.startswith('#'):
                continue

            if line.startswith(('"""', "'''")):
                doc_lines = []
                current_line = i

                while current_line < len(lines):
                    doc_lines.append(lines[current_line])
                    if lines[current_line].rstrip().endswith(('"""', "'''")):
                        break
                    current_line += 1

                for doc_line in doc_lines:
                    if self.GENERATION_MARKER in doc_line:
                        return True

                return False
            break

        return False

    def _replace_docstring(self, lines: list[str], position: Position, new_doc: str) -> list[str]:
        """Заменяет существующий docstring на новый"""
        return self._insert_docstring(self._remove_docstring(lines, position), position, new_doc)

    def _remove_docstring(self, lines: list[str], position: Position) -> list[str]:
        """
        Удаляет существующий docstring на указанной позиции
        Возвращает новый список строк без docstring
        """
        start_line = position.start_line
        end_line = self._find_end_of_definition(lines, start_line)

        doc_start = -1
        for i in range(end_line + 1, min(end_line + 10, len(lines))):
            line = lines[i].strip()
            if line.startswith(('"""', "'''")):
                doc_start = i
                break

        if doc_start == -1:
            return lines

        doc_end = doc_start
        for i in range(doc_start, min(doc_start + 20, len(lines))):
            if lines[i].rstrip().endswith(('"""', "'''")):
                doc_end = i
                break

        return lines[:doc_start] + lines[doc_end + 1 :]

    @staticmethod
    def _read_file(file_path: str) -> list[str]:
        """Читает файл в список строк"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.readlines()

    @staticmethod
    def _write_file(file_path: str, lines: list[str]) -> None:
        """Записывает файл"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

    @staticmethod
    def _find_end_of_definition(lines: list[str], start_line: int) -> int:
        """Находит конец определения функции или класса (строку с двоеточием)"""
        if start_line < 0:
            return 0
        if start_line >= len(lines):
            return len(lines) - 1

        current_line = start_line

        if lines[start_line].strip().startswith('class '):
            return start_line

        # Для функций/методов - ищем двоеточие
        elif lines[start_line].strip().startswith('def '):
            paren_depth = 0
            bracket_depth = 0
            brace_depth = 0

            while current_line < len(lines):
                line = lines[current_line].rstrip()

                # Считаем скобки
                for char in line:
                    if char == '(':
                        paren_depth += 1
                    elif char == ')':
                        paren_depth -= 1
                    elif char == '[':
                        bracket_depth += 1
                    elif char == ']':
                        bracket_depth -= 1
                    elif char == '{':
                        brace_depth += 1
                    elif char == '}':
                        brace_depth -= 1

                # Если нашли двоеточие и все скобки закрыты
                if ':' in line and paren_depth <= 0 and bracket_depth <= 0 and brace_depth <= 0:
                    return current_line

                current_line += 1

        return start_line

    def _has_existing_docstring(self, lines: list[str], position: Position) -> bool:
        """Проверяет, есть ли уже docstring после указанной позиции"""
        start_line = position.start_line

        if start_line >= len(lines):
            return False

        end_line = self._find_end_of_definition(lines, start_line)

        if end_line >= len(lines) - 1:
            return False

        for i in range(end_line + 1, min(end_line + 10, len(lines))):
            line = lines[i].strip()

            if not line or line.startswith('#'):
                continue

            if line.startswith(('"""', "'''")):
                return True

            return False

        return False

    def _insert_docstring(self, lines: list[str], position: Position, docstring: str) -> list[str]:
        """Вставляет docstring"""
        if position.start_line >= len(lines):
            return lines

        if not docstring.strip():
            return lines

        start_line = position.start_line
        end_line = self._find_end_of_definition(lines, start_line)

        target_line = lines[end_line]
        indent = len(target_line) - len(target_line.lstrip())
        indent_str = ' ' * indent

        formatted_docstring = self._format_docstring(docstring, indent_str)

        return lines[: end_line + 1] + formatted_docstring + lines[end_line + 1 :]

    @staticmethod
    def _format_docstring(docstring: str, indent: str) -> list[str]:
        """Форматирует docstring с правильными отступами"""
        if not docstring or not docstring.strip():
            return []

        docstring_lines = docstring.strip().split('\n')
        formatted_lines = []

        extra_indent = '    '

        # однострочный docstring
        if len(docstring_lines) == 1:
            formatted_lines.append(f'{indent}{extra_indent}"""{docstring_lines[0]}"""\n')
        else:
            # многострочный docstring
            formatted_lines.append(f'{indent}{extra_indent}"""\n')
            for line in docstring_lines:
                formatted_lines.append(f'{indent}{extra_indent}{line}\n')
            formatted_lines.append(f'{indent}{extra_indent}"""\n')

        return formatted_lines
