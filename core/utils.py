"""
Утилиты для работы с путями, URL и файлами.
"""

import os
import re
import logging
from pathlib import Path
from urllib.parse import urlparse, urljoin, urlunparse

logger = logging.getLogger(__name__)


def normalize_url(url: str) -> str:
    """
    Нормализует URL - добавляет протокол если отсутствует.
    
    Args:
        url: URL для нормализации
        
    Returns:
        Нормализованный URL
    """
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url.rstrip('/')


def get_safe_filename(url_path: str, default_name: str = 'index.html') -> str:
    """
    Создает безопасное имя файла из URL пути.
    
    Args:
        url_path: Путь из URL
        default_name: Имя по умолчанию
        
    Returns:
        Безопасное имя файла
    """
    if not url_path or url_path == '/':
        return default_name
    
    # Удаляем начальный слэш
    path = url_path.lstrip('/')
    
    # Удаляем query параметры и фрагменты
    path = path.split('?')[0].split('#')[0]
    
    # Заменяем недопустимые символы
    path = re.sub(r'[<>:"|?*]', '_', path)
    
    # Если путь заканчивается на /, добавляем index.html
    if path.endswith('/'):
        path += 'index.html'
    
    # Если нет расширения, добавляем .html
    if '.' not in os.path.basename(path):
        path += '.html'
    
    return path


def resolve_url(url: str, base_url: str) -> str:
    """
    Преобразует относительный URL в абсолютный.
    
    Args:
        url: URL (может быть относительным)
        base_url: Базовый URL
        
    Returns:
        Абсолютный URL
    """
    if url.startswith(('http://', 'https://')):
        return url
    
    if url.startswith('//'):
        return f"{urlparse(base_url).scheme}:{url}"
    
    return urljoin(base_url, url)


def is_same_domain(url: str, domain: str) -> bool:
    """
    Проверяет, принадлежит ли URL тому же домену.
    
    Args:
        url: URL для проверки
        domain: Домен для сравнения
        
    Returns:
        True если тот же домен
    """
    try:
        parsed = urlparse(url)
        return parsed.netloc == domain or parsed.netloc == ''
    except:
        return False


def get_file_extension(url: str) -> str:
    """
    Определяет расширение файла из URL.
    
    Args:
        url: URL файла
        
    Returns:
        Расширение файла (без точки)
    """
    parsed = urlparse(url)
    path = parsed.path
    
    if '.' in path:
        return path.split('.')[-1].lower()
    
    return ''


def create_project_structure(output_dir: Path) -> dict:
    """
    Создает структуру папок проекта.
    
    Args:
        output_dir: Корневая директория проекта
        
    Returns:
        Словарь с путями к папкам
    """
    dirs = {
        'root': output_dir,
        'css': output_dir / 'css',
        'js': output_dir / 'js',
        'images': output_dir / 'images',
        'fonts': output_dir / 'fonts',
        'assets': output_dir / 'assets'
    }
    
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Создана структура проекта: {output_dir}")
    
    return dirs


def sanitize_filename(filename: str) -> str:
    """
    Очищает имя файла от недопустимых символов.
    
    Args:
        filename: Исходное имя файла
        
    Returns:
        Очищенное имя файла
    """
    # Удаляем недопустимые символы
    filename = re.sub(r'[<>:"|?*\x00-\x1f]', '_', filename)
    
    # Удаляем пробелы в начале и конце
    filename = filename.strip()
    
    # Если имя пустое, возвращаем default
    if not filename:
        filename = 'file'
    
    # Ограничиваем длину
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:250] + ext
    
    return filename


def get_project_name_from_url(url: str) -> str:
    """
    Извлекает имя проекта из URL.
    
    Args:
        url: URL сайта
        
    Returns:
        Имя проекта (домен)
    """
    parsed = urlparse(normalize_url(url))
    domain = parsed.netloc.replace('www.', '')
    
    # Очищаем от недопустимых символов
    domain = sanitize_filename(domain)
    
    return domain

