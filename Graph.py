#!/usr/bin/env python
# coding: UTF-8

#################################################################
# Copyright (C) 2017 Mono Wireless Inc. All Rights Reserved.    #
# Released under MW-SLA-*J,*E (MONO WIRELESS SOFTWARE LICENSE   #
# AGREEMENT).                                                   #
#################################################################

# ライブラリのインポート
import typing
from PyQt5 import QtCore
from PyQt5.QtWidgets import QWidget
from MNLib.apptag import AppTag
import sys
import os
import threading
import time
import copy
from datetime import datetime, timedelta
from optparse import OptionParser
from math import sqrt, acos, degrees
import csv
from enum import Enum, auto

# グラフおよびQt系のインポート
try:
    from PyQt5.QtWidgets import QWidget
    from PyQt5.QtQml import QQmlApplicationEngine
    from PyQt5 import QtCore, QtGui, QtWidgets, uic
    import pyqtgraph as pg
    # from pyqtgraph import QtGui, QtCore, QtWidgets
    import numpy as np
except ImportError:
    print("Cannot import pyqtgraph...")
    print("Please install pyqtgraph.")
    quit()


class State(Enum):
    stop = auto()
    recording = auto()
    pause = auto()


def make_file_name() -> str:
    return f"Record-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"


def check_state(func):
    def wrapper(self):
        print(f"処理前の状態：{state}")
        func(self)
        print(f"処理後の状態：{state}")
    return wrapper


# ここより下はグローバル変数の宣言

# コマンドラインオプションで使用する変数
options = None
args = None

# 各種フラグ
bExit = False
bUpdate = False
bEnableVolt = False
bEnableLQI = False
bEnableADC = False
bEnableOutput = False
bEnableLog = False
bEnablePlayer = False
bEnableErrMsg = False
bRestart = False
bRecord = False

# グラフのプロパティ
SampleNum = 128
YRange = 2
FPS = 100
NewLineNum = 2

# データやデータを保存しておくリストなど
RcvAddr = None		# グラフを描画するTWELITEのSID
SnsMode = None		# センサモード
Window = None		# QtのWindowのクラス
SnsData = list()  # センサデータを保持するリスト
SnsOrder = list()
graph = list()		# グラフの属性を保持するリスト

dummySensorDecline = 0xfe
dummySensorShock = 0xff
numDecline = -1
numShock = -1
# 各センサの累積値
sum_decline = 0.0
sum_shock = 0.0
count = 0
# 各スコアを保持
decline_score = 0
shock_score = 0

output_file_name = make_file_name()
state = State.stop

