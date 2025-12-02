![GitHub License](https://img.shields.io/github/license/Leafeon2020/Server-Automatic-Power-Management-Tool)
# サーバー電源管理Bot
DiscordのBotにサーバーマシンの電源管理をさせる自作Bot

まず初めに書いて置きますが、僕はこの手のプログラムを書くのが初めてなので読みにくかったらもうしわけありません。([尊師リスペクト](https://krsw-wiki.in/wiki/?curid=1367))  

## 動作概要
### 超概略
このDiscordのBotは以下の機能を提供します。
- 接続無しの場合に自動スリープする
- DiscordのBot経由でサーバーマシンを起動する
- クラッシュログの自動出力(MOD環境向け)
- 統合版サーバーの自動アップデート
- DiscordのBot経由でMinecraftサーバーの起動(JE・BE両対応)
- サーバー起動時の自動バックアップ機能
- Discordからの強制バックアップ機能

### 普通の概略
本プログラムはサーバープログラム本体を動かす大きいサーバー(P-Server)と電源管理をする小さいサーバー(E-Server)の2台を必要とします。  
要となる小さいサーバーは最低限の機能だけで良いため、Raspberry Piなどでも稼働します。テストマシンはRaspberry Pi 3Bです。  
双方のサーバーがDiscord上で動作し、スラッシュコマンドによってP-Serverを制御する形になります。  
クラッシュログが生成されたら通知する機能も付いてます。

元々Minecraftのサーバー用に書いてますが各種変数とかを触れば一応他に流用は出来ます。

## 更新履歴
各ファイルに記載してあります。性質上修正が必要になるのはほぼほぼP-ServerになるためE-Serverはあまり更新が無いと思います。

## 必要環境
### 両方に必要
- Linux *(P-ServerはUbuntu 24.04、E-ServerはRaspbbery Pi OS Bullseyeで動作確認済)*
- Python 3.x *(3.11.2で動作確認済)*
- [discord.py](https://github.com/Rapptz/discord.py)
### P-Serverに必要
- [pixz](https://github.com/vasi/pixz)
- [watchfile](https://github.com/samuelcolvin/watchfiles)
- [MCStatus](https://github.com/py-mine/mcstatus)
- [Requests](https://github.com/psf/requests)
- [Selenium](https://www.selenium.dev/ja/)
- [Firefox](https://www.firefox.com/ja/)
- [geckodriver](https://github.com/mozilla/geckodriver)
- 各種デスクトップ環境(デフォルトでは[MATE](https://mate-desktop.org/ja/)の記述になっています)
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
*元々ハイブリッドスリープ([S4ステート](https://learn.microsoft.com/ja-jp/windows-hardware/drivers/kernel/system-sleeping-states#system-power-state-s4))を使う予定でやっていましたが、途中で無理なのに気づいて通常の[S3ステート](https://learn.microsoft.com/ja-jp/windows-hardware/drivers/kernel/system-sleeping-states#system-power-state-s3)のスリープに切り替えてるのでハイバーネートとかハイブリッドスリープとかは必要無いと思います。*

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
Python、watchfile、pixz、discord.py、MCStatus、requests、Seleniumを導入します。  
邪魔くさい人向けに一括でセットアップ出来るコマンドを貼っておきます **※無保証**

P-Server用
```sh
sudo apt update && sudo apt install -y pixz python3.12 watchfile && sudo snap insatll firefox geckodriver && pip install -U pip && pip install discord.py mcstatus requests selenium
```
E-Server用 *テスト環境がRaspberry Piなのでvenvまで書いてます*
```sh
sudo apt update && sudo apt install -y python3.12 wakeonlan && python -m venv venv && . venv/bin/activate && pip install -U pip && pip install discord.py
```

6. DiscordのBot環境を構築する
    1. [Discord Developer Portal](https://discord.com/developers/applications)で開発者として登録する
    2. Botを作成する 2個に分けて作ったほうが多分安全
    3. Botのトークンを取得する **一度しか表示されないのでちゃんと控える事**
    4. OAuth2でapplication.commandとbotにチェック入れてその下のSebd NessagesとUse Slash Commandにチェックを入れた招待URLを作成
    5. 適当な鯖に導入する

7. 環境変数を変更する

本Botは突っ込んだ状態だと一切動かないのでそれぞれのソースコードで必要な箇所を編集します。  
編集が必要な箇所は以下の通り。
|触る変数|書き込む値|触る方|
|----|----|----|
|TOKEN|先程取得したBotのトークン|両方|
|Manage_Channel|Botが書き込むチャンネル|両方|
|process_name|Botに監視させたいプロセス名(JE)|P-Server|
|process_name_be|Botに監視させたいプロセス名(BE)|P-Server|
|directory|操作対象ディレクトリ(JE)|P-Server|
|directory_be|操作対象ディレクトリ(BE)|P-Server|
|command|startコマンドで実行するコマンド(JE) ※管理目的でGUI環境の端末を呼び出してますがCLIで起動も可|P-Server|
|be_start|startコマンドで実行するコマンド(BE版)|P-Server|
|backup|バックアップ先(JE)|P-Server|
|backup_be|バックアップ先(BE)|P-Server|
|port_a、port_b、port_c、port_d|接続数監視ポート|P-Server|
|cloud|最新のバックアップを保存する場所|P-Server|
|host|pingを送る対象のアドレス|E-Server|
|mac|Wake on LANを送るMACアドレス|E-Server|

クラウドと銘打った変数ですが、作者はMEGAに最新のバックアップを別途保管する目的で記述しています。容量節約のため、**最新版でない物は自動で消去します。**  
パスさえ通れば別にどこにでも置けるのでMEGA以外にNASに保管するなども可能。

他にいくつか変数で設定を変えられる箇所がありますが、全部コメントを書いているので恐らく読めば分かると思います。

8. visudoを編集する

スリープモードをコマンドからするためにはroot権限が必要なのだが、visudoを編集する事でパスワード入力を省略して実行出来る環境にする必要があります。  
visudoに以下の記述を追加する。※(USERNAME)は各自のユーザー名に変更する事
```ini
(USERNAME) ALL=NOPASSWD: /usr/bin/systemctl suspend
```
Hamachiで接続している場合は``(USERNAME) ALL=NOPASSWD: /usr/bin/systemctl restart logmein-hamachi.service``も追記する必要がある。また、P-Serverの``subprocess.run(["sudo", "systemctl", "restart", "logmein-hamachi.service"], check = True)``のCOも解除する事。

### 起動方法
ここまで環境を組んだら``python P-Server.py``でP-Serverが、``python E-Server.py``でE-Serverが起動します。  
[ね?簡単でしょう?](https://dic.nicovideo.jp/a/%E3%81%AD%E3%80%81%E7%B0%A1%E5%8D%98%E3%81%A7%E3%81%97%E3%82%87%E3%81%86%3F)

### 操作方法
DiscordのBotは以下のコマンドを受け付けます。
|コマンド名|動作|動く方|
|----|----|----|
|start|環境変数で指定したバックアップ先にワールドデータのバックアップを生成した後にcommandを実行 JEかBEか選択可|P-Server|
|status|process_nameで指定したプロセスが生きてるかを確認 JEかBEか選択可|P-Server|
|auto-sleep|自動スリープの有効化・無効化 ※要管理者権限|P-Server|
|players|プレイヤー数を取得|P-Server|
|force-backup|強制バックアップ JEかBEか選択可 ※要管理者権限|P-Server|
|boot|macで指定したMACアドレスにWake on LANのマジックパケットを送信します|E-Server|
|ping|hostに指定したアドレスにpingを送って死活確認をします|E-Server|
|debug|内部で使ってる変数の中身を吐きます(定期確認で使っている物なのでリアルタイムの物ではありません)|両方|
|exit|botを終了します|両方|

### 注意事項
BE鯖の自動アプデですが、directory_beで指定したフォルダ内の[公式サイト](https://www.minecraft.net/ja-jp/download/server/bedrock)からDLした名前のzipファイルのファイル名でバージョン管理をしています。そのため、新規セットアップする際もzipファイルを対象ディレクトリ内に入れておいて下さい。さもないと自動で上書きされるので注意が必要です。

## 内部的な話
本プログラムは1分を単位として処理しています。そのため、各種死活確認と接続数は1分単位で再取得しているため即座に反応する事はありません。*ただしクラッシュログ監視を除く*  
割と実装が雑なんで変な呼び出し方してます。Linux限定なのは10割subprocessで呼び出してる外部コマンドのせいなのでそれだけ対応したらWindowsでも動きます。  
スリープからの復帰はdiscord.pyのon_readyイベントを使ったズボラ実装なので復帰から諸々の処理が入るのは時間がかかります。  
[改造版CatServer](https://github.com/Leafeon2020/CatServer)にWatchdogを無効化するために制御用ファイルを生成します。中身は1バイトのテキストです。  
BEのアップデートには[Javascriptを用いて動的にURLを生成しているサイト](https://www.minecraft.net/ja-jp/download/server/bedrock)に対応するためにFirefox+Seleniumを利用しています。元々GUI環境向けの記述になりますが、一応CLI環境用の改造も可能です。Beautiful Soup4+Requestsでは処理出来なかったためこのような形になりました。

## 既知の問題
- スリープモードに入った直後に復帰させると復帰時の処理が行われない
    - 原因:復帰時の処理にdiscord.pyのon_readyイベントでDiscordに再接続した時をトリガーとして処理しているため ~~要はスボラ実装の犠牲~~
    - 対策:スリープモードになった直後に/bootコマンドを使わない 接続が切れる必要があるので数分待つ必要がありそうです

## 連絡先
基本無保証ですが何かあったら[Misskey](https://misskey.nukumori-sky.net/@krsw)にでも書いてください。反応したりしなかったりします。

## ライセンス
![GPLv3](https://upload.wikimedia.org/wikipedia/commons/thumb/9/93/GPLv3_Logo.svg/720px-GPLv3_Logo.svg.png)
