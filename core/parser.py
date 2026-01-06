"""
Модуль для парсинга HTML и извлечения ресурсов.
"""

import re
import logging
from typing import List, Dict, Tuple
from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse

from .utils import resolve_url, is_same_domain

logger = logging.getLogger(__name__)


class HTMLParser:
    """Класс для парсинга HTML и извлечения ресурсов."""
    
    def __init__(self, html_content: str, base_url: str, domain: str):
        """
        Инициализация парсера.
        
        Args:
            html_content: HTML содержимое
            base_url: Базовый URL страницы
            domain: Домен сайта
        """
        self.html_content = html_content
        self.base_url = base_url
        self.domain = domain
        self.soup = BeautifulSoup(html_content, 'html.parser')
    
    def extract_external_css(self) -> List[Dict[str, str]]:
        """
        Извлекает ссылки на внешние CSS файлы.
        
        Returns:
            Список словарей с информацией о CSS файлах
        """
        css_files = []
        
        for link in self.soup.find_all('link', rel='stylesheet', href=True):
            url = resolve_url(link['href'], self.base_url)
            
            if is_same_domain(url, self.domain):
                css_files.append({
                    'url': url,
                    'tag': link,
                    'type': 'external'
                })
        
        logger.info(f"Найдено внешних CSS файлов: {len(css_files)}")
        return css_files
    
    def extract_inline_css(self) -> List[Dict[str, str]]:
        """
        Извлекает inline CSS из тегов <style>.
        
        Returns:
            Список словарей с CSS кодом
        """
        inline_styles = []
        
        for style_tag in self.soup.find_all('style'):
            if style_tag.string:
                css_content = style_tag.string.strip()
                if css_content:
                    inline_styles.append({
                        'content': css_content,
                        'tag': style_tag,
                        'type': 'inline'
                    })
        
        logger.info(f"Найдено inline CSS блоков: {len(inline_styles)}")
        return inline_styles
    
    def extract_external_js(self) -> List[Dict[str, str]]:
        """
        Извлекает ссылки на внешние JS файлы.
        
        Returns:
            Список словарей с информацией о JS файлах
        """
        js_files = []
        
        for script in self.soup.find_all('script', src=True):
            url = resolve_url(script['src'], self.base_url)
            
            if is_same_domain(url, self.domain):
                js_files.append({
                    'url': url,
                    'tag': script,
                    'type': 'external'
                })
        
        logger.info(f"Найдено внешних JS файлов: {len(js_files)}")
        return js_files
    
    def extract_inline_js(self) -> List[Dict[str, str]]:
        """
        Извлекает inline JavaScript из тегов <script>.
        
        Returns:
            Список словарей с JS кодом
        """
        inline_scripts = []
        
        for script_tag in self.soup.find_all('script', src=False):
            if script_tag.string:
                js_content = script_tag.string.strip()
                if js_content and not js_content.startswith('<!--'):
                    inline_scripts.append({
                        'content': js_content,
                        'tag': script_tag,
                        'type': 'inline'
                    })
        
        logger.info(f"Найдено inline JS блоков: {len(inline_scripts)}")
        return inline_scripts
    
    def extract_images(self) -> List[Dict[str, str]]:
        """
        Извлекает ссылки на изображения.
        
        Returns:
            Список словарей с информацией об изображениях
        """
        images = []
        
        for img in self.soup.find_all('img', src=True):
            url = resolve_url(img['src'], self.base_url)
            
            if is_same_domain(url, self.domain):
                images.append({
                    'url': url,
                    'tag': img,
                    'type': 'image'
                })
        
        # Также ищем в CSS background-image
        for tag in self.soup.find_all(style=True):
            style_content = tag.get('style', '')
            urls = re.findall(r'url\(["\']?([^"\')]+)["\']?\)', style_content)
            for url in urls:
                abs_url = resolve_url(url, self.base_url)
                if is_same_domain(abs_url, self.domain):
                    images.append({
                        'url': abs_url,
                        'tag': tag,
                        'type': 'image'
                    })
        
        logger.info(f"Найдено изображений: {len(images)}")
        return images
    
    def extract_fonts_from_css(self, css_content: str) -> List[str]:
        """
        Извлекает URL шрифтов из CSS контента.
        
        Args:
            css_content: CSS содержимое
            
        Returns:
            Список URL шрифтов
        """
        fonts = []
        
        # Ищем @font-face с url()
        pattern = r'@font-face\s*\{[^}]*url\(["\']?([^"\')]+)["\']?\)[^}]*\}'
        matches = re.finditer(pattern, css_content, re.IGNORECASE | re.DOTALL)
        
        for match in matches:
            font_url = match.group(1)
            abs_url = resolve_url(font_url, self.base_url)
            if is_same_domain(abs_url, self.domain):
                fonts.append(abs_url)
        
        # Также ищем обычные url() в контексте font
        pattern = r'url\(["\']?([^"\')]+\.(woff|woff2|ttf|otf|eot))["\']?\)'
        matches = re.finditer(pattern, css_content, re.IGNORECASE)
        
        for match in matches:
            font_url = match.group(1)
            abs_url = resolve_url(font_url, self.base_url)
            if is_same_domain(abs_url, self.domain) and abs_url not in fonts:
                fonts.append(abs_url)
        
        return fonts
    
    def get_soup(self) -> BeautifulSoup:
        """
        Возвращает объект BeautifulSoup.
        
        Returns:
            BeautifulSoup объект
        """
        return self.soup
    
    def get_html(self) -> str:
        """
        Возвращает HTML как строку.
        
        Returns:
            HTML содержимое
        """
        return str(self.soup)