# グラフの属性を保持するクラス
class Graph():
    # インスタンス
    def __init__(self, mode=None):
        self.curve = list()
        self.curvenum = 0
        self.datalist = None
        self.Mode = mode

        self.plt = Window.addPlot()
        self.plt.showGrid(True, True, 1)
        # self.plt.setLabel('bottom','Sample')

        # print(self.plt.viewRange())

        self.plt.getAxis("bottom").setStyle(
            tickFont=QtGui.QFont("Helvetica", 20))
        self.plt.getAxis("left").setStyle(
            tickFont=QtGui.QFont("Helvetica", 20))

        self.text = pg.TextItem('', anchor=(1, 0))
        self.plt.addItem(self.text)
        self.text.setFont(QtGui.QFont("Helvetica", 120))
        self.score = 0

        if mode is not None:
            self.setmode(mode)

    # Y軸の範囲を指定する
    def setYRange(self, llimit, ulimit):
        self.plt.setYRange(llimit, ulimit)

    # Y軸のラベルを指定する
    def setYLabel(self, label, unit=None, color='FFFFFF'):
        # ラベルの文字色を白にする HTML形式で指定
        __Label = '<font size=\'10\' color=\'#'+color+'\'>'+label+'</font>'

        if unit is None:  # 単位が指定されていなければそのまま表示
            self.plt.setLabel('left', __Label)
        else:				# 指定されている場合は単位の文字色も白にして表示する
            __Unit = '<font size=\'10\' color=\'#'+color+'\'>'+unit+'</font>'
            self.plt.setLabel('left', __Label, __Unit)

    # グラフに描画する折れ線の初期化
    def CurveInit(self, num, namelist=None):
        # 1本目は赤、2本目は緑、3本目は水色、4本目は白を指定する
        R = [0,   0,   0, 255]
        G = [255, 255, 255, 255]
        B = [0,   0, 255, 255]

        # 描画したい線の数が0以下だったら何もしない
        if num <= 0:
            return

        # 凡例が指定されている場合は凡例を表示する
        if namelist is not None:
            self.plt.addLegend()

        self.curvenum = num
        self.datalist = [None] * num

        i = 0
        while i < num:
            if namelist is None:
                # 凡例が指定されていなければそのまま
                self.curve.append(
                    self.plt.plot(
                        pen=pg.mkPen((R[i], G[i], B[i]), width=3)))
                # self.curve.append(self.plt.plot(pen=(R[i], G[i], B[i])))
            else:
                # 凡例が指定されている場合、凡例も一緒に指定
                self.curve.append(self.plt.plot(
                    pen=(R[i], G[i], B[i]), name=namelist[i]))

            i += 1

    # グラフを更新する
    def GraphUpdate(self):
        i = 0
        while i < self.curvenum:
            self.curve[i].setData(self.datalist[i])
            i += 1
        vr = self.plt.viewRange()
        if bRecord:
            # White
            self.text.setColor((255,255,255))
        else:
            self.text.setColor((0,255,0))
        self.text.setPos(vr[0][1]*0.95, vr[1][1]*0.95)
        # self.score = vr[0][1]
        prefix = ""
        if self.Mode == dummySensorDecline:
            prefix = "傾き "
        elif self.Mode == dummySensorShock:
            prefix = "衝撃 "
        self.text.setPlainText(f'{prefix}{self.score:.0f}')

    # センサデータの代入
    def setData(self, datalist):
        # データのリストがlistでない場合何もしない
        if not isinstance(datalist, list):
            return

        # あらかじめ指定されたデータ数より少ない場合、何もしない
        if len(datalist) < self.curvenum:
            return

        # 値渡しにて代入する
        i = 0
        while i < self.curvenum:
            self.datalist[i] = datalist[i][:]
            i += 1

    # グラフのタイトルを設定する
    def setTitle(self, title):
        self.plt.setTitle(
            '<font size=\'20\' color=\'#FFFFFF\'>'+title+'</font>')

    # グラフのセンサモードを指定する
    def setmode(self, mode):
        self.Mode = mode

        if self.Mode == 0x10:
            self.setTitle('Analog')
            self.setYRange(0, 2500)
            self.setYLabel('Voltage (mV)')
            labelname = ['ADC1', 'ADC2']
            self.CurveInit(2, labelname)

        elif self.Mode == 0x11:
            self.setTitle('LM61')
            self.setYRange(0, 42)
            self.setYLabel('Temprature (C)')
            self.CurveInit(1)

        elif self.Mode == 0x31:
            self.setTitle('SHT21 - Temprature -')
            self.setYRange(0, 42)
            self.setYLabel('Temprature (C)')
            self.CurveInit(1)

        elif self.Mode == 0x71:
            self.setTitle('SHT21 - Humidity -')
            self.setYRange(0, 100)
            self.setYLabel('Humidity (%)')
            self.CurveInit(1)

        elif self.Mode == 0x32:
            self.setTitle('ADT7410')
            self.setYRange(0, 42)
            self.setYLabel('Temprature (C)')
            self.CurveInit(1)

        elif self.Mode == 0x33:
            self.setTitle('MPL115A2')
            self.setYRange(800, 1200)
            self.setYLabel('Pressure (hPa)')
            self.CurveInit(1)

        elif self.Mode == 0x34:
            self.setTitle('LIS3DH')
            self.setYRange(-1*YRange, YRange)
            self.setYLabel('Accel', 'g')
            labelname = ['X', 'Y', 'Z']
            self.CurveInit(3, labelname)

        elif self.Mode == 0x35:
            self.setTitle('ADXL34x')
            self.setYRange(-1*YRange, YRange)
            self.setYLabel('Accel', 'g')
            labelname = ['X', 'Y', 'Z']
            self.CurveInit(3, labelname)

        elif self.Mode == 0x36:
            self.setTitle('TSL2561')
            self.setYRange(0, 1200)
            self.setYLabel('Lux')
            self.CurveInit(1)

        elif self.Mode == 0x37:
            self.setTitle('L3GD20')
            self.setYRange(-300, 300)
            self.setYLabel('Angular Velocity', 'dps')
            labelname = ['Roll', 'Pitch', 'Yaw']
            self.CurveInit(3, labelname)

        elif self.Mode == 0x38:
            self.setTitle('S11059-02DT')
            self.setYRange(0, 1000)
            self.setYLabel('Power')
            labelname = ['Red', 'Green', 'Blue', 'IR']
            self.CurveInit(4, labelname)

        elif self.Mode == 0x39:
            self.setTitle('BME280 - Temprature - ')
            self.setYRange(0, 42)
            self.setYLabel('Temprature (C)')
            self.CurveInit(1)

        elif self.Mode == 0x72:
            self.setTitle('BME280 - Humidity - ')
            self.setYRange(0, 100)
            self.setYLabel('Temprature (%)')
            self.CurveInit(1)

        elif self.Mode == 0x73:
            self.setTitle('BME280 - Pressure - ')
            self.setYRange(0, 42)
            self.setYLabel('Pressure (hPa)')
            self.CurveInit(1)

        elif self.Mode == 0x00:		# 電源電圧
            self.setTitle('Power Voltage')
            self.setYRange(1950, 3600)
            self.setYLabel('Power (mV)')
            self.CurveInit(1)

        elif self.Mode == 0x01:		# LQI
            self.setTitle('LQI')
            self.setYRange(0, 255)
            self.setYLabel('LQI')
            self.CurveInit(1)

        elif self.Mode == dummySensorDecline:
            self.setTitle('傾き')
            self.setYRange(0, 1.0)
            self.setYLabel('')
            self.CurveInit(1)

        elif self.Mode == dummySensorShock:
            self.setTitle('衝撃')
            self.setYRange(0, YRange)
            self.setYLabel('')
            self.CurveInit(1)


