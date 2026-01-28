#Create by Infinity.ELF
#License: GPLv3

#起動の前に 以下の環境が必要になります
#OS:Linux
#Pythonライブラリ:discord.py、watchfiles、MCStatus、Selenium
#必要な外部ソフト:pixz、Firefox、geckodriver、wget

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
#JEBE両対応してますが別にどちらか片方だけでも(多分)例外吐かずに動きます
#Firefoxはsnap版の前提になってます 多分OSのデフォで入ってるやつはsnap版です(確証無し) ちなみにテスト環境はUbuntu Server 24.04 LTSにLDMとMATE仕込んだ環境です
#ファイルのDLに関しては全て投げ出してwgetで取得してもいいんじゃないの? Used to be 諦めるのは easy

#開発用メモ
#コマンドを呼び出した後はawait interaction.response.send_message("メッセージ")で返信しないと応答無し扱いになる
#毎回チャンネル名取得してるけどグローバル変数化したら最初の1回だけで済むかも
#鯖起動だけsubprocess.Popenにしてるのはsubprocess.runだと鯖が死ぬまで応答が無くなるため
#subprocess.Popenの引数の渡し方は呼び出すやつ,オプション1,オプション2…みたいな書き方しないとエラー吐いて無理って言われる
#返信が3秒以上遅れる場合はawait interaction.response.defer()で考え中にしてawait interaction.followup.send("")でやらないとエラーになる
#グローバル変数化はPythonの仕様上関数ごとに呼び出さないといけないらしい
#killコマンド関連はkillallに変えたほうがコード長が短くなる事を書いてから知りました もう面倒なんでこのまま行きます

#ToDo
#サーバープロセスにkillコマンド使った時の反応を確認(SIGTERMで/stopの代替になればそれ使う)
#関数の置いてる場所を整理して可読性を上げる

#恒心ログ
#2025/04/18 v1 - リリース
#2025/04/25 v2 - killコマンドを使ってプロセスを一時停止させる機能を実装し、応答なしエラーで落ちる事を回避するように変更
#2025/05/08 v3 - killコマンドの例外実装を追加
#2025/05/21 v4 - クラウドへのバックアップ機能と改造版CatServerに合わせた記述を追加 改造版CatServer以外の互換性は無いです
#2025/05/23 v5 - バックアップ周りのバグ修正とCatServer用の挙動の変更
#2025/05/29 v6 - 同時接続数監視のバグ修正
#2025/06/02 v7 - BEサポートを追加、接続数コマンド実装、接続数の監視方法をMCStatusに変更
#2025/06/16 v8 - MCStatusの例外処理実装
#2025/07/01 v9 - 復帰時のkillコマンドの例外追加
#2025/07/22 v10 - 起動コマンドの変数をdirectory変数を参照する物に変更
#2025/07/27 v11 - 起動コマンドのガバ修正
#2025/08/31 v12 - バックアップ世代数制限機能追加
#2025/09/07 v13 - バックアップ世代数制限のON/OFFフラグ追加
#2025/11/19 v14 - BE鯖アプデ機能と強制バックアップ追加
#2025/12/02 v15 - BE鯖公式ページの仕様に対応
#2025/12/06 v16 - 削っちゃいけないとこ削ってたので修正
#2025/12/15 v17 - BE鯖のDLが出来てなかった問題を解決(と細かいとこの修正)
#2025/12/19 v18 - BE鯖アプデ方式変更
#2026/01/21 v19 - chmodの追加とバックアップ周りのバグ修正
#2026/01/28 v20 - 関数類の整理、終了コマンドの修正、端末制御周りの変更、パイプ接続実装、screen起動実装 多分このバージョン没

#Discord類のインポート
import discord
from discord import app_commands
from discord.ext import tasks
from discord.app_commands import describe
#外部ライブラリのインポート
from watchfiles import awatch
from mcstatus import JavaServer
from mcstatus import BedrockServer
import selenium
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
#システム系のインポート
import os
import re
from glob import glob
from datetime import datetime
import subprocess
import shutil
import asyncio
from urllib.parse import urlparse

#初期設定
intents = discord.Intents.default()	#反応イベント指定
client = discord.Client(intents=intents)	#Botクライアント読み込み
tree = app_commands.CommandTree(client)	#コマンド類宣言

#変数類
#Pythonはvarで自動宣言するけどC#のノリで型指定してます
#環境変数
TOKEN: str = "https://krsw-wiki.in/wiki/?cuid=3896"	#Botのトークン
process_name: str = "java"	#プロセス名指定
process_name_be: str = "bedrock_server"	#プロセス名指定
Manage_Channel: str = "管理bot用"	#書き込み先
directory: str = "/home/krsw/.minecraft"	#対象ディレクトリ
directory_be: str = "/home/krsw/Minecraft_Bedrock"	#対象ディレクトリ
backup: str = "/home/krsw/backup"	#バックアップ保存先
backup_be: str = "/home/krsw/Minecraft_Bedrock/backup"	#バックアップ保存先
port_a: int = 2783	#ポート番号その1(JEポート)
port_b: int = 40298	#ポート番号その2(SSHポート)
port_c: int = 43044	#ポート番号その3(BEポートIPv4)
port_d: int = 5900	#ポート番号その4(VNCポート)
sleep_timer: int = 10	#スリープ移行までの時間(分)
cloud: str = "/home/krsw/MEGA"	#クラウドストレージの保存先
cloud_swtich: bool = True	#クラウドに保存するか
backup_limit: int = 20	#バックアップ世代数
backup_remove: bool = True	#バックアップ自動消去フラグ

