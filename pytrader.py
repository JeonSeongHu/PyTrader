import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtTest import *
from PyQt5 import uic
from Kiwoom import *
from bs4 import BeautifulSoup
import requests
import datetime
import random as r

form_class = uic.loadUiType("pytrader.ui")[0]

class GetPortfolio(QThread):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

    def run(self):
        f = open("portfolio.txt", "rt")
        tmpp = f.readlines()
        for i in range(len(tmpp)):
            line = tmpp[i].rstrip().split(";")

            self.parent.portfolio.append([line[0], float(line[1]), int(line[2])])
        print("portfolio done")

class SetList(QThread):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

    def run(self):
        if not self.parent.set_list_done:
            self.set_sell_list()
            print("set_sell_list done")
            self.set_buy_list()
            print("set_buy_list done")
        self.load_buy_sell_list()
        print("load_buy_sell_list done")

    def set_buy_list(self):
        try:
            f = open("buy_list.txt", 'rt', encoding="cp949")
            tmp = f.readlines()
            for line in tmp:
                if line.rstrip().split(';')[-1] == '매수전':
                    continue
                t = datetime.datetime.strptime(line.rstrip().split(';')[-1].split()[0], '%Y/%m/%d').date()
                now = datetime.datetime.now().date()
                if  t >= now:
                    return
        except:
            pass

        f = open("buy_list.txt", 'w', encoding="cp949")

        tmp_list = []
        for stock in self.parent.portfolio:
            code = stock[0]
            self.parent.kiwoom.set_input_value("종목코드", code)
            self.parent.kiwoom.comm_rq_data("opt10001_req", "opt10001", 0, "0101")

            open_price = abs(int(self.parent.kiwoom.open_price.replace(",", "")))
            stock[1] = stock[1] if stock[1] <= 1 else 1
            buy_price = open_price + stock[2] * 0.5
            buy_count = int(self.parent.deposit.replace(",", "")) * stock[1] / open_price / 3
            tmp_list.append(f"매수;{code};시장가;{int(buy_count)};{int(buy_price)};매수전\n")
            QTest.qWait(int(1000 * 0.4))

        for line in tmp_list:
            f.write(line)
        f.close()

    def set_sell_list(self):
        try :
            f = open("sell_list.txt", 'rt', encoding="cp949")
            tmp = f.readline().rstrip()
            if tmp.split(';')[-1] == '매도전':
                return
            t = datetime.datetime.strptime(tmp.rstrip().split(';')[-1].split()[0], '%Y/%m/%d').date()
            now = datetime.datetime.now().date()
            if t >= now:
                return
        except:
            pass

        f = open("sell_list.txt", 'w', encoding="cp949")
        tmp_list = []
        item_count = len(self.parent.stock_list)
        for j in range(item_count):
            row = self.parent.stock_list[j]
            tmp_list.append(f"매도;{row[-1][1:]};시장가;{row[1]};0;매도전\n")
        for line in tmp_list:
            f.write(line)
        f.close()

    def load_buy_sell_list(self):
        f = open("buy_list.txt", 'rt')
        buy_list = f.readlines()
        buy_list = [v for v in buy_list if v != '\n']
        f.close()

        f = open("sell_list.txt", 'rt')
        sell_list = f.readlines()
        sell_list = [v for v in sell_list if v != '\n']
        f.close()

        row_count = len(buy_list) + len(sell_list)
        self.parent.tableWidget_3.setRowCount(row_count)

        # buy list
        for j in range(len(buy_list)):
            row_data = buy_list[j]
            split_row_data = row_data.split(';')
            split_row_data[1] = self.parent.kiwoom.get_master_code_name(split_row_data[1].rsplit())

            for i in range(len(split_row_data)):
                item = QTableWidgetItem(split_row_data[i].rstrip())
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignCenter)
                self.parent.tableWidget_3.setItem(j, i, item)

        # sell list
        for j in range(len(sell_list)):
            row_data = sell_list[j]
            split_row_data = row_data.split(';')
            split_row_data[1] = self.parent.kiwoom.get_master_code_name(split_row_data[1].rstrip())

            for i in range(len(split_row_data)):
                item = QTableWidgetItem(split_row_data[i].rstrip())
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignCenter)
                self.parent.tableWidget_3.setItem(len(buy_list) + j, i, item)

        self.parent.tableWidget_3.resizeRowsToContents()

