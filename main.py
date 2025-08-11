"""
Скрипт для анализа лог-файлов в формате JSON.
Формирует отчеты по эндпоинтам с количеством запросов и средним временем ответа.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict
import re

try:
    from tabulate import tabulate
    TABULATE_AVAILABLE = True
except ImportError:
    TABULATE_AVAILABLE = False


class LogProcessor:
    """Класс для обработки лог-файлов и генерации отчетов."""
    
    def __init__(self):
        self.logs = []
    
    def load_logs(self, file_paths: List[str], date_filter: Optional[str] = None) -> None:
        """
        Загружает логи из указанных файлов.
        
        Args:
            file_paths: Список путей к лог-файлам
            date_filter: Фильтр по дате в формате YYYY-MM-DD
        """
        target_date = None
        if date_filter:
            try:
                target_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError(f"Неверный формат даты: {date_filter}. Используйте YYYY-MM-DD")
        
        for file_path in file_paths:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"Файл не найден: {file_path}")
            
            try:
                with open(path, 'r', encoding='utf-8') as file:
                    for line_num, line in enumerate(file, 1):
                        line = line.strip()
                        if not line:
                            continue
                        
                        try:
                            log_entry = json.loads(line)
                            
                            # Фильтрация по дате, если указана
                            if target_date:
                                timestamp_str = log_entry.get('@timestamp', '')
                                if timestamp_str:
                                    try:
                                        log_date = datetime.fromisoformat(
                                            timestamp_str.replace('Z', '+00:00')
                                        ).date()
                                        if log_date != target_date:
                                            continue
                                    except (ValueError, TypeError):
                                        continue
                            
                            self.logs.append(log_entry)
                        
                        except json.JSONDecodeError as e:
                            print(f"Ошибка парсинга JSON в файле {file_path}, строка {line_num}: {e}")
                            continue
            
            except Exception as e:
                raise Exception(f"Ошибка чтения файла {file_path}: {e}")
    
    def generate_average_report(self) -> List[Dict[str, Any]]:
        """
        Генерирует отчет average с эндпоинтами, количеством запросов и средним временем ответа.
        
        Returns:
            Список словарей с данными отчета
        """
        endpoint_stats = defaultdict(lambda: {'total_requests': 0, 'total_response_time': 0.0})
        
        for log_entry in self.logs:
            url = log_entry.get('url')
            response_time = log_entry.get('response_time')
            
            # Проверяем, что оба поля присутствуют и валидны
            if url and response_time is not None and isinstance(response_time, (int, float)):
                endpoint_stats[url]['total_requests'] += 1
                endpoint_stats[url]['total_response_time'] += response_time
        
        # Формирование отчета
        report_data = []
        for endpoint, stats in endpoint_stats.items():
            avg_response_time = (
                stats['total_response_time'] / stats['total_requests'] 
                if stats['total_requests'] > 0 else 0
            )
            
            report_data.append({
                'handler': endpoint,
                'total': stats['total_requests'],
                'avg_response_time': round(avg_response_time, 3)
            })
        
        # Сортировка по количеству запросов (по убыванию)
        report_data.sort(key=lambda x: x['total'], reverse=True)
        
        return report_data
    
    def generate_user_agent_report(self) -> List[Dict[str, Any]]:
        """
        Генерирует отчет по User-Agent браузеров.
        
        Returns:
            Список словарей с данными отчета
        """
        user_agent_stats = defaultdict(int)
        total_requests = 0
        
        for log_entry in self.logs:
            user_agent = log_entry.get('http_user_agent', '')
            if user_agent:
                browser = self._extract_browser_from_user_agent(user_agent)
                user_agent_stats[browser] += 1
                total_requests += 1
        
        # Формирование отчета
        report_data = []
        for browser, count in user_agent_stats.items():
            percentage = (count / total_requests * 100) if total_requests > 0 else 0
            
            report_data.append({
                'browser': browser,
                'requests': count,
                'percentage': round(percentage, 2)
            })
        
        # Сортировка по количеству запросов (по убыванию)
        report_data.sort(key=lambda x: x['requests'], reverse=True)
        
        return report_data
    
    def generate_status_report(self) -> List[Dict[str, Any]]:
        """
        Генерирует отчет по HTTP статус кодам.
        
        Returns:
            Список словарей с данными отчета
        """
        status_stats = defaultdict(int)
        total_requests = 0
        
        for log_entry in self.logs:
            status = log_entry.get('status')
            if status is not None:
                status_stats[str(status)] += 1
                total_requests += 1
        
        # Формирование отчета
        report_data = []
        for status, count in status_stats.items():
            percentage = (count / total_requests * 100) if total_requests > 0 else 0
            
            report_data.append({
                'status_code': status,
                'requests': count,
                'percentage': round(percentage, 2)
            })
        
        # Сортировка по количеству запросов (по убыванию)
        report_data.sort(key=lambda x: x['requests'], reverse=True)
        
        return report_data
    
    def _extract_browser_from_user_agent(self, user_agent: str) -> str:
        """
        Извлекает название браузера из User-Agent строки.
        
        Args:
            user_agent: Строка User-Agent
            
        Returns:
            Название браузера
        """
        if not user_agent or user_agent == '...':
            return 'Unknown'
        
        user_agent_lower = user_agent.lower()
        
        # Порядок проверки важен! Chrome должен быть после Edge
        if 'edg/' in user_agent_lower:
            return 'Edge'
        elif 'firefox' in user_agent_lower:
            return 'Firefox'
        elif 'chrome' in user_agent_lower:
            return 'Chrome'
        elif 'safari' in user_agent_lower and 'chrome' not in user_agent_lower:
            return 'Safari'
        elif 'opera' in user_agent_lower or 'opr/' in user_agent_lower:
            return 'Opera'
        elif 'trident' in user_agent_lower or 'msie' in user_agent_lower:
            return 'Internet Explorer'
        elif 'curl' in user_agent_lower:
            return 'curl'
        elif 'wget' in user_agent_lower:
            return 'wget'
        elif 'python' in user_agent_lower:
            return 'Python'
        elif 'bot' in user_agent_lower or 'crawler' in user_agent_lower:
            return 'Bot/Crawler'
        else:
            return 'Other'


class ReportGenerator:
    """Класс для генерации различных типов отчетов."""
    
    def __init__(self, processor: LogProcessor):
        self.processor = processor
        # Реестр доступных отчетов для легкого расширения
        self._report_registry = {
            'average': {
                'method': self.processor.generate_average_report,
                'headers': ['handler', 'total', 'avg_response_time'],
                'description': 'Статистика по эндпоинтам с количеством запросов и средним временем ответа'
            },
            'user_agent': {
                'method': self.processor.generate_user_agent_report,
                'headers': ['browser', 'requests', 'percentage'],
                'description': 'Статистика по браузерам пользователей'
            },
            'status': {
                'method': self.processor.generate_status_report,
                'headers': ['status_code', 'requests', 'percentage'],
                'description': 'Статистика по HTTP статус кодам'
            }
        }
    
    def get_available_reports(self) -> Dict[str, str]:
        """
        Возвращает список доступных отчетов с их описаниями.
        
        Returns:
            Словарь {название_отчета: описание}
        """
        return {name: info['description'] for name, info in self._report_registry.items()}
    
    def get_report_headers(self, report_type: str) -> List[str]:
        """
        Возвращает заголовки для указанного типа отчета.
        
        Args:
            report_type: Тип отчета
            
        Returns:
            Список заголовков
        """
        if report_type not in self._report_registry:
            raise ValueError(f"Неподдерживаемый тип отчета: {report_type}")
        
        return self._report_registry[report_type]['headers']
    
    def generate_report(self, report_type: str) -> List[Dict[str, Any]]:
        """
        Генерирует отчет указанного типа.
        
        Args:
            report_type: Тип отчета
        
        Returns:
            Данные отчета
        """
        if report_type not in self._report_registry:
            raise ValueError(f"Неподдерживаемый тип отчета: {report_type}")
        
        report_method = self._report_registry[report_type]['method']
        return report_method()
    
    def add_report_type(self, name: str, method, headers: List[str], description: str):
        """
        Добавляет новый тип отчета в реестр.
        
        Args:
            name: Название отчета
            method: Метод для генерации отчета
            headers: Заголовки таблицы
            description: Описание отчета
        """
        self._report_registry[name] = {
            'method': method,
            'headers': headers,
            'description': description
        }


def format_table(data: List[Dict[str, Any]], headers: List[str]) -> str:
    """
    Форматирует данные в виде таблицы.
    
    Args:
        data: Данные для отображения
        headers: Заголовки таблицы
    
    Returns:
        Отформатированная таблица
    """
    if not data:
        return "Нет данных для отображения"
    
    # Преобразуем данные в список списков для tabulate
    table_data = []
    for item in data:
        row = [item.get(header.lower().replace(' ', '_'), '') for header in headers]
        table_data.append(row)
    
    if TABULATE_AVAILABLE and tabulate is not None:
        return tabulate(table_data, headers=headers, tablefmt='grid')
    else:
        # Простое табличное форматирование без tabulate
        result = []
        
        # Вычисляем ширину колонок
        col_widths = [len(header) for header in headers]
        for row in table_data:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))
        
        # Создаем разделитель
        separator = '+' + '+'.join('-' * (width + 2) for width in col_widths) + '+'
        
        result.append(separator)
        
        # Заголовки
        header_row = '|' + '|'.join(f' {header:<{col_widths[i]}} ' for i, header in enumerate(headers)) + '|'
        result.append(header_row)
        result.append(separator)
        
        # Данные
        for row in table_data:
            data_row = '|' + '|'.join(f' {str(cell):<{col_widths[i]}} ' for i, cell in enumerate(row)) + '|'
            result.append(data_row)
        
        result.append(separator)
        
        return '\n'.join(result)


def main():
    """Основная функция программы."""
    # Создаем временный генератор для получения списка отчетов
    temp_processor = LogProcessor()
    temp_generator = ReportGenerator(temp_processor)
    available_reports = list(temp_generator.get_available_reports().keys())
    
    parser = argparse.ArgumentParser(
        description='Анализ лог-файлов и генерация отчетов',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python main.py --file example1.log --report average
  python main.py --file example1.log example2.log --report user_agent
  python main.py --file example1.log --report status --date 2025-06-22
  
Доступные отчеты:
  average    - Статистика по эндпоинтам
  user_agent - Статистика по браузерам пользователей
  status     - Статистика по HTTP статус кодам
        """
    )
    
    parser.add_argument(
        '--file',
        nargs='+',
        required=True,
        help='Путь к лог-файлу(ам)'
    )
    
    parser.add_argument(
        '--report',
        required=True,
        choices=available_reports,
        help='Тип отчета для генерации'
    )
    
    parser.add_argument(
        '--date',
        help='Фильтр по дате в формате YYYY-MM-DD'
    )
    
    args = parser.parse_args()
    
    try:
        # Инициализация процессора логов
        processor = LogProcessor()
        
        # Загрузка логов
        processor.load_logs(args.file, args.date)
        
        if not processor.logs:
            print("Не найдено записей для обработки")
            return
        
        # Генерация отчета
        report_generator = ReportGenerator(processor)
        report_data = report_generator.generate_report(args.report)
        
        if not report_data:
            print("Нет данных для отчета")
            return
        
        # Вывод отчета
        headers = report_generator.get_report_headers(args.report)
        print(format_table(report_data, headers))
        
    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()