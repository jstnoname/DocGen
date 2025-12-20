import tempfile
import os
from docgen.parser import Parser
from docgen.records import Position, PosWithBody


def test_simple_function():
    # Простая функция: проверка start_line, end_line и body
    code = """def foo():
    pass
"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write(code)
        f.flush()
        parser = Parser()
        result = parser.parse_from_file(f.name)

    path = os.path.realpath(f.name)
    key = f"{path}/foo"
    assert key in result
    pos = result[key].position
    assert pos.start_line == 0
    assert pos.end_line == 2
    assert result[key].body == ["def foo():\n", "    pass\n"]


def test_simple_class():
    # Простой класс с методом
    code = """class MyClass:
    def method(self):
        pass
"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write(code)
        f.flush()
        parser = Parser()
        result = parser.parse_from_file(f.name)

    path = os.path.realpath(f.name)
    class_key = f"{path}/MyClass"
    method_key = f"{class_key}/method"

    assert class_key in result
    assert method_key in result
    assert result[class_key].position.start_line == 0
    assert result[class_key].position.end_line == 3
    assert result[class_key].body == [
        "class MyClass:\n",
        "    def method(self):\n",
        "        pass\n"
    ]
    assert result[method_key].position.start_line == 1
    assert result[method_key].position.end_line == 3
    assert result[method_key].body == ["    def method(self):\n", "        pass\n"]


def test_nested_functions():
    # Вложенные функции
    code = """def outer():
    def inner():
        return 42
    return inner()
"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write(code)
        f.flush()
        parser = Parser()
        result = parser.parse_from_file(f.name)

    path = os.path.realpath(f.name)
    outer_key = f"{path}/outer"
    inner_key = f"{outer_key}/inner"

    assert outer_key in result
    assert inner_key in result
    assert result[inner_key].position.start_line == 1
    assert result[inner_key].position.end_line == 2
    assert result[inner_key].body == ["    def inner():\n"]
    assert result[outer_key].position.start_line == 0
    assert result[outer_key].position.end_line == 4
    assert result[outer_key].body == [
        "def outer():\n",
        "    def inner():\n",
        "        return 42\n",
        "    return inner()\n"
    ]


def test_empty_file():
    # Пустой файл → пустой результат
    code = ""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write(code)
        f.flush()
        parser = Parser()
        result = parser.parse_from_file(f.name)

    assert result == {}


def test_class_and_function_same_name():
    # Имя класса и функции совпадают — функция перезаписывает (последняя)
    code = """class A:
    def method(self):
        pass

def A():
    return 1
"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write(code)
        f.flush()
        parser = Parser()
        result = parser.parse_from_file(f.name)

    path = os.path.realpath(f.name)
    a_key = f"{path}/A"
    assert a_key in result
    assert result[a_key].position.start_line == 4
    assert result[a_key].body == ["def A():\n", "    return 1\n"]

def test_empty_function_body():
    # Функция с пустым телом (только pass)
    code = """def empty():
    pass
"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write(code)
        f.flush()
        parser = Parser()
        result = parser.parse_from_file(f.name)

    path = os.path.realpath(f.name)
    key = f"{path}/empty"
    assert key in result
    assert result[key].body == ["def empty():\n", "    pass\n"]


def test_class_with_empty_body():
    # Пустой класс
    code = """class Empty:
    pass
"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write(code)
        f.flush()
        parser = Parser()
        result = parser.parse_from_file(f.name)

    path = os.path.realpath(f.name)
    key = f"{path}/Empty"
    assert key in result
    assert result[key].body == ["class Empty:\n", "    pass\n"]


def test_nested_class_in_function():
    # Вложенный класс (редко, но возможно)
    code = """def container():
    class Inner:
        def method(self): pass
    return Inner
"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write(code)
        f.flush()
        parser = Parser()
        result = parser.parse_from_file(f.name)

    path = os.path.realpath(f.name)
    inner_key = f"{path}/container/Inner"
    method_key = f"{inner_key}/method"

    assert inner_key in result
    assert method_key in result
    assert result[inner_key].position.start_line == 1
    assert result[method_key].position.start_line == 2


def test_correct_end_line_after_multiline_function():
    # Функция с многострочной сигнатурой
    code = """def long_func(
    a: int,
    b: str
):
    return a + len(b)
"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write(code)
        f.flush()
        parser = Parser()
        result = parser.parse_from_file(f.name)

    path = os.path.realpath(f.name)
    key = f"{path}/long_func"
    assert key in result
    assert result[key].position.start_line == 0
    assert result[key].position.end_line == 5
    assert "return a + len(b)" in ''.join(result[key].body)


def test_position_repr():
    # Проверка корректности __repr__ у Position
    pos = Position(start_line=5, pos=4, end_line=10)
    assert repr(pos) == "(lines:5-10, offset:4)"


def test_pos_with_body_default_factory():
    # Проверка, что body по умолчанию — пустой список (а не общий для всех)
    item1 = PosWithBody(Position(0, 0))
    item2 = PosWithBody(Position(1, 0))
    item1.body.append("x")
    assert item2.body == []