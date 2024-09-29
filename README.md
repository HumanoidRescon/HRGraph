# HRGraph - ヒト型レスコンのセンサポイント用スクリプト

ヒト型レスキューロボットコンテスト実行委員会  
升谷 保博  
協力者  
信岡 直宏  
2024年9月30日  

## 概要

- 2023年11月5日に行われた「ヒト型レスキューロボットコンテスト2023」において，要救助者人形に内蔵された無線式の加速度センサのデータを受信し，衝撃と傾きを計算し，そのグラフと積算値を画面に表示するために利用したPythonのスクリプトである．その積算値からコンテストで使うセンサポイントが決まる．
- 無線式の加速度センサとして，[モノワイヤレス株式会社](https://mono-wireless.com/)の[TWILITE CUE](https://mono-wireless.com/jp/products/twelite-cue/index.html)を使っている．
- モノワイヤレス株式会社が公開している[グラフ描画スクリプト](https://mono-wireless.com/jp/products/TWE-Lite-2525A/howtouse-graph.html) Graphを基にしたものである．
- Graphは汎用的なスクリプトとして作られているが，それを半ば強引にヒト型レスコンに特化したスクリプトにしている．
- Windows PCで動作する（他のOSでは未検証）．
- [モノワイヤレスソフトウェア使用許諾契約書](MW-SLA-1J.txt)を添付して公開する．

## インストール

- Pythonをインストールする．
- 必要なパッケージをインストール．
  ```
  pip install pyserial
  pip install pyqt5
  pip install pyqtgraph
  ```
- [HRGraph](https://github.com/HumanoidRescon/HRGraph)の一式を入手する．

## 使い方

- TWILITE CUEに電池を入れ，MONOSTICKをPCのUSBポートに接続する． 
- デバイスマネージャを開き，ポート（COMとLPT）の中からMONOSTICKが利用しているUSB Serial Portの名前（例えば，COM7）を見つけ，それで`start.bat`の中の`-t`の後の内容を書き替える（例えば，COM4 → COM7）．
- `start.bat`をダブルクリックする．
- 「記録開始」のボタンをクリックすると，積算値が0にリセットされ，記録が開始される．
- 記録中に「記録中断」をクリックすると，記録を一時停止する．
- 停止中に「記録再開」をクリックすると，記録を再開する．
- 「記録停止」をクリックすると，記録が終了し，ログファイル（CSVファイル）が出力される．

## 実装の説明

- 後日追記予定
