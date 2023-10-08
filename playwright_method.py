import requests
import datetime
import time
from tqdm import tqdm
from pathlib import Path
import pandas as pd

from fix_price_parser_data_by_article import bcolors

from playwright.sync_api import Playwright, sync_playwright, expect


class FixParser():
    def __init__(self):
        self.save_path = f'{str(Path(__file__).parents[1])}'
        self.__main_url = 'https://fix-price.com/'

        self.res_df_ozon = pd.DataFrame()
        self.res_df_wb = pd.DataFrame()
        self.stocks = []
        self.price = []
        self.name = []
        self.description = []
        self.brand = []
        self.code = []
        self.packing_width = []  # ширина
        self.packing_height = []  # высота
        self.package_length = []  # длина
        self.weight = []
        self.country = []
        self.properties_extra = []
        self.url_img = []

        self.js = """
        Object.defineProperties(navigator, {webdriver:{get:()=>undefined}});
        """

    def read_articles_from_txt(self):
        with open('fix_price_articles.txt', 'r', encoding='utf-8') as file:
            articles = [f'{line}'.rstrip() for line in file]
            return articles

    def set_city(self):
        print(f'{bcolors.OKGREEN}Устанавливаем город{bcolors.ENDC}')
        self.page.goto("https://fix-price.com/")
        self.page.wait_for_load_state('load')
        self.page.get_by_text("Москва").click()
        # Ожидаем появления элемента с placeholder 'Ваш город'
        self.page.wait_for_selector('input[placeholder="Ваш город"]')
        # Вводим значение в поле 'Ваш город'
        self.page.fill('input[placeholder="Ваш город"]', 'Брянск')
        time.sleep(10)
        self.page.wait_for_selector('//*[@id="modal"]/div/div[4]/div/div[1]').click()
        time.sleep(2)
        self.page.locator('//*[@id="modal"]/div/div/div/button[2]').click()
        self.page.locator('//*[@id="app-header"]/header/div/div[1]/div[1]/div[2]/div[2]/div[1]').click()
        self.page.locator('//*[@id="modal"]/div/div/div/div[3]/div/div[2]/div').click()  # выбрать магазин
        time.sleep(2)
        find_shop_placeholder = self.page.locator(
            '//*[@id="modal"]/div/div/div[2]/div/div[2]/div[2]/div[1]/div[2]/div[1]/div[1]/div[1]/input')
        find_shop_placeholder.click()
        time.sleep(2)
        find_shop_placeholder.type(text='г.Брянск, ул.Бежицкая, д.1Б', delay=1.5)
        self.page.wait_for_load_state('load')
        time.sleep(3)
        self.page.locator('//*[@id="modal"]/div/div/div[2]/div/div[2]/div[2]/div[1]/div[2]/div[5]/div/div[1]').click()
        time.sleep(2)
        self.page.locator('//*[1]/ymaps/div/div/button/span').click()
        time.sleep(2)

        # # ---------------------
        # context.close()
        # browser.close()

    def get_data_from_articles(self, articles):
        count_for_clear_cart = 0
        for art in tqdm(articles):
            try:
                self.page.goto(f'{self.__main_url}catalog/{art}')
                self.page.wait_for_load_state('load')
                time.sleep(1)
                stock_product = self.page.wait_for_selector('.product-stock .text',
                                                            timeout=10000).inner_text()  # Установите нужное время ожидания в миллисекундах.
                if stock_product == 'Нет в наличии':
                    print(f'{bcolors.WARNING}Нет в наличии{bcolors.ENDC} {art}')
                    with open('out_of_stock.txt', 'a') as output:
                        output.write(art + '\n')
                    count_for_clear_cart += 1
                elif stock_product == 'В наличии':
                    count_for_clear_cart += 1
                    print(f' {bcolors.OKGREEN}[+]{bcolors.ENDC} {art}')
                    with open('available_in_stock.txt', 'a') as output:
                        output.write(art + '\n')
                    self.page.wait_for_selector('[data-test="button"]', timeout=10000).click()
                    self.page.fill('[data-test="counter-value"]', '999')
                    self.page.wait_for_timeout(3000)
                    time.sleep(1)
                    stock = self.page.evaluate(
                        '() => { return document.querySelector("#__layout > div > div > div.page-content > div > div > '
                        'div > div > div.product > div.product-details > div.price-quantity-block > '
                        'div.price-wrapper.price > div > div > div.quantity > div > input").value; }')
                    name = self.page.wait_for_selector(".product-details .title", timeout=10000).inner_text()
                    price = self.page.wait_for_selector(".product-details .regular-price",
                                                        timeout=10000).inner_text()
                    price = float(price.replace(' ₽', '').replace(',', '.'))
                    # description = self.page.wait_for_selector(".product-details .description",
                    #                                           timeout=10000).inner_text()
                    description_element = self.page.query_selector(".product-details .description")
                    description = description_element.inner_text() if description_element else '-'

                    # Извлекаем данные и создаем словарь
                    data = {}
                    properties = self.page.query_selector_all(".properties .property")
                    time.sleep(1)
                    for property_element in properties:
                        title = property_element.query_selector("span.title").inner_text()
                        value = property_element.query_selector("span.value").inner_text()
                        data[title] = value
                    self.code.append(data.get('Код товара', '-'))
                    self.packing_width.append(data.get('Ширина, мм.', '-'))
                    self.packing_height.append(data.get('Высота, мм.', '-'))
                    self.package_length.append(data.get('Длина, мм.', '-'))
                    self.weight.append(data.get('Вес, гр.', '-'))
                    self.country.append(data.get('Страна производства', '-'))
                    self.brand.append(data.get('Бренд', 'NoName'))
                    self.stocks.append(stock)
                    self.name.append(name)
                    self.price.append(price)
                    self.description.append(description)

                    image_links = self.page.query_selector_all('img')
                    filtered_links = [
                        img.get_attribute('src')
                        for img in image_links
                        if img.get_attribute('src') is not None
                           and img.get_attribute('src').startswith('https://img.fix-price.com/')
                           and '800x800' in img.get_attribute('src')
                    ]
                    url_img = list(set(filtered_links))
                    if len(url_img) > 14:
                        url_img = url_img[:14]
                    if url_img:
                        self.url_img.append(url_img)
                    else:
                        url_img = ''
                        self.url_img.append(url_img)
                    # self.check_control_sum()
                    if count_for_clear_cart > 80:
                        print('\nОчищаем корзинку В наличии')
                        self.clear_cart()
                        count_for_clear_cart = 0
                else:
                    print(f'{bcolors.FAIL}НЕ ОПРЕДЕЛЕНО наличие товара: {art}')
                    with open('articles_with_bad_req.txt', 'a') as output:
                        output.write('НЕ ОПРЕДЕЛЕНО наличие товара: ' + art + '\n')
            except Exception as exp:
                print(f'{bcolors.FAIL}ОШИБКА! В articles_with_bad_req.txt добавлено: \n{bcolors.ENDC}{art}\n\n{exp}')
                with open('articles_with_bad_req.txt', 'a') as output:
                    output.write(art + '\n')
                time.sleep(10)

    def clear_cart(self):
        time.sleep(10)
        try:
            self.page.goto(f'https://fix-price.com/cart', timeout=10000)
            time.sleep(10)
            self.page.get_by_text("Удалить выбранные").click()
        except:
            print(f'{bcolors.OKCYAN}Корзина не была очищена{bcolors.ENDC}')

    def create_df(self):
        self.res_df_ozon.insert(0, 'Артикул', [f'p_{x}' for x in self.code])
        self.res_df_ozon.insert(1, 'Название', self.name)
        self.res_df_ozon.insert(2, 'Цена FixPrice', self.price)
        self.res_df_ozon.insert(3, 'Цена для OZON', [390 if x * 4 < 390 else round(x * 3.3) for x in self.price])
        self.res_df_ozon.insert(4, 'Остаток на Бежицкой 1Б', self.stocks)
        self.res_df_ozon.insert(5, 'Брэнд', self.brand)
        self.res_df_ozon.insert(6, 'Описание', self.description)
        self.res_df_ozon.insert(7, 'Вес, г', self.weight)
        self.res_df_ozon.insert(8, 'Ширина, мм', self.packing_width)
        self.res_df_ozon.insert(9, 'Высота, мм', self.packing_height)
        self.res_df_ozon.insert(10, 'Длина, мм', self.package_length)
        self.res_df_ozon.insert(11, 'Производитель', self.country)
        self.res_df_ozon.insert(12, 'Ссылка на главное фото товара', [x[0] for x in self.url_img])
        self.res_df_ozon.insert(13, 'Ссылки на фото товара',
                                [' '.join(map(str, x)) for x in [x[1:] if len(x) > 1 else '-' for x in self.url_img]])

        self.res_df_wb.insert(0, 'Артикул', [f'p_{x}' for x in self.code])
        self.res_df_wb.insert(1, 'Название', self.name)
        self.res_df_wb.insert(2, 'Цена FixPrice', self.price)
        self.res_df_wb.insert(3, 'Цена для WB', [390 if x * 4 < 390 else round(x * 3.3) for x in self.price])
        self.res_df_wb.insert(4, 'Остаток на Бежицкой 1Б', self.stocks)
        self.res_df_wb.insert(5, 'Брэнд', self.brand)
        self.res_df_wb.insert(6, 'Описание', self.description)
        self.res_df_wb.insert(7, 'Вес, г', self.weight)
        self.res_df_wb.insert(8, 'Ширина, cм', [x[:-1] for x in self.packing_width])
        self.res_df_wb.insert(9, 'Высота, cм', [x[:-1] for x in self.packing_height])
        self.res_df_wb.insert(10, 'Длина, cм', [x[:-1] for x in self.package_length])
        self.res_df_wb.insert(11, 'Производитель', self.country)
        self.res_df_wb.insert(12, 'Ссылка на главное фото товара', [x[0] for x in self.url_img])
        self.res_df_wb.insert(13, 'Ссылки на фото товара',
                              [';'.join(map(str, x)) for x in [x[1:] if len(x) > 1 else '-' for x in self.url_img]])

    def create_xls(self):
        """Создание файла excel из 1-го DataFrame"""
        file_name = f'FP_{self.code[0]}_{self.code[-1]}.xlsx'
        writer = pd.ExcelWriter(file_name, engine_kwargs={'options': {'strings_to_urls': False}})
        self.res_df_ozon.to_excel(writer, sheet_name='OZON', index=False, na_rep='NaN', engine='openpyxl')
        self.res_df_wb.to_excel(writer, sheet_name='WB', index=False, na_rep='NaN', engine='openpyxl')
        # Auto-adjust columns' width OZON
        for column in self.res_df_ozon:
            column_width = max(self.res_df_ozon[column].astype(str).map(len).max(), len(column)) + 2
            col_idx = self.res_df_ozon.columns.get_loc(column)
            writer.sheets[f'{"OZON"}'].set_column(col_idx, col_idx, column_width)
        writer.sheets["OZON"].set_column(1, 1, 30)
        writer.sheets["OZON"].set_column(6, 6, 30)
        writer.sheets["OZON"].set_column(12, 12, 30)
        writer.sheets["OZON"].set_column(13, 13, 30)
        writer.sheets["OZON"].set_column(14, 14, 30)

        # Auto-adjust columns' width WB
        for column in self.res_df_wb:
            column_width = max(self.res_df_wb[column].astype(str).map(len).max(), len(column)) + 2
            col_idx = self.res_df_wb.columns.get_loc(column)
            writer.sheets[f'{"WB"}'].set_column(col_idx, col_idx, column_width)
        writer.sheets["WB"].set_column(1, 1, 30)
        writer.sheets["WB"].set_column(6, 6, 30)
        writer.sheets["WB"].set_column(12, 12, 30)
        writer.sheets["WB"].set_column(13, 13, 30)
        writer.sheets["WB"].set_column(14, 14, 30)

        writer.close()

    def check_control_sum(self):
        if len(self.code) == len(self.name) == len(self.price) == len(self.stocks) == len(self.brand) == \
                len(self.description) == len(self.weight) == len(self.packing_width) == len(self.packing_height) == \
                len(self.package_length) == len(self.country) == len(self.url_img):
            return
        else:
            breakpoint()

    def send_logs_to_telegram(self, message):
        import platform
        import socket
        import os

        platform = platform.system()
        hostname = socket.gethostname()
        user = os.getlogin()

        bot_token = '6456958617:AAF8thQveHkyLLtWtD02Rq1UqYuhfT4LoTc'
        chat_id = '128592002'

        url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
        data = {"chat_id": chat_id, "text": message + f'\n\n{platform}\n{hostname}\n{user}'}
        response = requests.post(url, data=data)
        return response.json()

    def start(self):
        t1 = datetime.datetime.now()
        print(f'Start: {t1}')
        try:
            with sync_playwright() as playwright:
                self.browser = playwright.chromium.launch(headless=False, args=['--blink-settings=imagesEnabled=false'])
                self.context = self.browser.new_context()
                self.page = self.context.new_page()
                self.page.add_init_script(self.js)
                self.set_city()
                articles = self.read_articles_from_txt()
                self.get_data_from_articles(articles)
                self.context.close()
                self.browser.close()
                self.create_df()
                self.create_xls()
        except Exception as exp:
            print(exp)
            self.send_logs_to_telegram(message=f'Произошла ошибка!\n\n\n{exp}')
        t2 = datetime.datetime.now()
        print(f'Finish: {t2}, TIME: {t2 - t1}')
        self.send_logs_to_telegram(message=f'Finish: {t2}, TIME: {t2 - t1}')


if __name__ == '__main__':
    FixParser().start()