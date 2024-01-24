"""
Скрипт на основе playwright считывает ссылки на товары Fix-Price из файла fix_price_articles.txt,
переходит по ним, предварительно установив город и адрес магазина из констант CITY и ADDRESS,
считыват информацию и остатки каждого товара, если брэнда товара нет в файле bad_brand.txt,
записывает результаты в файл XLS.

Помимо результирующего файла XLS, формируются дополнительные файлы:
articles_with_bad_req.txt - для ссылок, которые не удалось загрузить, либо товар из списка нежелательных
брэндов
available_in_stock.txt - товары, которые есть в наличии по указанному адресу магазина
catalogs.txt - список каталогов сайта
out_of_stock.txt - список товаров, остатки которых равны 0.
"""
import requests
import datetime
import time
from tqdm import tqdm
from pathlib import Path
import pandas as pd
import json

from old_vers.fix_price_parser_data_by_article import bcolors

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

CITY = 'Брянск'
ADDRESS = 'г.Брянск, ул.Бежицкая, д.1Б'


def send_logs_to_telegram(message):
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


def read_articles_from_txt():
    with open('in/fix_price_articles.txt', 'r', encoding='utf-8') as file:
        articles = [f'{line}'.rstrip() for line in file]
        return articles


def read_bad_brand():
    with open('in/bad_brand.txt', 'r', encoding='utf-8') as file:
        bad_brand = [f'{line}'.rstrip().lower() for line in file]
        return bad_brand