#システム用変数 触るな
status: int = 0	#プロセス状態用フラグ 0で落ちてて1で生きてる2で起動処理中
status_be: int = 0	#プロセス状態用フラグ 0で落ちてて1で生きてる2で起動処理中
resume: bool = False	#復帰フラグ
auto_sleep: bool = True	#自動スリープ設定
sleep: int = -1	#無接続時間
intosleep: bool = False	#スリープモード移行フラグ
counter: int = 0	#同時アクセス数(設定全ポート分)
process_id: str = 0	#プロセスID(JE)
process_id_be: str = 0	#プロセスID(BE)
switch_file: str = directory + "/sleep_switch.txt"	#watchdog制御用ファイル
JE_server = JavaServer.lookup("localhost:" + str(port_a))	#JE鯖の読み込み
BE_server = BedrockServer.lookup("localhost:" + str(port_c))	#BE鯖の読み込み
type = ["JE", "BE"]	#引数用
firefox_bin: str = "/snap/firefox/current/usr/lib/firefox/firefox"	#Firefox実行ファイルパス
firefoxdriver_bin: str = "/snap/firefox/current/usr/lib/firefox/geckodriver"	#GeckoDriver実行ファイルパス
pipe_flag_je: bool = False	#JEパイプフラグ
pipe_flag_be: bool = False	#BEパイプフラグ
JE_FIFO_IN: str = "/tmp/je_session_in"	#JE鯖パイプ入力先
JE_FIFO_OUT: str = "/tmp/je_session_out"	#JE鯖パイプ出力先
BE_FIFO_IN: str = "/tmp/be_session_in"	#BE鯖パイプ入力先
BE_FIFO_OUT: str = "/tmp/be_session_out"	#BE鯖パイプ出力先
session_name_je: str = "je_server"	#JE鯖screenセッション名
session_name_be: str = "be_server"	#BE鯖screenセッション名
#非同期入出力用変数
#JE
stdin_pipe_je = None
stdout_pipe_je = None
#BE
stdin_pipe_be = None
stdout_pipe_be = None

#自動実行コマンド類
#JE鯖起動コマンド
command: str = f"screen -dmS {session_name_je} bash -c 'tail -f {JE_FIFO_IN} | java -Xmx28G -jar {directory}/CatServer-universal.jar 2>&1 | tee {JE_FIFO_OUT}'"	#鯖起動命令
#BE鯖起動コマンド
be_start: str = (f"export LD_LIBRARY_PATH={directory_be}; tail -f {BE_FIFO_IN} | {directory_be}/{process_name_be} 2>&1 | tee {BE_FIFO_OUT}")	#鯖起動命令
#端末
je_terminal: str =(
	"mate-terminal", 
	"--maximize", 
	"--command", 
	f"screen -r {session_name_je}"	#JE鯖操作端末起動コマンド
)
be_terminal: str = (
	"mate-terminal", 
	"--maximize", 
	"--command", 
	f"screen -r {session_name_be}"	#BE鯖操作端末起動コマンド
)	#BE鯖操作端末起動コマンド

#オートコンプリート関数
async def version_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
	return [
		app_commands.Choice(name=version, value=version)
		for version in type if current.lower() in version.lower()
	][:2]

#各種関数類
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

#終了処理
async def mcstop(version: int):
	global process_name
	global process_name_be
	global pipe_flag_je
	global pipe_flag_be
	global stdin_pipe_je
	global stdin_pipe_be
	#JE鯖停止
	if version == 0:
		if pipe_flag_je == True:	#パイプ接続中
			try:
				if stdin_pipe_je:
					await stdin_pipe_je.write("stop\r\n")
					await stdin_pipe_je.flush()
				pipe_flag_je = False
				print("JE停止命令送信完了")
				return True
			except Exception as e:
				print(f"JE停止例外\r\n{e}")
				return e
		else:	#パイプ未接続
			try:
				subprocess.run(["pkill", "-f", process_name, "-s", "SIGTERM"], check=True)
				print("JE強制停止完了")
				return True
			except subprocess.CalledProcessError as e:
				print(f"JE強制停止例外\r\n{e}")
				return e
	#BE鯖停止
	elif version == 1:
		if pipe_flag_be == True:	#パイプ接続中
			try:
				if stdin_pipe_be:
					await stdin_pipe_be.write("stop\r\n")
					await stdin_pipe_be.flush()
				pipe_flag_be = False
				print("BE停止命令送信完了")
				return True
			except Exception as e:
				print(f"BE停止例外\r\n{e}")
				return e
		else:	#パイプ未接続
			try:
				subprocess.run(["pkill", "-f", process_name_be, "-s", "SIGTERM"], check=True)
				print("BE強制停止完了")
				return True
			except subprocess.CalledProcessError as e:
				print(f"BE強制停止例外\r\n{e}")
				return e

