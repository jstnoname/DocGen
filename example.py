import copy
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterator, NamedTuple, NewType


class Position(NamedTuple):
    x: int
    y: int


class Comparison(Enum):
    more = 1
    less = -1


class Condition(NamedTuple):
    comparison: Comparison
    value: int


@dataclass
class Cell:
    position: Position
    value: int
    condition: Condition = Condition(Comparison.more, 0)

    def __repr__(self) -> str:
        return f"{self.value}"

    def __str__(self) -> str:
        return f"{self.value}"

    def __eq__(self, other: Any) -> bool:
        return bool(self.value == other.value and self.position == other.position)


Field = NewType("Field", list[list[Cell]])


class Fillomino:
    """Головоломка филломино"""

    def __init__(self, width: int, height: int, field: Field) -> None:
        self._max_val = width * height
        self._width = width
        self._height = height
        self._field = field
        self._solutions: list[Field] = []

    def check(self) -> None:
        """Проверяет корректность входных данных"""
        for line in self._field:
            if len(line) != self._width:
                raise Exception(f"Некорректные входные данные: строка {line} отличается по длине")
            for cell in line:
                if cell.value < 0 or (cell.condition.comparison == Comparison.less and cell.condition.value <= 0):
                    raise Exception("Некорректные входные данные: числа не могут быть меньше нуля")
                if cell.value > self._max_val or (
                    cell.condition.comparison == Comparison.more and cell.condition.value > self._max_val
                ):
                    raise Exception(f"Некорректные входные данные: число {cell} превосходит площадь поля")

    def solve(self) -> None:
        """Основная логика решения: проверяет логичность одного хода и вызывается рекурсивно"""
        if self.is_field_complete():
            self._solutions.append(copy.deepcopy(self._field))
            return

        for x, line in enumerate(self._field):
            for y, cell in enumerate(line):
                if cell.value > 0:
                    continue
                if cell.condition.comparison == Comparison.less:
                    max = cell.condition.value
                    min = 1
                else:
                    min = cell.condition.value + 1
                    max = self._max_val + 1
                for number in range(min, max):
                    if self.is_valid(Position(x, y), number):
                        self.solve()
                    self._field[x][y].value = 0
                return
        return

    def position_generator(self, position: Position) -> Iterator[tuple[Position, int]]:
        """Генерирует соседние клетки, не выходящие за пределы поля, и их значения"""
        x, y = position
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            if 0 <= x + dx < self._height and 0 <= y + dy < self._width:
                position = Position(x + dx, y + dy)
                value = self._field[x + dx][y + dy].value
                yield position, value

    def is_valid(self, position: Position, number: int) -> bool:
        """Проверяет логичность действия (постановки числа в клетку) и выполняет его, если оно логично

        Действие считается логичным, если после него не появились группы клеток, противоречащие правилам игры
        1) Группы из N смежных клеток со значениями меньше чем N
        2) Группы из клеток со значениями N или 0 площадью меньше, чем N
        """
        x, y = position
        self._field[x][y].value = number
        connected_cells = [position]
        connected_cells = self.find_connected_cells(connected_cells, position, number)
        possible_cells = [position]
        possible_cells = self.find_all_possible_cells(possible_cells, position, number)
        if len(connected_cells) > number or len(possible_cells) < number:
            return False

        for neighbor, neighbor_number in self.position_generator(position):
            possible_cells = [neighbor]
            possible_cells = self.find_all_possible_cells(possible_cells, neighbor, neighbor_number)
            if len(possible_cells) < neighbor_number:
                return False

        return True

    def find_connected_cells(
        self,
        connected_cells: list[Position],
        position: Position,
        number: int,
    ) -> list[Position]:
        """Находит все клетки поля, которые при записи числа в данную клетку БУДУТ связаны с ней

        Клетка считается связанной, если:
        1) она имеет то же значение
        2) она является соседом данной клетки или другой связанной клетки
        """
        for neighbor, neighbor_number in self.position_generator(position):
            if neighbor_number != number or neighbor in connected_cells:
                continue
            connected_cells.append(neighbor)
            connected_cells = self.find_connected_cells(connected_cells, neighbor, number)
        return connected_cells

    def find_all_possible_cells(
        self,
        possible_cells: list[Position],
        position: Position,
        number: int,
    ) -> list[Position]:
        """Находит все клетки поля, которые при записи числа в данную клетку МОГУТ БЫТЬ связаны с ней

        Клетка считаются такой, если:
        1) её значение совпадает с числом или равно 0
        2) она является соседом данной клетки или другой такой клетки
        """
        for neighbor, neighbor_number in self.position_generator(position):
            if (neighbor_number != number and neighbor_number != 0) or neighbor in possible_cells:
                continue
            possible_cells.append(neighbor)
            possible_cells = self.find_all_possible_cells(possible_cells, neighbor, number)
        return possible_cells

    def is_field_complete(self) -> bool:
        """Проверяет, заполнено ли поле"""
        return all(cell.value != 0 for row in self._field for cell in row)
