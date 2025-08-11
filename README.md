# logfile

Скрипт для анализа лог-файлов в формате JSON. Формирует различные отчеты по данным логов.

## Установка

```bash
# Установите зависимости
pip install tabulate

# Для разработки (включая тесты)
pip install pytest pytest-cov
```

## Использование

### Основные команды

```bash
# Анализ эндпоинтов
python main.py --file example1.log --report average

# Анализ браузеров пользователей
python main.py --file example1.log --report user_agent

# Анализ статус кодов
python main.py --file example1.log --report status

# Анализ нескольких файлов
python main.py --file example1.log example2.log --report average

# Анализ с фильтром по дате
python main.py --file example1.log --report average --date 2025-06-22
```

### Параметры

- `--file` - Путь к лог-файлу(ам). Можно указать несколько файлов
- `--report` - Тип отчета: `average`, `user_agent`, `status`
- `--date` - Фильтр по дате в формате YYYY-MM-DD (опционально)

## Формат входных данных

Логи должны быть в формате JSON, по одной записи на строку:

```json
{"@timestamp": "2025-06-22T13:57:32+00:00", "status": 200, "url": "/api/homeworks", "response_time": 0.1, "http_user_agent": "Mozilla/5.0..."}
```

## Типы отчетов

### average
Показывает статистику по эндпоинтам:
- `handler` - URL эндпоинта
- `total` - общее количество запросов
- `avg_response_time` - среднее время ответа

### user_agent
Показывает статистику по браузерам пользователей:
- `browser` - название браузера
- `requests` - количество запросов
- `percentage` - процент от общего количества

### status
Показывает статистику по HTTP статус кодам:
- `status_code` - код статуса
- `requests` - количество запросов
- `percentage` - процент от общего количества

## Расширяемость

Архитектура позволяет легко добавлять новые типы отчетов:

```python
# Добавление нового отчета
def generate_custom_report(processor):
    # Логика генерации отчета
    return report_data

# Регистрация в ReportGenerator
generator.add_report_type(
    'custom',
    generate_custom_report,
    ['header1', 'header2'],
    'Описание отчета'
)
```

## Тестирование

```bash
# Запуск тестов
pytest

# Запуск тестов с покрытием
pytest --cov=. --cov-report=term-missing

# Запуск тестов с HTML отчетом о покрытии
pytest --cov=. --cov-report=html
```

## Примеры запуска

```bash
# Основной отчет по эндпоинтам
python main.py --file example1.log --report average

# Анализ браузеров пользователей
python main.py --file example1.log --report user_agent

# Анализ статус кодов за конкретную дату
python main.py --file example1.log --report status --date 2025-06-22

# Анализ нескольких файлов
python main.py --file example1.log example2.log --report average
```