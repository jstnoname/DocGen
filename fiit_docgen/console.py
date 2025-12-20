import argparse
import os
import sys
from pathlib import Path

from fiit_docgen.ai_requester import AIRequester
from fiit_docgen.code_changer import CodeChanger
from fiit_docgen.parser import Parser
from fiit_docgen.records import PosWithBody, PosWithDoc


class DocGen:
    """Главный класс приложения DocGen."""

    def __init__(self) -> None:
        self.parser = argparse.ArgumentParser(description='DocGen - automatically generate documentation for your code')
        self._setup_arguments()
        self._code_path: Path | None = None
        self._api_key: str | None = None
        self._regen: bool = False

    def _setup_arguments(self) -> None:
        self.parser.add_argument('path', type=Path, help='Path to the code file')
        self.parser.add_argument('--api-key', '-a', type=str, help='Gemini API key')
        self.parser.add_argument('-r', '--regen', action='store_true', help='Regenerate existing documentation')

    def _parse_arguments(self) -> None:
        args = self.parser.parse_args()
        self._code_path = args.path
        self._api_key = args.api_key or os.getenv('GEMINI_API_KEY')
        self._regen = args.regen

    def _validate_paths(self) -> bool:
        if not self._check_path(self._code_path):
            return False
        return True

    def _validate_api_key(self) -> bool:
        return self._api_key is not None and len(self._api_key) > 0

    @staticmethod
    def _check_path(path: Path | None) -> bool:
        return path is not None and path.exists() and path.is_file()

    def _run_parser(self) -> dict[str, PosWithBody]:
        print(f'Parsing file: {self._code_path}')
        parser = Parser(str(self._code_path))
        if self._regen:
            result = parser.parse_generated_from_file(str(self._code_path))
            print(f'Found {len(result)} items of {parser.objects_length} with generated documentation to regenerate')
        else:
            result = parser.parse_from_file(str(self._code_path))
            print(f'Found {len(result)} items of {parser.objects_length} to document')
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
            if len(parsed_data) == 0:
                print('No objects to doc found')
                sys.exit(0)
            ai_data = self._generate_documentation(parsed_data)
            self._apply_changes(ai_data)
        except Exception as e:
            print(f'Error: {e}')
            sys.exit(1)


def main() -> None:
    DocGen().run()
