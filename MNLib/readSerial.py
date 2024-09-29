#!/usr/bin/python
# coding: UTF-8

try:
	import serial
except ImportError:
	print( "Cannot inport pyserial..." )
	print( "Please install pyserial. " )
	quit()

from .parseFmt_Ascii import FmtAscii
from .parseFmt_Binary import FmtBinary

# シリアル読み込みを行うクラス

class ReadSerial:
	def __init__( self, ser=None, mode='Ascii' ):
		self.reinit(ser, mode)

	def reinit(self, ser, mode):
		self.ser = ser
		self.mode = mode
		self.bDataArrived = False

		if self.ser == None:
			return

		self.Fmt = None
		if self.mode == 'Ascii':
			self.Fmt = FmtAscii()
		elif self.mode == 'Binary':
			self.Fmt = FmtBinary()
		else:
			return

	def GetPayload(self):
		if self.ser != None and self.Fmt != None :
			return self.Fmt.get_payload()
		else:
			return None

	def ReadSerialLine(self):
		self.bDataArrived = False
		if self.mode == 'Ascii':
			self.msg = self.ser.readline().rstrip()
			if(len(self.msg) > 0):
				self.Fmt.process(self.msg)
				if self.Fmt.is_comp():
					self.bDataArrived = True
			else:
				self.bDataArrived = False

		elif self.mode == 'Binary':
			if self.ser.inWaiting() > 0:
				while True:
					self.c = ord(self.ser.read(1))
					self.Fmt.process(self.c)
					if self.Fmt.is_comp():
						break
				if self.Fmt.is_comp():
					self.bDataArrived = True
				else:
					self.bDataArrived = False
					self.Fmt.terminate()
			else:
				self.bDataArrived = False
		else:
			return 0

		return 1

	def IsDataArrived(self):
		return self.bDataArrived

	def GetMode(self):
		return self.mode

	def GetCheckSum(self):
		return self.Fmt.get_checksum()

# テスト用コード
if __name__=='__main__':
	ser = serial.Serial( "/dev/ttyUSB0", 115200, timeout=0.1  )
	fmt = ReadSerial( ser, 'Binary' )

	i = 0
	try:
		while True:
			fmt.ReadSerialLine()
			if fmt.IsDataArrived():
				msg = fmt.GetPayload()
				print(msg)
	except KeyboardInterrupt:
		ser.close()