#PID取得
def get_pid(switch: int):
	global process_name
	try:
		if switch == 0:
			result = subprocess.run(["pgrep", "-o", process_name], capture_output=True, text=True)
		elif switch == 1:
			result = subprocess.run(["pgrep", "-o", process_name_be], capture_output=True, text=True)
		if result.returncode == 0 and result.stdout.strip():
			return str(result.stdout.strip())
	except Exception as e:
		print(f"なんか例外吐いてるぞ: {e}")
	return None	#例外吐いた時の保険

#バックアップファイル名取得
def get_latest_backup_file(directory: str, switch: int) -> str:
	if switch == 0:
		pattern = re.compile(r"world-(\d{8})-(\d{6})\.tar\.xz")	#パターン指定
	elif switch == 1:
		pattern = re.compile(r"be-world-(\d{8})-(\d{6})\.tar\.xz")	#パターン指定
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

#バックアップ作成
async def create_backup(switch: int):
	try:
		#ファイル名生成
		timestamp: str = datetime.now().strftime("%Y%m%d-%H%M%S")
		if switch == 0:
			filename: str = f"world-{timestamp}.tar.xz"
		elif switch == 1:
			filename: str = f"be-world-{timestamp}.tar.xz"
		#.tar.xzで圧縮
		print("圧縮開始")
		if switch == 0:
			subprocess.run(["tar", "-I", "pixz", "-cvpf", filename, "-C", directory + "/world", "./"], check=True, cwd = backup)	#pixzに投げる
		elif switch == 1:
			subprocess.run(["tar", "-I", "pixz", "-cvpf", filename, "-C", directory_be + "/worlds", "./world"], check=True, cwd = backup_be)	#pixzに投げる
		print("xzで圧縮")
		for channel in client.get_all_channels():
			if channel.name == Manage_Channel:
				await channel.send(f'バックアップを生成しました')
		#クラウドにバックアップするか
		if cloud_swtich == True:
			cloud_backup: str = get_latest_backup_file(cloud, switch)	#既存バックアップ名取得
			#バックアップが既にある場合は消去してコピー
			if cloud_backup != "":
				os.remove(cloud + "/" + cloud_backup)
			if switch == 0:
				shutil.copy(backup + "/" + filename, cloud)
			elif switch == 1:
				shutil.copy(backup_be + "/" + filename, cloud)
		#古いバックアップ削除
		if switch == 0:
			files = glob(f"{backup}/world-????????-??????.tar.xz")
		elif switch == 1:
			files = glob(f"{backup_be}/be-world-????????-??????.tar.xz")
		if backup_remove == True:
			if len(files) > backup_limit:
				files.sort(key=os.path.getmtime)
				for file in files[:-backup_limit]:
					os.remove(file)
					print(f"古いバックアップファイルを削除しました: {file}")
	#例外処理
	except subprocess.CalledProcessError as e:
		print("圧縮例外\r\n" + e)
		for channel in client.get_all_channels():
			if channel.name == Manage_Channel:
				await channel.send(f'なんか上手いこと行かなかったみたいですよ(subprocess例外)\r\n例外詳細:{e}')
	except Exception as e:
			print(f"Exception\r\n" + e)
			for channel in client.get_all_channels():
				if channel.name == Manage_Channel:
					await channel.send(f'なんかやらかしてるみたいですよ…\r\n詳細:{e}')

