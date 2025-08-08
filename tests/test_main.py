"""
Тесты для модуля main.py
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open
from main import LogProcessor, ReportGenerator, format_table


class TestLogProcessor:
    """Тесты для класса LogProcessor."""
    
    def test_init(self):
        """Тест инициализации LogProcessor."""
        processor = LogProcessor()
        assert processor.logs == []
    
    def test_load_logs_single_file(self):
        """Тест загрузки логов из одного файла."""
        test_logs = [
            '{"@timestamp": "2025-06-22T13:57:32+00:00", "status": 200, "url": "/api/test", "response_time": 0.1}',
            '{"@timestamp": "2025-06-22T13:57:33+00:00", "status": 404, "url": "/api/missing", "response_time": 0.05}'
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp_file:
            tmp_file.write('\n'.join(test_logs))
            tmp_file.flush()
            
            processor = LogProcessor()
            processor.load_logs([tmp_file.name])
            
            assert len(processor.logs) == 2
            assert processor.logs[0]['url'] == '/api/test'
            assert processor.logs[1]['url'] == '/api/missing'
            
            Path(tmp_file.name).unlink()
    
    def test_load_logs_multiple_files(self):
        """Тест загрузки логов из нескольких файлов."""
        test_logs1 = ['{"url": "/api/test1", "response_time": 0.1}']
        test_logs2 = ['{"url": "/api/test2", "response_time": 0.2}']
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp_file1, \
             tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp_file2:
            
            tmp_file1.write('\n'.join(test_logs1))
            tmp_file1.flush()
            tmp_file2.write('\n'.join(test_logs2))
            tmp_file2.flush()
            
            processor = LogProcessor()
            processor.load_logs([tmp_file1.name, tmp_file2.name])
            
            assert len(processor.logs) == 2
            urls = [log['url'] for log in processor.logs]
            assert '/api/test1' in urls
            assert '/api/test2' in urls
            
            Path(tmp_file1.name).unlink()
            Path(tmp_file2.name).unlink()
    
    def test_load_logs_with_date_filter(self):
        """Тест загрузки логов с фильтром по дате."""
        test_logs = [
            '{"@timestamp": "2025-06-22T13:57:32+00:00", "url": "/api/test1", "response_time": 0.1}',
            '{"@timestamp": "2025-06-23T13:57:32+00:00", "url": "/api/test2", "response_time": 0.2}',
            '{"@timestamp": "2025-06-22T14:57:32+00:00", "url": "/api/test3", "response_time": 0.3}'
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp_file:
            tmp_file.write('\n'.join(test_logs))
            tmp_file.flush()
            
            processor = LogProcessor()
            processor.load_logs([tmp_file.name], date_filter='2025-06-22')
            
            assert len(processor.logs) == 2
            urls = [log['url'] for log in processor.logs]
            assert '/api/test1' in urls
            assert '/api/test3' in urls
            assert '/api/test2' not in urls
            
            Path(tmp_file.name).unlink()
    
    def test_load_logs_invalid_date_format(self):
        """Тест обработки неверного формата даты."""
        processor = LogProcessor()
        
        with pytest.raises(ValueError, match="Неверный формат даты"):
            processor.load_logs([], date_filter='invalid-date')
    
    def test_load_logs_file_not_found(self):
        """Тест обработки отсутствующего файла."""
        processor = LogProcessor()
        
        with pytest.raises(FileNotFoundError, match="Файл не найден"):
            processor.load_logs(['nonexistent_file.log'])
    
    def test_load_logs_invalid_json(self):
        """Тест обработки невалидного JSON."""
        test_logs = [
            '{"valid": "json"}',
            'invalid json line',
            '{"another": "valid json"}'
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp_file:
            tmp_file.write('\n'.join(test_logs))
            tmp_file.flush()
            
            processor = LogProcessor()
            
            # Перехватываем вывод print
            with patch('builtins.print') as mock_print:
                processor.load_logs([tmp_file.name])
            
            # Должны загрузиться только валидные записи
            assert len(processor.logs) == 2
            
            # Проверяем, что было выведено сообщение об ошибке
            mock_print.assert_called()
            
            Path(tmp_file.name).unlink()
    
    def test_generate_average_report(self):
        """Тест генерации отчета average."""
        processor = LogProcessor()
        processor.logs = [
            {"url": "/api/test1", "response_time": 0.1},
            {"url": "/api/test1", "response_time": 0.2},
            {"url": "/api/test2", "response_time": 0.3},
            {"url": "/api/test1", "response_time": 0.3}
        ]
        
        report = processor.generate_average_report()
        
        assert len(report) == 2
        
        # Проверяем первый эндпоинт (должен быть отсортирован по количеству запросов)
        test1_data = next(item for item in report if item['handler'] == '/api/test1')
        assert test1_data['total'] == 3
        assert test1_data['avg_response_time'] == 0.2  # (0.1 + 0.2 + 0.3) / 3
        
        test2_data = next(item for item in report if item['handler'] == '/api/test2')
        assert test2_data['total'] == 1
        assert test2_data['avg_response_time'] == 0.3
        
        # Проверяем сортировку (по убыванию количества запросов)
        assert report[0]['handler'] == '/api/test1'
        assert report[1]['handler'] == '/api/test2'
    
    def test_generate_average_report_empty_logs(self):
        """Тест генерации отчета для пустых логов."""
        processor = LogProcessor()
        processor.logs = []
        
        report = processor.generate_average_report()
        
        assert report == []
    
    def test_generate_average_report_missing_fields(self):
        """Тест генерации отчета с отсутствующими полями."""
        processor = LogProcessor()
        processor.logs = [
            {"url": "/api/test1"},  # нет response_time
            {"response_time": 0.1},  # нет url
            {"url": "/api/test2", "response_time": "invalid"},  # невалидное время
            {"url": "/api/test3", "response_time": 0.2}  # валидная запись
        ]
        
        report = processor.generate_average_report()
        
        assert len(report) == 1
        assert report[0]['handler'] == '/api/test3'
        assert report[0]['total'] == 1
        assert report[0]['avg_response_time'] == 0.2


class TestReportGenerator:
    """Тесты для класса ReportGenerator."""
    
    def test_init(self):
        """Тест инициализации ReportGenerator."""
        processor = LogProcessor()
        generator = ReportGenerator(processor)
        assert generator.processor == processor
    
    def test_generate_average_report(self):
        """Тест генерации отчета average."""
        processor = LogProcessor()
        processor.logs = [
            {"url": "/api/test", "response_time": 0.1}
        ]
        
        generator = ReportGenerator(processor)
        report = generator.generate_report('average')
        
        assert len(report) == 1
        assert report[0]['handler'] == '/api/test'
    
    def test_generate_unsupported_report(self):
        """Тест генерации неподдерживаемого типа отчета."""
        processor = LogProcessor()
        generator = ReportGenerator(processor)
        
        with pytest.raises(ValueError, match="Неподдерживаемый тип отчета"):
            generator.generate_report('unsupported')


class TestFormatTable:
    """Тесты для функции format_table."""
    
    def test_format_table_empty_data(self):
        """Тест форматирования пустых данных."""
        result = format_table([], ['header1', 'header2'])
        assert result == "Нет данных для отображения"
    
    def test_format_table_with_data(self):
        """Тест форматирования данных в таблицу."""
        data = [
            {'handler': '/api/test1', 'total': 10, 'avg_response_time': 0.1},
            {'handler': '/api/test2', 'total': 5, 'avg_response_time': 0.2}
        ]
        headers = ['handler', 'total', 'avg_response_time']
        
        result = format_table(data, headers)
        
        assert isinstance(result, str)
        assert '/api/test1' in result
        assert '/api/test2' in result
        assert '10' in result
        assert '5' in result
    
    @patch('main.tabulate', None)
    @patch('main.TABULATE_AVAILABLE', False)
    def test_format_table_without_tabulate(self):
        """Тест форматирования без библиотеки tabulate."""
        data = [
            {'handler': '/api/test', 'total': 1, 'avg_response_time': 0.1}
        ]
        headers = ['handler', 'total', 'avg_response_time']
        
        result = format_table(data, headers)
        
        assert isinstance(result, str)
        assert '/api/test' in result
        assert '1' in result
        assert '0.1' in result
        assert '+' in result  # Проверяем наличие разделителей таблицы
        assert '|' in result


class TestIntegration:
    """Интеграционные тесты."""
    
    def test_full_workflow(self):
        """Тест полного рабочего процесса."""
        test_logs = [
            '{"@timestamp": "2025-06-22T13:57:32+00:00", "status": 200, "url": "/api/homeworks", "response_time": 0.1}',
            '{"@timestamp": "2025-06-22T13:57:33+00:00", "status": 200, "url": "/api/context", "response_time": 0.05}',
            '{"@timestamp": "2025-06-22T13:57:34+00:00", "status": 200, "url": "/api/homeworks", "response_time": 0.2}'
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp_file:
            tmp_file.write('\n'.join(test_logs))
            tmp_file.flush()
            
            # Полный цикл обработки
            processor = LogProcessor()
            processor.load_logs([tmp_file.name])
            
            generator = ReportGenerator(processor)
            report = generator.generate_report('average')
            
            # Проверяем результат
            assert len(report) == 2
            
            homeworks_data = next(item for item in report if item['handler'] == '/api/homeworks')
            assert homeworks_data['total'] == 2
            assert homeworks_data['avg_response_time'] == 0.15  # (0.1 + 0.2) / 2
            
            context_data = next(item for item in report if item['handler'] == '/api/context')
            assert context_data['total'] == 1
            assert context_data['avg_response_time'] == 0.05
            
            # Проверяем сортировку
            assert report[0]['handler'] == '/api/homeworks'  # больше запросов
            assert report[1]['handler'] == '/api/context'
            
            Path(tmp_file.name).unlink()
