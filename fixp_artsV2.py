"""Скрипт на основе playwright считывает каталоги Fix-Price из файла catalogs.txt и собирает ссылки со всех имеющихся
 страниц в файл fix_price_articles.txt с учетом магазина. Выбор магазина уменьшает количество товаров в категории
 до 2 раз. Если выбрать несколько магазинов, то в файл fix_price_articles.txt дозаписываются ссылки в конец"""

import requests
import datetime
import time
from tqdm import tqdm
from pathlib import Path
import pandas as pd
import asyncio

# from playwright.sync_api import Playwright, sync_playwright, expect
from playwright.async_api import Playwright, async_playwright

SAVE_PATH = f'{str(Path(__file__).parents[1])}'
MAIN_URL = 'https://fix-price.com/'
CITY = 'Брянск'
ADDRESS = 'г.Брянск, ул.Бежицкая, д.1Б'


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def read_catalogs_from_txt():
    """Считывает и возвращает список каталогов из файла"""
    with open('in/catalogs.txt', 'r', encoding='utf-8') as file:
        catalogs = [f'{line}'.rstrip() for line in file]
    return catalogs


def write_txt_file_all_articles(all_art):
    with open('in/fix_price_articles.txt', 'a') as output:
        print('Записываю в файл fix_price_articles.txt')
        for row in all_art:
            output.write(str(row) + '\n')


async def playwright_config(playwright):
    js = """
    Object.defineProperties(navigator, {webdriver:{get:()=>undefined}});
    """
    browser = await playwright.chromium.launch(headless=False, args=['--blink-settings=imagesEnabled=false'])
    context = await browser.new_context()
    page = await context.new_page()
    await page.add_init_script(js)
    return page


async def manual_set_city(page):
    print(f'{bcolors.OKGREEN}Загружаю...{bcolors.ENDC}')
    await page.goto("https://fix-price.com/")
    await page.wait_for_load_state('load')
    await asyncio.sleep(5)
    print(f'{bcolors.OKGREEN}Установите город и адрес вручную, затем в инспекторе нажмите продолжить{bcolors.ENDC}')
    await page.pause()


async def set_city(page):
    print(f'{bcolors.OKGREEN}Устанавливаем город{bcolors.ENDC}')

    await page.goto("https://fix-price.com/")
    await page.wait_for_load_state('load')
    await asyncio.sleep(5)

    # Нажимаем на элемент с текстом 'Москва'
    await page.wait_for_selector('//*[@id="app-header"]/header/div/div[1]/div[1]/div[1]/span')
    await page.click('//*[@id="app-header"]/header/div/div[1]/div[1]/div[1]/span')

    # Ожидаем появления элемента с placeholder 'Ваш город'
    await page.wait_for_selector('input[placeholder="Ваш город"]')

    # Вводим значение в поле 'Ваш город'
    await page.fill('input[placeholder="Ваш город"]', f'{CITY}')
    await asyncio.sleep(5)
    # Ожидаем появления модального окна
    await page.wait_for_selector('//*[@id="modal"]/div/div[4]/div/div[1]')
    await asyncio.sleep(5)
    # Кликаем по первому элементу
    await page.click('//*[@id="modal"]/div/div[4]/div/div[1]')

    # Ожидаем появления кнопки и закрываем модальное окно
    await page.wait_for_selector('//*[@id="modal"]/div/div/div/button[2]')
    await page.click('//*[@id="modal"]/div/div/div/button[2]')

    # Кликаем по элементам
    await page.click('//*[@id="app-header"]/header/div/div[1]/div[1]/div[2]/div[2]/div[1]')
    await page.click('//*[@id="modal"]/div/div/div/div[3]/div/div[2]/div')

    await asyncio.sleep(5)
    # Ожидаем, когда Locator станет видимым
    await page.wait_for_selector(
        '//*[@id="modal"]/div/div/div[2]/div/div[2]/div[2]/div[1]/div[2]/div[1]/div[1]/div[1]/input')
    # Создаем Locator
    find_shop_locator = page.locator(
        '//*[@id="modal"]/div/div/div[2]/div/div[2]/div[2]/div[1]/div[2]/div[1]/div[1]/div[1]/input')
    # Кликаем по Locator
    await find_shop_locator.click()
    await find_shop_locator.type(f'{ADDRESS}', delay=150)
    await asyncio.sleep(5)
    # Ожидаем загрузки страницы
    await page.wait_for_load_state('load')

    # Кликаем по элементу
    await page.click('//*[@id="modal"]/div/div/div[2]/div/div[2]/div[2]/div[1]/div[2]/div[5]/div/div[1]')
    # Кликаем по кнопке
    await page.click('//*[1]/ymaps/div/div/button/span')
    await asyncio.sleep(5)


async def get_arts_in_catalogs(page, catalogs):
    max_attempts = 5
    all_art = []
    for catalog in catalogs:
        print(f'Работаю с каталогом: {catalog}')
        number_page = 1
        catalog_end_flag = True
        while True:
            if catalog_end_flag:
                for attempt in range(1, max_attempts + 1):
                    try:
                        await page.goto(f'{catalog}?sort=sold&page={number_page}', timeout=30000)
                        time.sleep(5)
                        number_page += 1
                        title = await page.title()
                        if title != 'Ошибка 404: Страница не найдена':
                            product_wrappers = await page.query_selector_all('.product__wrapper')
                            for pw in product_wrappers:
                                title_element = await pw.query_selector('.title')
                                if title_element:
                                    url = await title_element.get_attribute('href')
                                    if url:
                                        all_art.append(url)
                                    else:
                                        # Найти элемент с классом "description"
                                        description_element = await pw.query_selector('.description')
                                        # Извлечь значение атрибута "href" из дочернего элемента <a>
                                        href_value = await description_element.query_selector('a')
                                        if href_value:
                                            url = await href_value.get_attribute('href')
                                            all_art.append(url)
                            break
                        else:
                            catalog_end_flag = False
                            print(f'Закончились страницы в каталоге')
                            break
                    except Exception as exp:
                        print(f'{bcolors.WARNING}Попытка {attempt} из {max_attempts} не удалась. '
                              f'Страница: {number_page}. Ошибка: {bcolors.ENDC}\n\n{exp}')
                        number_page -= 1
                        time.sleep(10)
            else:
                break
    return all_art


async def run(playwright: Playwright) -> None:
    page = await playwright_config(playwright)
    catalogs = read_catalogs_from_txt()
    await manual_set_city(page)
    all_art = await get_arts_in_catalogs(page, catalogs)
    res_arts = [x[9:] for x in all_art]
    write_txt_file_all_articles(res_arts)


async def main() -> None:
    async with async_playwright() as playwright:
        await run(playwright)


asyncio.run(main())
