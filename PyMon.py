import sys
from PyQt5.QtWidgets import *
import Kiwoom
import math
import numpy as np
import datetime
import time
import FinanceDataReader as fdr
import random as r


MARKET_KOSPI   = 0
MARKET_KOSDAQ  = 10

class PyMon:
    def __init__(self):
        self.kiwoom = Kiwoom.Kiwoom()
        self.kiwoom.comm_connect()
        self.get_code_list()

    def get_code_list(self):
        self.kospi_codes = self.kiwoom.get_code_list_by_market(MARKET_KOSPI)
        self.kosdaq_codes = self.kiwoom.get_code_list_by_market(MARKET_KOSDAQ)

    def get_ohlcv(self, code):
        day = 100
        start = (datetime.datetime.today()-datetime.timedelta(day)).strftime("%Y%m%d")
        end = (datetime.datetime.today()).strftime("%Y%m%d")
        time.sleep(0.1)
        df = fdr.DataReader(symbol=code, start=start, end=end)
        return df

    def get_info(self, code):
        df = self.get_ohlcv(code)
        if len(df) < 60 or int(df['Close'][-1]) < 1000 or int(df['Volume'][-1]) < 100000 :
            return False

        self.noise20 = self.noise_Ndays_avg(df, 20)
        self.invest_ratio = 0.02 / self.cal_volatility(df)
        self.range = abs(int(df['High'][-1])-int(df['Low'][-1]))
        return True

    def noise_Ndays_avg(self, df, N):
        noise_sum = 0
        for i in range(1, N+1):
            day = df.iloc[-i]
            noise_sum += 1 - abs((day['Open'] - day['Close']) / (day['High'] - day['Low']))
        return noise_sum / N

    def cal_volatility(self, df):
        volatility_by_day = []
        for i in range(1, 60 + 1):
            day = df.iloc[-i]
            volatility_by_day.append((day['Open'] - day['Close'])/day['Open'])
        return np.std(np.array(volatility_by_day))

    def update_portfolio(self, buy_list):
        f = open("portfolio.txt", "wt")
        for code in buy_list:
            f.writelines(f"{code[0]};{code[2]};{code[3]}\n")
        f.close()

    def run(self):
        self.tmp_list = []
        num = len(self.kosdaq_codes)
        for i, code in enumerate(self.kosdaq_codes):
            if not self.get_info(code):
                continue
            print(f"{i+1} / {num} : {code} 노이즈20 : {self.noise20:1f} | 투자비율: {self.invest_ratio:1f}")
            if not math.isinf(self.noise20) and not math.isnan(self.noise20) and not math.isnan(self.invest_ratio) :
                self.tmp_list.append([code, self.noise20, self.invest_ratio, self.range])

        self.tmp_list.sort(key=lambda x:x[1])
        self.portfolio1 = self.tmp_list[0:10]
        self.update_portfolio(self.portfolio1)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    pymon = PyMon()
    pymon.run()

