"""
Модуль для нормализации структуры проекта.
Выносит inline CSS/JS в отдельные файлы и сортирует ресурсы.
"""

import re
import logging
from pathlib import Path
from typing import List, Dict
from bs4 import BeautifulSoup

from .parser import HTMLParser
from .downloader import ResourceDownloader
from .utils import get_file_extension, sanitize_filename, is_same_domain

logger = logging.getLogger(__name__)


class StructureNormalizer:
    """Класс для нормализации структуры проекта."""
    
    def __init__(self, html_content: str, base_url: str, domain: str, 
                 output_dir: Path, downloader: ResourceDownloader):
        """
        Инициализация нормализатора.
        
        Args:
            html_content: HTML содержимое
            base_url: Базовый URL страницы
            domain: Домен сайта
            output_dir: Директория для сохранения
            downloader: Объект загрузчика ресурсов
        """
        self.parser = HTMLParser(html_content, base_url, domain)
        self.output_dir = output_dir
        self.downloader = downloader
        self.base_url = base_url
        self.domain = domain
        
        # Пути к папкам
        self.css_dir = output_dir / 'css'
        self.js_dir = output_dir / 'js'
        self.images_dir = output_dir / 'images'
        self.fonts_dir = output_dir / 'fonts'
        self.assets_dir = output_dir / 'assets'
    
    def normalize(self) -> str:
        """
        Основной метод нормализации структуры.
        
        Returns:
            Нормализованный HTML
        """
        logger.info("Начало нормализации структуры...")
        
        # 1. Обрабатываем внешние CSS
        self._process_external_css()
        
        # 2. Выносим inline CSS
        self._extract_inline_css()
        
        # 3. Обрабатываем внешние JS
        self._process_external_js()
        
        # 4. Выносим inline JS
        self._extract_inline_js()
        
        # 5. Обрабатываем изображения
        self._process_images()
        
        # 6. Обрабатываем шрифты
        self._process_fonts()
        
        # 7. Переписываем пути в HTML
        normalized_html = self._rewrite_paths()
        
        logger.info("Нормализация завершена!")
        
        return normalized_html
    
    def _process_external_css(self):
        """Обрабатывает внешние CSS файлы."""
        css_files = self.parser.extract_external_css()
        
        for idx, css_info in enumerate(css_files):
            url = css_info['url']
            tag = css_info['tag']
            
            # Определяем имя файла
            filename = f"main_{idx + 1}.css"
            if 'href' in tag.attrs:
                href = tag['href']
                if '.' in href.split('/')[-1]:
                    filename = sanitize_filename(href.split('/')[-1])
            
            # Скачиваем CSS файл
            file_path = self.downloader.download_resource(
                url, self.output_dir, 'css', filename
            )
            
            # Обновляем ссылку в HTML (относительный путь)
            relative_path = file_path.relative_to(self.output_dir)
            tag['href'] = str(relative_path).replace('\\', '/')
    
    def _extract_inline_css(self):
        """Выносит inline CSS в отдельный файл."""
        inline_styles = self.parser.extract_inline_css()
        
        if not inline_styles:
            return
        
        # Объединяем все inline стили
        combined_css = []
        for style_info in inline_styles:
            css_content = style_info['content']
            combined_css.append(f"/* Inline style block */\n{css_content}\n")
        
        # Сохраняем в файл
        inline_css_path = self.css_dir / 'inline.css'
        with open(inline_css_path, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(combined_css))
        
        logger.info(f"Создан файл: css/inline.css ({len(inline_styles)} блоков)")
        
        # Удаляем inline стили из HTML
        soup = self.parser.get_soup()
        for style_info in inline_styles:
            style_info['tag'].decompose()
        
        # Добавляем ссылку на inline.css в head
        head = soup.find('head')
        if head:
            link_tag = soup.new_tag('link', rel='stylesheet', href='css/inline.css')
            head.append(link_tag)
    
    def _process_external_js(self):
        """Обрабатывает внешние JS файлы."""
        js_files = self.parser.extract_external_js()
        
        for idx, js_info in enumerate(js_files):
            url = js_info['url']
            tag = js_info['tag']
            
            # Определяем имя файла
            filename = f"main_{idx + 1}.js"
            if 'src' in tag.attrs:
                src = tag['src']
                if '.' in src.split('/')[-1]:
                    filename = sanitize_filename(src.split('/')[-1])
            
            # Скачиваем JS файл
            file_path = self.downloader.download_resource(
                url, self.output_dir, 'js', filename
            )
            
            # Обновляем ссылку в HTML (относительный путь)
            relative_path = file_path.relative_to(self.output_dir)
            tag['src'] = str(relative_path).replace('\\', '/')
    
    def _extract_inline_js(self):
        """Выносит inline JS в отдельный файл."""
        inline_scripts = self.parser.extract_inline_js()
        
        if not inline_scripts:
            return
        
        # Объединяем все inline скрипты
        combined_js = []
        for script_info in inline_scripts:
            js_content = script_info['content']
            combined_js.append(f"/* Inline script block */\n{js_content}\n")
        
        # Сохраняем в файл
        inline_js_path = self.js_dir / 'inline.js'
        with open(inline_js_path, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(combined_js))
        
        logger.info(f"Создан файл: js/inline.js ({len(inline_scripts)} блоков)")
        
        # Удаляем inline скрипты из HTML
        soup = self.parser.get_soup()
        for script_info in inline_scripts:
            script_info['tag'].decompose()
        
        # Добавляем ссылку на inline.js перед закрывающим </body>
        body = soup.find('body')
        if body:
            script_tag = soup.new_tag('script', src='js/inline.js')
            body.append(script_tag)
        else:
            # Если body нет, добавляем в конец HTML
            script_tag = soup.new_tag('script', src='js/inline.js')
            soup.append(script_tag)
    
    def _process_images(self):
        """Обрабатывает изображения."""
        images = self.parser.extract_images()
        
        for idx, img_info in enumerate(images):
            url = img_info['url']
            tag = img_info['tag']
            
            # Определяем расширение
            ext = get_file_extension(url)
            if not ext:
                ext = 'jpg'  # По умолчанию
            
            # Определяем имя файла
            filename = f"image_{idx + 1}.{ext}"
            if 'src' in tag.attrs:
                src = tag['src']
                if '.' in src.split('/')[-1]:
                    filename = sanitize_filename(src.split('/')[-1])
            
            # Скачиваем изображение
            file_path = self.downloader.download_resource(
                url, self.output_dir, 'images', filename
            )
            
            # Обновляем ссылку в HTML (относительный путь)
            if tag.name == 'img':
                relative_path = file_path.relative_to(self.output_dir)
                tag['src'] = str(relative_path).replace('\\', '/')
            elif 'style' in tag.attrs:
                # Обновляем в inline стилях
                relative_path = file_path.relative_to(self.output_dir)
                local_path = str(relative_path).replace('\\', '/')
                style = tag['style']
                style = re.sub(
                    rf'url\(["\']?{re.escape(url)}["\']?\)',
                    f'url({local_path})',
                    style
                )
                tag['style'] = style
    
    def _process_fonts(self):
        """Обрабатывает шрифты из CSS файлов."""
        # Получаем все CSS файлы
        css_files = list(self.css_dir.glob('*.css'))
        
        fonts_found = []
        
        for css_file in css_files:
            try:
                with open(css_file, 'r', encoding='utf-8') as f:
                    css_content = f.read()
                
                # Извлекаем шрифты
                font_urls = self.parser.extract_fonts_from_css(css_content)
                
                for font_url in font_urls:
                    if font_url not in fonts_found:
                        fonts_found.append(font_url)
                        
                        # Определяем имя файла
                        ext = get_file_extension(font_url)
                        filename = f"font_{len(fonts_found)}.{ext}" if ext else "font.woff"
                        
                        # Скачиваем шрифт
                        file_path = self.downloader.download_resource(
                            font_url, self.output_dir, 'fonts', filename
                        )
                        
                        # Обновляем путь в CSS
                        css_content = css_content.replace(
                            font_url,
                            f"../fonts/{file_path.name}"
                        )
                
                # Сохраняем обновленный CSS
                if font_urls:
                    with open(css_file, 'w', encoding='utf-8') as f:
                        f.write(css_content)
                        
            except Exception as e:
                logger.warning(f"Ошибка обработки CSS файла {css_file}: {e}")
        
        if fonts_found:
            logger.info(f"Обработано шрифтов: {len(fonts_found)}")
    
    def _rewrite_paths(self) -> str:
        """
        Переписывает все пути в HTML на локальные.
        
        Returns:
            HTML с переписанными путями
        """
        soup = self.parser.get_soup()
        
        # Переписываем ссылки на CSS
        for link in soup.find_all('link', rel='stylesheet', href=True):
            href = link['href']
            if href.startswith('http'):
                # Если это внешняя ссылка, оставляем как есть или удаляем
                if not is_same_domain(href, self.domain):
                    link.decompose()
        
        # Переписываем ссылки на JS
        for script in soup.find_all('script', src=True):
            src = script['src']
            if src.startswith('http'):
                if not is_same_domain(src, self.domain):
                    script.decompose()
        
        # Переписываем ссылки на изображения
        for img in soup.find_all('img', src=True):
            src = img['src']
            if src.startswith('http'):
                if not is_same_domain(src, self.domain):
                    # Заменяем на placeholder или удаляем
                    img['src'] = 'images/placeholder.png'
        
        return str(soup)

