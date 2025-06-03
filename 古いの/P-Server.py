#Create by Infinity.ELF
#License: GPLv3

#起動の前に 以下の環境が必要になります
#OS:Linux
#Pythonライブラリ:discord.py、watchfiles
#必要な外部ソフト:pixz

#仕様メモ
#改行コードはとりあえずCR+LFで統一してます OSはLinuxですがWindows方言だと多分どのOSでも問題無いかと
#コマンド実行する外部コマンドは全部Linux用です Windowsでは使えません macOSは知らん
#commnadの最初の変数を変えれば別のDEでも動く
#起動メッセージはURL直リンで対応という荒業 403吐くようになったらオラ知らね(無責任)
#圧縮周りは最終的に容量が小さくなりそうなxzで圧縮してる pixzに処理投げて待ち時間短縮や(誤差レベル)
#鯖本体を直接操作して動かす事を想定してるため監視の自動停止はわざとしてません 止める時はtask.stop()とwatchdog.stop()で止めてください
#定期死活確認は死んでたら処理を全部すっ飛ばします 外部から起動した場合は/statusでフラグを恒心してやる必要があります
#クラッシュログ通知は一度出力したら止まりますが毎分起動します
#visudoでsudo systenctl suspendをパスワード不要で実行出来る環境にする必要あり
#一応Hamachi対応です sudo systemctl restart logmein-hamachi.serviceをvisudo触ってパスワード無しで使えるようにしてCO外せば機能します その代わり復帰処理の時間が伸びます
#確認したいポートを増やす場合はport_cとかの変数(int型)を増やしてssをsubprocessで呼び出しているとこを増やしてください
#ssの結果は必ず-1してください 行数を見てるのでヘッダーもカウントされてます
#構造上いくらポート接続者数を増やしても対応出来る設計にはなってます
#スリープモードに移行するためにCatServer側に仕込んだwatchdog_switch.javaを使った強引なWatchdogThread制御スイッチを起動するための処理をしてます その後プロセスを一時停止してます
#復帰時はまずプロセスを再開(この時はまだwatchdogが止まってる)してからwathcdog_switch.javaを反応させるためファイルを書き換えてWatchdogThreadを再起動します
#復帰時の待機時間は長めに取っておいたほうがいいです kill -CONTを飛ばしてから実際にプロセスが動き出すまで結構時間掛かってる感じがしたので1分待機させてます
#クラッシュした時の対策とかも兼ねて自動再起動は入れてません(というよりSpigot側に実装されてる)

#開発用メモ
#コマンドを呼び出した後はawait interaction.response.send_message("メッセージ")で返信しないと応答無し扱いになる
#毎回チャンネル名取得してるけどグローバル変数化したら最初の1回だけで済むかも
#鯖起動だけsubprocess.Popenにしてるのはsubprocess.runだと鯖が死ぬまで応答が無くなるため
#subprocess.Popenの引数の渡し方は呼び出すやつ,オプション1,オプション2…みたいな書き方しないとエラー吐いて無理って言われる
#返信が3秒以上遅れる場合はawait interaction.response.defer()で考え中にしてawait interaction.followup.send("")でやらないとエラーになる
#グローバル変数化はPythonの仕様上関数ごとに呼び出さないといけないらしい
#killコマンド関連はkillallに変えたほうがコード長が短くなる事を書いてから知りました もう面倒なんでこのまま行きます

#恒心ログ
#2025/04/18 v1 - リリース
#2025/04/25 v2 - killコマンドを使ってプロセスを一時停止させる機能を実装し、応答なしエラーで落ちる事を回避するように変更
#2025/05/08 v3 - killコマンドの例外実装を追加
#2025/05/21 v4 - クラウドへのバックアップ機能と改造版CatServerに合わせた記述を追加 改造版CatServer以外の互換性は無いです
#2025/05/23 v5 - バックアップ周りのバグ修正とCatServer用の挙動の変更
#2025/05/29 v6 - 同時接続数監視のバグ修正

