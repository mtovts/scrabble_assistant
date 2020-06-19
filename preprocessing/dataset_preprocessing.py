import time
import warnings
from pathlib import Path
from shutil import rmtree

import numpy as np
from skimage import img_as_ubyte, img_as_bool

from skimage.io import imread, imsave

from CV.scan import IMG_SIZE, crop_letter, cut_board_on_cells, \
    cut_by_external_contour, cut_by_internal_contour, CutException
from preprocessing.model_preprocessing import rgb_to_gray, gray_to_binary

IMAGES_TO_CUT_PATH = Path('!raw_images_to_cut')
DATASET_PATH = Path('ML/dataset')
IS_EMPTY_CELLS_INCLUDED = False  # True, если нужны пустые клетки в датасете

# authors - Misha, Matvey
if __name__ == "__main__":

    # Массив одномерных координат клеток с буквами и пустых
    coordinates = np.arange(33)
    if IS_EMPTY_CELLS_INCLUDED:
        coordinates = np.append(coordinates, (50, 52, 48, 76, 105, 112))
    coordinates = np.reshape(coordinates, (len(coordinates), 1))
    # Массив категорий для классификации
    categories = np.arange(1, 34)
    if IS_EMPTY_CELLS_INCLUDED:
        categories = np.append(categories, ('Empty', 'Green', 'Blue',
                                            'Yellow', 'Red', 'White'))
    # Объединение их в массив, состоящий из [координата, категория]
    crd_ctg = []
    for i in range(len(categories)):
        crd_ctg = np.append(crd_ctg, (str(coordinates[i][0]),
                                      str(categories[i])))
    crd_ctg = np.reshape(crd_ctg, (len(coordinates), 2))

    # (Пере-)создание папок-категорий будущего датасета
    for folder in (Path.cwd().parent / DATASET_PATH).glob('*'):
        rmtree(Path.cwd().parent / DATASET_PATH / Path(folder), True)
    time.sleep(3)  # Вынужденно встроенная задержка перед созданием новых папок
    for category in categories:
        (Path.cwd().parent / DATASET_PATH / Path(str(category)))\
            .mkdir(mode=0o777)

    # Создаем генератор путей исходных изображений
    path_gen = (Path.cwd().parent / IMAGES_TO_CUT_PATH).glob('*.jpg')
    # Записываем пути
    paths = [path for path in path_gen if path.is_file()]

    # Массив для отлова фоток, которые не получилось обрезать
    bad_images = []
    warnings.filterwarnings('error')

    for k, file_img in enumerate(paths, 1):
        filename = str(file_img).split('\\')[-1]  # fixme
        image = imread(str(file_img))
        try:
            external_crop = cut_by_external_contour(image)
            internal_crop = cut_by_internal_contour(external_crop)
            #internal_crop = img_as_ubyte(internal_crop)
            board_squares = cut_board_on_cells(internal_crop)
            # Решейп из двухмерного в одномерный массив изображений
            flat_board = board_squares.reshape(
                (board_squares.shape[0] * board_squares.shape[1], IMG_SIZE,
                 IMG_SIZE, 3))  # если нет фильтра то добавляется форма 3

            # Обработка и запись клеток
            for c in crd_ctg:
                img_cell = flat_board[int(c[0])]
                img_cell = rgb_to_gray(img_cell, [1, 0, 0])
                img_cell = gray_to_binary(img_cell)
                img_cell = img_as_ubyte(img_cell)
                # Округление можно добавить тут.
                img_cell = crop_letter(img_cell)  # не работает как надо?

                imsave(str(Path.cwd().parent / DATASET_PATH / Path(c[1]) / Path(filename)),
                       img_cell)
        except (CutException, RuntimeWarning, UserWarning):
            bad_images.append(filename)
        # Вывод процента выполнения
        print(filename, '|', str(round(k / len(paths) * 100, 1)) + "%")
    # Вывод результатов операции
    print('Готово!')
    if len(bad_images) > 0:
        print('Не удалось обрезать:')
        [print(b, sep=', ') for b in bad_images]
        print('Удалить?(y/n)', end=' ')
        answer = input()
        if answer == 'y':
            for b in bad_images:
                Path(Path.cwd().parent / IMAGES_TO_CUT_PATH / b).unlink()
            print('Удаление завершено')