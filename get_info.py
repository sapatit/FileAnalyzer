import os
import time
import argparse
import logging
from dataclasses import dataclass
from typing import List, Optional, Set, Callable
from tabulate import tabulate
from pathlib import Path
from contextlib import suppress
from enum import Enum
from tqdm import tqdm
from datetime import datetime


# Настройка логирования
class LogLevel(Enum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


def setup_logging(level: LogLevel) -> None:
    """Настройка логирования."""
    logging.basicConfig(level=level.value, format='%(asctime)s - %(levelname)s - %(message)s')


@dataclass
class FileInfo:
    """Класс для хранения информации о файле."""
    name: str
    path: Path
    size: int
    modified_time: str
    parent_dir: Path

    @classmethod
    def from_path(cls, filepath: Path) -> Optional['FileInfo']:
        """Создание объекта FileInfo из пути к файлу."""
        try:
            filetime = filepath.stat().st_mtime
            formatted_time = time.strftime("%d.%m.%Y %H:%M", time.localtime(filetime))
            filesize = filepath.stat().st_size
            return cls(name=filepath.name, path=filepath, size=filesize, modified_time=formatted_time,
                       parent_dir=filepath.parent)
        except FileNotFoundError:
            logging.error(f"Файл не найден: {filepath}")
            return None
        except PermissionError:
            logging.error(f"Нет доступа к файлу: {filepath}")
            return None
        except OSError as e:
            logging.error(f"Ошибка при получении информации о файле {filepath}: {e}")
            return None


def collect_file_info(directory: Path, extensions: Set[str], recursive: bool = True) -> List[FileInfo]:
    """Сбор информации о файлах в указанном каталоге."""
    file_info_list = []
    search_pattern = directory.rglob('*') if recursive else directory.glob('*')

    for filepath in tqdm(search_pattern, desc="Обработка файлов"):
        if filepath.is_file() and (not extensions or filepath.suffix.lower() in extensions):
            file_info = FileInfo.from_path(filepath)
            if file_info:
                file_info_list.append(file_info)
    return file_info_list


def display_file_info(file_info_list: List[FileInfo], sort_by: Optional[Callable[[FileInfo], any]] = None) -> None:
    """Отображение информации о файлах в виде таблицы."""
    if not file_info_list:
        logging.info("Файлы не найдены.")
        return

    if sort_by:
        file_info_list.sort(key=sort_by)

    table = [(f.name, str(f.path), f.size, f.modified_time, str(f.parent_dir)) for f in file_info_list]
    output = tabulate(table,
                      headers=["Имя файла", "Путь", "Размер (байт)", "Время изменения", "Родительская директория"],
                      tablefmt="grid")
    print(output)


def write_to_file(file_info_list: List[FileInfo], output_file: Optional[Path], output_format: str) -> None:
    """Запись информации о файлах в указанный файл или вывод в консоль."""
    if output_file:
        try:
            with output_file.open('w', encoding='utf-8') as f:
                table = [(f.name, str(f.path), f.size, f.modified_time, str(f.parent_dir)) for f in file_info_list]
                output = tabulate(table, headers=["Имя файла", "Путь", "Размер (байт)", "Время изменения",
                                                  "Родительская директория"], tablefmt=output_format)
                f.write(output)
                logging.info(f"Информация о файлах записана в файл {output_file}")
        except PermissionError:
            logging.error(f"Нет доступа для записи в файл {output_file}")
        except IOError as e:
            logging.error(f"Ошибка ввода-вывода при записи в файл {output_file}: {e}")
        except Exception as e:
            logging.error(f"Неизвестная ошибка при записи в файл {output_file}: {e}")

    else:
        table = [(f.name, str(f.path), f.size, f.modified_time, str(f.parent_dir)) for f in file_info_list]
        output = tabulate(table, headers=["Имя файла", "Путь", "Размер (байт)", "Время изменения",
                                          "Родительская директория"], tablefmt=output_format)
        print(output)  # Если output_file не указан, выводим в консоль


def filter_by_name(file_info_list: List[FileInfo], name_filter: str) -> List[FileInfo]:
    """Фильтрация файлов по имени."""
    return [f for f in file_info_list if name_filter.lower() in f.name.lower()]


def filter_by_date(file_info_list: List[FileInfo], date_filter: str) -> List[FileInfo]:
    """Фильтрация файлов по дате изменения."""
    try:
        filter_date = datetime.strptime(date_filter, "%d.%m.%Y %H:%M")
    except ValueError:
        logging.error(f"Неверный формат даты: {date_filter}. Ожидается формат 'дд.мм.гггг чч:мм'.")
        raise ValueError(f"Неверный формат даты: {date_filter}. Ожидается формат 'дд.мм.гггг чч:мм'.")

    return [f for f in file_info_list if datetime.strptime(f.modified_time, "%d.%m.%Y %H:%M") >= filter_date]


def main(directory: str, extensions: List[str], output_file: Optional[Path], log_level: str,
         sort_by: Optional[str] = None, min_size: Optional[int] = None, recursive: bool = True,
         output_formats: List[str] = None, name_filter: Optional[str] = None,
         date_filter: Optional[str] = None) -> None:
    """Основная функция для сбора и отображения информации о файлах."""
    level = LogLevel[log_level.upper()]  # Преобразуем строку в значение перечисления LogLevel
    setup_logging(level)

    # Используем переменную окружения для каталога
    env_directory = os.getenv('FILE_DIRECTORY')
    directory_path = Path(env_directory) if env_directory else Path(directory)

    if not directory_path.is_dir():
        logging.error(f"Указанный каталог не существует: {directory_path}")
        return

    extensions_set: Set[str] = {ext.lower() for ext in extensions.split(',')} if extensions else set()
    logging.info("Начинаем сбор информации о файлах.")

    file_info_list: List[FileInfo] = collect_file_info(directory_path, extensions_set, recursive)
    logging.info(f"Найдено файлов: {len(file_info_list)}")

    if min_size:
        file_info_list = [f for f in file_info_list if f.size >= min_size]
        logging.info(f"Отфильтровано файлов по размеру: {len(file_info_list)}")

    if name_filter:
        file_info_list = filter_by_name(file_info_list, name_filter)
        logging.info(f"Отфильтровано файлов по имени: {len(file_info_list)}")

    if date_filter:
        file_info_list = filter_by_date(file_info_list, date_filter)
        logging.info(f"Отфильтровано файлов по дате изменения: {len(file_info_list)}")

    sort_funcs = {
        'name': lambda x: x.name,
        'size': lambda x: x.size,
        'modified': lambda x: x.modified_time,
    }
    sort_by_func = sort_funcs.get(sort_by)

    # Отображение информации о файлах
    display_file_info(file_info_list, sort_by_func)

    # Запись информации о файлах в указанные форматы
    if output_formats:
        for fmt in output_formats:
            write_to_file(file_info_list, output_file, fmt)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Обход каталога и получение информации о файлах.')
    parser.add_argument('directory', type=str, nargs='?', default='.', help='Путь к каталогу для обхода')
    parser.add_argument('--extensions', type=str, help='Фильтр по расширениям файлов (например, .txt,.jpg)')
    parser.add_argument('--output', type=Path, help='Файл для записи информации о файлах')
    parser.add_argument('--log-level', type=str, choices=[level.name for level in LogLevel], default='INFO',
                        help='Уровень логирования')
    parser.add_argument('--sort-by', type=str, choices=['name', 'size', 'modified'], help='Критерий сортировки')
    parser.add_argument('--min-size', type=int, help='Минимальный размер файла (в байтах)')
    parser.add_argument('--recursive', action='store_true', help='Рекурсивный обход подкаталогов')
    parser.add_argument('--output-formats', type=str, nargs='*', default=['grid'],
                        help='Форматы вывода (например, grid, csv)')
    parser.add_argument('--name-filter', type=str, help='Фильтр по имени файла (например, myfile)')
    parser.add_argument('--date-filter', type=str, help='Фильтр по дате изменения (формат: дд.мм.гггг чч:мм)')

    args = parser.parse_args()

    # Запуск основной функции
    main(args.directory, args.extensions or '', args.output, args.log_level, args.sort_by, args.min_size,
         args.recursive, args.output_formats, args.name_filter, args.date_filter)
