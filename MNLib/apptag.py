#!/usr/bin/env python
# coding: UTF-8

try:
	import serial
except ImportError:
	print( "Cannot inport pyserial..." )
	print( "Please install pyserial. " )
	quit()

import datetime
import os
from collections import OrderedDict

from .appbase import AppBase
from .readSerial import ReadSerial

class AppTag(AppBase):
	# コンストラクタ
	def __init__(self, port=None, baud=115200, tout=0.1 , sformat='Ascii', autolog=False ):
		super(AppTag,self).__init__(port,baud,tout,App='AppTag', smode=sformat)
		self.AutoLog = autolog
		self.InitDict()

	# デストラクタ
	def __del__(self):
		self.SerialClose()
		if self.file != None and self.b_openfile :
			self.FileClose()

	# シリアルデータを読み込んで解釈する
	def ReadSensorData(self):
		self.InitDict()
		self.ByteArr = self.SerialRead()
		if self.ByteArr != None:
			self.ReadDict['ArriveTime'] = datetime.datetime.today()
			self.ReadDict['LogicalID'] = self.ByteArr[11]
			self.ReadDict['EndDeviceSID'] = self.BinList2StrHex(self.ByteArr[7:11])
			self.ReadDict['RouterSID'] = self.BinList2StrHex(self.ByteArr[0:4])
			self.ReadDict['LQI'] = self.ByteArr[4]
			self.ReadDict['SequenceNumber'] = self.BinList2Int(self.ByteArr[5:7])
			self.ReadDict['Power'] = (1950+self.ByteArr[13]*5) if (self.ByteArr[13] <= 170) else (2800+(self.ByteArr[13]-170)*10)
			self.ReadDict['ADC1'] = self.BinList2Int(self.ByteArr[14:16])
			self.ReadDict['ADC2'] = self.BinList2Int(self.ByteArr[16:18])
			self.ReadDict['Sensor'] = self.ByteArr[12]

			# 各々のセンサの値を入れる
			if self.ReadDict['Sensor'] == 0x11:
				self.ReadDict['Temperature'] = (10.0 * self.ReadDict['ADC2'] - 6000.0 + self.BinList2Int(self.ByteArr[18:20]))/100.0

			elif self.ReadDict['Sensor'] == 0x31:
				self.ReadDict['Temperature'] = self.Unsigned2Signed(self.BinList2Int(self.ByteArr[18:20]),2)/100.0
				self.ReadDict['Humidity'] = self.Unsigned2Signed(self.BinList2Int(self.ByteArr[20:22]),2)/100.0

			elif self.ReadDict['Sensor'] == 0x32:
				self.ReadDict['Tempetature'] = self.Unsigned2Signed(self.BinList2Int(self.ByteArr[18:20]),2)/100.0

			elif self.ReadDict['Sensor'] == 0x33:
				self.ReadDict['Pressure'] = self.BinList2Int(self.ByteArr[18:20])

			elif self.ReadDict['Sensor'] == 0x34:
				self.ReadDict['AccelerationX'] = self.Unsigned2Signed(self.BinList2Int(self.ByteArr[18:20]),2)/100.0
				self.ReadDict['AccelerationY'] = self.Unsigned2Signed(self.BinList2Int(self.ByteArr[20:22]),2)/100.0
				self.ReadDict['AccelerationZ'] = self.Unsigned2Signed(self.BinList2Int(self.ByteArr[22:24]),2)/100.0

			elif self.ReadDict['Sensor'] == 0x35:
				self.ReadDict['Mode'] = self.ByteArr[18]
				if self.ReadDict['Mode'] == 0xFA:		# Burst
					__AccelNum = self.ByteArr[19]
					self.ReadDict['AccelerationX'] = []
					self.ReadDict['AccelerationY'] = []
					self.ReadDict['AccelerationZ'] = []
					i = 0
					while i < __AccelNum:
						self.ReadDict['AccelerationX'].append(self.Unsigned2Signed(self.BinList2Int(self.ByteArr[i*6+20:i*6+22]),2)/1000.0)
						self.ReadDict['AccelerationY'].append(self.Unsigned2Signed(self.BinList2Int(self.ByteArr[i*6+22:i*6+24]),2)/1000.0)
						self.ReadDict['AccelerationZ'].append(self.Unsigned2Signed(self.BinList2Int(self.ByteArr[i*6+24:i*6+26]),2)/1000.0)
						i += 1

				elif self.ReadDict['Mode'] == 0xFB:		# Spin
					self.ReadDict['PWM'] = self.BinList2Int(self.ByteArr[19:21])
					self.ReadDict['Degree'] = self.BinList2Int(self.ByteArr[21:23])/10.0

				else:
					self.ReadDict['AccelerationX'] = self.Unsigned2Signed(self.BinList2Int(self.ByteArr[19:21]),2)/100.0
					self.ReadDict['AccelerationY'] = self.Unsigned2Signed(self.BinList2Int(self.ByteArr[21:23]),2)/100.0
					self.ReadDict['AccelerationZ'] = self.Unsigned2Signed(self.BinList2Int(self.ByteArr[23:25]),2)/100.0

			elif self.ReadDict['Sensor'] == 0x36:
				self.ReadDict['Illuminance'] = self.BinList2Int(self.ByteArr[18:22])

			elif self.ReadDict['Sensor'] == 0x37:
				self.ReadDict['Roll'] = self.Unsigned2Signed(self.BinList2Int(self.ByteArr[18:20]),2)
				self.ReadDict['Pitch'] = self.Unsigned2Signed(self.BinList2Int(self.ByteArr[20:22]),2)
				self.ReadDict['Yaw'] = self.Unsigned2Signed(self.BinList2Int(self.ByteArr[22:24]),2)

			elif self.ReadDict['Sensor'] == 0x38:
				self.ReadDict['Red'] = self.BinList2Int(self.ByteArr[18:20])
				self.ReadDict['Green'] = self.BinList2Int(self.ByteArr[20:22])
				self.ReadDict['Blue'] = self.BinList2Int(self.ByteArr[22:24])
				self.ReadDict['IR'] = self.BinList2Int(self.ByteArr[24:26])

			elif self.ReadDict['Sensor'] == 0x39:
				self.ReadDict['Temperature'] = self.Unsigned2Signed(self.BinList2Int(self.ByteArr[18:20]),2)/100.0
				self.ReadDict['Humidity'] = self.Unsigned2Signed(self.BinList2Int(self.ByteArr[20:22]),2)/100.0
				self.ReadDict['Pressure'] = self.BinList2Int(self.ByteArr[22:24])

			elif self.ReadDict['Sensor'] == 0xD1:
				__SensorNum = self.ByteArr[18]
				i = 0
				__SnsData = self.ByteArr[19:]
				self.ReadDict['SensorBitmap'] = 0

				while i < __SensorNum:
					__nextSns = __SnsData[0]

					if __nextSns == 0x31:
						self.ReadDict['SensorBitmap'] |= 0x0001
						self.ReadDict['Temperature'] = self.Unsigned2Signed(self.BinList2Int(__SnsData[1:3]),2)/100.0
						self.ReadDict['Humidity'] = self.Unsigned2Signed(self.BinList2Int(__SnsData[3:5]),2)/100.0
						__Increment = 5

					elif __nextSns == 0x32:
						self.ReadDict['SensorBitmap'] |= 0x0002
						self.ReadDict['Temperature'] = self.Unsigned2Signed(self.BinList2Int(__SnsData[1:3]),2)/100.0
						__Increment = 3

					elif __nextSns == 0x33:
						self.ReadDict['SensorBitmap'] |= 0x0004
						self.ReadDict['Pressure'] = self.BinList2Int(__SnsData[1:3])
						__Increment = 3

					elif __nextSns == 0x34:
						self.ReadDict['SensorBitmap'] |= 0x0008
						self.ReadDict['AccelerationX'] = self.Unsigned2Signed(self.BinList2Int(__SnsData[1:3]),2)/100.0
						self.ReadDict['AccelerationY'] = self.Unsigned2Signed(self.BinList2Int(__SnsData[3:5]),2)/100.0
						self.ReadDict['AccelerationZ'] = self.Unsigned2Signed(self.BinList2Int(__SnsData[5:7]),2)/100.0
						__Increment = 7

					elif __nextSns == 0x35:
						self.ReadDict['SensorBitmap'] |= 0x0010
						self.ReadDict['ADXL34xMode'] = __SnsData[1]
						self.ReadDict['AccelerationX'] = self.Unsigned2Signed(self.BinList2Int(__SnsData[2:4]),2)/100.0
						self.ReadDict['AccelerationY'] = self.Unsigned2Signed(self.BinList2Int(__SnsData[4:6]),2)/100.0
						self.ReadDict['AccelerationZ'] = self.Unsigned2Signed(self.BinList2Int(__SnsData[6:8]),2)/100.0
						__Increment = 8

					elif __nextSns == 0x36:
						self.ReadDict['SensorBitmap'] |= 0x0020
						self.ReadDict['Illuminance'] = self.BinList2Int(__SnsData[1:5])
						__Increment = 5

					elif __nextSns == 0x37:
						self.ReadDict['SensorBitmap'] |= 0x0040
						self.ReadDict['Roll'] = self.Unsigned2Signed(self.BinList2Int(__SnsData[1:3]),2)
						self.ReadDict['Pitch'] = self.Unsigned2Signed(self.BinList2Int(__SnsData[3:5]),2)
						self.ReadDict['Yaw'] = self.Unsigned2Signed(self.BinList2Int(__SnsData[5:7]),2)
						__Increment = 7

					elif __nextSns == 0x38:
						self.ReadDict['SensorBitmap'] |= 0x0080
						self.ReadDict['Red'] = self.BinList2Int(__SnsData[1:3])
						self.ReadDict['Green'] = self.BinList2Int(__SnsData[3:5])
						self.ReadDict['Blue'] = self.BinList2Int(__SnsData[5:7])
						self.ReadDict['IR'] = self.BinList2Int(__SnsData[7:9])
						__Increment = 9

					elif __nextSns == 0x39:
						self.ReadDict['SensorBitmap'] |= 0x0100
						self.ReadDict['Temperature'] = self.Unsigned2Signed(self.BinList2Int(__SnsData[1:3]),2)/100.0
						self.ReadDict['Humidity'] = self.Unsigned2Signed(self.BinList2Int(__SnsData[3:5]),2)/100.0
						self.ReadDict['Pressure'] = self.BinList2Int(__SnsData[5:7])
						__Increment = 7

					__SnsData = __SnsData[__Increment:]
					i+=1

			elif self.ReadDict['Sensor'] == 0xFE:
				self.ReadDict['Mode'] = self.ByteArr[18]
				self.ReadDict['EndDeviceDI'] = self.ByteArr[19]
				self.ReadDict['ParentDO'] = self.ByteArr[20]
			else:
				return False

			if self.AutoLog:
				self.OutputData()

			return True
		else:
			return False

	def GetSensorName(self):
		__PrintStr = 'None'
		__Element = self.ReadDict['Sensor']
		if __Element == 0x10: __PrintStr = 'Analog'
		elif __Element == 0x11: __PrintStr = 'LM61'
		elif __Element == 0x31: __PrintStr = 'SHT21'
		elif __Element == 0x32: __PrintStr = 'ADT7410'
		elif __Element == 0x33: __PrintStr = 'MPL115A2'
		elif __Element == 0x34: __PrintStr = 'LIS3DH'
		elif __Element == 0x35: __PrintStr = 'ADXL34x'
		elif __Element == 0x36: __PrintStr = 'TSL2561'
		elif __Element == 0x37: __PrintStr = 'L3GD20'
		elif __Element == 0x38: __PrintStr = 'S11059-02DT'
		elif __Element == 0x39: __PrintStr = 'BME280'
		elif __Element == 0xD1: __PrintStr = 'MultiSensor'
		elif __Element == 0xFE: __PrintStr = 'Button'

		return __PrintStr

	def GetModeName(self, sensor, mode):
		__ReturnVal = ''
		# ADXL34xの場合
		if sensor == 0x35:
			if mode == 0x00: __ReturnVal = 'Normal'
			elif mode == 0xFF: __ReturnVal = 'Nekotter'
			elif mode == 0xFE: __ReturnVal = 'Low Energy'
			elif mode == 0xFD: __ReturnVal = 'Dice'
			elif mode == 0xFC: __ReturnVal = 'Shake'
			elif mode == 0xFB: __ReturnVal = 'Spin'
			elif mode == 0xFA: __ReturnVal = 'Burst'
			elif mode <= 0x1F:
				if mode&0x01: __ReturnVal += 'Tap '
				if mode&0x02: __ReturnVal += 'DoubleTap '
				if mode&0x04: __ReturnVal += 'FreeFall '
				if mode&0x08: __ReturnVal += 'Active '
				if mode&0x10: __ReturnVal += 'Inactive'
		# 押しボタンの場合
		elif sensor == 0xFE:
			if mode == 0x00: __ReturnVal = 'Falling Edge'
			elif mode == 0x01: __ReturnVal = 'Rising Edge'
			elif mode == 0x02: __ReturnVal = 'Falling/Rising Edge'
			elif mode == 0x04: __ReturnVal = 'TWELITE SWING'

		return __ReturnVal

	# 自動ログ機能を有効にする
	def EnableAutoLog(self):
		self.AutoLog = True

	# 自動ログ機能を無効にする
	def DisableAutoLog(self):
		self.AutoLog = False

	# ログを書き込むファイルを開く
	def FileOpen(self):
		self.b_openfile = True
		__date = datetime.datetime.today()
		__ModuleSID = self.ReadDict['EndDeviceSID'][1:len(self.ReadDict['EndDeviceSID'])]
		__SensorName = self.GetSensorName()
		if __SensorName == 'ADXL34x':
			if self.ReadDict['Mode'] == 0xFB:
				__SensorName += '-Spin'

		__FileName = self.AppName + '_'+ __ModuleSID + '_' + __SensorName + '_%04d%02d%02d' % (__date.year, __date.month, __date.day)
		__ext = '.csv'
		__FileName += __ext

		if os.path.exists(__FileName):
			self.file = open(__FileName,'a')
		else:
			self.file = open(__FileName,'w')
			self.OutputList( self.ReadDict.keys() )

	def OutputData(self):
		self.FileOpen()
		self.OutputList(self.CreateOutputList())
		if self.ReadDict['Sensor'] == 0x35:
			if self.ReadDict['Mode'] == 0xFA:
				i = 1
				__AccelList = ['']*len(self.ReadDict)
				while i < len(self.ReadDict['AccelerationX']):
					__AccelList[len(__AccelList)-3] =  self.ReadDict['AccelerationX'][i]
					__AccelList[len(__AccelList)-2] =  self.ReadDict['AccelerationY'][i]
					__AccelList[len(__AccelList)-1] =  self.ReadDict['AccelerationZ'][i]
					self.OutputList(__AccelList)
					i += 1

		self.FileClose()

	def CreateOutputList(self):
		Outlist = list()

		# 辞書のキーを取得する
		__KeyList = self.ReadDict.keys()

		# キーごとに出力を変える
		for keys in __KeyList:
			# 出力する文字列を入れる変数の初期化
			__OutStr = ''
			# 要素を入れる
			__Element = self.ReadDict[keys]

			# 到来時間
			if keys == 'ArriveTime':
				__OutStr = '\t%04d/%02d/%02d %02d:%02d:%02d.%03d' % ( __Element.year,
																	  __Element.month,
																	  __Element.day,
																	  __Element.hour,
																	  __Element.minute,
																	  __Element.second,
																	  __Element.microsecond/1000)

			# SID
			elif keys.find('SID') >= 0:
				# 要素の中身が0x80000000の場合、中継していないのでその旨を出力する
				if __Element == '80000000':
					__OutStr = '\tNo Relay'
				# 最上位ビットが不要なため消す
				else:
					__OutStr = '\t' + __Element[1:len(self.ReadDict[keys])]

			# センサー
			elif keys == 'Sensor':
				__OutStr = '\t' + self.GetSensorName()

			elif keys == 'SensorBitmap':
				__OutStr = '\t%04X' % __Element

			# センサごとのモード
			elif keys == 'Mode':
				__OutStr = self.GetModeName(self.ReadDict['Sensor'], __Element )

			# 加速度
			elif keys.find('Acceleration') >= 0:
				if isinstance( __Element, list ):
					__OutStr = __Element[0]
				else:
					__OutStr = __Element

			else:
				__OutStr = __Element

			Outlist.append(__OutStr)

		return Outlist

	# 辞書の中のデータを標準出力する
	def ShowSensorData(self):
		# 辞書のキーを取得する
		__KeyList = self.ReadDict.keys()

		# コンソールをクリアする
		#print( '%c[2J%c[H' % (27, 27) )
		if os.name == 'nt':
			os.system('cls')
		elif os.name == 'posix':
			os.system('clear')

		# キーごとに出力を変える
		for keys in __KeyList:
			# 出力する文字列を入れる変数の初期化
			__PrintStr = ''
			# 要素を入れる
			__Element = self.ReadDict[keys]

			# 到来時間
			if keys == 'ArriveTime':
				__PrintStr = '%04d/%02d/%02d %02d:%02d:%02d.%03d' % ( __Element.year,
																	  __Element.month,
																	  __Element.day,
																	  __Element.hour,
																	  __Element.minute,
																	  __Element.second,
																	  __Element.microsecond/1000)

			# SID
			elif keys.find('SID') >= 0:
				# 要素の中身が0x80000000の場合、中継していないのでその旨を出力する
				if __Element == '80000000':
					__PrintStr = 'No Relay'
				# 最上位ビットが不要なため消す
				else:
					__PrintStr = __Element[1:len(self.ReadDict[keys])]

			# LQI
			elif keys == 'LQI':
				__dbm = (7.0 * __Element - 1970.0) / 20.0
				__PrintStr = str(__Element) + ' (%.02f [dBm])' % __dbm

			# センサー
			elif keys == 'Sensor':
				__PrintStr = self.GetSensorName()

			# センサー
			elif keys == 'SensorBitmap':
				__PrintStr = '0x%04X' % __Element

			# 電源電圧 or ADC
			elif keys == 'Power' or keys.find('ADC') >= 0:
				__PrintStr = str(__Element) + ' [mV]'

			# 温度
			elif keys == 'Temperature':
				__PrintStr = '%.02f' % __Element + ' [°C]'

			# 湿度
			elif keys == 'Humidity':
				__PrintStr = '%.02f' % __Element + ' [%]'

			# 気圧
			elif keys == 'Pressure':
				__PrintStr = str(__Element) + ' [hPa]'

			# 加速度
			elif keys.find('Acceleration') >= 0:
				if isinstance( __Element, list ):
					for data in __Element:
						__PrintStr += '%.03f\t' % data
				else:
					__PrintStr = '%.03f' % __Element + ' [g]'

			# 角度
			elif keys == 'Degree':
				__PrintStr = str(__Element) + ' [°]'

			# ジャイロの角速度
			elif keys == 'Roll' or keys == 'Pitch' or keys == 'Yaw':
				__PrintStr = str(__Element) + ' [dps]'

			# 照度
			elif keys == 'Illuminance':
				__PrintStr = str(__Element) + ' [lux]'

			# センサごとのモード
			elif keys == 'Mode':
				__PrintStr = self.GetModeName(self.ReadDict['Sensor'], __Element )

			# 出力用の文字列に中身が入っている場合はそちらを出力する
			if __PrintStr != '':
				print( keys + ' : ' + __PrintStr )
			# 出力用の文字列に何も入っていない場合はそのまま出力する
			else:
				print( keys + ' : ' + str(__Element) )

# 実装実験用Main関数
if __name__ == '__main__':
	Tag = AppTag(port='COM5', sformat='Ascii', autolog=True)

	try:
		while True:
			if Tag.ReadSensorData():
				Tag.ShowSensorData()
				#Tag.OutputData()

	except KeyboardInterrupt:
		del Tag