#Discord類のインポート
import discord # type: ignore
from discord import app_commands # type: ignore
from discord.ext import tasks # type: ignore
from discord.app_commands import describe	# type: ignore
#外部ライブラリのインポート
from watchfiles import awatch	# type: ignore
#システム系のインポート
import os
import re
from glob import glob
from datetime import datetime
import subprocess
import shutil
import asyncio

#初期設定
intents = discord.Intents.default()	#反応イベント指定
client = discord.Client(intents=intents)	#Botクライアント読み込み
tree = app_commands.CommandTree(client)	#コマンド類宣言

#変数類
#Pythonはvarで自動宣言するけどC#のノリで型指定してます
#環境変数
TOKEN: str = "https://krsw-wiki.in/"	#Botのトークン
process_name: str = "java"	#プロセス名指定
Manage_Channel: str = "うんち"	#書き込み先
directory: str = "/home/krsw/.minecraft"	#対象ディレクトリ
command: str = (
		"mate-terminal",	#DEの端末
		"--maximize",	#最大化
		"--command",	#以下のコマンドを実行する
		"java -Xmx1024M -Xms1024M -jar /home/krsw/.minecraft/CatServer-universal.jar"	#鯖起動命令
	)	#鯖起動コマンド
backup: str = "/home/krsw/backup"	#バックアップ保存先
port_a : int = 2783	#ポート番号その1
port_b : int = 43044	#ポート番号その2
sleep_timer: int = 10	#スリープ移行までの時間(分)
cloud: str = "/home/krsw/MEGA"	#クラウドストレージの保存先
cloud_swtich: bool = True	#クラウドに保存するか

#システム用変数 触るな
global status
status: int = 0	#プロセス状態用フラグ 0で落ちてて1で生きてる2で起動処理中
global resume
resume: bool = False	#復帰フラグ
global auto_sleep
auto_sleep: bool = True	#自動スリープ設定
global sleep
sleep: int = -1	#無接続時間
global intosleep
intosleep: bool = False	#スリープモード移行フラグ
global counter
counter: int = 0	#同時アクセス数(設定全ポート分)
global process_id
process_id: str = 0	#プロセスID
switch_file: str = directory + "/sleep_switch.txt"	#watchdog制御用ファイル

#本体
#起動時処理 on_readyが条件なんでスリープ復帰時にも処理されます
@client.event
async def on_ready():
	global status
	global resume
	global intosleep
	global sleep
	global process_id
	print("サーバーマシン、起動!w")
	await client.change_presence(activity=discord.Game("開示請求を発行中…"))
	await tree.sync()	#コマンド読み込み
	#書き込み先チャンネルID取得
	for channel in client.get_all_channels():
		if channel.name == Manage_Channel:
			await channel.send("http://riceballman.fc2web.com/AA-Illust/Data/NeetOkita.jpg")	#起動通知
	#鯖生存確認
	print("死活確認")
	try:
		subprocess.run(["pgrep", process_name], check=True)	#pgrepが例外吐くかどうかで死活確認
		status = 1	#生存フラグ
	except subprocess.CalledProcessError:	#死んでる時
		status = 0	#死亡フラグ
		for channel in client.get_all_channels():
			if channel.name == Manage_Channel:
				await channel.send(f'鯖が起動してないですを')
	await tree.sync()	#コマンドリスト恒心
	#watchdogフラグ制御ファイル作成
	if os.path.isfile(switch_file) == False:
		with open(switch_file, 'w') as f:
			f.write("1")
		print("制御ファイルを作成しました")
	#on_readyの仕様を利用したスリープ復帰検出のズボラ
	if intosleep == True:
		print("復帰")
		#一時停止解除
		try:
			subprocess.run(["kill", "-CONT", process_id], check = True)
			print("プロセスを再開しました")
		except subprocess.CalledProcessError:
			print("プロセス指定不可")
		resume = True
		intosleep = False
		sleep = -1
		#subprocess.run(["sudo", "systemctl", "restart", "logmein-hamachi.service"], check = True)
		for channel in client.get_all_channels():
			if channel.name == Manage_Channel:
				await channel.send(f'復帰処理が終わりました')
		sleep = -1
	try:
		watchdog.start()	#クラッシュログ監視起動
	except:
		print("watchdog起動済")
	try:
		task.start()	#死活確認起動
	except:
		print("死活確認起動済")
	await asyncio.sleep(60)	#恒心検知処理が動くようにちょっと待つ
	with open(switch_file, 'w') as f:
		f.write("1")
	return

