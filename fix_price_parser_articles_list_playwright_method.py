import requests
import datetime
import time
from tqdm import tqdm
from pathlib import Path
import pandas as pd

from fix_price_parser_data_by_article import bcolors

from playwright.sync_api import Playwright, sync_playwright, expect


class ParserArticlesByCatalogs:
    def __init__(self):
        self.page = None
        self.context = None
        self.browser = None
        self.save_path = f'{str(Path(__file__).parents[1])}'
        self.__main_url = 'https://fix-price.com/'
        self.all_art = []
        self.js = """
        Object.defineProperties(navigator, {webdriver:{get:()=>undefined}});
        """

    def read_catalogs_from_txt(self):
        """Считывает и возвращает список каталогов из файла"""
        with open('catalogs.txt', 'r', encoding='utf-8') as file:
            catalogs = [f'{line}'.rstrip() for line in file]
        return catalogs

    def write_txt_file_all_articles(self):
        with open('fix_price_articles.txt', 'a') as output:
            for row in self.all_art:
                output.write(str(row[9:]) + '\n')

    def get_arts_in_catalogs(self, catalogs):
        page = 1
        for i in catalogs:
            while True:
                self.page.goto(f'{self.__main_url}{i}?sort=sold&page={page}')
                page += 1
                time.sleep(3)
                page_title = self.page.title()
                if page_title != 'Ошибка 404: Страница не найдена':
                    product_wrappers = self.page.query_selector_all('.product__wrapper')
                    for pw in product_wrappers:
                        url = pw.query_selector('.title').get_attribute('href')
                        self.all_art.append(url)
                else:
                    break

    def start(self):
        t1 = datetime.datetime.now()
        print(f'Start: {t1}')
        try:
            with sync_playwright() as playwright:
                self.browser = playwright.chromium.launch(headless=False, args=['--blink-settings=imagesEnabled=false'])
                self.context = self.browser.new_context()
                self.page = self.context.new_page()
                self.page.add_init_script(self.js)
                catalogs = self.read_catalogs_from_txt()
                self.get_arts_in_catalogs(catalogs)
                self.write_txt_file_all_articles()
                self.context.close()
                self.browser.close()
        except Exception as exp:
            print(exp)
            # self.send_logs_to_telegram(message=f'Произошла ошибка!\n\n\n{exp}')
        t2 = datetime.datetime.now()
        print(f'Finish: {t2}, TIME: {t2 - t1}')
        # self.send_logs_to_telegram(message=f'Finish: {t2}, TIME: {t2 - t1}')


if __name__ == '__main__':
    ParserArticlesByCatalogs().start()
