from dataclasses import dataclass


@dataclass
class Position:
    start_line: int
    pos: int
    end_line: int = 0


class CodeChanger:
    """Класс для добавления документации в код"""
    """
    на вход: {
        "name_of_file/ClassName": (Position(start_line, pos, end_line), "doc"),
        "name_of_file/func_name": (Position(start_line, pos, end_line), "doc"),
        "name_of_file/ClassName/method_name": (Position(start_line, pos, end_line), "doc")
    }
    """
    def __init__(self, config: dict[str, str] | None= None):
        # config - настройки программы (в будущем)
        self.config = config or {}

    def process_files(self, ai_data: dict[str, tuple[Position, str]]) -> None:
        """Основной метод для обработки всех файлов"""
        files_data = self._group_by_files(ai_data)

        for file_path, elements in files_data.items():
            self._process_single_file(file_path, elements)

    def _group_by_files(self, ai_data: dict[str, tuple[Position, str]]) -> dict[str, list[dict[str, str | Position]]]:
        """Группирует элементы по файлам"""
        files_data = {}

        for key, (position, docstring) in ai_data.items():
            file_path = key.split('/')[0]

            if file_path not in files_data:
                files_data[file_path] = []

            files_data[file_path].append({
                'key': key,
                'position': position,
                'docstring': docstring
            })

        return files_data

    def _process_single_file(self, file_path: str, elements: list[dict[str, str | Position]]) -> None:
        """Обрабатывает один файл"""
        try:
            lines = self._read_file(file_path)

            # Сортируем по убыванию start_line (будем вставлять документацию, начиная с конца файла, чтобы позиция не изменилась)
            elements.sort(key=lambda x: x['position'].start_line, reverse=True)

            modified = False
            for element in elements:
                # проверяем, нет ли уже docstring
                if not self._has_existing_docstring(lines, element['position']):
                    lines = self._insert_docstring(
                        lines,
                        element['position'],
                        element['docstring']
                    )
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

    def _read_file(self, file_path: str) -> list[str]:
        """Читает файл в список строк"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.readlines()

    def _write_file(self, file_path: str, lines: list[str]) -> None:
        """Записывает файл"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

    #Пока с этим методом есть проблема: мы проверяем сразу след строку, но если в метод передается много аргументов (с переносами строк), то все ломается. надо переделывать
    def _has_existing_docstring(self, lines: list[str], position: Position) -> bool:
        """Проверяет, есть ли уже docstring после указанной позиции"""
        start_line = position.start_line

        # Ищем следующую непустую строку после определения метода/класса
        current_line = start_line + 1
        while current_line < len(lines) and current_line <= start_line + 3:
            line = lines[current_line].strip()

            if line.startswith(('"""', "'''")):
                return True

            # Если нашли непустую строку без docstring - значит docstring нет
            if line and not line.startswith(('"""', "'''")):
                return False

            current_line += 1

        return False

    def _insert_docstring(self, lines: list[str], position: Position, docstring: str) -> list[str]:
        """Вставляет docstring в код"""
        start_line = position.start_line

        current_line = lines[start_line]
        indent = len(current_line) - len(current_line.lstrip()) # кол-во пробелов в начале строки(отступы)
        indent_str = ' ' * indent

        # форматируем docstring
        formatted_docstring = self._format_docstring(docstring, indent_str)

        return lines[:start_line + 1] + formatted_docstring + lines[start_line + 1:]

    def _format_docstring(self, docstring: str, indent: str) -> list[str]:
        """Форматирует docstring с правильными отступами"""
        if not docstring.strip():
            return []

        docstring_lines = docstring.strip().split('\n')
        formatted_lines = []

        # однострочный docstring
        if len(docstring_lines) == 1:
            formatted_lines.append(f'{indent}    """{docstring_lines[0]}"""\n')
        else:
            # многострочный docstring
            formatted_lines.append(f'{indent}    """\n')
            for line in docstring_lines:
                formatted_lines.append(f'{indent}    {line}\n')
            formatted_lines.append(f'{indent}    """\n')

        return formatted_lines