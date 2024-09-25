# coding: UTF-8

from parseFmt import FmtBase

# 特別な書式ではないが、1行を読み取る
class FmtLine(FmtBase):
    def __init__(self):
        self.reinit()
        
        # 状態と呼び出すべき関数のテーブル
        self.key_dict = {
            'e' : self.s_empty,
            'p' : self.s_payload,
        }

    def s_empty(self, c):
        if not(c == 0x0d or c == 0x0a):
            self.reinit()
            self.state = 'p'
            self.b_complete = False
    
    def s_payload(self, c):
        if c == 0x0d or c == 0x0a:
            self.b_complete = True
            self.state = 'e'
        else:
            self.len_read = self.len_read + 1
            self.payload.append(c)
