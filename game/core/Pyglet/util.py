from __future__ import annotations
from pyglet.event import EventDispatcher
from typing import (
    TypeVar, 
    Any, 
    Optional, 
    Iterable, 
    Callable, 
    overload, 
    Coroutine, 
    Union, 
    AsyncIterable
)

T=TypeVar("T")

Coro=Coroutine[Any, Any, T]

def _attrgetter(o: object, attr: str) -> Any:
    if "__" in attr:
        for i, v in enumerate(attr.split("__")):
            if i==0:
                attribute=getattr(o, v)
            else:
                attribute=getattr(attribute, v)
        return attribute
    else:
        return getattr(o, attr)

async def _aget(Object: AsyncIterable[T], /, **attributes: Any) -> Coro[Optional[T]]:
    async for item in Object:
        if all(_attrgetter(item, key)==value for key, value in attributes.items()):
            return item
    return None

def _get(Object: Iterable[T], /, **attributes: Any) -> Optional[T]:
    for item in Object:
        if all(_attrgetter(item, key)==value for key, value in attributes.items()):
            return item
    return None

@overload
def get(Object: AsyncIterable[T], /, **attributes: Any) -> Optional[T]:
    ...

@overload
def get(Object: Iterable[T], /, **attributes: Any) -> Optional[T]:
    ...



def get(Object: Union[Iterable[T], AsyncIterable[T]], /, **attributes: Any) -> Union[Optional[T], Coro[Optional[T]]]:
    """Возвращает объект в списке, атрибуты которого полностью совпадают
    
    Параметры
    ----------
    object: Iterable[T]
        Список объектов для поиска
    **attributes: Any
        Список атрибутов типа ключ, значение для поиска совпадений

        Если атрибут является другим объектом для поиска, то
        можно использовать \"__\" для поиска атрибута.

    Возвращает
    ----------
    Optional[T]
        Если найден объект, атрибуты которого совпадают, то оно
        возвращает этот объект

        Если объект не найден, то возвращает None
    """
    if hasattr(Object, "__aiter__"):
        return _aget(Object, **attributes)
    else:
        return _get(Object, **attributes)

async def _afind(Object: AsyncIterable[T], /, predicate: Callable[[T], bool]) -> Optional[T]:
    async for item in Object:
        if predicate(item):
            return item
    else:
        return None

def _find(Object: Iterable[T], /, predicate: Callable[[T], bool]) -> Optional[T]:
    for item in Object:
        if predicate(item):
            return item
    else:
        return None

@overload
def find(Object: AsyncIterable[T], predicate: Callable[[T], bool]) -> Coro[Optional[T]]:
    ...

@overload
def find(Object: Iterable[T], predicate: Callable[[T], bool]) -> Optional[T]:
    ...

def find(Object: Union[Iterable[T], AsyncIterable[T]], predicate: Callable[[T], bool]) -> Union[Optional[T], Coro[Optional[T]]]:
    """Возвращает объект в из списка, если функция `predicate` возвращает True

    Параметры
    ----------
    object: Union[Iterable[T], AsyncIterable[T]]
        Список объектов для поиска
    predicate: Callable[[T], bool]
        Функция для обработки
        В неё передаётся объект из списка
        Она должна возвращать `True` или `False`

    Возвращает
    ----------
    Union[Optional[T], Coro[Optional[T]]]
        Если найден объект, при котором `predicate` выдаёт `True`, то оно
        возвращает этот объект

        Если объект не найден, то возвращает `None`"""
    if hasattr(Object, "__aiter__"):
        return _afind(Object, predicate)
    else:
        return _find(Object, predicate)

class MouseEvent(EventDispatcher):
    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.dispatch_event('on_mouse_move', x, y, dx, dy)
    
    def on_mouse_motion(self, x, y, dx, dy):
        self.dispatch_event('on_mouse_move', x, y, dx, dy)
        
    def on_mouse_enter(self, x, y):
        self.dispatch_event('on_mouse_move', x, y, 0, 0)
        
    def on_mouse_leave(self, x, y):
        self.dispatch_event('on_mouse_move', x, y, 0, 0)
    
    def on_mouse_press(self, x, y, button, modifiers):
        self.dispatch_event('on_mouse_move', x, y, 0, 0)
    
    def on_mouse_release(self, x, y, button, modifiers):
        self.dispatch_event('on_mouse_move', x, y, 0, 0)
    
    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        self.dispatch_event('on_mouse_move', x, y, 0, 0)
    
    def on_mouse_move(self, x, y, dx=0, dy=0):
        """on_mouse_motion OR on_mouse_drag"""
        
MouseEvent.register_event_type('on_mouse_move')

    
def rgba(color):
    r, g, b, *a = color
    return r, g, b, a[0] if a else 255