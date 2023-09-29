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

        self.res_df = pd.DataFrame()
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
        find_shop_placeholder.type(text='г.Брянск, ул.Бежицкая, д.1Б', delay=1.5)
        time.sleep(3)
        self.page.locator('//*[@id="modal"]/div/div/div[2]/div/div[2]/div[2]/div[1]/div[2]/div[5]/div/div[1]').click()
        time.sleep(2)
        self.page.locator('//*[1]/ymaps/div/div/button/span').click()
        time.sleep(2)

        # # ---------------------
        # context.close()
        # browser.close()

    def get_data_from_articles(self, articles):
        for art in tqdm(articles):
            self.page.goto(f'{self.__main_url}catalog/{art}')
            self.page.wait_for_load_state('load')
            stock_product = self.page.wait_for_selector('.product-stock .text',
                                                        timeout=10000).inner_text()  # Установите нужное время ожидания в миллисекундах.
            if stock_product == 'Нет в наличии':
                print(f'{bcolors.WARNING}Нет в наличии{bcolors.ENDC} {art}')
                # with open('out_of_stock.txt', 'a') as output:
                #     output.write(art + '\n')
                continue
            elif stock_product == 'В наличии':
                print(f' {bcolors.OKGREEN}[+]{bcolors.ENDC} {art}')
                self.page.wait_for_selector('[data-test="button"]', timeout=10000).click()
                self.page.fill('[data-test="counter-value"]', '999')

                value = self.page.evaluate('(element) => element.value', self.page.locator('[data-test="counter-value"]'))

                stock = self.page.locator('[data-test="counter-value"]').get_attribute('value')
                name = self.page.wait_for_selector(".product-details .title", timeout=10000).inner_text()
                price = self.page.wait_for_selector(".product-details .regular-price", timeout=10000).inner_text()
                description = self.page.wait_for_selector(".product-details .description", timeout=10000).inner_text()
                properties = self.page.wait_for_selector(".product-details .properties", timeout=10000).inner_text()

                # Извлекаем данные и создаем словарь
                data = {}
                properties = self.page.query_selector_all(".properties .property")
                for property_element in properties:
                    title = property_element.query_selector("span.title").inner_text()
                    value = property_element.query_selector("span.value").inner_text()
                    data[title] = value
                print()
            else:
                print(f'{bcolors.FAIL}НЕ ОПРЕДЕЛЕНО наличие товара: {art}')

    def start(self):
        with sync_playwright() as playwright:
            self.browser = playwright.chromium.launch(headless=False)
            self.context = self.browser.new_context()
            self.page = self.context.new_page()
            self.page.add_init_script(self.js)
            self.set_city()
            articles = self.read_articles_from_txt()
            self.get_data_from_articles(articles)


if __name__ == '__main__':
    FixParser().start()
