import tempfile
import os
from parser import Parser


def test_simple_function() -> None:
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


def test_simple_class() -> None:
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


def test_nested_functions() -> None:
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


def test_empty_file() -> None:
    code = ""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write(code)
        f.flush()
        parser = Parser()
        result = parser.parse_from_file(f.name)

    assert result == {}


def test_class_and_function_same_name() -> None:
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


def test_update_previous_on_file_end() -> None:
    code = """def f():
    x = 1
def g():
    y = 2
"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write(code)
        f.flush()
        parser = Parser()
        result = parser.parse_from_file(f.name)

    path = os.path.realpath(f.name)
    f_key = f"{path}/f"
    g_key = f"{path}/g"

    assert result[f_key].position.end_line == 1
    assert result[g_key].position.end_line == 4
    assert result[f_key].body == ["def f():\n"]
    assert result[g_key].body == ["def g():\n", "    y = 2\n"]