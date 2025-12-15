import argparse
import sys
from parser import Parser, PosWithBody
from pathlib import Path

from ai_requester import AIRequester, PosWithDoc
from code_changer import CodeChanger


class DocGen:
    """
    Главный класс приложения DocGen.
    Координирует работу всех модулей: parser, AI и code_changer.
    """

    def __init__(self) -> None:
        self.parser = argparse.ArgumentParser(description='DocGen - automatically generate documentation for your code')
        self._setup_arguments()
        self._code_path: Path | None = None
        self._config_path: Path | None = None

    def _setup_arguments(self) -> None:
        """Настройка аргументов командной строки."""
        self.parser.add_argument(
            'path',
            type=Path,
            help='Absolute or relative path to the code file',
        )
        self.parser.add_argument(
            '--config',
            type=Path,
            default='pyproject.toml',
            help='Absolute or relative path to the config file',
        )

    def _parse_arguments(self) -> None:
        """Парсинг аргументов командной строки и сохранение путей."""
        args = self.parser.parse_args()
        self._code_path = args.path
        self._config_path = args.config

    def _validate_paths(self) -> bool:
        """Валидация путей к файлам."""
        if not self._check_path(self._code_path):
            return False
        if not self._check_path(self._config_path):
            return False
        return True

    @staticmethod
    def _check_path(path: Path | None) -> bool:
        """Проверка существования файла по указанному пути."""
        if path is None:
            return False
        if not path.exists():
            return False
        if not path.is_file():
            return False
        return True

    def _run_parser(self) -> dict[str, PosWithBody]:
        """
        Запуск парсера для анализа кода.

        Returns:
            dict: Словарь с распарсенными данными о коде
        """
        parser = Parser()
        parsed_data = parser.parse_from_file(str(self._code_path))
        return parsed_data

    def _generate_documentation(self, parsed_data: dict[str, PosWithBody]) -> dict[str, PosWithDoc]:
        """
        Генерация документации с помощью AI.

        Args:
            parsed_data: Словарь с данными от парсера

        Returns:
            dict: Словарь вида {
                "name_of_file/ClassName": (Position(start_line, pos, end_line), "doc"),
                "name_of_file/func_name": (Position(start_line, pos, end_line), "doc"),
                "name_of_file/ClassName/method_name": (Position(start_line, pos, end_line), "doc")
            }
        """
        # TODO: Реализовать когда будет готов модуль ai_module
        # ai = AIModule(self.config_path)
        # documentation = ai.generate(parsed_data)
        # return documentation
        docs = AIRequester(parsed_data).get_docs()
        return docs

    def _apply_changes(self, ai_data: dict[str, PosWithDoc]) -> None:
        """
        Применение изменений к коду (добавление документации).

        Args:
            ai_data: Словарь с документацией от AI в формате:
                {
                    "name_of_file/ClassName": (Position(start_line, pos, end_line), "doc"),
                    "name_of_file/func_name": (Position(start_line, pos, end_line), "doc"),
                    "name_of_file/ClassName/method_name": (Position(start_line, pos, end_line), "doc")
                }
        """
        # TODO: Реализовать когда будет готов модуль code_changer
        # changer = CodeChanger()
        # changer.process_files(ai_data)
        CodeChanger().process_files(ai_data)
        pass

    def run(self) -> None:
        """Основной метод запуска приложения."""
        try:
            # 1. Парсинг аргументов командной строки
            self._parse_arguments()

            # 2. Валидация путей
            if not self._validate_paths():
                sys.exit(1)

            # 3. Запуск парсера
            parsed_data = self._run_parser()

            # 4. Генерация документации через AI
            ai_data = self._generate_documentation(parsed_data)

            # 5. Применение изменений к коду
            self._apply_changes(ai_data)

        except Exception:
            sys.exit(1)


def main() -> None:
    """Точка входа в приложение."""
    app = DocGen()
    app.run()


if __name__ == '__main__':
    main()
