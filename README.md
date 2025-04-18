# サーバー電源管理Bot
Q.なぁにこれぇ  
A.DiscordのBotにサーバーマシンの電源管理機能を実装する変なのですを

まず初めに書いて置きますが、僕はこの手のプログラムを書くのが初めてなので読みにくかったらもうしわけありません。([尊師リスペクト](https://krsw-wiki.in/wiki/?curid=1367))  
あと色々雑に作ってるので保証はしません OSSだし[仕方ないね♂](https://dic.nicovideo.jp/a/%E4%BB%95%E6%96%B9%E3%81%AA%E3%81%84%E3%81%AD)

## 動作概要
本プログラムはサーバープログラム本体を動かす大きいサーバー(P-Server)と電源管理をする小さいサーバー(E-Server)の2台を必要とします。  
要となる小さいサーバーは最低限の機能だけで良いため、Raspberry Piなどでも稼働します。テストマシンはRaspberry Pi 3Bです。  
双方のサーバーがDiscord上で動作し、スラッシュコマンドによってP-Serverを制御する形になります。  
クラッシュログが生成されたら通知する機能も付いてます。

元々Minecraftの鯖用に書いてますが各種変数とかを触れば一応他に流用は出来ます。

## 必要環境
### 両方に必要
- Linux *(P-ServerはUbuntu 24.04、E-ServerはRaspbbery Pi OS Bullseyeで動作確認済)*
- Python 3.x *(3.11.2で動作確認済)*
- [discord.py](https://discordpy.readthedocs.io/ja/latest/index.html)
### P-Serverに必要
- [pixz](https://github.com/vasi/pixz)
- [watchfile](https://github.com/samuelcolvin/watchfiles)
- Wake on LANに対応したハードウェア
### E-Serverに必要
- [wakeonlan](https://github.com/jpoliv/wakeonlan)

## 使い方
**起動の前に**  
本ソフトウェアはサーバー向けではありますが、サーバーへのアクセスが無い場合に**サーバーマシンをスリープモードにする**という強引に消費電力を削減する目的で作成したためスリープモードが使える環境を用意する必要があります。
### 下準備(Ubuntu)
Debian系なら大体同じになるはずです。RedHat系は知らん
1. Ubuntu Serverを使う場合、デフォルトでスリープモードが無効化されているため、有効化する必要があります。そのため、以下のコマンドを実行してください。
```sh
sudo systemctl unmask sleep.target suspend.target hibernate.target hybrid-sleep.target
```
2. スリープモードに必要な設定をするため、/etc/systemd/sleep.confに以下の記述を加えてください。
```ini
[Sleep]
AllowSuspend=yes
AllowHibernation=yes
AllowHybridSleep=yes
SuspendState=mem
HibernateState=disk
HybridSleepMode=suspend platform shutdown
HybridSleepState=disk
```
*元々ハイブリッドスリープを使う予定でやってたが途中で無理なのに気づいて通常のS3ステートのスリープに切り替えてるのでハイバーネートとかハイブリッドスリープとかは必要無いと思います*

3. Wake on LANの設定をします

ネットワークアダプタ側の設定は
```sh
sudo ethtool <デバイス名> | grep -i wake-on
```
で``Wake-on: d``と表示された場合、以下のコマンドを実行します。
```sh
nmcli c modify "<有線接続名>" 802-3-ethernet.wake-on-lan magic
```
後はUEFI側でWake on LANを有効化してください。物によって設定方法が違うのでこれは省略。全ての設定を終えたら一度再起動。

5. 諸々の前提ソフトを導入

邪魔くさい人向けに一括でセットアップ出来るコマンドを貼っておきます **※無保証**  
P-Server用
```sh
sudo apt update && sudo apt install -y pixz python3.12 watchfile && pip install discord.py
```
E-Server用 *テスト環境がRaspberry Piなのでvenvまで書いてます*
```sh
sudo apt update && sudo apt install -y python3.12 wakeonlan && python -m venv venv && . venv/bin/activate && pip install discord.py
```

6. DiscordのBot環境を構築する
6.1 [Discord Developer Portal](https://discord.com/developers/applications)で開発者として登録する
6.2 Botを作成する 2個に分けて作ったほうが多分安全
6.3 Botのトークンを取得する **一度しか表示されないのでちゃんと控える事**
6.4 OAuth2でapplication.commandとbotにチェック入れてその下のとこでSebd NessagesとUse Slash Commandにチェックを入れた招待URLを作成
6.5 適当な鯖に導入する

7. 環境変数を変更する

本Botは突っ込んだ状態だと一切動かないのでそれぞれのソースコードで必要な箇所を編集します。  
編集が必要な箇所は以下の通り。
|触る変数|書き込む値|触る方|
|----|----|----|
|TOKEN|先程取得したBotのトークン|両方|
|Manage_Channel|Botが書き込むチャンネル|両方|
|process_name|Botに監視させたいプロセス名|P-Server|
|directory|操作対象ディレクトリ|P-Server|
|command|startコマンドで実行するコマンド|P-Server|
|backup|バックアップ先|P-Server|
|port_a、port_b|接続数監視ポート|P-Server|
|host|pingを送る対象のアドレス|E-Server|
|mac|Wake on LANを送るMACアドレス|E-Server|

### 起動方法
ここまで環境を組んだら``python P-Server.py``でP-Serverが、``python E-Server.py``でE-Serverが起動します。  
[ね?簡単でしょう?](https://dic.nicovideo.jp/a/%E3%81%AD%E3%80%81%E7%B0%A1%E5%8D%98%E3%81%A7%E3%81%97%E3%82%87%E3%81%86%3F)

### 操作方法
DiscordのBotは以下のコマンドを受け付けます。
|コマンド名|動作|動く方|
|----|----|----|
|start|環境変数で指定したバックアップ先にワールドデータのバックアップを生成した後にcommandを実行|P-Server|
|status|process_nameで指定したプロセスが生きてるかを確認|P-Server|
|auto-sleep|自動スリープの有効化・無効化|P-Server|
|boot|macで指定したMACアドレスにWake on LANのマジックパケットを送信します|E-Server|
|ping|hostに指定したアドレスにpingを送って死活確認をします|E-Server|
|debug|内部で使ってる変数の中身を吐きます(定期確認で使っている物なのでリアルタイムの物ではありません)|両方|
|exit|botを終了します|両方|

## 内部的な話
本プログラムは1分を単位として処理しています。そのため、各種死活確認と接続数は1分単位で再取得しているため即座に反応する事はありません。*ただしクラッシュログ監視を除く*  
割と実装が雑なんで変な呼び出し方してます。Linux限定なのは10割subprocessで呼び出してる外部コマンドのせいなのでそれだけ対応したらWindowsでも動きます。  
スリープからの復帰はdiscord.pyのon_readyイベントを使ったズボラ実装なので復帰から諸々の処理が入るのは時間がかかります。

## 連絡先
基本無保証ですが何かあったら[Misskey](https://misskey.nukumori-sky.net/@krsw)にでも書いてください。反応したりしなかったりします。

## ライセンス
![GPLv3](https://i.imgur.com/GiBhaDs.png)
