import argparse
import os
import sys
from pathlib import Path

from docgen.ai_requester import AIRequester
from docgen.code_changer import CodeChanger
from docgen.parser import Parser
from docgen.records import PosWithBody, PosWithDoc


class DocGen:
    """Главный класс приложения DocGen."""

    def __init__(self) -> None:
        self.parser = argparse.ArgumentParser(description='DocGen - automatically generate documentation for your code')
        self._setup_arguments()
        self._code_path: Path | None = None
        self._config_path: Path | None = None
        self._api_key: str | None = None
        self._regen: bool = False
        self._full: bool = False

    def _setup_arguments(self) -> None:
        self.parser.add_argument('path', type=Path, help='Path to the code file')
        self.parser.add_argument('--config', type=Path, default='pyproject.toml', help='Path to config file')
        self.parser.add_argument('--api-key', type=str, help='Gemini API key')
        self.parser.add_argument('-r', '--regen', action='store_true', help='Regenerate existing documentation')
        self.parser.add_argument(
            '-f', '--full', action='store_true', help='Generate documentation for all objects in file'
        )

    def _parse_arguments(self) -> None:
        args = self.parser.parse_args()
        self._code_path = args.path
        self._config_path = args.config
        self._api_key = args.api_key or os.getenv('GEMINI_API_KEY')
        self._regen = args.regen
        self._full = args.full

    def _validate_paths(self) -> bool:
        if not self._check_path(self._code_path):
            return False
        if self._config_path and self._config_path != Path('pyproject.toml'):
            return self._check_path(self._config_path)
        return True

    def _validate_api_key(self) -> bool:
        return self._api_key is not None and len(self._api_key) > 0

    @staticmethod
    def _check_path(path: Path | None) -> bool:
        return path is not None and path.exists() and path.is_file()

    def _run_parser(self) -> dict[str, PosWithBody]:
        print(f'Parsing file: {self._code_path}')
        parser = Parser()
        if self._regen:
            result = parser.parse_generated_from_file(str(self._code_path))
            print(f'Found {len(result)} items with generated documentation to regenerate')
        else:
            result = parser.parse_from_file(str(self._code_path))
            print(f'Found {len(result)} items to document')
        return result

    def _generate_documentation(self, parsed_data: dict[str, PosWithBody]) -> dict[str, PosWithDoc]:
        print('Generating documentation with AI...')
        result = AIRequester(parsed_data, apikey=self._api_key or "").get_docs()
        print(f'Generated documentation for {len(result)} items')
        return result

    def _apply_changes(self, ai_data: dict[str, PosWithDoc]) -> None:
        print('Applying changes to code...')
        CodeChanger(regen=self._regen).process_files(ai_data)
        print('Documentation successfully applied!')

    def run(self) -> None:
        try:
            self._parse_arguments()
            if not self._validate_paths():
                print('Error: Invalid file paths')
                sys.exit(1)
            if not self._validate_api_key():
                print('Error: Gemini API key is required. Use --api-key or set GEMINI_API_KEY environment variable.')
                sys.exit(1)
            parsed_data = self._run_parser()
            ai_data = self._generate_documentation(parsed_data)
            self._apply_changes(ai_data)
        except Exception as e:
            print(f'Error: {e}')
            sys.exit(1)


def main() -> None:
    DocGen().run()
