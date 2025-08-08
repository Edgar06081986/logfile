# logfile

Скрипт для анализа лог-файлов в формате JSON. Формирует отчеты по эндпоинтам с количеством запросов и средним временем ответа.

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
# Анализ одного файла
python main.py --file example1.log --report average

# Анализ нескольких файлов
python main.py --file example1.log example2.log --report average

# Анализ с фильтром по дате
python main.py --file example1.log --report average --date 2025-06-22
```

### Параметры

- `--file` - Путь к лог-файлу(ам). Можно указать несколько файлов
- `--report` - Тип отчета. Сейчас поддерживается: `average`
- `--date` - Фильтр по дате в формате YYYY-MM-DD (опционально)

## Формат входных данных

Логи должны быть в формате JSON, по одной записи на строку:

```json
{"@timestamp": "2025-06-22T13:57:32+00:00", "status": 200, "url": "/api/homeworks", "response_time": 0.1}
```

## Отчеты

### average

Показывает статистику по эндпоинтам:
- `handler` - URL эндпоинта
- `total` - общее количество запросов
- `avg_response_time` - среднее время ответа

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

Примеры с файлами example1.log и example2.log:

```bash
# Основной отчет
python main.py --file example1.log --report average

# Анализ нескольких файлов
python main.py --file example1.log example2.log --report average

# Фильтр по конкретной дате
python main.py --file example1.log --report average --date 2025-06-22
```