class GraphData():
    def __init__(self, sid, sns, mode=None, num=0):
        self.SID = sid
        self.Sensor = sns
        self.Mode = mode
        self.Data = list()
        self.bUpdate = False

        if num > 0:
            self.InitData(num)
        print(f'{sns:02x}')

    def InitData(self, datanum):
        if datanum <= 0:
            return

        self.Data = [[0 for i in range(SampleNum)] for j in range(datanum)]

    def SetData(self, datalist):
        # print(f'{self.Sensor:02x} {datalist}')
        if len(datalist) != len(self.Data):
            return

        i = 0
        while i < len(self.Data):
            if isinstance(datalist[i], list):
                self.Data[i] += datalist[i]
                if len(self.Data[i]) > SampleNum:
                    self.Data[i][0:] = self.Data[i][len(
                        self.Data[i])-SampleNum:]
            else:
                self.Data[i].append(datalist[i])
                self.Data[i][0:] = self.Data[i][1:]
            i += 1

        self.bUpdate = True

    def SetUpdateFalse(self):
        self.bUpdate = False

    def GetSID(self):
        return self.SID

    def GetSensor(self):
        return self.Sensor

    def GetMode(self):
        return self.Mode

    def GetUpdate(self):
        return self.bUpdate

    def GetData(self):
        return self.Data


def update():
    global SnsData, SnsOrder, graph, Window

    if len(SnsData) > 0:
        if len(graph) == 0:
            i = 0
            __Row = len(SnsData)
            __Row -= 1 if bEnableVolt else 0
            __Row -= 1 if bEnableLQI else 0

            __AnotherSns = 1 if bEnableVolt else 0
            __AnotherSns += 1 if bEnableLQI else 0

            if __Row == 1 and __AnotherSns > __Row:
                __Row = len(SnsData)
                __AnotherSns = 0

            if __Row > 3:
                __wheight = 900
            else:
                __wheight = 300*__Row

            Window.resize(1280 if __AnotherSns else 1024, __wheight)

            while i < __Row:
                graph.append(Graph(SnsData[i].GetSensor()))
                SnsOrder.append(i)
                i += 1

                if __AnotherSns:
                    graph.append(
                        Graph(SnsData[len(SnsData)-__AnotherSns].GetSensor()))
                    SnsOrder.append(len(SnsData)-__AnotherSns)
                    __AnotherSns -= 1

                Window.nextRow()

            Window.setWindowTitle(
                "MONOWIRELESS App_Tag Viewer : " + RcvAddr[1:] + '  - '
                + SnsMode + ' - ')

        i = 0
        while i < len(graph):
            if SnsData[SnsOrder[i]].GetUpdate():
                graph[i].setData(SnsData[SnsOrder[i]].GetData())
                graph[i].GraphUpdate()
                SnsData[SnsOrder[i]].SetUpdateFalse()
            i += 1


