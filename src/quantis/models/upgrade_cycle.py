"""Продвинутый циклический итератор с навигацией вперёд/назад.

Патерн Итератор: ✓
Single Responsibility: ✓ — только навигация по коллекции
"""

from __future__ import annotations

from typing import Any, Iterable


class UpgradeCycle:
    """Продвинутый цикл.

    Attributes:
        values: Кортеж элементов.
    """

    def __init__(self, values: Iterable[Any]) -> None:
        self._index = 0
        self.values: tuple[Any, ...] = tuple(values)

    def __iter__(self) -> "UpgradeCycle":
        """Возвращаем итератор

        Returns:
            UpgradeCycle: итератор
        """
        return self

    def __next__(self) -> Optional[Any]:
        """Возвращаем следующее значение

        Returns:
            Optional[Any]: следующее значение
        """
        self._index = (self._index + 1) % len(self.values)
        return self.values[self._index]

    def __len__(self) -> int:
        return len(self.values)

    def remove(self, item: Any) -> bool:
        """Удаляет элемент из цикла.

        Returns:
            ``True`` если элемент найден и удалён, иначе ``False``.
        """
        lst = list(self.values)
        try:
            idx = lst.index(item)
        except ValueError:
            return False
        lst.pop(idx)
        self.values = tuple(lst)
        if self._index >= len(self.values) > 0:
            self._index = len(self.values) - 1
        return True

    def move_previous(self) -> Optional[Any]:
        """Переключаемся на предыдущий трек

        Returns:
            Optional[Any]: предыдущий трек
        """
        if self._index != 0:
            self._index -= 1
        else:
            self._index = len(self.values) - 1
        return self.values[self._index]

    def peek_current(self) -> Optional[Any]:
        """Получаем текущий трек

        Returns:
            Optional[Any]: текущий трек
        """
        return self.values[self._index]

    def peek_previous(self) -> Optional[Any]:
        """Получаем предыдущий трек

        Returns:
            Optional[Any]: предыдущий трек
        """
        if self._index != 0:
            return self.values[self._index - 1]
        return self.values[len(self.values) - 1]

    def set_index(self, index: int) -> None:
        """Устанавливает текущий индекс."""
        self._index = index