#監視処理
@tasks.loop(seconds=60)	#毎分確認
async def task():
	global status
	global auto_sleep
	global sleep
	global sleep_timer
	global intosleep
	global resume
	global counter
	global process_id
	#プロセス監視
	if status == 1:	#プロセスが死んでたらスルー(連投対策)
		print("死活確認中")
		try:
			subprocess.run(["pgrep", process_name], check=True)
			status = 1	#生存フラグ
			print("生きてた")
		except subprocess.CalledProcessError:
			status = 0	#死亡フラグ
			for channel in client.get_all_channels():
				if channel.name == Manage_Channel:
					await channel.send(f'なんてこった!サーバーが殺されちゃった!\r\nこの人でなし!')
			print("死んでた")
	#接続数監視
	#復帰フラグ時の処理
	if resume == True:
		print("目が冴えてる(" + str(sleep) + "分経過)")
		sleep += 1
	#アクセス0の時の処理
	else:
		#ポートごとのアクセス数確認
		result1 = subprocess.run("ss -tn sport = :" + str(port_a) +" | wc -l", shell = True, capture_output=True, text=True)
		counter = int(result1.stdout.strip()) - 1
		result2 = subprocess.run("ss -tn sport = :" + str(port_b) +" | wc -l",shell = True, capture_output=True, text=True)
		counter += int(result2.stdout.strip()) - 1
		#誰も居ない時
		if counter == 0:
			sleep += 1
			print("誰も居ないなぁ…(" + str(sleep) + "分経過)")
		#誰か居た時
		else:
			sleep = 0
			print("今" + str(counter) + "人居る")
		#スリープモード起動
		if sleep > sleep_timer and auto_sleep == True and intosleep == False:
			#プロセス一時停止処理
			if status == 1:
				process_id = get_pid()
				try:
					with open(switch_file, 'w') as f:
						f.write("0")
					await asyncio.sleep(5)	#鯖側で処理するための待ち時間
					subprocess.run(["kill", "-STOP", process_id], check = True)
					print("プロセスを一時停止します")
				except subprocess.CalledProcessError:
					print("プロセス指定不可")
			sleep = -1
			intosleep = True
			for channel in client.get_all_channels():
				if channel.name == Manage_Channel:
					await channel.send(f'スリープモードに移行します\r\n復帰には/bootを使ってください')
			print("スリープモード移行")
			subprocess.run(["sudo", "systemctl", "suspend"], check = True)
			task.stop()
	#復帰フラグ解除
	if resume == True and sleep > 5:
		print("待機時間終わり!")
		resume = False
		sleep = 0
	return

#PID取得
def get_pid():
	global process_name
	try:
		result = subprocess.run(["pgrep", "-o", process_name], capture_output=True, text=True)
		if result.returncode == 0 and result.stdout.strip():
			return str(result.stdout.strip())
	except Exception as e:
		print(f"なんか例外吐いてるぞ: {e}")
	return None	#例外吐いた時の保険

#クラッシュログ通知
@tasks.loop(seconds=60)	#起動聖句を思いつかなかったのでtask.loopで起動してます
async def watchdog():
	#クラッシュログの欲しい箇所を指定(行単位で出力されます)
	start_str: str = "Description:"
	end_str: str = "at java.lang.Thread.run"
	#クラッシュログ取得
	async for changes in awatch(directory + '/crash-reports'):	#ファイル恒心時にループに入る
		#ファイル姪取得
		target = os.path.join(directory + '/crash-reports', '*')
		files = [(f, os.path.getmtime(f)) for f in glob(target)]
		latest_modified_file_path = sorted(files, key=lambda files: files[1])[-1]
		latest_file = latest_modified_file_path[0]
		#ログ抽出
		crash_log = extract(latest_file, start_str, end_str)
		for channel in client.get_all_channels():
			if channel.name == Manage_Channel:
				await channel.send(f'鯖は死んだ… 残されたダイイングメッセージには以下のように残されていた\r\n```' + crash_log + "\r\n```")
		break
	return
	
