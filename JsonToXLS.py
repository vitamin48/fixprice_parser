"""
Скрипт считывает файл JSON с товарами и записывает данные в Excel.
"""
import json
import pandas as pd

PATH = 'merge_dictionaries/result_merge/data.json'


def read_json(path='out/data.json'):
    with open(path, encoding='utf-8') as json_file:
        data = json.load(json_file)
        return data


def create_df_by_dict(data_dict):
    pd.options.mode.copy_on_write = True
    # Преобразуйте словарь в DataFrame
    df = pd.DataFrame.from_dict(data_dict, orient='index')

    # Добавление цены для продажи
    # Функция для преобразования значения столбца price
    def transform_price(x):
        result = x * 5 if x < 200 else (
            x * 4.5 if 200 <= x < 500 else (
                x * 4 if 500 <= x < 1000 else (
                    x * 3.5 if 1000 <= x < 5000 else (
                        x * 3 if 5000 <= x < 10000 else (
                            x * 2.5 if 10000 <= x < 20000 else (x * 2))))))
        # Убеждаемся, что значение после преобразований не меньше 490
        result = max(result, 490)
        # Округление до целого числа
        return round(result)

    df['price2'] = df['price'].apply(transform_price)
    # Вставить столбец "price2" после третьего столбца
    df.insert(2, 'price2', df.pop('price2'))
    # Создание столбца Ссылки на фото товара
    df['url_img2'] = df['url_img']
    df['url_img2'] = df.apply(lambda row: ', '.join(row['url_img'][1:]) if len(row['url_img']) > 1 else '-', axis=1)
    # Оставляем в столбце Ссылка на главное фото товара только первый элемент из списка
    df['url_img'] = df['url_img'].apply(lambda x: x[0] if x else None)
    res_df_ozon = df[['name', 'price', 'price2', 'stock', 'brand', 'description', 'weight', 'packing_width',
                      'packing_height', 'package_length', 'country', 'url_img', 'url_img2']]
    # Переименуйте столбцы
    res_df_ozon.columns = ['Название', 'Цена FixPrice', 'Цена для OZON', 'Остаток', 'Брэнд', 'Описание',
                           'Вес, г', 'Ширина, мм', 'Высота, мм', 'Длина, мм', 'Производитель',
                           'Ссылка на главное фото товара', 'Ссылки на фото товара']
    # Создаем столбец Артикул из ключей словаря
    res_df_ozon['Артикул'] = res_df_ozon.index.values
    # Переносим столбец Артикул на 1 место
    res_df_ozon.insert(0, 'Артикул', res_df_ozon.pop('Артикул'))
    # Сбросьте индекс для чистоты
    res_df_ozon.reset_index(drop=True, inplace=True)
    # Создаем копию таблицы для WB
    res_df_wb = res_df_ozon.copy()
    # Переименовываем столбцы для WB
    res_df_wb = res_df_wb.rename(columns={'Ширина, мм': 'Ширина, cм'})
    res_df_wb = res_df_wb.rename(columns={'Высота, мм': 'Высота, cм'})
    res_df_wb = res_df_wb.rename(columns={'Длина, мм': 'Длина, cм'})
    # Конверт мм в см
    res_df_wb['Ширина, cм'] = res_df_wb['Ширина, cм'].apply(
        lambda x: int(round(int(x) / 10)) if x != '-' else '-')
    res_df_wb['Высота, cм'] = res_df_wb['Высота, cм'].apply(
        lambda x: int(round(int(x) / 10)) if x != '-' else '-')
    res_df_wb['Длина, cм'] = res_df_wb['Длина, cм'].apply(
        lambda x: int(round(int(x) / 10)) if x != '-' else '-')
    # Сбросьте индекс для чистоты
    res_df_wb.reset_index(drop=True, inplace=True)
    return res_df_ozon, res_df_wb


def create_xls(res_df_ozon, res_df_wb):
    """Создание файла excel из 1-го DataFrame"""
    first_art = res_df_ozon['Артикул'].iloc[0]
    last_art = res_df_ozon['Артикул'].iloc[-1]
    file_name = f'out\\FP_{first_art}_{last_art}.xlsx'
    writer = pd.ExcelWriter(file_name, engine_kwargs={'options': {'strings_to_urls': False}})
    res_df_ozon.to_excel(writer, sheet_name='OZON', index=False, na_rep='NaN', engine='openpyxl')
    res_df_wb.to_excel(writer, sheet_name='WB', index=False, na_rep='NaN', engine='openpyxl')
    # Auto-adjust columns' width OZON
    for column in res_df_ozon:
        column_width = max(res_df_ozon[column].astype(str).map(len).max(), len(column)) + 2
        col_idx = res_df_ozon.columns.get_loc(column)
        writer.sheets[f'{"OZON"}'].set_column(col_idx, col_idx, column_width)
    writer.sheets["OZON"].set_column(1, 1, 30)
    writer.sheets["OZON"].set_column(6, 6, 30)
    writer.sheets["OZON"].set_column(12, 12, 30)
    writer.sheets["OZON"].set_column(13, 13, 30)
    writer.sheets["OZON"].set_column(14, 14, 30)

    # Auto-adjust columns' width WB
    for column in res_df_wb:
        column_width = max(res_df_wb[column].astype(str).map(len).max(), len(column)) + 2
        col_idx = res_df_wb.columns.get_loc(column)
        writer.sheets[f'{"WB"}'].set_column(col_idx, col_idx, column_width)
    writer.sheets["WB"].set_column(1, 1, 30)
    writer.sheets["WB"].set_column(6, 6, 30)
    writer.sheets["WB"].set_column(12, 12, 30)
    writer.sheets["WB"].set_column(13, 13, 30)
    writer.sheets["WB"].set_column(14, 14, 30)

    writer.close()
    print(f'Данные успешно сохранены в файл: out\\FP_{first_art}_{last_art}.xlsx')


if __name__ == '__main__':
    data_json = read_json(path=PATH)
    df_ozon, df_wb = create_df_by_dict(data_dict=data_json)
    create_xls(res_df_ozon=df_ozon, res_df_wb=df_wb)
