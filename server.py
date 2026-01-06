"""
Веб-сервер для клонирования сайтов с отправкой через Telegram бота.

Основные возможности:
- Полное клонирование сайта (HTML, CSS, JS, изображения, шрифты)
- Сохранение структуры папок
- Переписывание ссылок для локального просмотра
- Архивирование в ZIP
- Отправка архива через Telegram бота
- Подробное логирование
"""

import http.server
import socketserver
import os
import re
import logging
import zipfile
import shutil
from urllib.parse import urlparse, urljoin, urlunparse, parse_qs
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import threading
import json

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cloner.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Константы
CLONED_SITES_DIR = 'cloned_sites'
CONFIG_FILE = 'config.json'
PORT = 5000

# Загрузка конфигурации
def load_config():
    """Загружает конфигурацию из файла config.json"""
    default_config = {
        "telegram_bot_token": "",
        "telegram_chat_id": ""
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return {**default_config, **config}
        except Exception as e:
            logger.warning(f"Ошибка загрузки config.json: {e}. Используются значения по умолчанию.")
    
    return default_config

CONFIG = load_config()


class WebsiteCloner:
    """Класс для клонирования веб-сайтов"""
    
    def __init__(self, url, output_dir):
        """
        Инициализация клонировщика
        
        Args:
            url: URL сайта для клонирования
            output_dir: Директория для сохранения файлов
        """
        self.url = self._normalize_url(url)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Парсинг URL
        parsed = urlparse(self.url)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        self.domain = parsed.netloc
        
        # Сессия для запросов
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Отслеживание скачанных ресурсов
        self.downloaded_urls = set()
        self.failed_urls = []
        
        logger.info(f"Инициализация клонирования: {self.url}")
        logger.info(f"Директория сохранения: {self.output_dir.absolute()}")
    
    def _normalize_url(self, url):
        """Нормализует URL (добавляет протокол если отсутствует)"""
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url.rstrip('/')
    
    def _get_safe_filename(self, url_path):
        """
        Создает безопасное имя файла из URL пути
        
        Args:
            url_path: Путь из URL
            
        Returns:
            Безопасное имя файла
        """
        # Удаляем начальный слэш
        path = url_path.lstrip('/')
        
        # Если путь пустой, возвращаем index.html
        if not path or path == '/':
            return 'index.html'
        
        # Заменяем недопустимые символы
        path = re.sub(r'[<>:"|?*]', '_', path)
        
        # Если путь заканчивается на /, добавляем index.html
        if path.endswith('/'):
            path += 'index.html'
        
        # Если нет расширения, добавляем .html
        if '.' not in os.path.basename(path):
            path += '.html'
        
        return path
    
    def _download_file(self, url, file_path):
        """
        Скачивает файл по URL
        
        Args:
            url: URL файла
            file_path: Путь для сохранения (может быть Path объектом или строкой)
            
        Returns:
            True если успешно, False в противном случае
        """
        # Пропускаем если уже скачали
        if url in self.downloaded_urls:
            return True
        
        try:
            # Преобразуем в Path если нужно
            if isinstance(file_path, str):
                file_path = Path(file_path)
            
            # Очищаем путь от недопустимых символов
            parts = []
            for part in file_path.parts:
                # Заменяем недопустимые символы
                clean_part = re.sub(r'[<>:"|?*]', '_', part)
                parts.append(clean_part)
            file_path = Path(*parts)
            
            # Создаем директорию если нужно
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Скачиваем файл
            response = self.session.get(url, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            # Определяем тип контента
            content_type = response.headers.get('Content-Type', '').lower()
            
            # Сохраняем файл
            if 'text' in content_type or 'html' in content_type or 'css' in content_type or 'javascript' in content_type:
                # Текстовые файлы сохраняем с правильной кодировкой
                with open(file_path, 'w', encoding='utf-8', errors='ignore') as f:
                    f.write(response.text)
            else:
                # Бинарные файлы
                with open(file_path, 'wb') as f:
                    f.write(response.content)
            
            self.downloaded_urls.add(url)
            logger.info(f"  ✓ Скачан: {url} -> {file_path.relative_to(self.output_dir)}")
            return True
            
        except requests.exceptions.RequestException as e:
            self.failed_urls.append((url, str(e)))
            logger.warning(f"  ✗ Ошибка скачивания {url}: {e}")
            return False
        except Exception as e:
            self.failed_urls.append((url, str(e)))
            logger.error(f"  ✗ Неожиданная ошибка при скачивании {url}: {e}")
            return False
    
    def _resolve_url(self, url, base_url=None):
        """
        Преобразует относительный URL в абсолютный
        
        Args:
            url: URL (может быть относительным)
            base_url: Базовый URL (по умолчанию self.base_url)
            
        Returns:
            Абсолютный URL
        """
        if base_url is None:
            base_url = self.base_url
        
        # Если URL уже абсолютный
        if url.startswith(('http://', 'https://')):
            return url
        
        # Если URL начинается с //
        if url.startswith('//'):
            return f"{urlparse(base_url).scheme}:{url}"
        
        # Объединяем с базовым URL
        return urljoin(base_url, url)
    
    def _is_same_domain(self, url):
        """Проверяет, принадлежит ли URL тому же домену"""
        try:
            parsed = urlparse(url)
            return parsed.netloc == self.domain or parsed.netloc == ''
        except:
            return False
    
    def _should_download(self, url):
        """
        Определяет, нужно ли скачивать ресурс
        
        Args:
            url: URL ресурса
            
        Returns:
            True если нужно скачать, False в противном случае
        """
        # Пропускаем внешние домены (можно настроить)
        if not self._is_same_domain(url):
            return False
        
        # Пропускаем уже скачанные
        if url in self.downloaded_urls:
            return False
        
        # Пропускаем data: и javascript: URL
        if url.startswith(('data:', 'javascript:', 'mailto:', 'tel:')):
            return False
        
        return True
    
    def _rewrite_urls_in_html(self, html_content, base_url):
        """
        Переписывает URL в HTML для локального просмотра
        
        Args:
            html_content: Содержимое HTML
            base_url: Базовый URL страницы
            
        Returns:
            HTML с переписанными URL
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Теги с атрибутом href
        for tag in soup.find_all(['a', 'link'], href=True):
            original_url = tag['href']
            if self._should_download(self._resolve_url(original_url, base_url)):
                local_path = self._url_to_local_path(original_url, base_url)
                tag['href'] = local_path
        
        # Теги с атрибутом src
        for tag in soup.find_all(['img', 'script', 'iframe', 'source', 'audio', 'video'], src=True):
            original_url = tag['src']
            if self._should_download(self._resolve_url(original_url, base_url)):
                local_path = self._url_to_local_path(original_url, base_url)
                tag['src'] = local_path
        
        # CSS в style тегах
        for tag in soup.find_all('style'):
            if tag.string:
                tag.string = self._rewrite_css_urls(tag.string, base_url)
        
        # Атрибут style
        for tag in soup.find_all(style=True):
            tag['style'] = self._rewrite_css_urls(tag['style'], base_url)
        
        return str(soup)
    
    def _rewrite_css_urls(self, css_content, base_url):
        """
        Переписывает URL в CSS
        
        Args:
            css_content: Содержимое CSS
            base_url: Базовый URL
            
        Returns:
            CSS с переписанными URL
        """
        def replace_url(match):
            url = match.group(1).strip('\'"')
            absolute_url = self._resolve_url(url, base_url)
            if self._should_download(absolute_url):
                local_path = self._url_to_local_path(url, base_url)
                return f"url({local_path})"
            return match.group(0)
        
        # Паттерн для url() в CSS
        pattern = r'url\(([^)]+)\)'
        return re.sub(pattern, replace_url, css_content)
    
    def _url_to_local_path(self, url, base_url):
        """
        Преобразует URL в локальный путь относительно корня сайта
        
        Args:
            url: URL (может быть относительным)
            base_url: Базовый URL текущей страницы
            
        Returns:
            Относительный путь для использования в HTML
        """
        absolute_url = self._resolve_url(url, base_url)
        parsed = urlparse(absolute_url)
        path = parsed.path
        
        # Если путь пустой, возвращаем index.html
        if not path or path == '/':
            return 'index.html'
        
        # Удаляем начальный слэш
        path = path.lstrip('/')
        
        # Если нет расширения и это не директория, добавляем .html
        if '.' not in os.path.basename(path) and not path.endswith('/'):
            path += '.html'
        
        return path
    
    def clone(self):
        """
        Основной метод клонирования сайта
        
        Returns:
            True если успешно, False в противном случае
        """
        try:
            logger.info(f"Начало клонирования сайта: {self.url}")
            
            # Скачиваем главную страницу
            logger.info("Скачивание главной страницы...")
            response = self.session.get(self.url, timeout=30)
            response.raise_for_status()
            
            # Определяем тип контента
            content_type = response.headers.get('Content-Type', '').lower()
            
            if 'html' in content_type:
                # Обрабатываем HTML
                html_content = response.text
                
                # Переписываем URL
                html_content = self._rewrite_urls_in_html(html_content, self.url)
                
                # Сохраняем главную страницу
                index_path = self.output_dir / 'index.html'
                with open(index_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                logger.info(f"Главная страница сохранена: {index_path}")
                
                # Находим и скачиваем все ресурсы
                self._download_resources(html_content, self.url)
                
            else:
                # Если не HTML, просто сохраняем как есть
                file_path = self.output_dir / 'index.html'
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"Файл сохранен: {file_path}")
            
            # Скачиваем CSS файлы
            self._download_css_files()
            
            # Скачиваем JS файлы
            self._download_js_files()
            
            # Скачиваем изображения
            self._download_images()
            
            # Скачиваем шрифты
            self._download_fonts()
            
            logger.info(f"Клонирование завершено!")
            logger.info(f"Скачано файлов: {len(self.downloaded_urls)}")
            if self.failed_urls:
                logger.warning(f"Не удалось скачать: {len(self.failed_urls)} файлов")
            
            return True
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Ошибка при клонировании сайта: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Неожиданная ошибка: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def _download_resources(self, html_content, base_url):
        """Находит и скачивает все ресурсы из HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # CSS файлы
        for link in soup.find_all('link', rel='stylesheet', href=True):
            url = self._resolve_url(link['href'], base_url)
            # Удаляем query параметры и фрагменты из URL
            url = url.split('?')[0].split('#')[0]
            if self._should_download(url):
                parsed = urlparse(url)
                file_path = self.output_dir / parsed.path.lstrip('/')
                if not file_path.suffix:
                    file_path = file_path.parent / (file_path.name + '.css')
                elif file_path.suffix == '':
                    file_path = file_path.parent / (file_path.name + '.css')
                self._download_file(url, file_path)
        
        # JS файлы
        for script in soup.find_all('script', src=True):
            url = self._resolve_url(script['src'], base_url)
            url = url.split('?')[0].split('#')[0]
            if self._should_download(url):
                parsed = urlparse(url)
                file_path = self.output_dir / parsed.path.lstrip('/')
                if not file_path.suffix:
                    file_path = file_path.parent / (file_path.name + '.js')
                elif file_path.suffix == '':
                    file_path = file_path.parent / (file_path.name + '.js')
                self._download_file(url, file_path)
        
        # Изображения
        for img in soup.find_all('img', src=True):
            url = self._resolve_url(img['src'], base_url)
            url = url.split('?')[0].split('#')[0]
            if self._should_download(url):
                parsed = urlparse(url)
                file_path = self.output_dir / parsed.path.lstrip('/')
                self._download_file(url, file_path)
        
        # Другие ресурсы
        for tag in soup.find_all(['source', 'audio', 'video'], src=True):
            url = self._resolve_url(tag['src'], base_url)
            url = url.split('?')[0].split('#')[0]
            if self._should_download(url):
                parsed = urlparse(url)
                file_path = self.output_dir / parsed.path.lstrip('/')
                self._download_file(url, file_path)
    
    def _download_css_files(self):
        """Скачивает CSS файлы и обрабатывает встроенные URL"""
        # Находим все CSS файлы в структуре
        for css_file in self.output_dir.rglob('*.css'):
            try:
                # Определяем базовый URL для этого CSS файла
                relative_path = css_file.relative_to(self.output_dir)
                if relative_path.parent == Path('.'):
                    css_dir_url = f"{self.base_url}/"
                else:
                    css_dir_url = f"{self.base_url}/{relative_path.parent.as_posix().replace(chr(92), '/')}/"
                
                with open(css_file, 'r', encoding='utf-8', errors='ignore') as f:
                    css_content = f.read()
                
                # Находим и скачиваем ресурсы из CSS перед переписыванием
                pattern = r'url\(([^)]+)\)'
                for match in re.finditer(pattern, css_content):
                    url = match.group(1).strip('\'"')
                    absolute_url = self._resolve_url(url, css_dir_url)
                    # Удаляем query параметры
                    absolute_url = absolute_url.split('?')[0].split('#')[0]
                    if self._should_download(absolute_url):
                        parsed = urlparse(absolute_url)
                        # Сохраняем относительно директории CSS файла
                        resource_relative = parsed.path.lstrip('/')
                        if resource_relative:
                            resource_path = css_file.parent / resource_relative
                            self._download_file(absolute_url, resource_path)
                
                # Переписываем URL в CSS
                css_content = self._rewrite_css_urls(css_content, css_dir_url)
                
                # Сохраняем обработанный CSS
                with open(css_file, 'w', encoding='utf-8') as f:
                    f.write(css_content)
                    
            except Exception as e:
                logger.warning(f"Ошибка обработки CSS файла {css_file}: {e}")
    
    def _download_js_files(self):
        """Скачивает JS файлы"""
        js_dir = self.output_dir / 'js'
        if not js_dir.exists():
            return
        
        # JS файлы уже скачаны в _download_resources
        pass
    
    def _download_images(self):
        """Скачивает изображения"""
        # Изображения уже скачаны в _download_resources
        pass
    
    def _download_fonts(self):
        """Скачивает шрифты из CSS"""
        # Шрифты обрабатываются в _download_css_files
        pass


def create_zip_archive(source_dir, zip_path):
    """
    Создает ZIP архив из директории
    
    Args:
        source_dir: Исходная директория
        zip_path: Путь к ZIP файлу
        
    Returns:
        Путь к созданному ZIP файлу
    """
    logger.info(f"Создание ZIP архива: {zip_path}")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname)
                logger.debug(f"  Добавлен в архив: {arcname}")
    
    zip_size = os.path.getsize(zip_path) / (1024 * 1024)  # MB
    logger.info(f"ZIP архив создан: {zip_path} ({zip_size:.2f} MB)")
    
    return zip_path


def send_telegram_file(file_path, bot_token, chat_id):
    """
    Отправляет файл через Telegram бота
    
    Args:
        file_path: Путь к файлу
        bot_token: Токен Telegram бота
        chat_id: ID чата для отправки
        
    Returns:
        True если успешно, False в противном случае
    """
    if not bot_token or not chat_id:
        logger.warning("Telegram бот не настроен. Пропуск отправки.")
        return False
    
    try:
        logger.info(f"Отправка файла через Telegram: {file_path}")
        
        url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
        
        with open(file_path, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': chat_id}
            response = requests.post(url, files=files, data=data, timeout=300)
            response.raise_for_status()
        
        logger.info("Файл успешно отправлен через Telegram")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка отправки файла через Telegram: {e}")
        return False


class RequestHandler(http.server.SimpleHTTPRequestHandler):
    """Обработчик HTTP запросов"""
    
    def do_GET(self):
        """Обработка GET запросов"""
        if self.path == "/":
            self.path = "index.html"
        try:
            return http.server.SimpleHTTPRequestHandler.do_GET(self)
        except FileNotFoundError:
            self.send_error(404, "File not found")
    
    def do_POST(self):
        """Обработка POST запросов (клонирование сайта)"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode("utf-8")
        
        # Парсинг данных формы
        form = parse_qs(post_data)
        url = form.get("submitButton", [""])[0]
        
        if not url:
            self.send_error(400, "Bad Request: URL is missing")
            return
        
        # Запускаем клонирование в отдельном потоке
        thread = threading.Thread(
            target=self._clone_website_async,
            args=(url,)
        )
        thread.daemon = True
        thread.start()
        
        # Отправляем ответ пользователю
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        
        response_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Клонирование начато</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                .message { background: #e8f5e9; padding: 20px; border-radius: 10px; display: inline-block; }
            </style>
        </head>
        <body>
            <div class="message">
                <h2>Клонирование начато!</h2>
                <p>Сайт <strong>{}</strong> клонируется в фоновом режиме.</p>
                <p>Проверьте логи для отслеживания прогресса.</p>
                <p><a href="/">Вернуться на главную</a></p>
            </div>
        </body>
        </html>
        """.format(url)
        
        self.wfile.write(response_html.encode('utf-8'))
    
    def _clone_website_async(self, url):
        """Асинхронное клонирование сайта"""
        try:
            # Нормализуем URL
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Создаем безопасное имя папки
            parsed = urlparse(url)
            site_name = parsed.netloc.replace('www.', '')
            site_name = re.sub(r'[<>:"|?*]', '_', site_name)
            
            # Путь для сохранения
            project_folder = Path(CLONED_SITES_DIR) / site_name
            
            logger.info("=" * 60)
            logger.info(f"НАЧАЛО КЛОНИРОВАНИЯ: {url}")
            logger.info(f"Папка сохранения: {project_folder.absolute()}")
            logger.info("=" * 60)
            
            # Создаем клонировщик
            cloner = WebsiteCloner(url, project_folder)
            
            # Клонируем сайт
            cloner.clone()
            
            # Создаем ZIP архив
            zip_filename = f"{site_name}.zip"
            zip_path = Path(CLONED_SITES_DIR) / zip_filename
            
            create_zip_archive(project_folder, zip_path)
            
            # Отправляем через Telegram
            send_telegram_file(
                zip_path,
                CONFIG.get('telegram_bot_token', ''),
                CONFIG.get('telegram_chat_id', '')
            )
            
            logger.info("=" * 60)
            logger.info(f"КЛОНИРОВАНИЕ ЗАВЕРШЕНО: {url}")
            logger.info(f"Архив: {zip_path.absolute()}")
            logger.info("=" * 60)
            
        except Exception as e:
            error_msg = f"Ошибка при клонировании: {e}"
            logger.error(error_msg)
            
            # Можно отправить сообщение об ошибке в Telegram
            if CONFIG.get('telegram_bot_token') and CONFIG.get('telegram_chat_id'):
                try:
                    send_url = f"https://api.telegram.org/bot{CONFIG['telegram_bot_token']}/sendMessage"
                    requests.post(send_url, json={
                        'chat_id': CONFIG['telegram_chat_id'],
                        'text': f"❌ Ошибка клонирования {url}:\n{error_msg}"
                    })
                except:
                    pass


def main():
    """Главная функция запуска сервера"""
    # Создаем директорию для клонированных сайтов
    os.makedirs(CLONED_SITES_DIR, exist_ok=True)
    
    # Устанавливаем рабочую директорию
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Проверяем конфигурацию Telegram
    if not CONFIG.get('telegram_bot_token') or not CONFIG.get('telegram_chat_id'):
        logger.warning("Telegram бот не настроен. Архивирование будет выполнено, но отправка пропущена.")
        logger.warning("Настройте config.json для использования Telegram бота.")
    
    # Запускаем сервер
    with socketserver.TCPServer(("127.0.0.1", PORT), RequestHandler) as s:
        s.allow_reuse_address = True
        logger.info(f"Сервер запущен на http://127.0.0.1:{PORT}")
        logger.info(f"Откройте браузер и перейдите по адресу http://127.0.0.1:{PORT}")
        s.serve_forever()


if __name__ == "__main__":
    main()
