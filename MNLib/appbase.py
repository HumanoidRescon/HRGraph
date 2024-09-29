#!/usr/bin/env python
#encoding=utf-8

try:
	import serial
except ImportError:
	print( "Cannot inport pyserial..." )
	print( "Please install pyserial. " )
	quit()

import datetime
import os
from collections import OrderedDict

from .readSerial import ReadSerial

#
# アプリごとに使用するであろう共通機能をまとめた基底クラス
# このクラスを直接インスタンス化するのは非推奨
#

class AppBase(object):
	# コンストラクタ
	def __init__( self, port=None, baud=115200, timeout=0.1, parity=serial.PARITY_NONE, stop=1, byte=8, rtscts=0, dsrdtr=0, App=None, smode='Ascii'):
		self.reinit( port, baud, timeout, parity, stop, byte, rtscts, dsrdtr, App, smode )

	# 各変数の初期化
	def reinit( self, port=None, baud=115200, timeout=0.1, parity=serial.PARITY_NONE, stop=1, byte=8, rtscts=0, dsrdtr=0, App=None, smode='Ascii' ):
		self.port = port
		self.baud = baud
		self.timeout = timeout
		self.parity = parity
		self.stopbits = stop
		self.bytesize = byte
		self.rtscts = rtscts
		self.dsrdtr = dsrdtr

		self.AppName = App
		self.SerialMode = smode

		self.ser = None
		self.b_arrived = False
		self.arrive_time = None
		self.file = None
		self.b_openfile = False
		self.ReadDict = None
		self.ReadData = None

		if self.port != None and self.ser == None :
			if self.SerialOpen():
				self.ReadData = ReadSerial(self.ser, self.SerialMode )
			else:
				__ErrStr = "Cannot open " + self.port + "..."
				print( __ErrStr )
				print( "Please close the software using " + self.port + "." )
				quit()
		else:
			print( "Serial port is not specified..." )
			quit()

	# シリアルポートを開く
	def SerialOpen(self):
		if self.port != None:
			try:
				self.ser = serial.Serial(
							self.port,
							self.baud,
							timeout = self.timeout,
							parity = self.parity,
							stopbits = self.stopbits,
							bytesize = self.bytesize,
							rtscts = self.rtscts,
							dsrdtr = self.dsrdtr
						)
				return True
			except:
				return False
		else:
			return False

	# シリアルポートを閉じる
	def SerialClose(self):
		if self.ser != None:
			self.ser.close()

	# シリアルデータを読み込む
	def SerialRead(self):
		self.ReadData.ReadSerialLine()
		if self.ReadData.IsDataArrived():
			return self.ReadData.GetPayload()
		else:
			return None

	def SerialWrite(self, Cmd):
		if self.ser != None:
			self.ser.write(Cmd)

	# このメソッドを呼んだ日付のファイル名を開く
	def FileOpen(self):
		self.b_openfile = True
		__date = datetime.datetime.today()

		if self.AppName == None:
			__strtime = __date.strftime('%4Y%02m%02d')
		else:
			__strtime = self.AppName + '_%04d%02d%02d' % (__date.year, __date.month, __date.day)

		__ext = '.csv'
		__filename = __strtime+__ext

		if os.path.exists(__filename):
			self.file = open(__filename,'a')
		else:
			self.file = open(__filename,'w')
			self.OutputList( self.ReadDict.keys() )

	def FileClose(self):
		if self.file != None:
			self.b_openfile = False
			self.file.close()

	def GetDataDict(self):
		return self.ReadDict

	def OutputList(self, outlist):
		if self.file != None and self.b_openfile:
			__Len = len(outlist)
			i = 0
			for x in outlist:
				self.file.write(str(x))
				i += 1
				if i != __Len:
					self.file.write(',')
			if os.name == 'nt':
				self.file.write('\n')
			else:
				self.file.write('\r\n')

	# 辞書の初期化
	def InitDict(self):
		if self.ReadDict == None:
			self.ReadDict = OrderedDict()
		else:
			self.ReadDict.clear()

	def OutputData(self, outlist):
		self.FileOpen()
		self.OutputList(outlist)
		self.FileClose()

	def BinList2Int(self, lst):
		num = len(lst)
		val = 0
		if num > 0:
			for x in lst:
				val += (x<<(8*(num-1)))
				num -= 1

		return val

	def BinList2StrHex(self, lst):
		sHex = ''
		for x in lst:
			sHex += '%02X' % x

		return sHex

	def __Unsigned2Signed64(self, val):
		return -(val&0x8000000000000000)|(val&0x7FFFFFFFFFFFFFFF)

	def __Unsigned2Signed32(self, val):
		return -(val&0x80000000)|(val&0x7FFFFFFF)

	def __Unsigned2Signed16(self, val):
		return -(val&0x8000)|(val&0x7FFF)

	def __Unsigned2Signed8(self, val):
		return -(val&0x80)|(val&0x7F)

	def Unsigned2Signed(self,val,bytenum=0):
		if bytenum == 0:
			if val > 0xFFFFFFFFFFFFFFFF: return None
			elif val > 0xFFFFFFFF: return self.__Unsigned2Signed64(val)
			elif val > 0xFFFF: return self.__Unsigned2Signed32(val)
			elif val > 0xFF: return self.__Unsigned2Signed16(val)
			else: return self.__Unsigned2Signed8(val)
		else:
			if bytenum == 1: return self.__Unsigned2Signed8(val)
			elif bytenum == 2: return self.__Unsigned2Signed16(val)
			elif bytenum <= 4: return self.__Unsigned2Signed32(val)
			elif bytenum <= 8: return self.__Unsigned2Signed64(val)
			else : return None
