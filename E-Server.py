#Create by Infinity.ELF
#License: GPLv3

#起動の前に 以下の環境が必要になります
#OS:Linux
#Pythonライブラリ:discord.py
#必要な外部ソフト:wakeonlan

#恒心ログ
#2025/04/18 v1 - リリース
#2025/05/14 v2 - 再接続時の例外処理を実装
#2025/07/22 v3 - 起動待機中に起動しなかった場合にWoLを再送信する機能の実装
#2026/02/23 v4 - 遠隔起動のリトライ上限を設定
#2026/03/07 v5 - 変数の宣言忘れによるエラー解消
#2026/10/21 v6 - リトライ回数のガバ修正、P-Serverの開発版からメッセージ送信関数を移植
#2026/10/25 v7 - リトライ処理の時間設定が出来るように変更

#ToDo
#自動システムアプデ実装
#1画面用の恒心オプションを実装

#Discord類のインポート
import discord
from discord import app_commands
from discord.ext import tasks
#システム系のインポート
import subprocess

#初期設定
TOKEN: str = "https://steadiness-law.jp/"	#Botのトークン
intents = discord.Intents.default()	#反応イベント指定
client = discord.Client(intents=intents)	#Botクライアント読み込み
tree = app_commands.CommandTree(client)	#コマンド類宣言

#変数類
#Pythonはvarで自動宣言するけどC#のノリで型指定してます
#環境変数
Manage_Channel: str = "うんち"	#書き込み先
host: str = "192.168.1.2"   #ping確認対象
mac: str = "AB:CD:EF:12:34:56"	#対象MACアドレス
retry_limit: int = 5	#起動リトライ上限回数
retry_timer: int = 3	#起動リトライ間隔(分)

#システム用変数 触るな
status: int = 0	#鯖状態用フラグ 0で落ちてて1で生きてる2で起動処理中
timer: int = 0	#起動監視タイマー
counter: int = 0	#起動回数カウント用

#本体
#投稿
async def post_message(message: str):
	#チャンネル識別
	for channel in client.get_all_channels():
		if channel.name == Manage_Channel:
			await channel.send(message)

#起動時処理
@client.event
async def on_ready():
	global status
	print("監視サーバー、起動!w")
	await client.change_presence(activity=discord.Game("開示請求を棄却中…"))
	await tree.sync()	#コマンド読み込み
	#書き込み先チャンネルID取得
	await post_message("https://i.imgur.com/ySa5Rf3.png")	#起動通知
	#鯖生存確認
	result = subprocess.run(['ping', host, "-c", "3"], capture_output=True, text=True)	#pingが返ってくるかで死活確認 3回送って全部不通だったら死んでる判定
	print("ping確認")
	if result.returncode == 0:	#生きてた時
		status = 1	#生存フラグ
		print("生きてる")
	else:	#死んでる時
		status = 0	#死亡フラグ
		await post_message(f'ごりん終、だな')
		print("死んでる")
	try:
		task.start()	#死活確認起動
	except:
		print("死活確認起動済")
	await tree.sync()
	return

#監視処理
@tasks.loop(minutes=1)	#毎分確認
async def task():
	global status
	global timer
	global counter
	print("死活確認中")
	if status == 1:	#鯖が死んでたらスルー(連投対策)
		result = subprocess.run(['ping', host, "-c", "3"], capture_output=True, text=True)	#pingが返ってくるかで死活確認 3回送って全部不通だったら死んでる判定
		print("ping確認")
		if result.returncode == 0:
			status = 1	#生存フラグ
			print("生きてた")
		else:
			status = 0	#死亡フラグ
			await post_message("https://i.imgur.com/AXm3PRM.png")
			print("死んでた")
	elif status == 2:	#起動処理中の処理
		result = subprocess.run(['ping', host, "-c", "3"], capture_output=True, text=True)	#pingが返ってくるかで死活確認 3回送って全部不通だったら死んでる判定
		print("ping確認")
		if result.returncode == 0:	#pingが返ってきたら生存状態にする
			status = 1	#生存フラグ
			await post_message("サーバーマシンが起動しました")
			print("サーバー起動")
		else:
			timer += 1	#インクリメント
			print("まだ起動してない")
			if timer == retry_timer and counter < retry_limit:	#指定時間経過しても起動しない場合
				#再度WoLを送信
				try:
					subprocess.run(["wakeonlan", mac], check=True)
					await post_message(str(retry_timer) + "分経っても起床しないのでもう一度叩き起こしてみます")
					print("WoL再送信")
				#例外処理
				except subprocess.CalledProcessError as e:
					print("subprocess例外")
					await post_message("おおっと例外処理\r\n内容は" + str(e))
					status = 0	#死亡フラグ
				timer = 0	#リセット
				counter += 1	#起動回数カウント
			elif counter == retry_limit:	#リトライ上限到達
				print(str(retry_limit) + "回再試行したが失敗")
				await post_message(str(retry_limit) + "回叩き起こしたけど起動してないね MACアドレスとか間違えてない?")
				status = 0	#死亡フラグ
				timer = 0	#リセット
				counter = 0	#リセット
	return