def update2():
    global SnsData, SnsOrder, graph, Window, numDecline, numShock, decline_score, shock_score
    # t1 = time.time()
    if len(SnsData) > 0:
        if len(graph) == 0:
            i = 0
            while i < len(SnsData):
                print(f'{i} {SnsData[i].GetSensor():02x}')
                if SnsData[i].GetSensor() == dummySensorDecline:
                    numDecline = i
                elif SnsData[i].GetSensor() == dummySensorShock:
                    numShock = i
                i += 1

            Window.resize(1024, 900)

            graph.append(Graph(dummySensorDecline))
            Window.nextRow()

            graph.append(Graph(dummySensorShock))
            Window.nextRow()

            Window.setWindowTitle("Humanoid Rescue Robot Contest")

        # print(f'{numDecline} {numShock}')
        if SnsData[numDecline].GetUpdate():
            graph[0].setData(SnsData[numDecline].GetData())
            graph[0].score = decline_score = sum_decline / 30  # 要調整
            graph[0].GraphUpdate()
            SnsData[numDecline].SetUpdateFalse()

        if SnsData[numShock].GetUpdate():
            # print(f'{SnsData[numShock].GetData()}')
            graph[1].setData(SnsData[numShock].GetData())
            graph[1].score = shock_score = sum_shock / 30  # 要調整
            graph[1].GraphUpdate()
            SnsData[numShock].SetUpdateFalse()
    # t2 = time.time()
    # print(t2 - t1)

def ParseArgs():
    global options, args

    parser = OptionParser()
    if os.name == 'nt':
        parser.add_option(
            '-t', '--target', type='string',
            help='target for connection', dest='target', default='COM4')
    else:
        parser.add_option(
            '-t', '--target', type='string',
            help='target for connection', dest='target',
            default='/dev/ttyUSB0')

    parser.add_option(
        '-b', '--baud', dest='baud', type='int',
        help='baud rate for serial connection.', metavar='BAUD',
        default=115200)
    parser.add_option(
        '-s', '--serialmode', dest='format', type='string',
        help='serial data format type. (Ascii or Binary)',  default='Ascii')
    parser.add_option(
        '-n', '--num', dest='samplenum',
        type='int', help='plot sample number.',  default=1024)
    parser.add_option(
        '-r', '--range', dest='range',
        type='int', help='Y axis range',  default=2)
    parser.add_option(
        '-a', '--autolog', dest='autolog',
        action='store_true', help='enable auto log.', default=True)
    parser.add_option(
        '-v', '--volt', dest='volt', action='store_true',
        help='plot power voltage.', default=False)
    parser.add_option(
        '-l', '--lqi', dest='lqi',
        action='store_true', help='plot LQI.', default=False)
    parser.add_option(
        '-A', '--adc', dest='adc', action='store_true',
        help='plot ADC1 and ADC2.', default=False)
    parser.add_option(
        '-o', '--output', dest='output', action='store_true',
        help='output arrived data to console.', default=False)
    parser.add_option(
        '-p', '--player', dest='play',
        action='store_true', help='execute log player', default=False)
    parser.add_option(
        '-f', '--fps', dest='fps', type='int',
        help='set update frequency (fps) when log player.',  default=100)
    parser.add_option(
        '-e', '--errormessage', dest='err',
        action='store_true', help='output error message.', default=False)
    (options, args) = parser.parse_args()


def GetSensorName(sensor):
    __PrintStr = 'None'
    __Element = sensor
    if __Element == 0x10:
        __PrintStr = 'Analog'
    elif __Element == 0x11:
        __PrintStr = 'LM61'
    elif __Element == 0x31:
        __PrintStr = 'SHT21'
    elif __Element == 0x32:
        __PrintStr = 'ADT7410'
    elif __Element == 0x33:
        __PrintStr = 'MPL115A2'
    elif __Element == 0x34:
        __PrintStr = 'LIS3DH'
    elif __Element == 0x35:
        __PrintStr = 'ADXL34x'
    elif __Element == 0x36:
        __PrintStr = 'TSL2561'
    elif __Element == 0x37:
        __PrintStr = 'L3GD20'
    elif __Element == 0x38:
        __PrintStr = 'S11059-02DT'
    elif __Element == 0x39:
        __PrintStr = 'BME280'
    elif __Element == 0xD1:
        __PrintStr = 'MultiSensor'
    elif __Element == 0xFE:
        __PrintStr = 'Button'

    return __PrintStr


def ReadSensor(Tag):
    global bRestart, sum_decline, sum_shock
    while True:
        bRestart = False
        sum_decline = 0.0
        sum_shock = 0.0
        print('ReadSensor() initialized')
        while True:
            try:
                if Tag.ReadSensorData():
                    Dic = Tag.GetDataDict()

                    SetData(Dic)

                    if bEnableOutput:
                        Tag.ShowSensorData()
                    if bEnableLog:
                        Tag.OutputData()

                if bRestart:
                    break

                if bExit:
                    break
            except Exception:
                if bEnableErrMsg:
                    import traceback
                    traceback.print_exc()
                else:
                    print("Exception occured.")
                    print("Please retry this script.")

                break
        if not bRestart:
            break