#ログ抽出
def extract(file_path, start_str, end_str):
    extracted_lines = []	#str型配列 ログ格納用
    inside_section = False	#追記開始フラグ
	#読み込み処理
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:	#上から読み込み
			#開始行発見
            if start_str in line:
                inside_section = True
			#ログを文字列に追記(改行コード込)
            if inside_section:
                extracted_lines.append(line)
			#終了行で停止
            if end_str in line and inside_section:
                break
    return ''.join(extracted_lines)	#str型で返す

#コマンド処理
#起動
@tree.command(name="start", description="サーバープロセスを実行します")
async def com_start(interaction: discord.Interaction):
	global status
	print("起動プロセス開始")
	try:
		subprocess.run(["pgrep", process_name], check=True)
		status = 1	#生存フラグ
	except subprocess.CalledProcessError:
		status = 0	#死亡フラグ
	#起動処理
	if status == 0:
		print("鯖が死んでたので起動")
		status = 2	#ステータスを起動処理中にする
		await interaction.response.send_message("起動処理を実行します")
		#バックアップ生成
		try:
			#ファイル名生成
			timestamp: str = datetime.now().strftime("%Y%m%d-%H%M%S")
			filename: str = f"world-{timestamp}.tar.xz"
			#.tar.xzで圧縮
			print("圧縮開始")
			subprocess.run(["tar", "-I", "pixz", "-cvpf", filename, "-C", directory + "/world", "./"], check=True, cwd = backup)	#pixzに投げる
			print("xzで圧縮")
			for channel in client.get_all_channels():
				if channel.name == Manage_Channel:
					await channel.send(f'バックアップを生成しました')
			#クラウドにバックアップするか
			if cloud_swtich == True:
				cloud_backup: str = get_latest_backup_file(cloud)	#既存バックアップ名取得
				#バックアップが既にある場合は消去してコピー
				if cloud_backup != "":
					os.remove(cloud + "/" + cloud_backup)
				shutil.copy(backup + "/" + filename, cloud)
		#例外処理
		except subprocess.CalledProcessError as e:
			print("圧縮例外\r\n" + e)
			for channel in client.get_all_channels():
				if channel.name == Manage_Channel:
					await channel.send(f'なんか上手いこと行かなかったみたいですよ(subprocess例外)\r\n例外詳細:{e}')
					status = 0	#死んだ扱いにする
		except Exception as e:
				print(f"Exception\r\n" + e)
				for channel in client.get_all_channels():
					if channel.name == Manage_Channel:
						await channel.send(f'なんかやらかしてるみたいですよ…\r\n詳細:{e}')
		#メッセージ送信
		#鯖起動
		try:
			print("起動命令送信")
			subprocess.Popen(command, cwd = directory)	#起動聖句
			for channel in client.get_all_channels():
				if channel.name == Manage_Channel:
					await channel.send(f'鯖の起動命令を送ったナリよ')
			status = 1	#起動処理中から起動に変更
			print("起動成功")
		except subprocess.CalledProcessError as e:
			print("起動例外\r\n" + e)
			for channel in client.get_all_channels():
				if channel.name == Manage_Channel:
					await channel.send(f'なんか上手いこと行かなかったみたいですよ(subprocess例外)\r\n例外詳細:{e}')
					status = 0	#死んだ扱いにする
	#多重起動防止
	elif status == 2:
		for channel in client.get_all_channels():
			if channel.name == Manage_Channel:
				await channel.send(f"鯖は起動中なりを\r\nしばし待たれよ")
	else:
		print("多重起動防止")
		await interaction.response.send_message(f'鯖、生きてるってよ')
	return