class FixParser:
    def __init__(self):
        self.save_path = f'{str(Path(__file__).parents[1])}'
        self.__main_url = 'https://fix-price.com/'
        self.res_dict = {}
        self.browser = None
        self.context = None
        self.page = None
        self.res_df_ozon = pd.DataFrame()
        self.res_df_wb = pd.DataFrame()
        self.js = """
        Object.defineProperties(navigator, {webdriver:{get:()=>undefined}});
        """

    def set_city(self, playwright):
        self.browser = playwright.chromium.launch(headless=False, args=['--blink-settings=imagesEnabled=false'])
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.page.add_init_script(self.js)
        print(f'{bcolors.OKGREEN}Устанавливаем город{bcolors.ENDC}')
        self.page.goto("https://fix-price.com/")
        self.page.wait_for_load_state('load')
        time.sleep(10)
        self.page.locator('//*[@id="app-header"]/header/div/div[1]/div[1]/div[1]/span').click()
        time.sleep(10)
        # # Ожидаем появления элемента с placeholder 'Ваш город'
        # # self.page.wait_for_selector('input[placeholder="Ваш город"]')
        # time.sleep(5)
        # Вводим значение в поле 'Ваш город'
        self.page.fill('input[placeholder="Ваш город"]', 'Брянск')
        time.sleep(10)
        self.page.wait_for_selector('//*[@id="modal"]/div/div[4]/div/div[1]').click()
        time.sleep(2)
        self.page.locator('//*[@id="modal"]/div/div/div/button[2]').click()
        time.sleep(2)
        self.page.locator('//*[@id="app-header"]/header/div/div[1]/div[1]/div[2]/div[2]/div[1]').click()
        time.sleep(2)
        self.page.locator('//*[@id="modal"]/div/div/div/div[3]/div/div[2]/div').click()  # выбрать магазин
        time.sleep(2)
        find_shop_placeholder = self.page.locator(
            '//*[@id="modal"]/div/div/div[2]/div/div[2]/div[2]/div[1]/div[2]/div[1]/div[1]/div[1]/input')
        time.sleep(5)
        find_shop_placeholder.click()
        time.sleep(2)
        find_shop_placeholder.type(text='г.Брянск, ул.Бежицкая, д.1Б', delay=1.5)
        self.page.wait_for_load_state('load')
        time.sleep(7)
        self.page.locator('//*[@id="modal"]/div/div/div[2]/div/div[2]/div[2]/div[1]/div[2]/div[5]/div/div[1]').click()
        time.sleep(2)
        self.page.locator('//*[1]/ymaps/div/div/button/span').click()
        time.sleep(2)

    def get_data_from_articles(self, articles, bad_brand, playwright):
        count_for_clear_cart = 0
        for art in tqdm(articles):
            max_attempts = 2
            attempts = 0
            while attempts < max_attempts:
                try:
                    self.page.goto(f'{self.__main_url}catalog/{art}')
                    self.page.wait_for_load_state('load')
                    time.sleep(1)
                    stock_product = self.page.wait_for_selector('.product-stock .text',
                                                                timeout=10000).inner_text()
                    if stock_product == 'Нет в наличии':
                        print(f'{bcolors.WARNING}Нет в наличии:{bcolors.ENDC} {art}')
                        with open('out/out_of_stock.txt', 'a') as output:
                            output.write(art + '\n')
                        count_for_clear_cart += 1
                        break
                    elif stock_product == 'В наличии':
                        count_for_clear_cart += 1
                        print(f' {bcolors.OKGREEN}[+]{bcolors.ENDC} {art}')
                        self.page.wait_for_load_state('load')
                        with open('out/available_in_stock.txt', 'a') as output:
                            output.write(art + '\n')
                        self.page.wait_for_selector('[data-test="button"]', timeout=10000).click()
                        time.sleep(2)
                        self.page.fill('[data-test="counter-value"]', '99')
                        self.page.wait_for_timeout(3000)
                        time.sleep(2)
                        stock = self.page.evaluate(
                            '() => { return document.querySelector("#__layout > div > div > div.page-content > div > '
                            'div > '
                            'div > div > div.product > div.product-details > div.price-quantity-block > '
                            'div.price-wrapper.price > div > div > div.quantity > div > input").value; }')
                        if stock == '1':
                            print("stock == '1'!")
                            with open('out/articles_with_bad_req.txt', 'a') as output:
                                output.write(f'stock == 1: {art} + \n')
                        name = self.page.wait_for_selector(".product-details .title", timeout=10000).inner_text()
                        price = self.page.wait_for_selector(".product-details .regular-price",
                                                            timeout=10000).inner_text()
                        price = float(price.replace(' ₽', '').replace(',', '.'))
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
                        brand = data.get('Бренд', 'NoName')
                        if brand.lower() in bad_brand:
                            print(
                                f'{bcolors.WARNING}Товар {art} из списка нежелательных брэндов ({brand}){bcolors.ENDC}')
                            with open('out/articles_with_bad_req.txt', 'a') as output:
                                output.write(f'НЕЖЕЛАТЕЛЬНЫЙ БРЭНД: {art}\n')
                            break
                        else:
                            # self.code.append(data.get('Код товара', '-'))
                            """Делаем проверку Ширины, Высоты и веса, т.к. где-то Ширина, а где-то Ширина упаковки"""
                            # Ширина
                            width_var1 = data.get('Ширина, мм.', None)
                            width_var2 = data.get('Ширина упаковки, мм.', None)
                            # Высота
                            height_var1 = data.get('Высота, мм.', None)
                            height_var2 = data.get('Высота упаковки, мм.', None)
                            # Длина
                            length_var1 = data.get('Длина, мм.', None)
                            length_var2 = data.get('Длина упаковки, мм.', None)
                            # Вес
                            weight_var1 = data.get('Вес, гр.', None)
                            weight_var2 = data.get('Вес упаковки, гр.', None)

                            soup = BeautifulSoup(self.page.content(), 'lxml')
                            product_images = soup.find('div', class_='product-images')
                            img_list = []
                            swiper_wrapper = product_images.find('div', class_='swiper-wrapper')
                            if swiper_wrapper:
                                for sw in swiper_wrapper:
                                    len_contents = len(sw.next.contents)
                                    if len_contents > 7:
                                        img = sw.next.contents[6].attrs['src']
                                        img = img.replace('800x800/', '')
                                        img_list.append(img)
                                    else:
                                        img_list.append('-+'
                                                        ' ')
                            else:
                                img = \
                                    soup.find('div', class_='product-images').find('div',
                                                                                   class_='zoom-on-hover').contents[
                                        6].attrs[
                                        'src']
                                img = img.replace('800x800/', '')
                                img_list.append(img)
                                img_list.append('-')
                            if len(img_list) > 14:
                                img_list = img_list[13:]

                            code = data.get('Код товара', '-')
                            self.res_dict[code] = {'name': name, 'price': price, 'stock': stock, 'brand': brand,
                                                   'description': description,
                                                   'weight': weight_var1 if weight_var1 else (
                                                       weight_var2 if weight_var2 else '-'),
                                                   'packing_width': width_var1 if width_var1 else (
                                                       width_var2 if width_var2 else '-'),
                                                   'packing_height': height_var1 if height_var1 else (
                                                       height_var2 if height_var2 else '-'),
                                                   'package_length': length_var1 if length_var1 else (
                                                       length_var2 if length_var2 else '-'),
                                                   'country': data.get('Страна производства', '-'), 'url_img': img_list}
                            with open('out/data.json', 'w', encoding='utf-8') as json_file:
                                json.dump(self.res_dict, json_file, indent=2, ensure_ascii=False)
                            # with open('data.pickle', 'wb') as file:
                            #     pickle.dump(self.res_dict, file)
                            if count_for_clear_cart > 80:
                                print('\nОчищаем корзинку В наличии')
                                self.clear_cart()
                                count_for_clear_cart = 0
                            break
                    else:
                        print(f'{bcolors.FAIL}НЕ ОПРЕДЕЛЕНО наличие товара: {art}')
                        with open('out/articles_with_bad_req.txt', 'a') as output:
                            output.write('НЕ ОПРЕДЕЛЕНО наличие товара: ' + art + '\n')
                except Exception as exp:
                    attempts += 1
                    print(f'\n{bcolors.OKCYAN}Новая попытка {attempts} из {max_attempts}{bcolors.ENDC}\n\n'
                          f'Для артикула: {art}\n\nИсключение:\n\n{exp}')
            if attempts == max_attempts:
                print(f'{bcolors.FAIL}ОШИБКА! Все попытки исчерпаны. В articles_with_bad_req.txt добавлено: '
                      f'\n{bcolors.ENDC}{art}\n')
                with open('out/articles_with_bad_req.txt', 'a') as output:
                    output.write(art + '\n')
                time.sleep(10)
                print('Перезапускаю браузер')
                self.context.close()
                self.browser.close()
                time.sleep(3)
                self.set_city(playwright)

    def clear_cart(self):
        time.sleep(10)
        try:
            self.page.goto(f'https://fix-price.com/cart', timeout=10000)
            time.sleep(10)
            self.page.get_by_text("Удалить выбранные").click()
        except:
            print(f'{bcolors.OKCYAN}Корзина не была очищена{bcolors.ENDC}')

    def create_df_by_dict(self):
        pd.options.mode.copy_on_write = True

        # Преобразуйте словарь в DataFrame
        df = pd.DataFrame.from_dict(self.res_dict, orient='index')

        # Добавление цены для продажи
        df['price2'] = df['price'].apply(lambda x: x * 2 if x < 100 else (x * 3 if 100 <= x <= 500 else x * 4))

        # Вставить столбец "price2" после третьего столбца
        df.insert(2, 'price2', df.pop('price2'))

        # Создание столбца Ссылки на фото товара
        df['url_img2'] = df['url_img']
        df['url_img2'] = df.apply(lambda row: ', '.join(row['url_img'][1:]) if len(row['url_img']) > 1 else '-', axis=1)

        # Оставляем в столбце Ссылка на главное фото товара только первый элемент из списка
        df['url_img'] = df['url_img'].apply(lambda x: x[0] if x else None)

        self.res_df_ozon = df[['name', 'price', 'price2', 'stock', 'brand', 'description', 'weight', 'packing_width',
                               'packing_height', 'package_length', 'country', 'url_img', 'url_img2']]

        # Переименуйте столбцы
        self.res_df_ozon.columns = ['Название', 'Цена FixPrice', 'Цена для OZON', 'Остаток', 'Брэнд', 'Описание',
                                    'Вес, г', 'Ширина, мм', 'Высота, мм', 'Длина, мм', 'Производитель',
                                    'Ссылка на главное фото товара', 'Ссылки на фото товара']

        # Создаем столбец Артикул из ключей словаря
        self.res_df_ozon['Артикул'] = self.res_df_ozon.index.values

        # Переносим столбец Артикул на 1 место
        self.res_df_ozon.insert(0, 'Артикул', self.res_df_ozon.pop('Артикул'))

        # Сбросьте индекс для чистоты
        self.res_df_ozon.reset_index(drop=True, inplace=True)

        # Создаем копию таблицы для WB
        self.res_df_wb = self.res_df_ozon.copy()

        # Переименовываем столбцы для WB
        self.res_df_wb = self.res_df_wb.rename(columns={'Ширина, мм': 'Ширина, cм'})
        self.res_df_wb = self.res_df_wb.rename(columns={'Высота, мм': 'Высота, cм'})
        self.res_df_wb = self.res_df_wb.rename(columns={'Длина, мм': 'Длина, cм'})

        # Конверт мм в см
        self.res_df_wb['Ширина, cм'] = self.res_df_wb['Ширина, cм'].apply(
            lambda x: int(round(int(x) / 10)) if x != '-' else '-')
        self.res_df_wb['Высота, cм'] = self.res_df_wb['Высота, cм'].apply(
            lambda x: int(round(int(x) / 10)) if x != '-' else '-')
        self.res_df_wb['Длина, cм'] = self.res_df_wb['Длина, cм'].apply(
            lambda x: int(round(int(x) / 10)) if x != '-' else '-')

        # Сбросьте индекс для чистоты
        self.res_df_wb.reset_index(drop=True, inplace=True)

        print()

    def create_xls(self):
        """Создание файла excel из 1-го DataFrame"""
        file_name = f'out\\FP_.xlsx'
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

    def start(self):
        t1 = datetime.datetime.now()
        print(f'Start: {t1}')
        try:
            with sync_playwright() as playwright:
                self.set_city(playwright)
                articles = read_articles_from_txt()
                self.get_data_from_articles(articles, bad_brand=read_bad_brand(), playwright=playwright)
                self.context.close()
                self.browser.close()
                # self.create_df()
                self.create_df_by_dict()
                self.create_xls()
        except Exception as exp:
            print(exp)
            send_logs_to_telegram(message=f'Произошла ошибка!\n\n\n{exp}')
        t2 = datetime.datetime.now()
        print(f'Finish: {t2}, TIME: {t2 - t1}')
        send_logs_to_telegram(message=f'Finish: {t2}, TIME: {t2 - t1}')


if __name__ == '__main__':
    FixParser().start()
