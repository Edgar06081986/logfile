import pytest
import json
import tempfile
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

from main import LogProcessor, ReportGenerator, format_table


class TestLogProcessor:
    
    def test_init(self):
        processor = LogProcessor()
        assert processor.logs == []
    
    def test_load_logs_file_not_found(self):
        processor = LogProcessor()
        with pytest.raises(FileNotFoundError):
            processor.load_logs(['nonexistent.log'])
    
    def test_load_logs_invalid_date_format(self):
        processor = LogProcessor()
        with pytest.raises(ValueError, match="Неверный формат даты"):
            processor.load_logs(['test.log'], '2025-13-45')
    
    def test_load_logs_success(self):
        processor = LogProcessor()
        
        # Создаем временный файл с тестовыми данными
        test_data = [
            '{"@timestamp": "2025-06-22T13:57:32+00:00", "status": 200, "url": "/api/test", "response_time": 0.1}',
            '{"@timestamp": "2025-06-22T13:57:33+00:00", "status": 404, "url": "/api/missing", "response_time": 0.05}'
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            for line in test_data:
                f.write(line + '\n')
            temp_filename = f.name
        
        try:
            processor.load_logs([temp_filename])
            assert len(processor.logs) == 2
            assert processor.logs[0]['url'] == '/api/test'
            assert processor.logs[1]['url'] == '/api/missing'
        finally:
            os.unlink(temp_filename)
    
    def test_load_logs_with_date_filter(self):
        processor = LogProcessor()
        
        test_data = [
            '{"@timestamp": "2025-06-22T13:57:32+00:00", "status": 200, "url": "/api/test", "response_time": 0.1}',
            '{"@timestamp": "2025-06-23T13:57:33+00:00", "status": 404, "url": "/api/missing", "response_time": 0.05}'
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            for line in test_data:
                f.write(line + '\n')
            temp_filename = f.name
        
        try:
            processor.load_logs([temp_filename], '2025-06-22')
            assert len(processor.logs) == 1
            assert processor.logs[0]['url'] == '/api/test'
        finally:
            os.unlink(temp_filename)
    
    def test_load_logs_invalid_json(self):
        processor = LogProcessor()
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write('{"valid": "json"}\n')
            f.write('invalid json line\n')
            f.write('{"another": "valid"}\n')
            temp_filename = f.name
        
        try:
            with patch('builtins.print') as mock_print:
                processor.load_logs([temp_filename])
                # Должна быть одна ошибка парсинга
                mock_print.assert_called_once()
                assert "Ошибка парсинга JSON" in str(mock_print.call_args)
            
            # Должно быть загружено 2 валидные записи
            assert len(processor.logs) == 2
        finally:
            os.unlink(temp_filename)
    
    def test_generate_average_report(self):
        processor = LogProcessor()
        processor.logs = [
            {"url": "/api/test", "response_time": 0.1},
            {"url": "/api/test", "response_time": 0.2},
            {"url": "/api/other", "response_time": 0.3},
            {"url": "/api/test", "response_time": 0.15}
        ]
        
        report = processor.generate_average_report()
        
        assert len(report) == 2
        # Проверяем сортировку по количеству запросов
        assert report[0]['handler'] == '/api/test'
        assert report[0]['total'] == 3
        assert report[0]['avg_response_time'] == 0.15  # (0.1 + 0.2 + 0.15) / 3
        
        assert report[1]['handler'] == '/api/other'
        assert report[1]['total'] == 1
        assert report[1]['avg_response_time'] == 0.3
    
    def test_generate_average_report_missing_fields(self):
        processor = LogProcessor()
        processor.logs = [
            {"url": "/api/test", "response_time": 0.1},
            {"url": "", "response_time": 0.2},  # Пустой URL
            {"url": "/api/test"},  # Отсутствует response_time
            {"url": "/api/test", "response_time": "invalid"},  # Невалидный response_time
            {"url": "/api/test", "response_time": 0.2}
        ]
        
        report = processor.generate_average_report()
        
        assert len(report) == 1
        assert report[0]['handler'] == '/api/test'
        assert report[0]['total'] == 2  # Только 2 валидные записи
        assert report[0]['avg_response_time'] == 0.15  # (0.1 + 0.2) / 2
    
    def test_generate_user_agent_report(self):
        processor = LogProcessor()
        processor.logs = [
            {"http_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"},
            {"http_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"},
            {"http_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"},
            {"http_user_agent": "..."},
            {"http_user_agent": "curl/7.68.0"}
        ]
        
        report = processor.generate_user_agent_report()
        
        assert len(report) == 4
        # Проверяем Chrome (2 запроса)
        chrome_report = next(r for r in report if r['browser'] == 'Chrome')
        assert chrome_report['requests'] == 2
        assert chrome_report['percentage'] == 40.0
        
        # Проверяем Firefox (1 запрос)
        firefox_report = next(r for r in report if r['browser'] == 'Firefox')
        assert firefox_report['requests'] == 1
        assert firefox_report['percentage'] == 20.0
    
    def test_generate_status_report(self):
        processor = LogProcessor()
        processor.logs = [
            {"status": 200},
            {"status": 200},
            {"status": 404},
            {"status": 500},
            {"status": 200}
        ]
        
        report = processor.generate_status_report()
        
        assert len(report) == 3
        # Проверяем сортировку по количеству
        assert report[0]['status_code'] == '200'
        assert report[0]['requests'] == 3
        assert report[0]['percentage'] == 60.0
        
        assert report[1]['status_code'] == '404'
        assert report[1]['requests'] == 1
        assert report[1]['percentage'] == 20.0
    
    def test_extract_browser_from_user_agent(self):
        processor = LogProcessor()
        
        test_cases = [
            ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36", "Chrome"),
            ("Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0", "Firefox"),
            ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15", "Safari"),
            ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59", "Edge"),
            ("curl/7.68.0", "curl"),
            ("wget/1.20.3", "wget"),
            ("python-requests/2.25.1", "Python"),
            ("Googlebot/2.1", "Bot/Crawler"),
            ("...", "Unknown"),
            ("", "Unknown"),
            ("Some unknown user agent", "Other")
        ]
        
        for user_agent, expected_browser in test_cases:
            result = processor._extract_browser_from_user_agent(user_agent)
            assert result == expected_browser, f"Expected {expected_browser} for {user_agent}, got {result}"


class TestReportGenerator:
    
    def test_init(self):
        processor = LogProcessor()
        generator = ReportGenerator(processor)
        assert generator.processor == processor
        assert 'average' in generator._report_registry
        assert 'user_agent' in generator._report_registry
        assert 'status' in generator._report_registry
    
    def test_get_available_reports(self):
        processor = LogProcessor()
        generator = ReportGenerator(processor)
        reports = generator.get_available_reports()
        
        assert 'average' in reports
        assert 'user_agent' in reports
        assert 'status' in reports
        assert 'эндпоинтам' in reports['average']  # Проверяем описание
    
    def test_get_report_headers(self):
        processor = LogProcessor()
        generator = ReportGenerator(processor)
        
        headers = generator.get_report_headers('average')
        assert headers == ['handler', 'total', 'avg_response_time']
        
        headers = generator.get_report_headers('user_agent')
        assert headers == ['browser', 'requests', 'percentage']
    
    def test_get_report_headers_invalid_type(self):
        processor = LogProcessor()
        generator = ReportGenerator(processor)
        
        with pytest.raises(ValueError, match="Неподдерживаемый тип отчета"):
            generator.get_report_headers('invalid_report')
    
    def test_generate_report_average(self):
        processor = LogProcessor()
        processor.logs = [{"url": "/api/test", "response_time": 0.1}]
        
        generator = ReportGenerator(processor)
        report = generator.generate_report('average')
        
        assert len(report) == 1
        assert report[0]['handler'] == '/api/test'
    
    def test_generate_report_user_agent(self):
        processor = LogProcessor()
        processor.logs = [{"http_user_agent": "Chrome/91.0"}]
        
        generator = ReportGenerator(processor)
        report = generator.generate_report('user_agent')
        
        assert len(report) == 1
        assert report[0]['browser'] == 'Chrome'
    
    def test_generate_report_invalid_type(self):
        processor = LogProcessor()
        generator = ReportGenerator(processor)
        
        with pytest.raises(ValueError, match="Неподдерживаемый тип отчета"):
            generator.generate_report('invalid_report')
    
    def test_add_report_type(self):
        processor = LogProcessor()
        generator = ReportGenerator(processor)
        
        def custom_method():
            return [{'custom': 'data'}]
        
        generator.add_report_type(
            'custom',
            custom_method,
            ['custom'],
            'Custom report'
        )
        
        assert 'custom' in generator._report_registry
        assert generator.get_report_headers('custom') == ['custom']
        report = generator.generate_report('custom')
        assert report == [{'custom': 'data'}]


class TestFormatTable:
    
    def test_format_table_empty_data(self):
        result = format_table([], ['header1', 'header2'])
        assert result == "Нет данных для отображения"
    
    def test_format_table_with_tabulate(self):
        data = [{'name': 'test', 'value': 123}]
        headers = ['name', 'value']
        
        with patch('main.TABULATE_AVAILABLE', True), \
             patch('main.tabulate') as mock_tabulate:
            mock_tabulate.return_value = "mocked table"
            
            result = format_table(data, headers)
            
            mock_tabulate.assert_called_once()
            assert result == "mocked table"
    
    def test_format_table_without_tabulate(self):
        data = [{'name': 'test', 'value': 123}]
        headers = ['name', 'value']
        
        with patch('main.TABULATE_AVAILABLE', False):
            result = format_table(data, headers)
            
            assert '+' in result  # Проверяем, что есть границы таблицы
            assert 'name' in result
            assert 'value' in result
            assert 'test' in result
            assert '123' in result
    
    def test_format_table_tabulate_none(self):
        data = [{'name': 'test', 'value': 123}]
        headers = ['name', 'value']
        
        with patch('main.TABULATE_AVAILABLE', True), \
             patch('main.tabulate', None):
            result = format_table(data, headers)
            
            # Должен использовать простое форматирование
            assert '+' in result
            assert 'name' in result


class TestMainFunction:
    
    @patch('main.LogProcessor')
    @patch('main.ReportGenerator')
    @patch('main.format_table')
    def test_main_basic_flow(self, mock_format_table, mock_report_gen_class, mock_processor_class):
        # Настройка моков
        mock_processor = MagicMock()
        mock_processor.logs = [{'test': 'data'}]
        mock_processor_class.return_value = mock_processor
        
        mock_generator = MagicMock()
        mock_generator.generate_report.return_value = [{'handler': '/test', 'total': 1}]
        mock_generator.get_report_headers.return_value = ['handler', 'total']
        mock_report_gen_class.return_value = mock_generator
        
        mock_format_table.return_value = "formatted table"
        
        with patch('sys.argv', ['main.py', '--file', 'test.log', '--report', 'average']):
            with patch('builtins.print') as mock_print:
                from main import main
                main()
                
                mock_print.assert_called_with("formatted table")
                mock_processor.load_logs.assert_called_once_with(['test.log'], None)
                mock_generator.generate_report.assert_called_once_with('average')