#本体
#起動時処理 on_readyが条件なんでスリープ復帰時にも処理されます
@client.event
async def on_ready():
	global status
	global status_be
	global resume
	global intosleep
	global sleep
	global process_id
	global status_be
	global process_id_be
	global pipe_flag_je
	global pipe_flag_be
	print("サーバーマシン、起動!w")
	await client.change_presence(activity=discord.Game("開示請求を発行中…"))
	await tree.sync()	#コマンド読み込み
	#書き込み先チャンネルID取得
	for channel in client.get_all_channels():
		if channel.name == Manage_Channel:
			await channel.send("https://riceballman.web.fc2.com//AA-Illust/Data/NeetOkita.jpg")	#起動通知
	#鯖生存確認
	print("死活確認")
	#JE
	try:
		subprocess.run(["pgrep", process_name], check=True)	#pgrepが例外吐くかどうかで死活確認
		status = 1	#生存フラグ
	except subprocess.CalledProcessError:	#死んでる時
		status = 0	#死亡フラグ
		pipe_flag_je = False	#パイプ切断
		for channel in client.get_all_channels():
			if channel.name == Manage_Channel:
				await channel.send(f'JE鯖が起動してないですを')
	#BE
	try:
		subprocess.run(["pgrep", process_name_be], check=True)	#pgrepが例外吐くかどうかで死活確認
		status_be = 1	#生存フラグ
	except subprocess.CalledProcessError:	#死んでる時
		status_be = 0	#死亡フラグ
		pipe_flag_be = False	#パイプ切断
		for channel in client.get_all_channels():
			if channel.name == Manage_Channel:
				await channel.send(f'BE鯖が起動してないですを')
	await tree.sync()	#コマンドリスト恒心
	print("制御ファイル存在確認")
	#watchdogフラグ制御ファイル作成
	if os.path.exists(switch_file) == False:
		with open(switch_file, 'w') as f:
			f.write("1")
		print("制御ファイルを作成しました")
	#on_readyの仕様を利用したスリープ復帰検出のズボラ
	if intosleep == True:
		print("復帰")
		#一時停止解除
		#JE
		try:
			subprocess.run(["kill", "-CONT", process_id], check = True)
			print("プロセスを再開しました")
		except subprocess.CalledProcessError:
			print("プロセス指定不可")
		except TypeError:
			print("プロセス指定不可")
		except ValueError:
			print("プロセス指定不可")
		#BE
		try:
			subprocess.run(["kill", "-CONT", process_id_be], check = True)
			print("プロセスを再開しました")
		except subprocess.CalledProcessError:
			print("プロセス指定不可")
		except TypeError:
			print("プロセス指定不可")
		except ValueError:
			print("プロセス指定不可")
		resume = True
		intosleep = False
		sleep = -1
		#subprocess.run(["sudo", "systemctl", "restart", "logmein-hamachi.service"], check = True)	#Hamachiサービス再起動
		for channel in client.get_all_channels():
			if channel.name == Manage_Channel:
				await channel.send(f'復帰処理が終わりました')
		sleep = -1
	try:
		watchdog.start()	#クラッシュログ監視起動
		print("watchdog起動")
	except:
		print("watchdog起動済")
	try:
		task.start()	#死活確認起動
		print("死活確認起動")
	except:
		print("死活確認起動済")
	await asyncio.sleep(120)	#恒心検知処理が動くようにちょっと待つ
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
	global status_be
	global process_id_be
	global pipe_flag_je
	global pipe_flag_be
	#プロセス監視
	#JE
	if status == 1:	#プロセスが死んでたらスルー(連投対策)
		print("死活確認中")
		try:
			subprocess.run(["pgrep", process_name], check=True)
			status = 1	#生存フラグ
			print("生きてた")
		except subprocess.CalledProcessError:
			status = 0	#死亡フラグ
			#パイプ削除
			if os.path.exists(JE_FIFO_IN):
				os.remove(JE_FIFO_IN)
			if os.path.exists(JE_FIFO_OUT):
				os.remove(JE_FIFO_OUT)
			pipe_flag_je = False	#パイプ切断
			for channel in client.get_all_channels():
				if channel.name == Manage_Channel:
					await channel.send(f'なんてこった!JEサーバーが殺されちゃった!\r\nこの人でなし!')
			print("JEが死んでた")
	#BE
	if status_be == 1:	#プロセスが死んでたらスルー(連投対策)
		try:
			subprocess.run(["pgrep", process_name_be], check=True)
			status_be = 1	#生存フラグ
			print("生きてた")
		except subprocess.CalledProcessError:
			status_be = 0	#死亡フラグ
			#パイプ削除
			if os.path.exists(BE_FIFO_IN):
				os.remove(BE_FIFO_IN)
			if os.path.exists(BE_FIFO_OUT):
				os.remove(BE_FIFO_OUT)
			pipe_flag_be = False	#パイプ切断
			for channel in client.get_all_channels():
				if channel.name == Manage_Channel:
					await channel.send(f'なんてこった!BEサーバーが殺されちゃった!\r\nこの人でなし!')
			print("BEが死んでた")
	#接続数監視
	#復帰フラグ時の処理
	if resume == True:
		print("目が冴えてる(" + str(sleep) + "分経過)")
		sleep += 1
	#アクセス0の時の処理
	else:
		#ポートごとのアクセス数確認
		#JE
		try:
			JE_Status = JE_server.status()
			counter = JE_Status.players.online
		except ConnectionRefusedError:
			counter = 0
		except TimeoutError:
			counter = 0
		#SSH
		ssh = subprocess.run("ss -tn sport = :" + str(port_b) +" | wc -l",shell = True, capture_output=True, text=True)
		counter += int(ssh.stdout.strip()) - 1
		#BE
		try:
			BE_Status = BE_server.status()
			counter += BE_Status.players.online
		except ConnectionRefusedError:
			counter += 0
		except TimeoutError:
			counter += 0
		#VNC
		vnc = subprocess.run("ss -tn sport = :" + str(port_d) +" | wc -l",shell = True, capture_output=True, text=True)
		counter += int(vnc.stdout.strip()) - 1
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
			#JE
			if status == 1:
				process_id = get_pid(0)
				try:
					with open(switch_file, 'w') as f:
						f.write("0")
					await asyncio.sleep(5)	#鯖側で処理するための待ち時間
					subprocess.run(["kill", "-STOP", process_id], check = True)
					print("プロセスを一時停止します(JE)")
				except subprocess.CalledProcessError:
					print("プロセス指定不可(JE)")
			#BE
			if status_be == 1:
				process_id_be = get_pid(1)
				try:
					subprocess.run(["kill", "-STOP", process_id_be], check = True)
					print("プロセスを一時停止します(BE)")
				except subprocess.CalledProcessError:
					print("プロセス指定不可(BE)")
			sleep = -1
			intosleep = True
			for channel in client.get_all_channels():
				if channel.name == Manage_Channel:
					await channel.send(f'スリープモードに移行します\r\n復帰には/bootを使ってください')
			print("スリープモード移行")
			try:
				subprocess.run(["sudo", "systemctl", "suspend"], check = True)
				task.stop()
			except subprocess.CalledProcessError as e:
				print("スリープ移行失敗\r\n" + e)
				for channel in client.get_all_channels():
					if channel.name == Manage_Channel:
						await channel.send(f'なんか知らんがスリープ出来ないぞ visudoとかの仕込みちゃんとしたか?\r\n例外内容:\r\n{e}')
				auto_sleep = False	#スリープモード移行失敗時は自動スリープを無効化
	#復帰フラグ解除
	if resume == True and sleep > 5:
		print("待機時間終わり!")
		resume = False
		sleep = 0
	return

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
				await channel.send(f'鯖は死んだ… 残されたダイイングメッセージには以下のように残されていた\r\n```log\r\n' + crash_log + "\r\n```")
		break
	return