class TradeStocks(QThread):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.account = self.parent.comboBox.currentText()

    def run(self):
        if not self.parent.stock_sell_done and self.parent.is_market_opened:
            self.sell_stocks()
        self.buy_stocks()
        print("monitoring done")

    def sell_stocks(self):
        hoga_lookup = {'지정가': "00", '시장가': "03"}

        f = open("sell_list.txt", 'rt')
        sell_list = f.readlines()
        f.close()

    # sell list
        for i, row_data in enumerate(sell_list):
            if row_data == "\n":
                continue
            split_row_data = row_data.split(';')
            hoga = split_row_data[2]
            code = split_row_data[1]
            num = split_row_data[3].replace(",", "")
            price = split_row_data[4]

            if split_row_data[-1].rstrip() == '매도전' and self.parent.is_market_opened:
                self.parent.kiwoom.send_order("send_order_req", "0101", self.account, 2, code, num, price,
                                              hoga_lookup[hoga], "")
                tmp = sell_list[i].split(';')
                tmp[5] = (datetime.datetime.now()).strftime("%Y/%m/%d %H:%M:%S")
                tmp[4] = str(self.get_nowprice(code))

                sell_list[i] = ";".join(tmp)

        # file update
        f = open("sell_list.txt", 'wt')
        for row_data in sell_list:
            f.write(row_data + '\n')
        f.close()

        self.parent.stock_sell_done = True

    def buy_stocks(self):
        hoga_lookup = {'지정가': "00", '시장가': "03"}
        f = open("buy_list.txt", 'rt')
        buy_list = f.readlines()
        f.close()

        # buy list
        for i, row_data in enumerate(buy_list):
            if row_data == "\n":
                continue
            split_row_data = row_data.split(';')
            hoga = split_row_data[2]
            code = split_row_data[1]
            num = split_row_data[3]
            price = split_row_data[4]
            now_price = self.get_nowprice(code)

            if split_row_data[-1].rstrip() == '매수전' and now_price >= int(price) and self.parent.is_market_opened:
                self.parent.kiwoom.send_order("send_order_req", "0101", self.account,
                                              1, code, num, price, hoga_lookup[hoga], "")
                QTest.qWait(int(1000 * 0.2))
                buy_list[i] = buy_list[i].replace("매수전", (datetime.datetime.now()).strftime("%Y/%m/%d %H:%M:%S"))

        # file update
        f = open("buy_list.txt", 'wt')
        for row_data in buy_list:
            f.write(row_data)
        f.close()

    def get_nowprice(self, code):
        self.header = [{'User-Agent':'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36'},
        {'User-Agent':"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.79 Safari/537.36"},
        {'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.53 Safari/537.36"}]
        self.nowhdr = r.randint(0, 2)
        try:
            url = f"https://finance.naver.com/item/main.nhn?code={code}"
            result = requests.get(url, headers=self.header[self.nowhdr]).text
            soup = BeautifulSoup(result, "html.parser")
            tmp = soup.find("p", {"class": "no_today"})
            return int(tmp.find("span", {"class": "blind"}).text.replace(",", ""))
        except:
            print("현재가 갱신 중 오류발생")
            QTest.qWait(1000*10)
            self.get_nowprice()


class MyWindow(QMainWindow, form_class):
    def __init__(self):
        super().__init__()
        self.market_start_time = QTime(9, 0, 10)
        self.market_end_time = QTime(13, 00, 10)

        self.wait_time = 10  # 추가

        self.setupUi(self)
        self.kiwoom = Kiwoom()
        self.kiwoom.comm_connect()
        self.UIconnect()  # 추가

        self.portfolio = []
        self.h1 = GetPortfolio(self)
        self.h2 = SetList(self)
        self.h3 = TradeStocks(self)

        self.trade_stocks_done = False
        self.is_market_opened = False
        self.set_list_done = False
        self.stock_sell_done = False

        self.auto_trade_start()



    def UIconnect(self):  # 추가
        # 종목-코드 연결 (##code_changed 함수)
        self.lineEdit.textChanged.connect(self.code_changed)

        # 계좌 정보 추가
        self.comboBox.addItems(self._get_account_list())

        # 현금 주문 (##send_order 함수)
        self.pushButton.clicked.connect(self.send_order)

        # 타이머
        self.timer = QTimer(self)
        self.timer.start(1000 * 1)
        self.timer.timeout.connect(self.timeout)

        # 실시간 조회 타이머
        self.timer2 = QTimer(self)
        self.timer2.start(1000 * self.wait_time)
        self.timer2.timeout.connect(self.timeout2)

        # 리스트 자동 갱신
        self.timerList = QTimer(self)
        self.timerList.start(1000 * self.wait_time)
        self.timerList.timeout.connect(self.set_list)

        # 자동 모니터링 및 거래
        self.timerMon = QTimer(self)
        self.timerMon.start(1000 * self.wait_time)
        self.timerMon.timeout.connect(self.trade_stocks)

        # 조회 버튼
        self.pushButton_2.clicked.connect(self.check_balance)



    def auto_trade_start(self):
        self.check_balance()
        self.h1.run()
        self.h2.run()
        self.h3.run()
        self.set_list_done = True

    def set_list(self):
        if self.set_list_done:
            self.h2.run()

    def trade_stocks(self):
        # if self.is_market_opened:
            self.h3.run()

    def _get_account_list(self):
        accouns_num = int(self.kiwoom.get_login_info("ACCOUNT_CNT"))
        accounts = self.kiwoom.get_login_info("ACCNO")
        accounts_list = accounts.split(';')[0:accouns_num]
        accounts_list = reversed(accounts_list)
        return accounts_list

    def timeout(self):
        current_time = QTime.currentTime()
        self.is_market_opened = self.market_end_time > self.current_time > self.market_start_time
        text_time = current_time.toString("hh:mm:ss")
        time_msg = "현재시간: " + text_time

        state = self.kiwoom.get_connect_state()
        if state == 1:
            state_msg = "서버 연결 중"
        else:
            state_msg = "서버 미 연결 중"

        self.statusbar.showMessage(state_msg + " | " + time_msg)

    def code_changed(self):
        code = self.lineEdit.text()
        name = self.kiwoom.get_master_code_name(code)
        self.lineEdit_2.setText(name)

    def send_order(self):
        order_type_lookup = {'신규매수': 1, '신규매도': 2, '매수취소': 3, '매도취소': 4}
        hoga_lookup = {'지정가': "00", '시장가': "03"}

        account = self.comboBox.currentText()
        order_type = self.comboBox_2.currentText()
        code = self.lineEdit.text()
        hoga = self.comboBox_3.currentText()
        num = self.spinBox.value()
        price = self.spinBox_2.value()

        self.kiwoom.send_order("send_order_req", "0101", account, order_type_lookup[order_type], code, num, price,
                               hoga_lookup[hoga], "")

    def check_balance(self):
        self.kiwoom.reset_opw00018_output()
        account_number = self.comboBox.currentText()

        self.kiwoom.set_input_value("계좌번호", account_number)
        self.kiwoom.comm_rq_data("opw00018_req", "opw00018", 0, "2000")

        while self.kiwoom.remained_data:
            time.sleep(0.2)
            self.kiwoom.set_input_value("계좌번호", account_number)
            self.kiwoom.comm_rq_data("opw00018_req", "opw00018", 2, "2000")

        # opw00001
        self.kiwoom.set_input_value("계좌번호", account_number)
        self.kiwoom.comm_rq_data("opw00001_req", "opw00001", 0, "2000")

        # balance
        item = QTableWidgetItem(self.kiwoom.d2_deposit)
        item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.tableWidget.setItem(0, 0, item)

        for i in range(1, 6):
            item = QTableWidgetItem(self.kiwoom.opw00018_output['single'][i - 1])
            self.deposit = self.kiwoom.opw00018_output['single'][-1]
            item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
            self.tableWidget.setItem(0, i, item)

        self.tableWidget.resizeRowsToContents()

        # Item list
        item_count = len(self.kiwoom.opw00018_output['multi'])
        self.stock_list = self.kiwoom.opw00018_output['multi']
        self.tableWidget_2.setRowCount(item_count)

        for j in range(item_count):
            row = self.kiwoom.opw00018_output['multi'][j]
            for i in range(len(row)):
                item = QTableWidgetItem(row[i])
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
                self.tableWidget_2.setItem(j, i, item)

        self.tableWidget_2.resizeRowsToContents()

    def timeout2(self):
        if self.checkBox.isChecked():
            self.check_balance()

    def timeout(self):
        self.current_time = QTime.currentTime()
        self.is_market_opened = self.market_end_time > self.current_time > self.market_start_time

        text_time = self.current_time.toString("hh:mm:ss")
        time_msg = "현재시간: " + text_time

        state = self.kiwoom.get_connect_state()
        if state == 1:
            state_msg = "서버 연결 중"
        else:
            state_msg = "서버 미 연결 중"

        self.statusbar.showMessage(state_msg + " | " + time_msg)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWindow = MyWindow()
    myWindow.show()
    app.exec_()