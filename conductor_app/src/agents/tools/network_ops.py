"""
Network Operations Tools — handlers для сетевых операций.

Инструменты:
- fetch_url: HTTP запросы
- search_web: Поиск в интернете
- browser_snapshot: Получение содержимого веб-страниц
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


async def fetch_url(
    project_path: Path,
    url: str,
    method: str = "GET",
    headers: Optional[dict[str, str]] = None,
    body: Optional[str] = None,
    timeout: int = 30
) -> dict[str, Any]:
    """
    HTTP запрос к URL.
    
    Args:
        project_path: Путь к проекту (для контекста)
        url: URL для запроса
        method: HTTP метод
        headers: HTTP заголовки
        body: Тело запроса (для POST/PUT)
        timeout: Таймаут в секундах
        
    Returns:
        {"status": 200, "headers": {...}, "body": "..."} или {"error": "..."}
    """
    try:
        # Валидация URL
        parsed = urlparse(url)
        if parsed.scheme not in ["http", "https"]:
            return {"error": f"Поддерживаются только http/https URL: {url}"}
        
        # Запрет внутренних IP (защита от SSRF)
        hostname = parsed.hostname
        if hostname:
            if hostname in ["localhost", "127.0.0.1", "::1"]:
                pass  # Разрешаем localhost для тестирования API
            elif hostname.startswith("192.168.") or hostname.startswith("10."):
                return {"error": "Доступ к внутренним сетям запрещён"}
        
        logger.info(f"HTTP {method} запрос: {url}")
        
        async with aiohttp.ClientSession() as session:
            request_kwargs = {
                "method": method,
                "timeout": aiohttp.ClientTimeout(total=timeout)
            }
            
            if headers:
                request_kwargs["headers"] = headers
            
            if body and method in ["POST", "PUT", "PATCH"]:
                request_kwargs["data"] = body
            
            async with session.request(url, **request_kwargs) as response:
                body_text = await response.text(errors="replace")
                
                return {
                    "status": response.status,
                    "headers": dict(response.headers),
                    "body": body_text,
                    "url": str(response.url)
                }
                
    except asyncio.TimeoutError:
        return {"error": f"Таймаут запроса ({timeout}с): {url}"}
    except aiohttp.ClientError as e:
        logger.error(f"Ошибка HTTP запроса {url}: {e}")
        return {"error": f"HTTP ошибка: {str(e)}"}
    except Exception as e:
        logger.error(f"Ошибка fetch_url: {e}")
        return {"error": str(e)}


async def search_web(
    project_path: Path,
    query: str,
    num_results: int = 5
) -> dict[str, Any]:
    """
    Поиск в интернете через DuckDuckGo HTML.
    
    Args:
        project_path: Путь к проекту
        query: Поисковый запрос
        num_results: Количество результатов
        
    Returns:
        {"results": [{"title": "...", "url": "...", "snippet": "..."}]} или {"error": "..."}
    """
    try:
        # DuckDuckGo HTML search
        search_url = "https://html.duckduckgo.com/html/"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                search_url,
                data={"q": query},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                html = await response.text(errors="replace")
                
        # Парсинг результатов
        soup = BeautifulSoup(html, "html.parser")
        results = []
        
        # DuckDuckGo HTML формат
        result_elements = soup.select(".result")[:num_results]
        
        for elem in result_elements:
            title_elem = elem.select_one(".result__title")
            snippet_elem = elem.select_one(".result__snippet")
            url_elem = elem.select_one(".result__url")
            
            if title_elem and url_elem:
                title = title_elem.get_text(strip=True)
                url = url_elem.get("href", "")
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                # DuckDuckGo использует редиректы в URL
                if url.startswith("//"):
                    url = "https:" + url
                
                results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet
                })
        
        return {
            "query": query,
            "results_count": len(results),
            "results": results
        }
        
    except asyncio.TimeoutError:
        return {"error": "Таймаут поиска"}
    except Exception as e:
        logger.error(f"Ошибка поиска в web: {e}")
        return {"error": str(e)}


async def browser_snapshot(
    project_path: Path,
    url: str,
    wait_seconds: float = 2.0,
    screenshot: bool = False
) -> dict[str, Any]:
    """
    Получение текстового содержимого веб-страницы.
    
    Args:
        project_path: Путь к проекту
        url: URL страницы
        wait_seconds: Время ожидания (если поддерживается)
        screenshot: Сделать скриншот
        
    Returns:
        {"text": "...", "title": "...", "links": [...]} или {"error": "..."}
    """
    try:
        # Валидация URL
        parsed = urlparse(url)
        if parsed.scheme not in ["http", "https"]:
            return {"error": f"Поддерживаются только http/https URL: {url}"}
        
        logger.info(f"Получение snapshot: {url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                html = await response.text(errors="replace")
        
        # Парсинг страницы
        soup = BeautifulSoup(html, "html.parser")
        
        # Извлечение заголовка
        title = ""
        if soup.title:
            title = soup.title.get_text(strip=True)
        
        # Извлечение текста (без script и style)
        for script in soup(["script", "style", "meta", "link"]):
            script.decompose()
        
        text = soup.get_text(separator="\n", strip=True)
        
        # Ограничение размера текста
        max_text_length = 10000
        if len(text) > max_text_length:
            text = text[:max_text_length] + "... [обрезано]"
        
        # Извлечение ссылок
        links = []
        for link in soup.find_all("a", href=True)[:20]:
            href = link.get("href", "")
            link_text = link.get_text(strip=True)
            if href and link_text:
                links.append({"url": href, "text": link_text})
        
        result = {
            "url": url,
            "title": title,
            "text": text,
            "links_count": len(links),
            "links": links
        }
        
        # Скриншот (требует playwright/selenium - пока заглушка)
        if screenshot:
            screenshots_dir = project_path / "workspace" / "screenshots"
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"screenshot_{urlparse(url).hostname}_{int(asyncio.get_event_loop().time())}.png"
            screenshot_path = screenshots_dir / filename
            
            # Заглушка - в будущем можно интегрировать playwright
            result["screenshot_note"] = "Скриншоты требуют установки playwright. Сохранено только текстовое содержимое."
            result["screenshot_path"] = None
        
        return result
        
    except asyncio.TimeoutError:
        return {"error": f"Таймаут загрузки страницы: {url}"}
    except aiohttp.ClientError as e:
        logger.error(f"Ошибка загрузки страницы {url}: {e}")
        return {"error": f"Ошибка загрузки: {str(e)}"}
    except Exception as e:
        logger.error(f"Ошибка browser_snapshot: {e}")
        return {"error": str(e)}


def register_network_handlers(tool_registry, project_path: Path) -> None:
    """
    Регистрация всех network ops handlers в реестре.
    
    Args:
        tool_registry: ToolRegistry instance
        project_path: Путь к проекту
    """
    from functools import partial
    
    handlers = {
        "fetch_url": partial(fetch_url, project_path),
        "search_web": partial(search_web, project_path),
        "browser_snapshot": partial(browser_snapshot, project_path),
    }
    
    for name, handler in handlers.items():
        if tool_registry.has_tool(name):
            tool_registry.register_handler(name, handler)
            logger.debug(f"Зарегистрирован handler для {name}")
        else:
            logger.warning(f"Инструмент {name} не найден в реестре")
