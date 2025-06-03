#Create by Infinity.ELF
#License: GPLv3

#起動の前に 以下の環境が必要になります
#OS:Linux
#Pythonライブラリ:discord.py、watchfiles
#必要な外部ソフト:pixz

#Discord類のインポート
import discord # type: ignore
from discord import app_commands # type: ignore
from discord.ext import tasks # type: ignore
from discord.app_commands import describe	# type: ignore
#システム系のインポート
import os
from glob import glob
import datetime
import subprocess
from watchfiles import awatch	# type: ignore

#初期設定
intents = discord.Intents.default()	#反応イベント指定
client = discord.Client(intents=intents)	#Botクライアント読み込み
tree = app_commands.CommandTree(client)	#コマンド類宣言

#変数類
#Pythonはvarで自動宣言するけどC#のノリで型指定してます
#環境変数
TOKEN: str = "https://krsw-wiki.org"	#Botのトークン
process_name: str = "java"	#プロセス名指定
Manage_Channel: str = "うんち"	#書き込み先
directory: str = "/home/krsw/.minecraft"	#対象ディレクトリ
command: str = (
		"mate-terminal",	#DEの端末
		"--maximize",	#最大化
		"--command",	#以下のコマンドを実行する
		"java -Xmx1024M -Xms1024M -jar /home/krsw/.minecraft/minecraft_server.1.21.5.jar nogui"	#鯖起動命令
	)	#鯖起動コマンド
backup: str = "/home/krsw/backup"	#バックアップ保存先
global port_a
port_a : int = 2783	#ポート番号その1
global port_b
port_b : int = 43044	#ポート番号その2
global sleep_timer
sleep_timer: int = 10	#スリープ移行までの時間(分)
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
#確認したいポートを増やす場合はport_cとかの変数(int型)を増やしてssをsubprocessで呼び出しているとこを増やしてください
#ssの結果は必ず-1してください 行数を見てるのでヘッダーもカウントされてます
#構造上いくらポート接続者数を増やしても対応出来る設計にはなってます
#スリープモードに移行するために一度プロセスを一時停止させて無理やり応答なしで落ちないようにしてます

#開発用メモ
#コマンドを呼び出した後はawait interaction.response.send_message("メッセージ")で返信しないと応答無し扱いになる
#毎回チャンネル名取得してるけどグローバル変数化したら最初の1回だけで済むかも
#鯖起動だけsubprocess.Popenにしてるのはsubprocess.runだと鯖が死ぬまで応答が無くなるため
#subprocess.Popenの引数の渡し方は呼び出すやつ,オプション1,オプション2…みたいな書き方しないとエラー吐いて無理って言われる
#返信が3秒以上遅れる場合はawait interaction.response.defer()で考え中にしてawait interaction.followup.send("")でやらないとエラーになる
#グローバル変数化はPythonの仕様上関数ごとに呼び出さないといけないらしい

#恒心ログ
#2025/04/18 v1 - リリース
#2025/04/25 v2 - killコマンドを使ってプロセスを一時停止させる機能を実装し、応答なしエラーで落ちる事を回避するように変更(あんま効果無いかも…)
#2025/05/08 v3 - killコマンドの例外実装を追加

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
		#Hamachiで接続している場合のみこのCOを外してください
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
	return

#監視処理
@tasks.loop(seconds=60)	#毎分確認
async def task():
	global status
	global port_a
	global port_b
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
		result = subprocess.run("ss -tn sport = :" + str(port_a) +" | wc -l", shell = True, capture_output=True, text=True)
		counter = int(result.stdout.strip()) - 1
		result = subprocess.run("ss -tn sport = :" + str(port_b) +" | wc -l",shell = True, capture_output=True, text=True)
		counter = counter + int(result.stdout.strip()) - 1
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
			timestamp: str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
			filename: str = f"world-{timestamp}.tar.xz"
			#.tar.xzで圧縮
			print("圧縮開始")
			subprocess.run(["tar", "-I", "pixz", "-cvpf", filename, "-C", directory + "/world", "./"], check=True, cwd = backup)	#pixzに投げる
			print("xzで圧縮")
			for channel in client.get_all_channels():
				if channel.name == Manage_Channel:
					await channel.send(f'バックアップを生成しました')
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