def ReadLog(logdata):
    loglist = list()
    # tmplist = list()
    keylist = list()
    datadict = dict()
    for log in logdata:
        log = str(log)
        log = log.strip()
        log = log.replace('\t', '')
        datalist = log.split(',')
        if datalist[0] == 'ArriveTime':
            keylist = datalist[:]
            continue
        elif datalist[0] == '':
            if isinstance(loglist[len(loglist)-1]['AccelerationX'], list):
                loglist[len(loglist) -
                        1]['AccelerationX'].append(float(datalist[11]))
            else:
                tmpX = loglist[len(loglist)-1]['AccelerationX']
                loglist[len(loglist)-1]['AccelerationX'] = [tmpX,
                                                            float(datalist[11])
                                                            ]

            if isinstance(loglist[len(loglist)-1]['AccelerationY'], list):
                loglist[len(loglist) -
                        1]['AccelerationY'].append(float(datalist[12]))
            else:
                tmpX = loglist[len(loglist)-1]['AccelerationY']
                loglist[len(loglist)-1]['AccelerationY'] = [tmpX,
                                                            float(datalist[12])
                                                            ]

            if isinstance(loglist[len(loglist)-1]['AccelerationZ'], list):
                loglist[len(loglist) -
                        1]['AccelerationZ'].append(float(datalist[13]))
            else:
                tmpX = loglist[len(loglist)-1]['AccelerationZ']
                loglist[len(loglist)-1]['AccelerationZ'] = [tmpX,
                                                            float(datalist[13])
                                                            ]

            continue
        else:
            if len(keylist) == len(datalist):
                datadict.clear()
                i = 0
                for key in keylist:
                    if key == 'Sensor':
                        if datalist[i] == 'Analog':
                            datadict[key] = 0x10
                        elif datalist[i] == 'LM61':
                            datadict[key] = 0x11
                        elif datalist[i] == 'SHT21':
                            datadict[key] = 0x31
                        elif datalist[i] == 'ADT7410':
                            datadict[key] = 0x31
                        elif datalist[i] == 'MPL115A2':
                            datadict[key] = 0x33
                        elif datalist[i] == 'LIS3DH':
                            datadict[key] = 0x34
                        elif datalist[i] == 'ADXL34x':
                            datadict[key] = 0x35
                        elif datalist[i] == 'TSL2561':
                            datadict[key] = 0x36
                        elif datalist[i] == 'L3GD20':
                            datadict[key] = 0x37
                        elif datalist[i] == 'S11059-02DT':
                            datadict[key] = 0x38
                        elif datalist[i] == 'BME280':
                            datadict[key] = 0x39
                        elif datalist[i] == 'MultiSensor':
                            datadict[key] = 0xD1
                    elif key == 'SensorBitmap' or key == 'ADXL34xMode':
                        datadict[key] = int(datalist[i], 16)
                    elif key == 'Mode':
                        if datalist[i] == 'Normal':
                            datadict[key] = 0x00
                        elif datalist[i] == 'Nekotter':
                            datadict[key] = 0xFF
                        elif datalist[i] == 'Low Energy':
                            datadict[key] = 0xFE
                        elif datalist[i] == 'Dice':
                            datadict[key] = 0xFD
                        elif datalist[i] == 'Shake':
                            datadict[key] = 0xFC
                        elif datalist[i] == 'Spin':
                            datadict[key] = 0xFB
                        elif datalist[i] == 'Burst':
                            datadict[key] = 0xFA
                        elif datalist[i] == 'Tap':
                            datadict[key] = 0x01
                        elif datalist[i] == 'DoubleTap':
                            datadict[key] = 0x02
                        elif datalist[i] == 'FreeFall':
                            datadict[key] = 0x04
                        elif datalist[i] == 'Active':
                            datadict[key] = 0x08
                        elif datalist[i] == 'Inactive':
                            datadict[key] = 0x10
                        elif datalist[i] == 'Falling Edge':
                            datadict[key] = 0x00
                        elif datalist[i] == 'Rising Edge':
                            datadict[key] = 0x01
                        elif datalist[i] == 'Falling/Rising Edge':
                            datadict[key] = 0x02
                        elif datalist[i] == 'TWELITE SWING':
                            datadict[key] = 0x04
                    elif key == 'ArriveTime':
                        datadict[key] = datetime.datetime.strptime(
                            (datalist[i]+'000'), '%Y/%m/%d %H:%M:%S.%f')
                    elif key == 'EndDeviceSID' or key == 'RouterSID':
                        if datalist[i] == 'No Relay':
                            datadict[key] = '80000000'
                        else:
                            datadict[key] = '8'+datalist[i]
                    else:
                        datadict[key] = float(datalist[i])
                    i += 1

        loglist.append(copy.deepcopy(datadict))

    i = 0

    while i < len(loglist):
        SetData(loglist[i])

        if i+1 != len(loglist):
            __sleep = 1.0/float(FPS)
            if 'Mode' in loglist[i]:
                if loglist[i]['Mode'] == 0xFA:
                    __sleep *= 10
            elif 'ADXL34xMode' in loglist[i]:
                if loglist[i]['ADXL34xMode'] == 0xFA:
                    __sleep *= 10

            time.sleep(__sleep)

        i += 1

        if bExit:
            break


