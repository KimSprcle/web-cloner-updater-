# Структура проекта

## Итоговая структура проекта

```
web-cloner/
├── core/                      # Основные модули
│   ├── __init__.py           # Инициализация модуля
│   ├── downloader.py         # Загрузка ресурсов
│   ├── parser.py             # Парсинг HTML
│   ├── normalizer.py         # Нормализация структуры
│   └── utils.py              # Утилиты
│
├── logs/                     # Лог-файлы (создается автоматически)
│   └── cloner_*.log
│
├── output/                    # Нормализованные проекты (создается автоматически)
│   └── [project_name]/
│       ├── index.html
│       ├── css/
│       ├── js/
│       ├── images/
│       ├── fonts/
│       └── assets/
│
├── main.py                   # Точка входа
├── requirements.txt          # Зависимости Python
├── README.md                 # Основная документация
├── EXAMPLE.md                # Примеры использования
├── PROJECT_STRUCTURE.md      # Этот файл
└── ANALYSIS.md               # Анализ старого кода
```

## Описание модулей

### `core/downloader.py`
**Назначение:** Загрузка ресурсов с веб-сайтов

**Основные классы:**
- `ResourceDownloader` - класс для загрузки файлов

**Основные методы:**
- `download_file()` - скачивает файл по URL
- `download_resource()` - скачивает ресурс в нужную папку
- `get_failed_urls()` - возвращает список ошибок
- `get_downloaded_count()` - количество скачанных файлов

### `core/parser.py`
**Назначение:** Парсинг HTML и извлечение ресурсов

**Основные классы:**
- `HTMLParser` - класс для парсинга HTML

**Основные методы:**
- `extract_external_css()` - внешние CSS файлы
- `extract_inline_css()` - inline стили
- `extract_external_js()` - внешние JS файлы
- `extract_inline_js()` - inline скрипты
- `extract_images()` - изображения
- `extract_fonts_from_css()` - шрифты из CSS

### `core/normalizer.py`
**Назначение:** Нормализация структуры проекта

**Основные классы:**
- `StructureNormalizer` - класс для нормализации

**Основные методы:**
- `normalize()` - главный метод нормализации
- `_process_external_css()` - обработка внешних CSS
- `_extract_inline_css()` - вынос inline CSS
- `_process_external_js()` - обработка внешних JS
- `_extract_inline_js()` - вынос inline JS
- `_process_images()` - обработка изображений
- `_process_fonts()` - обработка шрифтов
- `_rewrite_paths()` - переписывание путей

### `core/utils.py`
**Назначение:** Утилиты для работы с URL и путями

**Основные функции:**
- `normalize_url()` - нормализация URL
- `get_safe_filename()` - безопасное имя файла
- `resolve_url()` - преобразование относительного URL в абсолютный
- `is_same_domain()` - проверка домена
- `get_file_extension()` - расширение файла
- `create_project_structure()` - создание структуры папок
- `sanitize_filename()` - очистка имени файла
- `get_project_name_from_url()` - имя проекта из URL

### `main.py`
**Назначение:** Точка входа приложения

**Основные классы:**
- `WebsiteNormalizer` - главный класс приложения

**Основные методы:**
- `normalize()` - основной метод нормализации
- `_download_html()` - загрузка HTML
- `_is_spa()` - определение SPA
- `_print_statistics()` - вывод статистики

**Функции:**
- `main()` - главная функция

## Поток выполнения

1. **Запуск** `main.py`
2. **Ввод URL** пользователем
3. **Инициализация** `WebsiteNormalizer`
4. **Загрузка HTML** через `_download_html()`
5. **Создание структуры** через `create_project_structure()`
6. **Инициализация** `ResourceDownloader`
7. **Нормализация** через `StructureNormalizer.normalize()`
8. **Сохранение** нормализованного HTML
9. **Вывод статистики**

## Зависимости

- `requests` - HTTP запросы
- `beautifulsoup4` - парсинг HTML
- `lxml` - парсер для BeautifulSoup

## Требования

- Python 3.10+
- Все зависимости из `requirements.txt`

## Готовность к PyInstaller

Проект готов к сборке в .exe:
- Все импорты корректны
- Относительные пути используются правильно
- Нет зависимостей от внешних файлов конфигурации