#コマンド処理
#起動
@tree.command(name="start", description="サーバープロセスを実行します")
@describe(boot="起動対象")
@app_commands.autocomplete(boot=version_autocomplete)
async def com_start(interaction: discord.Interaction, boot: str):
	if boot == "JE":
		global status
		global pipe_flag_je
		global stdin_pipe_je
		global stdout_pipe_je
		global stdin_pipe_be
		global stdout_pipe_be
		send_flag: bool = False	#メッセージ送信フラグ
		print("JE起動プロセス開始")
		try:
			subprocess.run(["pgrep", process_name], check=True)
			status = 1	#生存フラグ
		except subprocess.CalledProcessError:
			status = 0	#死亡フラグ
		#起動処理
		if status == 0:
			print("鯖が死んでたので起動")
			#FIFOパイプ作成
			if os.path.exists(JE_FIFO_IN):
				os.remove(JE_FIFO_IN)
			if os.path.exists(JE_FIFO_OUT):
				os.remove(JE_FIFO_OUT)
			os.mkfifo(JE_FIFO_IN)
			os.mkfifo(JE_FIFO_OUT)
			status = 2	#ステータスを起動処理中にする
			await interaction.response.send_message("起動処理を実行します")
			#バックアップ生成
			await create_backup(0)
			#メッセージ送信
			#鯖起動
			try:
				print("起動命令送信")
				subprocess.Popen(command, cwd=directory, shell=True)	#起動聖句
				await asyncio.sleep(2)	#鯖起動待ち
				#パイプ接続
				stdin_pipe_je = open(JE_FIFO_IN, 'w', buffering=1)
				stdout_fd = os.open(JE_FIFO_OUT, os.O_RDONLY | os.O_NONBLOCK)
				stdout_pipe_je = os.fdopen(stdout_fd, 'r', buffering=1)
				subprocess.Popen(je_terminal, cwd=directory)	#操作端末起動
				for channel in client.get_all_channels():
					if channel.name == Manage_Channel:
						await channel.send(f'JE鯖の起動命令を送ったナリよ')
				status = 1	#起動処理中から起動に変更
				pipe_flag_je = True	#パイプ接続
				print("JE起動成功")
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
					await channel.send(f"JE鯖は起動中なりを\r\nしばし待たれよ")
		else:
			print("多重起動防止")
			await interaction.response.send_message(f'JE鯖、生きてるってよ')
		return
	elif boot == "BE":
		await interaction.response.defer()
		global status_be
		global pipe_flag_be
		global stdin_pipe_be
		global stdout_pipe_be
		send_flag: bool = False	#メッセージ送信フラグ
		print("BE起動プロセス開始")
		try:
			subprocess.run(["pgrep", process_name_be], check=True)
			status_be = 1	#生存フラグ
		except subprocess.CalledProcessError:
			status_be = 0	#死亡フラグ
		#起動処理
		if status_be == 0:
			print("BE鯖アプデ確認")
			#SeleniumのFirefox仕込み
			options = webdriver.firefox.options.Options()
			options.add_argument('--headless')	#ヘッドレスモード
			options.binary_location = firefox_bin	#なんか知らんがsnap版だとこれじゃないと動かないんだとか
			driver = webdriver.Firefox(service=Service(firefoxdriver_bin), options=options)
			try:
				#MC公式からHTML取得
				driver.get("https://www.minecraft.net/ja-jp/download/server/bedrock")
				await asyncio.sleep(5)	#ページ読み込み待ち
				binary_url = driver.find_element(By.ID, "MC_Download_Server_2").get_attribute("href")	#URL取得
				driver.quit()	#ブラウザ終了
				print("BE鯖URL取得完了: " + binary_url)
				binary_name = os.path.basename(urlparse(binary_url).path)	#ファイル名抽出
				#既存ファイル名取得
				file_list = os.listdir(directory_be)
				zip_file: str = "bedrock-server-"
				for file in file_list:
					if zip_file in file:
						file_name = file
				print("ファイル名取得完了: " + binary_name)
				print("ファイル名比較\r\nローカル:" + file_name + "\r\nサーバー:" + binary_name)
				#実行ファイルの確認・アプデ周り
				if not os.path.isfile(directory_be + '/' + file_name):
					await interaction.followup.send("おい、BE鯖のデータが無いぞ\r\nという事でDLするナリよ～")
					print("BE鯖が無いのでDL")
					send_flag = True
					#実行ファイルダウンロード
					subprocess.run(["wget", "-P", directory_be, binary_url, "--no-check-certificate"])
					#展開
					shutil.unpack_archive(directory_be + '/' + binary_name, directory_be)
					#権限付与
					subprocess.run(["chmod", "755", process_name_be], cwd=directory_be)
					#通知
					for channel in client.get_all_channels():
						if channel.name == Manage_Channel:
							await channel.send("DL完了")
					print("BE鯖DL完了")
				#アプデ
				elif file_name != binary_name:
					await interaction.followup.send("BE鯖のアプデがあったぞ")
					print("BE鯖のアプデを実行")
					send_flag = True
					#既存ファイル削除
					os.remove(directory_be + '/' + file_name)
					#実行ファイルダウンロード
					subprocess.run(["wget", "-P", directory_be, binary_url, "--no-check-certificate"])
					print("BE鯖DL完了")
					#展開
					shutil.unpack_archive(directory_be + '/' + binary_name, directory_be + "/binary_temp")
					#上書きしたら困るやつを先に消す
					os.remove(directory_be + "/binary_temp/allowlist.json")
					os.remove(directory_be + "/binary_temp/permissions.json")
					os.remove(directory_be + "/binary_temp/server.properties")
					#既存ファイルを上書きコピー
					for item in os.listdir(directory_be + "/binary_temp"):
						s = os.path.join(directory_be + "/binary_temp", item)
						d = os.path.join(directory_be, item)
						if os.path.isdir(s):
							shutil.copytree(s, d, dirs_exist_ok=True)
						else:
							shutil.copy2(s, d)
					#展開用の一時フォルダを削除
					shutil.rmtree(directory_be + "/binary_temp")
					#権限付与
					subprocess.run(["chmod", "755", process_name_be], cwd=directory_be)
					#通知
					for channel in client.get_all_channels():
						if channel.name == Manage_Channel:
							await channel.send("アプデ完了")
			#例外処理
			except subprocess.CalledProcessError as e:
				await interaction.followup.send(f'なんか上手いこと行かなかったみたいですよ(subprocess例外)\r\n例外詳細:{e}')
				print("subprocess例外\r\n" + e)
			except selenium.common.exceptions.NoSuchElementException as e:
				await interaction.followup.send("多分HTML構造変わってる気がする\r\n例外内容:" + str(e))
				print("HTML構造変更?\r\n" + str(e))
			except selenium.timeout_exception.TimeoutException as e:
				await interaction.followup.send("通信が遅すぎますね…(タイムアウト)\r\n例外内容:" + str(e))
				print("タイムアウト\r\n" + str(e))
			except selenium.web_driver_exception.WebDriverException as e:
				await interaction.followup.send("Firefoxが立ち上がらないんだがバイナリの指定間違えてない?\r\n例外内容:" + str(e))
				print("Selenium起動失敗\r\n" + str(e))
			except selenium.invalid_selector_exception.InvalidSelectorException as e:
				await interaction.followup.send("強引にURLを取得する荒業が対処されたっぽいですね…(URL抽出元ID変更)\r\n例外内容:" + str(e))
				print("URL抽出元ID変更?\r\n" + str(e))
			except selenium.webdriver_exception.WebDriverException as e:
				await interaction.followup.send("Firefox周りでどうやらエラー吐いてるぞ\r\n例外内容:" + str(e))
				print("Firefox周りで例外\r\n" + str(e))
			except selenium.exception.Exception as e:
				await interaction.followup.send("Seleniumでよう分からん例外吐いた\r\n例外内容:" + str(e))
				print("Selenium例外\r\n" + str(e))
			except Exception as e:
				await interaction.followup.send("なんか知らんがBE鯖のアプデ確認に失敗しました\r\n例外内容:" + str(e))
				print("謎例外\r\n" + str(e))
			print("鯖が死んでたので起動")
			status_be = 2	#ステータスを起動処理中にする
			#フラグで送信方法変更
			if send_flag == False:	#返信で対応
				await interaction.followup.send("起動処理を実行します")
			else:	#新規送信で対応
				for channel in client.get_all_channels():
					if channel.name == Manage_Channel:
						await channel.send("起動処理を実行します")
			#バックアップ生成
			await create_backup(1)
			#メッセージ送信
			#鯖起動
			try:
				print("起動命令送信")
				#FIFOパイプ作成
				if os.path.exists(BE_FIFO_IN):
					os.remove(BE_FIFO_IN)
				if os.path.exists(BE_FIFO_OUT):
					os.remove(BE_FIFO_OUT)
				os.mkfifo(BE_FIFO_IN)
				os.mkfifo(BE_FIFO_OUT)
				#鯖起動
				screen_cmd = ["screen", "-dmS", session_name_be, "bash", "-c", be_start]
				subprocess.Popen(screen_cmd, cwd=directory_be)
				await asyncio.sleep(3)	#鯖起動待ち
				#パイプ接続
				stdin_pipe_be = open(BE_FIFO_IN, 'w', buffering=1)
				stdout_fd = os.open(BE_FIFO_OUT, os.O_RDONLY | os.O_NONBLOCK)
				stdout_pipe_be = os.fdopen(stdout_fd, 'r', buffering=1)
				subprocess.Popen(be_terminal, cwd=directory_be)	#操作端末起動
				for channel in client.get_all_channels():
					if channel.name == Manage_Channel:
						await channel.send(f'BE鯖の起動命令を送ったナリよ')
				status_be = 1	#起動処理中から起動に変更
				pipe_flag_be = True	#パイプ接続
				print("BE起動成功")
			except subprocess.CalledProcessError as e:
				print("起動例外\r\n" + e)
				for channel in client.get_all_channels():
					if channel.name == Manage_Channel:
						await channel.send(f'なんか上手いこと行かなかったみたいですよ(subprocess例外)\r\n例外詳細:{e}')
						status_be = 0	#死んだ扱いにする
		#多重起動防止
		elif status_be == 2:
			for channel in client.get_all_channels():
				if channel.name == Manage_Channel:
					await channel.send(f"BE鯖は起動中なりを\r\nしばし待たれよ")
		else:
			print("多重起動防止")
			await interaction.response.send_message(f'BE鯖、生きてるってよ')
		return
	else:
		await interaction.response.send_message(f'その引数は無効っスよ')

