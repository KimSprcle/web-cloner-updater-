"""
Модуль для загрузки ресурсов с веб-сайтов.
"""

import logging
import requests
from pathlib import Path
from typing import Set, List, Tuple
from urllib.parse import urlparse

from .utils import resolve_url, get_safe_filename, sanitize_filename

logger = logging.getLogger(__name__)


class ResourceDownloader:
    """Класс для загрузки ресурсов с веб-сайтов."""
    
    def __init__(self, base_url: str, domain: str):
        """
        Инициализация загрузчика.
        
        Args:
            base_url: Базовый URL сайта
            domain: Домен сайта
        """
        self.base_url = base_url
        self.domain = domain
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.downloaded_urls: Set[str] = set()
        self.failed_urls: List[Tuple[str, str]] = []
    
    def download_file(self, url: str, file_path: Path) -> bool:
        """
        Скачивает файл по URL.
        
        Args:
            url: URL файла
            file_path: Путь для сохранения
            
        Returns:
            True если успешно
        """
        # Пропускаем если уже скачали
        if url in self.downloaded_urls:
            return True
        
        try:
            # Создаем директорию если нужно
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Скачиваем файл
            response = self.session.get(url, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            # Определяем тип контента
            content_type = response.headers.get('Content-Type', '').lower()
            
            # Сохраняем файл
            if any(t in content_type for t in ['text', 'html', 'css', 'javascript', 'json']):
                with open(file_path, 'w', encoding='utf-8', errors='ignore') as f:
                    f.write(response.text)
            else:
                with open(file_path, 'wb') as f:
                    f.write(response.content)
            
            self.downloaded_urls.add(url)
            logger.info(f"  ✓ Скачан: {url} -> {file_path.name}")
            return True
            
        except requests.exceptions.RequestException as e:
            self.failed_urls.append((url, str(e)))
            logger.warning(f"  ✗ Ошибка скачивания {url}: {e}")
            return False
        except Exception as e:
            self.failed_urls.append((url, str(e)))
            logger.error(f"  ✗ Неожиданная ошибка при скачивании {url}: {e}")
            return False
    
    def download_resource(self, url: str, output_dir: Path, 
                         subfolder: str = '', filename: str = None) -> Path:
        """
        Скачивает ресурс и возвращает путь к файлу.
        
        Args:
            url: URL ресурса
            output_dir: Директория для сохранения
            subfolder: Подпапка (css, js, images и т.д.)
            filename: Имя файла (если не указано, берется из URL)
            
        Returns:
            Путь к скачанному файлу
        """
        # Определяем имя файла
        if not filename:
            parsed = urlparse(url)
            filename = get_safe_filename(parsed.path)
            filename = sanitize_filename(filename)
        
        # Формируем путь
        if subfolder:
            file_path = output_dir / subfolder / filename
        else:
            file_path = output_dir / filename
        
        # Скачиваем файл
        self.download_file(url, file_path)
        
        return file_path
    
    def get_failed_urls(self) -> List[Tuple[str, str]]:
        """
        Возвращает список URL с ошибками.
        
        Returns:
            Список кортежей (URL, ошибка)
        """
        return self.failed_urls
    
    def get_downloaded_count(self) -> int:
        """
        Возвращает количество успешно скачанных файлов.
        
        Returns:
            Количество файлов
        """
        return len(self.downloaded_urls)

