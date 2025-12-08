import tempfile
from pathlib import Path
from code_changer import CodeChanger, Position


def test_group_by_files():
    # Проверяет группировку элементов по файлам
    ai_data = {
        "file1.py/func1": (Position(5, 0), "Docs for func1"),
        "file1.py/Class1": (Position(10, 0), "Docs for Class1"),
        "file2.py/func2": (Position(3, 0), "Docs for func2"),
    }
    changer = CodeChanger()
    grouped = changer._group_by_files(ai_data)
    assert len(grouped) == 2
    assert "file1.py" in grouped
    assert "file2.py" in grouped
    assert len(grouped["file1.py"]) == 2
    assert len(grouped["file2.py"]) == 1


def test_has_existing_docstring_no_docstring():
    # Проверяет отсутствие docstring
    lines = [
        "def foo():\n",
        "    pass\n"
    ]
    position = Position(0, 0)
    changer = CodeChanger()
    assert not changer._has_existing_docstring(lines, position)


def test_has_existing_docstring_with_docstring():
    # Проверяет наличие docstring
    lines = [
        "def foo():\n",
        '    """This is a docstring."""\n',
        "    pass\n"
    ]
    position = Position(0, 0)
    changer = CodeChanger()
    assert changer._has_existing_docstring(lines, position)


def test_insert_docstring_function():
    # Вставка однострочной docstring в функцию
    lines = [
        "def foo():\n",
        "    pass\n"
    ]
    position = Position(0, 0)
    docstring = "This is a test function."
    changer = CodeChanger()
    new_lines = changer._insert_docstring(lines, position, docstring)
    expected = [
        "def foo():\n",
        "    \"\"\"This is a test function.\"\"\"\n",
        "    pass\n"
    ]
    assert new_lines == expected


def test_insert_docstring_multiline():
    # Вставка многострочной docstring
    lines = [
        "def foo():\n",
        "    x = 1\n"
    ]
    position = Position(0, 0)
    docstring = "Line 1\nLine 2"
    changer = CodeChanger()
    new_lines = changer._insert_docstring(lines, position, docstring)
    expected = [
        "def foo():\n",
        '    """\n',
        '    Line 1\n',
        '    Line 2\n',
        '    """\n',
        "    x = 1\n"
    ]
    assert new_lines == expected


def test_insert_docstring_class():
    # Вставка docstring в класс
    lines = [
        "class MyClass:\n",
        "    pass\n"
    ]
    position = Position(0, 0)
    docstring = "A test class."
    changer = CodeChanger()
    new_lines = changer._insert_docstring(lines, position, docstring)
    expected = [
        "class MyClass:\n",
        "    \"\"\"A test class.\"\"\"\n",
        "    pass\n"
    ]
    assert new_lines == expected


def test_process_single_file_with_no_existing_docstring(tmp_path: Path):
    # Обработка файла: добавление docstring, если её нет
    file_path = tmp_path / "test.py"
    file_path.write_text("def foo():\n    return 42\n", encoding="utf-8")

    ai_data = {
        "test.py/foo": (Position(0, 0), "Returns 42.")
    }

    changer = CodeChanger()
    files_data = changer._group_by_files(ai_data)
    changer._process_single_file(str(file_path), files_data["test.py"])

    result = file_path.read_text(encoding="utf-8")
    assert '"""Returns 42."""' in result


def test_process_single_file_with_existing_docstring(tmp_path: Path):
    # Обработка файла: пропуск, если docstring уже есть
    file_path = tmp_path / "test.py"
    file_path.write_text('def foo():\n    """Already documented."""\n    return 42\n', encoding="utf-8")

    ai_data = {
        "test.py/foo": (Position(0, 0), "New doc.")
    }

    changer = CodeChanger()
    files_data = changer._group_by_files(ai_data)
    changer._process_single_file(str(file_path), files_data["test.py"])

    result = file_path.read_text(encoding="utf-8")
    assert '"""New doc."""' not in result
    assert '"""Already documented."""' in result


def test_find_end_of_definition_function_simple():
    # Поиск конца простой функции
    lines = ["def foo():\n", "    pass\n"]
    changer = CodeChanger()
    end = changer._find_end_of_definition(lines, 0)
    assert end == 0


def test_find_end_of_definition_function_multiline_signature():
    # Поиск конца функции с многострочной сигнатурой
    lines = [
        "def foo(\n",
        "    a: int,\n",
        "    b: str\n",
        "):\n",
        "    pass\n"
    ]
    changer = CodeChanger()
    end = changer._find_end_of_definition(lines, 0)
    assert end == 3


def test_find_end_of_definition_class():
    # Поиск конца определения класса
    lines = ["class A:\n", "    def method(self): pass\n"]
    changer = CodeChanger()
    end = changer._find_end_of_definition(lines, 0)
    assert end == 0