# coding: UTF-8

from parseFmt import FmtBase

class FmtAscii(FmtBase):
    def __init__(self):
        self.reinit()

    def reinit(self):
        FmtBase.reinit(self)
        self.check_read = 0
        self.check_calc = 0

    def process(self, c):
        self.reinit()                   # 変数の初期化
        bStr = isinstance(c,str)

        # 最初の文字が:であることを確認
        bCom = False
        if bStr:
            if c[0] == ':':
                bCom = True
                s = c
        else:
            if c[0] == 58:
                bCom = True
                s = c.decode('ascii')    # 文字列に変換
                s = s.replace('\0','')

        if bCom:
            i = 0
            # listに変換
            while i < (len(s)-3)/2:
                self.payload.append(int(s[2*i+1: 2*i+3], 16))
                i += 1

            self.check_read = int(c[(len(c)-2):], 16)   # チェックサム
            self.calc_check()               # チェックサムの計算
            if self.check_calc == self.check_read:
                self.checksum = self.check_read
                self.len = len( self.payload )
                self.b_complete = True

    def calc_check(self):
        self.check_calc = 0
        for x in self.payload:
            self.check_calc = 0xFF&( self.check_calc+x )

        self.check_calc = 0x0100 - self.check_calc
