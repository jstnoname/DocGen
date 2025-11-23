import argparse
from pathlib import Path

# Initialize the parser
parser = argparse.ArgumentParser(description='Calculate the average of a list of numbers.')

# Add an argument
parser.add_argument('path', type=Path, help='Absolute or relative path to the code file')
parser.add_argument(
    '--config', type=Path, default='pyproject.toml', help='Absolute or relative path to the config file'
)

args = parser.parse_args()
code_path, config_path = args.path, args.config


def check_path(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        print(f'{path} does not exist or is not a file')
        return False
    else:
        return True


if check_path(code_path) and check_path(config_path):
    print('Code path:', code_path)
    print('Config path:', config_path)