def SetData(Dic):
    global SnsData, SnsMode, RcvAddr, Window
    global sum_shock, sum_decline, count, decline_score, shock_score
    global output_file_name

    if RcvAddr is None:
        RcvAddr = Dic['EndDeviceSID']
        SnsMode = GetSensorName(Dic['Sensor'])
        if (Dic['Sensor'] == 0x11 or Dic['Sensor'] == 0x32
                or Dic['Sensor'] == 0x33 or Dic['Sensor'] == 0x36):
            SnsData.append(GraphData(RcvAddr, Dic['Sensor'], None, 1))
        elif Dic['Sensor'] == 0x10:
            SnsData.append(GraphData(RcvAddr, Dic['Sensor'], None, 2))
        elif Dic['Sensor'] == 0x34 or Dic['Sensor'] == 0x37:
            SnsData.append(GraphData(RcvAddr, Dic['Sensor'], None, 3))
        elif Dic['Sensor'] == 0x35:
            SnsData.append(GraphData(RcvAddr, Dic['Sensor'], Dic['Mode'], 3))
            SnsData.append(GraphData(RcvAddr, dummySensorDecline, None, 1))
            SnsData.append(GraphData(RcvAddr, dummySensorShock, None, 1))
        elif Dic['Sensor'] == 0x31:
            SnsData.append(GraphData(RcvAddr, Dic['Sensor'], None, 1))
            SnsData.append(GraphData(RcvAddr, 0x71, None, 1))
        elif Dic['Sensor'] == 0x39:
            SnsData.append(GraphData(RcvAddr, Dic['Sensor'], None, 1))
            SnsData.append(GraphData(RcvAddr, 0x72, None, 1))
            SnsData.append(GraphData(RcvAddr, 0x73, None, 1))
        elif Dic['Sensor'] == 0xD1:
            i = 0
            while i < 16:
                if Dic['SensorBitmap'] & (1 << i):
                    if i == 1 or i == 2 or i == 5:
                        SnsData.append(GraphData(RcvAddr, 0x30+i+1, None, 1))
                    elif i == 0:
                        SnsData.append(GraphData(RcvAddr, 0x30+i+1, None, 1))
                        SnsData.append(GraphData(RcvAddr, 0x71, None, 1))
                    elif i == 3 or i == 6:
                        SnsData.append(GraphData(RcvAddr, 0x30+i+1, None, 3))
                    elif i == 4:
                        SnsData.append(
                            GraphData(
                                RcvAddr, 0x30+i+1, Dic['ADXL34xMode'], 3))
                    elif i == 7:
                        SnsData.append(GraphData(RcvAddr, 0x30+i+1, None, 4))
                    elif i == 8:
                        SnsData.append(GraphData(RcvAddr, 0x30+i+1, None, 1))
                        SnsData.append(GraphData(RcvAddr, 0x72, None, 1))
                        SnsData.append(GraphData(RcvAddr, 0x73, None, 1))
                i += 1
        else:
            RcvAddr = None
            return

        if bEnableADC and Dic['Sensor'] != 0x10:
            SnsData.append(GraphData(RcvAddr, 0x10, None, 2))
        if bEnableVolt:
            SnsData.append(GraphData(RcvAddr, 0x00, None, 1))
        if bEnableLQI:
            SnsData.append(GraphData(RcvAddr, 0x01, None, 1))

    elif RcvAddr != Dic['EndDeviceSID']:
        return
    i = 0
    while i < len(SnsData):
        if SnsData[i].GetSensor() == 0x00:
            try:
                if Dic['Mode'] == 0xFA or Dic['ADXL34xMode'] == 0xFA:
                    power = [Dic['Power']]*10
                    SnsData[i].SetData([power])
                else:
                    SnsData[i].SetData([Dic['Power']])
            except Exception:
                SnsData[i].SetData([Dic['Power']])
        elif SnsData[i].GetSensor() == 0x01:
            try:
                if Dic['Mode'] == 0xFA or Dic['ADXL34xMode'] == 0xFA:
                    lqi = [Dic['LQI']]*10
                    SnsData[i].SetData([lqi])
                else:
                    SnsData[i].SetData([Dic['LQI']])
            except Exception:
                SnsData[i].SetData([Dic['LQI']])
        elif SnsData[i].GetSensor() == 0x10:
            try:
                if Dic['Mode'] == 0xFA or Dic['ADXL34xMode'] == 0xFA:
                    adc1 = [Dic['ADC1']]*10
                    adc2 = [Dic['ADC2']]*10
                    SnsData[i].SetData([adc1, adc2])
                else:
                    SnsData[i].SetData([Dic['ADC1'], Dic['ADC2']])
            except Exception:
                SnsData[i].SetData([Dic['ADC1'], Dic['ADC2']])
        elif SnsData[i].GetSensor() == 0x11:
            SnsData[i].SetData([Dic['Temperature']])
        elif SnsData[i].GetSensor() == 0x31:
            SnsData[i].SetData([Dic['Temperature']])
        elif SnsData[i].GetSensor() == 0x32:
            SnsData[i].SetData([Dic['Temperature']])
        elif SnsData[i].GetSensor() == 0x33:
            SnsData[i].SetData([Dic['Pressure']])
        elif SnsData[i].GetSensor() == 0x34 or SnsData[i].GetSensor() == 0x35:
            # here
            acc = [
                Dic['AccelerationX'], Dic['AccelerationY'], Dic['AccelerationZ']]
            SnsData[i].SetData(acc)
            accs = SnsData[i].GetData()
            nrange = 20
            ntotal = len(accs[0])
            npart = len(acc[0])
            declines = []
            shocks = []
            # 移動平均を求める
            for j in range(npart):
                b = max(ntotal - npart - nrange + j + 1, 0)
                e = ntotal - npart + j + 1
                axs = accs[0][b:e]
                ays = accs[1][b:e]
                azs = accs[2][b:e]
                aax = sum(axs)/len(axs)
                aay = sum(ays)/len(ays)
                aaz = sum(azs)/len(azs)
                # print(j, b, e, azs)
                aa = sqrt(aax**2 + aay**2 + aaz**2)
                d = max(-aax/aa, 0.0)
                declines.append(d)
                if bRecord:
                    sum_decline += d
                ax, ay, az = acc[0][j], acc[1][j], acc[2][j]
                sx = ax - aax
                sy = ay - aay
                sz = az - aaz
                # 開始直後のデータを計算に使わない
                if count > nrange:
                    s = sqrt(sx**2 + sy**2 + sz**2)
                else:
                    s = 0
                shocks.append(s)
                # print(j, s)
                # 一定以下の場合は0とする
                if s > 0.1 and bRecord:
                    sum_shock += s
                count += 1
            # ファイルの保存処理
            make_header = False
            if not os.path.exists(f"{output_file_name}.csv"):
                make_header = True
            with open(f"{output_file_name}.csv", "a", newline="") as f:
                csv_writer = csv.writer(f)
                # センサーデータの転置
                data = np.array(acc).T
                # col_size = data.shape[1]
                # 時間の追加
                arrive_time: datetime = Dic["ArriveTime"]
                # arrive_time = arrive_time.isoformat()
                arrive_times = []
                arrive_times.append(arrive_time.isoformat())
                # 時間を0.1秒ごとに補完
                # パケットの数を出力
                # print(len(Dic["AccelerationX"]))
                # for _ in range(len(Dic["AccelerationX"]) - 1):
                #     arrive_time -= timedelta(seconds=0.01)
                #     arrive_times.insert(0, arrive_time.isoformat())
                data = data.astype("str")
                data = np.insert(data, 0, arrive_time, axis=1)
                # 傾きの追加
                data = np.insert(data, data.shape[1], declines, axis=1)
                # 衝撃の追加
                data = np.insert(data, data.shape[1], shocks, axis=1)
                # 傾きの得点の追加
                data = np.insert(data, data.shape[1], decline_score, axis=1)
                # 衝撃の得点の追加
                data = np.insert(data, data.shape[1], shock_score, axis=1)
                # 記録有無の追加
                data = np.insert(
                    data, data.shape[1], 1 if bRecord else 0, axis=1
                )
                # パケット送信順序の追加
                data = np.insert(data, data.shape[1], Dic["SequenceNumber"], axis=1)
                # ヘッダーの追加
                if make_header:
                    header = ["時間", "X軸加速度", "Y軸加速度", "Z軸加速度", "傾き", "衝撃", "傾きのスコア", "衝撃のスコア", "記録フラグ", "パケット送信順序"]
                    data = np.insert(data, 0, header, axis=0)
                csv_writer.writerows(data.tolist())
        elif SnsData[i].GetSensor() == 0x36:
            SnsData[i].SetData([Dic['Illuminance']])
        elif SnsData[i].GetSensor() == 0x37:
            SnsData[i].SetData([Dic['Roll'], Dic['Pitch'], Dic['Yaw']])
        elif SnsData[i].GetSensor() == 0x38:
            SnsData[i].SetData(
                [Dic['Red'], Dic['Green'], Dic['Blue'], Dic['IR']])
        elif SnsData[i].GetSensor() == 0x39:
            SnsData[i].SetData([Dic['Temperature']])
        elif SnsData[i].GetSensor() == 0x71:
            SnsData[i].SetData([Dic['Humidity']])
        elif SnsData[i].GetSensor() == 0x72:
            SnsData[i].SetData([Dic['Humidity']])
        elif SnsData[i].GetSensor() == 0x73:
            SnsData[i].SetData([Dic['Humidity']])
        elif SnsData[i].GetSensor() == dummySensorDecline:
            SnsData[i].SetData([declines])
        elif SnsData[i].GetSensor() == dummySensorShock:
            SnsData[i].SetData([shocks])
        else:
            i += 1
            continue
        i += 1


