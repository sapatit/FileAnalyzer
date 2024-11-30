import unittest
import time
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import datetime
from get_info import collect_file_info, filter_by_name, filter_by_date, FileInfo


class TestFileInfo(unittest.TestCase):

    def setUp(self):
        # Общие настройки для тестов
        self.mock_file_info_list = [
            FileInfo(name="test_file.txt", path=Path("/test/test_file.txt"), size=1024,
                     modified_time="01.01.2023 12:00", parent_dir=Path("/test")),
            FileInfo(name="example_file.txt", path=Path("/test/example_file.txt"), size=2048,
                     modified_time="01.01.2022 12:00", parent_dir=Path("/test")),
            FileInfo(name="another_file.txt", path=Path("/test/another_file.txt"), size=512,
                     modified_time="01.01.2023 15:00", parent_dir=Path("/test")),
        ]

    @patch('pathlib.Path.stat')
    def test_file_info_creation(self, mock_stat):
        # Настройка mock-объекта
        mock_stat.return_value.st_mtime = time.mktime(time.strptime("01.01.2023 12:00", "%d.%m.%Y %H:%M"))
        mock_stat.return_value.st_size = 1024
        mock_path = MagicMock(spec=Path)
        mock_path.name = "test_file.txt"
        mock_path.parent = Path("/test")
        mock_path.stat = mock_stat

        file_info = FileInfo.from_path(mock_path)

        self.assertIsNotNone(file_info)
        self.assertEqual(file_info.name, "test_file.txt")
        self.assertEqual(file_info.size, 1024)
        self.assertEqual(file_info.modified_time, "01.01.2023 12:00")
        self.assertEqual(file_info.parent_dir, Path("/test"))

    @patch('pathlib.Path.rglob')
    def test_collect_file_info(self, mock_rglob):
        # Настройка mock-объекта
        mock_file = MagicMock(spec=Path)
        mock_file.is_file.return_value = True
        mock_file.suffix = '.txt'
        mock_file.name = "test_file.txt"
        mock_file.stat.return_value.st_mtime = time.mktime(time.strptime("01.01.2023 12:00", "%d.%m.%Y %H:%M"))
        mock_file.stat.return_value.st_size = 1024
        mock_file.parent = Path("/test")

        mock_rglob.return_value = [mock_file]

        result = collect_file_info(Path("/test"), {'.txt'}, recursive=True)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "test_file.txt")

    def test_collect_file_info_empty_directory(self):
        # Проверка на пустую директорию
        with patch('pathlib.Path.rglob', return_value=[]):
            result = collect_file_info(Path("/empty"), {'.txt'}, recursive=True)
            self.assertEqual(len(result), 0)

    def test_collect_file_info_file_with_zero_size(self):
        # Проверка на файл с нулевым размером
        mock_file = MagicMock(spec=Path)
        mock_file.is_file.return_value = True
        mock_file.suffix = '.txt'
        mock_file.name = "empty_file.txt"
        mock_file.stat.return_value.st_mtime = time.mktime(time.strptime("01.01.2023 12:00", "%d.%m.%Y %H:%M"))
        mock_file.stat.return_value.st_size = 0
        mock_file.parent = Path("/test")

        with patch('pathlib.Path.rglob', return_value=[mock_file]):
            result = collect_file_info(Path("/test"), {'.txt'}, recursive=True)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].size, 0)

    def test_collect_file_info_invalid_file_metadata(self):
        # Проверка на файл с некорректными метаданными
        mock_file = MagicMock(spec=Path)
        mock_file.is_file.return_value = True
        mock_file.suffix = '.txt'
        mock_file.name = "invalid_metadata_file.txt"
        mock_file.stat.side_effect = OSError("Stat error")  # Исключение при вызове stat
        mock_file.parent = Path("/test")

        with patch('pathlib.Path.rglob', return_value=[mock_file]):
            result = collect_file_info(Path("/test"), {'.txt'}, recursive=True)
            self.assertEqual(len(result), 0)  # Ожидаем, что файл не будет добавлен

    def test_filter_by_name_with_duplicates(self):
        # Проверка на наличие дубликатов
        file_info_list = [
            FileInfo(name="test_file.txt", path=Path("/test/test_file.txt"), size=1024,
                     modified_time="01.01.2023 12:00", parent_dir=Path("/test")),
            FileInfo(name="test_file.txt", path=Path("/test/test_file_duplicate.txt"), size=1024,
                     modified_time="01.01.2023 12:00", parent_dir=Path("/test")),
        ]
        filtered_files = filter_by_name(file_info_list, "test")
        self.assertEqual(len(filtered_files), 2)  # Ожидаем, что оба файла будут найдены
        self.assertEqual({file.name for file in filtered_files}, {"test_file.txt"})  # Проверка на уникальность имен

    def test_filter_by_name(self):
        filtered_files = filter_by_name(self.mock_file_info_list, "test")
        self.assertEqual(len(filtered_files), 1)
        self.assertEqual(filtered_files[0].name, "test_file.txt")

    def test_filter_by_name_case_insensitive(self):
        file_info_list = [
            FileInfo(name="Test_File.txt", path=Path("/test/Test_File.txt"), size=1024,
                     modified_time="01.01.2023 12:00", parent_dir=Path("/test")),
        ]
        filtered_files = filter_by_name(file_info_list, "test")
        self.assertEqual(len(filtered_files), 1)
        self.assertEqual(filtered_files[0].name, "Test_File.txt")

    def test_filter_by_name_empty_list(self):
        file_info_list = []
        filtered_files = filter_by_name(file_info_list, "test")
        self.assertEqual(len(filtered_files), 0)

    def test_filter_by_name_multiple_matches(self):
        file_info_list = [
            FileInfo(name="test_file.txt", path=Path("/test/test_file.txt"), size=1024,
                     modified_time="01.01.2023 12:00", parent_dir=Path("/test")),
            FileInfo(name="test_file_2.txt", path=Path("/test/test_file_2.txt"), size=2048,
                     modified_time="01.01.2023 12:00", parent_dir=Path("/test")),
        ]
        filtered_files = filter_by_name(file_info_list, "test")
        self.assertEqual(len(filtered_files), 2)

    def test_filter_by_date(self):
        filtered_files = filter_by_date(self.mock_file_info_list, "01.01.2023 00:00")
        self.assertEqual(len(filtered_files), 2)  # Два файла изменены 01.01.2023

    def test_filter_by_date_empty_list(self):
        file_info_list = []
        filtered_files = filter_by_date(file_info_list, "01.01.2023 00:00")
        self.assertEqual(len(filtered_files), 0)

    def test_filter_by_date_multiple_files(self):
        filtered_files = filter_by_date(self.mock_file_info_list, "01.01.2023 00:00")
        self.assertEqual(len(filtered_files), 2)  # Два файла изменены 01.01.2023

    def test_filter_by_date_invalid_format(self):
        file_info_list = [
            FileInfo(name="test_file.txt", path=Path("/test/test_file.txt"), size=1024,
                     modified_time="01.01.2023 12:00", parent_dir=Path("/test")),
        ]

        with self.assertRaises(ValueError):
            filter_by_date(file_info_list, "invalid_date_format")

    def test_filter_by_date_boundary(self):
        file_info_list = [
            FileInfo(name="boundary_file.txt", path=Path("/test/boundary_file.txt"), size=512,
                     modified_time="31.12.2022 23:59", parent_dir=Path("/test")),
            FileInfo(name="test_file.txt", path=Path("/test/test_file.txt"), size=1024,
                     modified_time="01.01.2023 00:00", parent_dir=Path("/test")),
        ]

        filtered_files = filter_by_date(file_info_list, "01.01.2023 00:00")
        self.assertEqual(len(filtered_files), 1)  # Только один файл изменен 01.01.2023

    def test_filter_by_name_none(self):
        with self.assertRaises(TypeError):
            filter_by_name(None, "test")

    def test_filter_by_date_none(self):
        with self.assertRaises(TypeError):
            filter_by_date(None, "01.01.2023 00:00")

    def test_collect_file_info_large_directory(self):
        # Проверка производительности с большим количеством файлов
        mock_files = [MagicMock(spec=Path) for _ in range(1000)]
        for i, mock_file in enumerate(mock_files):
            mock_file.is_file.return_value = True
            mock_file.suffix = '.txt'
            mock_file.name = f"test_file_{i}.txt"
            mock_file.stat.return_value.st_mtime = time.mktime(time.strptime("01.01.2023 12:00", "%d.%m.%Y %H:%M"))
            mock_file.stat.return_value.st_size = 1024
            mock_file.parent = Path("/test")

        with patch('pathlib.Path.rglob', return_value=mock_files):
            result = collect_file_info(Path("/test"), {'.txt'}, recursive=True)
            self.assertEqual(len(result), 1000)

    def test_collect_file_info_with_hidden_files(self):
        # Проверка на наличие скрытых файлов
        mock_file = MagicMock(spec=Path)
        mock_file.is_file.return_value = True
        mock_file.suffix = '.txt'
        mock_file.name = ".hidden_file.txt"
        mock_file.stat.return_value.st_mtime = time.mktime(time.strptime("01.01.2023 12:00", "%d.%m.%Y %H:%M"))
        mock_file.stat.return_value.st_size = 1024
        mock_file.parent = Path("/test")

        with patch('pathlib.Path.rglob', return_value=[mock_file]):
            result = collect_file_info(Path("/test"), {'.txt'}, recursive=True)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].name, ".hidden_file.txt")

    def test_collect_file_info_with_subdirectories(self):
        # Проверка на наличие файлов в подкаталогах
        mock_file1 = MagicMock(spec=Path)
        mock_file1.is_file.return_value = True
        mock_file1.suffix = '.txt'
        mock_file1.name = "file_in_subdir.txt"
        mock_file1.stat.return_value.st_mtime = time.mktime(time.strptime("01.01.2023 12:00", "%d.%m.%Y %H:%M"))
        mock_file1.stat.return_value.st_size = 1024
        mock_file1.parent = Path("/test/subdir")

        mock_file2 = MagicMock(spec=Path)
        mock_file2.is_file.return_value = True
        mock_file2.suffix = '.txt'
        mock_file2.name = "file_in_root.txt"
        mock_file2.stat.return_value.st_mtime = time.mktime(time.strptime("01.01.2023 12:00", "%d.%m.%Y %H:%M"))
        mock_file2.stat.return_value.st_size = 2048
        mock_file2.parent = Path("/test")

        with patch('pathlib.Path.rglob', return_value=[mock_file1, mock_file2]):
            result = collect_file_info(Path("/test"), {'.txt'}, recursive=True)
            self.assertEqual(len(result), 2)

    def test_collect_file_info_with_different_extensions(self):
        # Проверка на файлы с разными расширениями
        mock_file1 = MagicMock(spec=Path)
        mock_file1.is_file.return_value = True
        mock_file1.suffix = '.txt'
        mock_file1.name = "file1.txt"
        mock_file1.stat.return_value.st_mtime = time.mktime(time.strptime("01.01.2023 12:00", "%d.%m.%Y %H:%M"))
        mock_file1.stat.return_value.st_size = 1024

        mock_file2 = MagicMock(spec=Path)
        mock_file2.is_file.return_value = True
        mock_file2.suffix = '.md'
        mock_file2.name = "file2.md"
        mock_file2.stat.return_value.st_mtime = time.mktime(time.strptime("01.01.2023 12:00", "%d.%m.%Y %H:%M"))
        mock_file2.stat.return_value.st_size = 2048

        with patch('pathlib.Path.rglob', return_value=[mock_file1, mock_file2]):
            result = collect_file_info(Path("/test"), {'.txt'}, recursive=True)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].name, "file1.txt")

if __name__ == '__main__':
    unittest.main()
