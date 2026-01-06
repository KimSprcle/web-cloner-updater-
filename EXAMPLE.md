# Примеры использования

## Пример 1: Простой статический сайт

```bash
python main.py https://example.com
```

**Результат:**
```
output/example.com/
├── index.html
├── css/
│   ├── main_1.css
│   └── inline.css
├── js/
│   └── inline.js
└── images/
    └── logo.png
```

## Пример 2: Сайт с множеством ресурсов

```bash
python main.py https://getbootstrap.com
```

**Результат:**
```
output/getbootstrap.com/
├── index.html
├── css/
│   ├── main_1.css
│   ├── main_2.css
│   └── inline.css
├── js/
│   ├── main_1.js
│   ├── main_2.js
│   └── inline.js
├── images/
│   ├── bootstrap-logo.svg
│   └── ...
└── fonts/
    └── ...
```

## Пример 3: Интерактивный режим

```bash
python main.py
```

Затем введите URL при запросе:
```
Введите URL сайта: github.com
```

## Структура логов

После выполнения создается лог-файл:
```
logs/cloner_20250105_165000.log
```

Содержимое лога:
```
2025-01-05 16:50:00 - INFO - ============================================================
2025-01-05 16:50:00 - INFO - НОРМАЛИЗАЦИЯ САЙТА: https://example.com
2025-01-05 16:50:00 - INFO - Домен: example.com
2025-01-05 16:50:00 - INFO - Проект: example.com
2025-01-05 16:50:00 - INFO - Директория: C:\...\output\example.com
2025-01-05 16:50:00 - INFO - ============================================================
2025-01-05 16:50:01 - INFO - Шаг 1: Загрузка HTML страницы...
2025-01-05 16:50:02 - INFO - ✓ HTML загружен (45231 символов)
...
```

## Обработка ошибок

Если сайт недоступен:
```
2025-01-05 16:50:00 - ERROR - Ошибка загрузки HTML: Connection timeout
```

Если ресурс не скачался:
```
2025-01-05 16:50:05 - WARNING - ✗ Ошибка скачивания https://example.com/resource.css: 404 Not Found
```

## SPA предупреждение

Если обнаружен SPA:
```
2025-01-05 16:50:02 - WARNING - ⚠ Обнаружен SPA (Single Page Application)
2025-01-05 16:50:02 - WARNING -   Структура будет восстановлена визуально
```