#死活確認
@tree.command(name="status", description="サーバープロセスが生きてるか確認します")
@describe(target="確認対象")
@app_commands.autocomplete(target=version_autocomplete)
async def com_status(interaction: discord.Interaction, target: str):
	if target == "JE":
		global status
		print("JE死活確認(コマンド)")
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
	elif target == "BE":
		global status_be
		print("BE死活確認(コマンド)")
		try:
			subprocess.run(["pgrep", process_name_be], check=True)
			status_be = 1	#生存フラグ
			for channel in client.get_all_channels():
				if channel.name == Manage_Channel:
					await interaction.response.send_message(f'生きてる')
			print("鯖生存")
		except subprocess.CalledProcessError:
			status_be = 0	#死亡フラグ
			for channel in client.get_all_channels():
				if channel.name == Manage_Channel:
					await interaction.response.send_message(f'陳死亡')
			print("鯖死亡")
		return
	else:
		await interaction.response.send_message(f'その引数は無効っスよ')

#自動スリープ切り替え
@tree.command(name="auto-sleep", description="自動スリープの設定をします")
@describe(switch="スイッチ")
@discord.app_commands.default_permissions(administrator=True)
async def sleep_switch(interaction: discord.Interaction, switch: bool):
	global auto_sleep
	global sleep
	if switch == True:
		auto_sleep = True
		sleep = 0
		await interaction.response.send_message(f'オートスリープを有効にしました')
		print("設定変更:オートスリープ有効")
	elif switch == False:
		auto_sleep = False
		await interaction.response.send_message(f'オートスリープを無効にしました')
		print("設定変更:オートスリープ無効")

