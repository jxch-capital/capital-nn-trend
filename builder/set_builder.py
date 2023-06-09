from utils.file_util import file_paths
import pandas as pd
import datetime
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED, FIRST_COMPLETED
import threading
import random
from utils.stockstats_util import neighbor_normalized, overall_normalized

lock = threading.Lock()


class SetBuilder(object):
    def __init__(self, slice_path, sliding=200):
        self.slice_path = slice_path
        self.sliding = sliding
        self.random_arr = []

    def build_random_arr(self, path):
        sheets = pd.read_excel(path, sheet_name=None)
        for sheet_name, df in sheets.items():
            df.drop(['Unnamed: 0'], axis=1, inplace=True)
            available_index = list(map(lambda x: x - self.sliding+1, list(
                filter(lambda x: x > self.sliding, df[df['mark'] > 0].index.values))))
            with lock:
                self.random_arr.append({
                    # 'available_index': list(range(0, df.shape[0] - self.sliding)),
                    'available_index': available_index,
                    'raw_data': df,
                })

    def build(self):
        print('正在将所有初始化数据写入内存...')
        start = datetime.datetime.now()
        executor = ThreadPoolExecutor(max_workers=16)
        tasks = [executor.submit(self.build_random_arr, path) for path in file_paths(self.slice_path)]
        wait(tasks, return_when=ALL_COMPLETED)
        print(f'随机器构造完成，耗时{(datetime.datetime.now() - start).seconds} s')
        executor.shutdown()

    def build_debug(self):
        path = file_paths(self.slice_path)[0]
        self.build_random_arr(path)

    def normalized(self, df):
        df.reset_index(inplace=True, drop=True)
        return overall_normalized(df)

    def random_one(self, normalized=True):
        for i in range(10):
            arr_index_random = random.randint(0, len(self.random_arr) - 1)
            available_index = self.random_arr[arr_index_random]['available_index']
            if i != 9 and len(available_index) == 0:
                continue
            elif i == 9 and len(available_index) == 0:
                print('资源已经用尽')
                self.random_arr[arr_index_random]['available_index'] = \
                    list(range(0, self.random_arr[arr_index_random]['raw_data'].shape[0] - self.sliding))
                available_index = self.random_arr[arr_index_random]['available_index']

            available_index_random = random.randint(0, len(available_index) - 1)
            index = available_index[available_index_random]
            try:
                del available_index[available_index_random]
            except:
                print('')
            res_df = self.random_arr[arr_index_random]['raw_data'][index:index + self.sliding].copy()
            return self.normalized(res_df) if normalized else res_df

    def random_data_arr(self, size=100000, normalized=True):
        print('正在生成数据集...')
        start = datetime.datetime.now()
        try:
            return [self.random_one(normalized) for i in range(size)]
        finally:
            print(f'数据集生成完毕，耗时{(datetime.datetime.now() - start).seconds} s')
