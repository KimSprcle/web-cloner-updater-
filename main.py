"""
Главный модуль для нормализации и клонирования веб-сайтов.
Точка входа приложения.
"""

import os
import sys
import logging
import requests
from pathlib import Path
from datetime import datetime

from core.utils import (
    normalize_url, 
    get_project_name_from_url, 
    create_project_structure
)
from core.downloader import ResourceDownloader
from core.parser import HTMLParser
from core.normalizer import StructureNormalizer

# Настройка логирования
LOG_DIR = Path('logs')
LOG_DIR.mkdir(exist_ok=True)

log_file = LOG_DIR / f"cloner_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class WebsiteNormalizer:
    """Главный класс для нормализации веб-сайтов."""
    
    def __init__(self, url: str, output_base_dir: Path = Path('output')):
        """
        Инициализация нормализатора.
        
        Args:
            url: URL сайта для нормализации
            output_base_dir: Базовая директория для сохранения проектов
        """
        self.url = normalize_url(url)
        self.output_base_dir = output_base_dir
        self.output_base_dir.mkdir(exist_ok=True)
        
        # Парсинг URL
        from urllib.parse import urlparse
        parsed = urlparse(self.url)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        self.domain = parsed.netloc
        
        # Имя проекта
        self.project_name = get_project_name_from_url(self.url)
        self.project_dir = self.output_base_dir / self.project_name
        
        logger.info("=" * 60)
        logger.info(f"НОРМАЛИЗАЦИЯ САЙТА: {self.url}")
        logger.info(f"Домен: {self.domain}")
        logger.info(f"Проект: {self.project_name}")
        logger.info(f"Директория: {self.project_dir.absolute()}")
        logger.info("=" * 60)
    
    def normalize(self) -> bool:
        """
        Основной метод нормализации.
        
        Returns:
            True если успешно
        """
        try:
            # 1. Загружаем HTML
            logger.info("Шаг 1: Загрузка HTML страницы...")
            html_content = self._download_html()
            
            if not html_content:
                logger.error("Не удалось загрузить HTML страницу")
                return False
            
            # 2. Создаем структуру проекта
            logger.info("Шаг 2: Создание структуры проекта...")
            dirs = create_project_structure(self.project_dir)
            
            # 3. Инициализируем загрузчик
            logger.info("Шаг 3: Инициализация загрузчика ресурсов...")
            downloader = ResourceDownloader(self.base_url, self.domain)
            
            # 4. Нормализуем структуру
            logger.info("Шаг 4: Нормализация структуры...")
            normalizer = StructureNormalizer(
                html_content, 
                self.base_url, 
                self.domain,
                self.project_dir,
                downloader
            )
            
            normalized_html = normalizer.normalize()
            
            # 5. Сохраняем нормализованный HTML
            logger.info("Шаг 5: Сохранение нормализованного HTML...")
            index_path = self.project_dir / 'index.html'
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(normalized_html)
            
            logger.info(f"✓ HTML сохранен: {index_path}")
            
            # 6. Выводим статистику
            self._print_statistics(downloader)
            
            logger.info("=" * 60)
            logger.info("НОРМАЛИЗАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
            logger.info(f"Проект сохранен в: {self.project_dir.absolute()}")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при нормализации: {e}", exc_info=True)
            return False
    
    def _download_html(self) -> str:
        """
        Загружает HTML страницу.
        
        Returns:
            HTML содержимое или пустая строка при ошибке
        """
        try:
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            response = session.get(self.url, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            # Определяем кодировку
            if response.encoding:
                html_content = response.text
            else:
                html_content = response.content.decode('utf-8', errors='ignore')
            
            logger.info(f"✓ HTML загружен ({len(html_content)} символов)")
            
            # Проверка на SPA
            if self._is_spa(html_content):
                logger.warning("⚠ Обнаружен SPA (Single Page Application)")
                logger.warning("  Структура будет восстановлена визуально")
            
            return html_content
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка загрузки HTML: {e}")
            return ""
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {e}")
            return ""
    
    def _is_spa(self, html_content: str) -> bool:
        """
        Определяет, является ли сайт SPA.
        
        Args:
            html_content: HTML содержимое
            
        Returns:
            True если SPA
        """
        spa_indicators = [
            'react',
            'vue',
            'angular',
            'next.js',
            'nuxt',
            '__NEXT_DATA__',
            'app-root',
            'ng-app'
        ]
        
        html_lower = html_content.lower()
        
        for indicator in spa_indicators:
            if indicator in html_lower:
                return True
        
        return False
    
    def _print_statistics(self, downloader: ResourceDownloader):
        """
        Выводит статистику по скачанным ресурсам.
        
        Args:
            downloader: Объект загрузчика
        """
        logger.info("=" * 60)
        logger.info("СТАТИСТИКА:")
        logger.info(f"  Скачано файлов: {downloader.get_downloaded_count()}")
        
        failed = downloader.get_failed_urls()
        if failed:
            logger.warning(f"  Ошибок загрузки: {len(failed)}")
            for url, error in failed[:5]:  # Показываем первые 5
                logger.warning(f"    - {url}: {error}")
        
        # Подсчет файлов по типам
        css_count = len(list(self.project_dir.glob('css/*.css')))
        js_count = len(list(self.project_dir.glob('js/*.js')))
        img_count = len(list(self.project_dir.glob('images/*')))
        font_count = len(list(self.project_dir.glob('fonts/*')))
        
        logger.info(f"  CSS файлов: {css_count}")
        logger.info(f"  JS файлов: {js_count}")
        logger.info(f"  Изображений: {img_count}")
        logger.info(f"  Шрифтов: {font_count}")
        logger.info("=" * 60)


def main():
    """Главная функция."""
    print("\n" + "=" * 60)
    print("ВЕБ-НОРМАЛИЗАТОР")
    print("Нормализация структуры веб-сайтов")
    print("=" * 60 + "\n")
    
    # Получаем URL от пользователя
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Введите URL сайта: ").strip()
    
    if not url:
        print("Ошибка: URL не указан")
        sys.exit(1)
    
    # Создаем нормализатор
    normalizer = WebsiteNormalizer(url)
    
    # Запускаем нормализацию
    success = normalizer.normalize()
    
    if success:
        print(f"\n✓ Проект успешно создан: {normalizer.project_dir}")
        print(f"✓ Лог сохранен: {log_file}")
        sys.exit(0)
    else:
        print("\n✗ Ошибка при нормализации сайта")
        print(f"✓ Лог сохранен: {log_file}")
        sys.exit(1)


if __name__ == "__main__":
    main()