class KeyPressWindow(pg.GraphicsLayoutWidget):
    sigKeyPress = QtCore.pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def keyPressEvent(self, ev):
        self.scene().keyPressEvent(ev)
        self.sigKeyPress.emit(ev)


def keyPressed(evt):
    global bRestart
    # print(f'{evt.key()=} {evt.text()=}')
    if evt.text() == '\x1b':
        print('Esc key pressed')
        bRestart = True


class ControlWindow(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.is_start = False
        ui_class = uic.loadUiType("form.ui", self)[0]
        self.ui = ui_class()
        # control_window.pushButton.clicked.connect(button_action)
        self.ui.setupUi(self)
        self.ui.startButton.clicked.connect(self.startButtonAction)
        self.ui.stopButton.clicked.connect(self.stopButtonAction)

    # @check_state
    def startButtonAction(self):
        global bRecord, output_file_name, state
        if state == State.stop:
            bRecord = True
            state = State.recording
            self.ui.label.setText("記録中")
            self.ui.label.setStyleSheet("color: red")
            self.ui.startButton.setText("記録中断")
        elif state == State.pause:
            bRecord = True
            state = State.recording
            self.ui.label.setText("記録中")
            self.ui.label.setStyleSheet("color: red")
            self.ui.startButton.setText("記録中断")
        elif state == State.recording:
            bRecord = False
            state = State.pause
            self.ui.label.setText("記録停止中")
            self.ui.label.setStyleSheet("color: green")
            self.ui.startButton.setText("記録再開")

    # @check_state
    def stopButtonAction(self):
        global bRecord, bRestart, output_file_name, state
        if state == State.recording or State.pause:
            output_file_name = make_file_name()
            bRecord = False
            # 積算リセット
            bRestart = True
            state = State.stop
            self.ui.label.setText("記録終了")
            self.ui.label.setStyleSheet("color: green")
            self.ui.startButton.setText("記録開始")
        elif state == State.stop:
            pass


if __name__ == '__main__':
    ParseArgs()

    SampleNum = options.samplenum
    YRange = options.range
    bEnableVolt = options.volt
    bEnableLQI = options.lqi
    bEnableADC = options.adc
    bEnableOutput = options.output
    bEnableLog = options.autolog
    bEnablePlayer = options.play
    bEnableErrMsg = options.err
    FPS = options.fps

    if YRange < 0:
        YRange *= -1

    Window = KeyPressWindow(show=True)
    Window.setWindowTitle("MONOWIRELESS AppTag Viewer")
    Window.resize(1280, 800)
    Window.sigKeyPress.connect(keyPressed)
    pg.setConfigOptions(antialias=True)

    control_window = ControlWindow()
    control_window.show()

    timer = QtCore.QTimer()
    timer.timeout.connect(update2)
    timer.start(10)

    if bEnablePlayer:
        try:
            logfile = open(options.target, 'r')
            logdata = logfile.readlines()
            logfile.close()
        except Exception:
            print("Please assign target file...")
            exit(1)

        subThread = threading.Thread(target=ReadLog, args=(logdata,))
    else:
        try:
            Tag = AppTag(port=options.target, baud=options.baud,
                         tout=0.05, sformat=options.format)
        except Exception:
            exit(1)
        subThread = threading.Thread(target=ReadSensor, args=(Tag,))

    subThread.setDaemon(True)
    subThread.start()

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtWidgets.QApplication.instance().exec_()

    bExit = True
    subThread.join()

    if not bEnablePlayer:
        del Tag