#強制バックアップ
@tree.command(name="force-backup", description="バックアップ処理を強制実行します")
@describe(target="対象")
@app_commands.autocomplete(target=version_autocomplete)
@discord.app_commands.default_permissions(administrator=True)
async def force_backup(interaction: discord.Interaction, target: str):
	try:
		if not target != "JE" and target != "BE":
			await interaction.response.send_message(f'その引数は無効っスよ')
		else:
			await interaction.response.defer()
			#ファイル名生成
			timestamp: str = datetime.now().strftime("%Y%m%d-%H%M%S")
			if target == "JE":
				filename: str = f"force-world-{timestamp}.tar.xz"
			elif target == "BE":
				filename: str = f"force-be-world-{timestamp}.tar.xz"
			#.tar.xzで圧縮
			print("圧縮開始")
			if target == "JE":
				subprocess.run(["tar", "-I", "pixz", "-cvpf", filename, "-C", directory + "/world", "./"], check=True, cwd = backup)	#pixzに投げる
			elif target == "BE":
				subprocess.run(["tar", "-I", "pixz", "-cvpf", filename, "-C", directory_be + "/worlds", "./world"], check=True, cwd = backup_be)	#pixzに投げる
			print("xzで圧縮")
			await interaction.followup.send(f'バックアップを生成しました')
			#クラウドにバックアップするか
			if cloud_swtich == True:
				if target == "JE":
					cloud_backup: str = get_latest_backup_file(cloud, 0)	#既存バックアップ名取得(JE)
				elif target == "BE":
					cloud_backup: str = get_latest_backup_file(cloud, 1)	#既存バックアップ名取得(BE)
				#バックアップが既にある場合は消去してコピー
				if cloud_backup != "":
					os.remove(cloud + "/" + cloud_backup)
				if target == "JE":
					shutil.copy(backup + "/" + filename, cloud)
				elif target == "BE":
					shutil.copy(backup_be + "/" + filename, cloud)
			#古いバックアップ削除
			if backup_remove == True:
				if target == "JE":
					files = glob(f"{backup}/force-world-????????-??????.tar.xz")
					if len(files) > backup_limit:
						files.sort(key=os.path.getmtime)
						for file in files[:-backup_limit]:
							os.remove(file)
							print(f"古いバックアップファイルを削除しました: {file}")
				elif target == "BE":
					files = glob(f"{backup_be}/force-be-world-????????-??????.tar.xz")
					if len(files) > backup_limit:
						files.sort(key=os.path.getmtime)
						for file in files[:-backup_limit]:
							os.remove(file)
							print(f"古いバックアップファイルを削除しました: {file}")
	#例外処理
	except subprocess.CalledProcessError as e:
		print("圧縮例外\r\n" + e)
		for channel in client.get_all_channels():
			if channel.name == Manage_Channel:
				await channel.send(f'なんか上手いこと行かなかったみたいですよ(subprocess例外)\r\n例外詳細:{e}')
	except Exception as e:
			print(f"Exception\r\n" + e)
			for channel in client.get_all_channels():
				if channel.name == Manage_Channel:
					await channel.send(f'なんかやらかしてるみたいですよ…\r\n詳細:{e}')