#バックアップファイル名取得
def get_latest_backup_file(directory: str) -> str:
	pattern = re.compile(r"world-(\d{8})-(\d{6})\.tar\.xz")	#パターン指定
	#初期化
	latest_time = None
	latest_file = None
	for filename in os.listdir(directory):	#引数で指定したフォルダの中身を片っ端から調査
		match = pattern.fullmatch(filename)	#条件完全一致で変数に格納
		if match:
			date_str = match.group(1) + match.group(2)	#YYYYmmddHHMMSS
			try:
				file_time = datetime.strptime(date_str, "%Y%m%d%H%M%S")	#基準時刻生成
				#ファイル名の時刻を分析して比較
				if latest_time is None or file_time > latest_time:
					latest_time = file_time
					latest_file = filename
			except ValueError:
				continue	#不正な日付はスキップ
	return latest_file if latest_file else ""	#ファイルが無いと長さ0のstr型を返す

#死活確認
@tree.command(name="status", description="サーバープロセスが生きてるか確認します")
async def com_status(interaction: discord.Interaction):
	global status
	print("死活確認(コマンド)")
	try:
		subprocess.run(["pgrep", process_name], check=True)
		status = 1	#生存フラグ
		for channel in client.get_all_channels():
			if channel.name == Manage_Channel:
				await interaction.response.send_message(f'生きてる')
		print("鯖生存")
	except subprocess.CalledProcessError:
		status = 0	#死亡フラグ
		for channel in client.get_all_channels():
			if channel.name == Manage_Channel:
				await interaction.response.send_message(f'陳死亡')
		print("鯖死亡")
	return

#自動スリープ切り替え
@tree.command(name="auto-sleep", description="自動スリープの設定をします")
@describe(cmd="スイッチ")
@discord.app_commands.default_permissions(administrator=True)
async def sleep_switch(interaction: discord.Interaction, cmd: bool):
	global auto_sleep
	global sleep
	if cmd == True:
		auto_sleep = True
		sleep = 0
		await interaction.response.send_message(f'オートスリープを有効にしました')
	elif cmd == False:
		auto_sleep = False
		await interaction.response.send_message(f'オートスリープを無効にしました')

#デバッグ用
@tree.command(name="debug", description="状態変数を返します")
async def debug(interaction: discord.Interaction):
	global status
	global auto_sleep
	global sleep
	global counter
	global process_name
	pid = get_pid()
	if pid == None:
		pid = ("プロセス無し")
	if status == 0:
		state = "0(プロセス無し)"
	elif status == 1:
		state = "1(プロセス実行中)"
	elif status == 2:
		state = "2(起動処理中)"
	await interaction.response.send_message("status:" + state + "\r\n自動スリープフラグ:" + str(auto_sleep) + "\r\n待機時間:" + str(sleep) + "\r\n同時アクセス数:" + str(counter) + "\r\n" + process_name + "のPID:" + pid)
	return

#終了処理
@tree.command(name="exit", description="監視botを終了させます")
@app_commands.default_permissions(administrator=True)
async def exit(interaction: discord.Interaction):
	print("bot終了")
	for channel in client.get_all_channels():
		if channel.name == Manage_Channel:
			await interaction.response.send_message(f'終了の時間だあああああああああああああああああああああああああああああああ！！！！！！！！！！！（ﾌﾞﾘﾌﾞﾘﾌﾞﾘﾌﾞﾘｭﾘｭﾘｭﾘｭﾘｭﾘｭ！！！！！！ﾌﾞﾂﾁﾁﾌﾞﾌﾞﾌﾞﾁﾁﾁﾁﾌﾞﾘﾘｲﾘﾌﾞﾌﾞﾌﾞﾌﾞｩｩｩｩｯｯｯ！！！！！！！）')
			await channel.send(f'監視カメラは爆発した')
	await client.close()
	exit()

#bot起動聖句
if __name__ == "__main__":
	client.run(TOKEN)
