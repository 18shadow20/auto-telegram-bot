import requests
from bs4 import BeautifulSoup
import fake_useragent
from selenium import webdriver
from selenium_stealth import stealth
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
import asyncio
import aiohttp
from urllib.parse import urljoin
from bot.utils.logger import setup_logger
import random
from math import ceil
from time import sleep
from bot.config import CHROME_DRIVER_PATH, BASE_URL

logger = setup_logger(__name__)

class ParserState:
    def __init__(self):
        self.all_marks = {}
        self.all_models = {}
        self.current_count = 0


parser_state = ParserState()



def get_driver():
    """Создает и настраивает экземпляр драйвера Chrome"""
    try:
        logger.info("Инициализация ChromeDriver")
        service = Service(CHROME_DRIVER_PATH)
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        driver = webdriver.Chrome(service=service, options=options)
        stealth(driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win64",
                fix_hairline=True)
        return driver
    except Exception as e:
        logger.critical(f"Ошибка инициализации ChromeDriver: {e}", exc_info=True)


async def pars_marks():
    """Парсит список марок автомобилей"""
    driver = None
    logger.info("Начало парсинга марок автомобилей")
    try:
        driver = get_driver()
        driver.get(BASE_URL)

        try:
            button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".catalog__show-all button")))
            button.click()
            logger.debug("Кнопка 'Все марки' нажата")
        except (NoSuchElementException, TimeoutException):
            return parser_state.all_marks

        sleep(1)
        mark_elements = driver.find_elements(By.CLASS_NAME, "catalog__link")

        for element in mark_elements:
            title = element.get_attribute("title")
            href = element.get_attribute("href")
            parser_state.all_marks[title] = href

        return parser_state.all_marks
        logger.info(f"Successfully parsed {len(parser_state.all_marks)} marks")
    except Exception as e:
        logger.error(f"Ошибка парсинга марок: {e}", exc_info=True)
        return {}
    finally:
        if driver:
            driver.quit()


async def pars_model(mark):
    """Парсит список моделей для указанной марки"""
    try:
        if mark not in parser_state.all_marks:
            return []

        url = parser_state.all_marks[mark]
        headers = {"user-agent": fake_useragent.UserAgent().random}

        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        model_elements = soup.find_all("a", class_="catalog__link")

        parser_state.all_models.clear()  # Очищаем словарь перед новой загрузкой

        for element in model_elements:
            title = element.get("title")
            href = element.get("href")
            parser_state.all_models[title] = urljoin(BASE_URL, href)

        return list(parser_state.all_models.keys())
    except Exception as e:
        return []


async def count_ads(url):
    """Подсчитывает количество объявлений"""
    try:
        while True:
            headers = {"user-agent": fake_useragent.UserAgent().random}
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, "lxml")
            count_ads_tag = soup.find("h3", class_="listing__title")

            if count_ads_tag:
                count_ads_text = "".join(filter(str.isdigit, count_ads_tag.text))
                parser_state.current_count = int(count_ads_text) if count_ads_text else 0
                logger.info(f"Найдено {parser_state.current_count} объявлений")
                return parser_state.current_count

            sleep(2)

    except Exception as e:
        logger.error(f"Ошибка подсчета: {e}", exc_info=True)
        return 0


async def get_url(model, models_data):
    """Получает URL для модели с учетом пагинации"""
    try:
        if model not in models_data:
            return None

        url = parser_state.all_models[model]
        ads_count = await count_ads(url)

        if ads_count >= 25:
            driver = get_driver()
            driver.get(url)

            try:
                button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "paging__button")))
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                sleep(1)
                button.click()
                sleep(2)
            except NoSuchElementException:
                return

            url = driver.current_url
            driver.quit()

        return url
    except Exception as e:
        return None


async def pars_auto(url, session=None):
    """Парсим объявления автомобилей"""
    logger.info(f"Парсинг объявлений по URL: {url}")
    headers = {"User-Agent": fake_useragent.UserAgent().random,
               "Referer": "https://cars.av.by/",
               "Accept-Language": "ru-RU,ru;q=0.9",
               "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp",
               "Connection": "keep-alive"}
    count_ads_new = parser_state.current_count

    def clean_text(text):
        return " ".join(text.replace("\xa0", " ").split()).strip()

    async def fetch_page(session, page_url):
        try:
            await asyncio.sleep(random.uniform(3, 5))
            async with session.get(page_url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, "lxml")

                    listings = []
                    for item in soup.find_all("div", class_="listing-item"):
                        try:
                            link = item.find("a", class_="listing-item__link")
                            price_byn = item.find("div", class_="listing-item__price")
                            price_usd = item.find("div", class_="listing-item__priceusd")
                            params = item.find("div", class_="listing-item__params")

                            if all([link, price_byn, price_usd, params]):
                                listings.append({
                                    "link": urljoin(page_url, link.get("href")),
                                    "model": clean_text(link.text),
                                    "price_byn": int(clean_text(price_byn.text).replace(" ", "")[:-2]),
                                    "price_usd": int(clean_text(price_usd.text).replace(" ", "")[1:-1]),
                                    "params": clean_text(params.get_text(separator=" "))
                                })
                        except Exception as e:
                            continue

                    return listings
                else:
                    return []
        except Exception as e:
            return []

    async with aiohttp.ClientSession() as session:
        pages = ceil(count_ads_new / 25) if count_ads_new > 0 else 1
        tasks = []

        if pages > 1:
            base_url = url[:-1] if url.endswith('/') else url
            tasks = [fetch_page(session, f"{base_url}{page}") for page in range(1, pages + 1)]
        else:
            tasks = [fetch_page(session, url)]

        results = await asyncio.gather(*tasks)
        all_listings = [item for sublist in results for item in sublist]

        if not all_listings:
            await asyncio.sleep(5)
            return await pars_auto(url, session)
        logger.debug(f"Обработано страниц: {pages}")
        logger.info(f"Найдено {len(all_listings)} объявлений")
        return all_listings