#デバッグ用
@tree.command(name="debug", description="状態変数を返します")
async def debug(interaction: discord.Interaction):
	await interaction.response.defer()
	global status
	global status_be
	global auto_sleep
	global sleep
	global counter
	global process_name
	global process_name_be
	pid = get_pid(0)
	pid_be = get_pid(1)
	if pid == None:
		pid = "(プロセス無し)"
	if pid_be == None:
		pid_be = "(プロセス無し)"
	if status == 0:
		state = "0(プロセス無し)"
	elif status == 1:
		state = "1(プロセス実行中)"
	elif status == 2:
		state = "2(起動処理中)"
	if status_be == 0:
		state_be = "0(プロセス無し)"
	elif status_be == 1:
		state_be = "1(プロセス実行中)"
	elif status_be == 2:
		state_be = "2(起動処理中)"
	await interaction.followup.send("status:" + state + "\r\nstatus_be:" + state_be + "\r\n自動スリープフラグ:" + str(auto_sleep) + "\r\n待機時間:" + str(sleep) + "\r\n同時アクセス数:" + str(counter) + "\r\n" + process_name + "のPID:" + pid + "\r\n" + process_name_be + "のPID:" + pid_be)
	return

#プレイヤー数取得
@tree.command(name="players", description="プレイヤー数を表示します")
async def com_start(interaction: discord.Interaction):
	await interaction.response.defer()
	#JE
	try:
		JE_Status = JE_server.status()
		player_je = JE_Status.players.online
	except ConnectionRefusedError:
		player_je = 0
	except TimeoutError:
		player_je = 0
	#BE
	try:
		BE_Status = BE_server.status()
		player_be = BE_Status.players.online
	except ConnectionRefusedError:
		player_be = 0
	except TimeoutError:
		player_be = 0
	await interaction.followup.send("現在JE鯖には" + str(player_je) + "人が、BE鯖には" + str(player_be) + "人が接続しています。")
	return

#サーバー停止処理
@tree.command(name="stop", description="サーバープロセスを停止します")
@describe(target="対象")
@app_commands.autocomplete(target=version_autocomplete)
@discord.app_commands.default_permissions(administrator=True)
async def mc_stop(interaction: discord.Interaction, target: str):
	if target == "JE":
		print("JE停止プロセス開始")
		result = mcstop(0)
		if result == True:
			await interaction.response.send_message(f'JE鯖の停止命令を送ったナリよ')
		else:
			await interaction.response.send_message(f'なんか上手いこと行かなかったみたいですよ\r\n例外詳細:{result}')
		return
	elif target == "BE":
		print("BE停止プロセス開始")
		result = mcstop(1)
		if result == True:
			await interaction.response.send_message(f'BE鯖の停止命令を送ったナリよ')
		else:
			await interaction.response.send_message(f'なんか上手いこと行かなかったみたいですよ\r\n例外詳細:{result}')
		return
	else:
		await interaction.response.send_message(f'その引数は無効っスよ')

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