#コマンド処理
#死活確認
@tree.command(name="ping", description="サーバーマシンにpingを送ります")
async def check(interaction: discord.Interaction):
	global status
	await interaction.response.defer()
	if status != 2:	#鯖が死んでたらスルー(連投対策)
		print("死活確認(コマンド)")
		result = subprocess.run(['ping', host, "-c", "3"], capture_output=True, text=True)	#pingが返ってくるかで死活確認 3回送って全部不通だったら死んでる判定
		print("ping確認")
		if result.returncode == 0:
			status = 1	#生存フラグ
			print("生きてた")
			await interaction.followup.send("生きてる")
		else:
			status = 0	#死亡フラグ
			print("死んでた")
			await interaction.followup.send("死んでる")
	elif status == 2:
		print("起動待機中")
		result = subprocess.run(['ping', host, "-c", "3"], capture_output=True, text=True)	#pingが返ってくるかで死活確認 3回送って全部不通だったら死んでる判定
		print("ping確認")
		if result.returncode == 0:	#pingが返ってきたら生存状態にする
			status = 1	#生存フラグ
			await interaction.followup.send("サーバーマシンが起動しました")
		else:
			await interaction.followup.send("起動処理中")
	return

#ブート処理
@tree.command(name="boot", description="サーバーマシンに起動命令を送ります")
async def boot(interaction: discord.Interaction):
	global status
	print("起動前死活確認")
	if status != 2:
		await interaction.response.defer()
		result = subprocess.run(['ping', host, "-c", "3"], capture_output=True, text=True)	#pingが返ってくるかで死活確認 3回送って全部不通だったら死んでる判定
		print("ping確認")
		if result.returncode == 0:
			await interaction.followup.send("大松「起きてるぞ」")
			print("起動済")
			status = 1	#生存フラグ
		else:
			try:
				subprocess.run(["wakeonlan", mac], check=True)
				await interaction.followup.send("起動命令を送信しました")
				print("WoL送信")
				status = 2	#起動待機フラグ
			except subprocess.CalledProcessError as e:
				print("subprocess例外")
				await interaction.followup.send("例外を吐きました\r\n内容は", e)
				status = 0	#死亡フラグ 一応折っておく
	else:
		await interaction.followup.send("鯖は起動中だ しばし待たれよ")
		print("起動待機のため中断")
	return

#デバッグ用
@tree.command(name="debug", description="状態変数を返します")
async def debug(interaction: discord.Interaction):
	global status
	if status == 0:
		state = "(ping応答無し)"
	elif status == 1:
		state = "(ping応答あり)"
	elif status == 2:
		state = "(起動待機中)"
	await interaction.response.send_message("status:" + str(status) + state + "\r\n起動回数:" + str(counter) + "\r\nタイマー:" + str(timer))
	return

#終了処理
@tree.command(name="exit", description="電源管理botを終了させます")
@app_commands.default_permissions(administrator=True)
async def exit(interaction: discord.Interaction):
	print("bot終了")
	await interaction.response.send_message(f'終了の時間だあああああああああああああああああああああああああああああああ！！！！！！！！！！！（ﾌﾞﾘﾌﾞﾘﾌﾞﾘﾌﾞﾘｭﾘｭﾘｭﾘｭﾘｭﾘｭ！！！！！！ﾌﾞﾂﾁﾁﾌﾞﾌﾞﾌﾞﾁﾁﾁﾁﾌﾞﾘﾘｲﾘﾌﾞﾌﾞﾌﾞﾌﾞｩｩｩｩｯｯｯ！！！！！！！）')
	await post_message(f'Nuclear missile is launched!\r\n(意訳:botが爆発しました)')
	await client.close()
	exit()
	
#bot起動聖句
client.run(TOKEN)
