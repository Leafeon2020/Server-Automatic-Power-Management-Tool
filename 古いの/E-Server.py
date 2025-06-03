#Create by Infinity.ELF
#License: GPLv3

#起動の前に 以下の環境が必要になります
#OS:Linux
#Pythonライブラリ:discord.py
#必要な外部ソフト:wakeonlan

#Discord類のインポート
import discord # type: ignore
from discord import app_commands # type: ignore
from discord.ext import tasks # type: ignore
#システム系のインポート
import subprocess

#初期設定
TOKEN: str = "https://steadiness-law.jp/"	#Botのトークン
intents = discord.Intents.default()	#反応イベント指定
client = discord.Client(intents=intents)	#Botクライアント読み込み
tree = app_commands.CommandTree(client)	#コマンド類宣言

#変数類
#Pythonはvarで自動宣言するけどC#のノリで型指定してます
global status	#グローバル変数化 Pythonの仕様上関数ごとに呼び出さないといけないらしい
status: int = 0	#プロセス状態用フラグ 0で落ちてて1で生きてる2で起動処理中
Manage_Channel: str = "うんち"	#書き込み先
host: str = "192.168.1.2"   #ping確認対象
mac: str = "AB:CD:EF:12:34:56"	#対象MACアドレス

#本体
#起動時処理
@client.event
async def on_ready():
	global status
	print("監視サーバー、起動!w")
	await client.change_presence(activity=discord.Game("開示請求を棄却中…"))
	await tree.sync()	#コマンド読み込み
	#書き込み先チャンネルID取得
	for channel in client.get_all_channels():
		if channel.name == Manage_Channel:
			await channel.send("https://i.imgur.com/ySa5Rf3.png")	#起動通知
	#鯖生存確認
	print("ping確認")
	result = subprocess.run(['ping', host, "-c", "3"], capture_output=True, text=True)	#pingが返ってくるかで死活確認 3回送って全部不通だったら死んでる判定
	if result.returncode == 0:
		status = 1	#生存フラグ
		print("生きてる")
	else:	#死んでる時
		status = 0	#死亡フラグ
		for channel in client.get_all_channels():
			if channel.name == Manage_Channel:
				await channel.send(f'ごりん終、だな')
		print("死んでる")
	task.start()	#死活確認起動
	await tree.sync()
	return

#監視処理
@tasks.loop(seconds=60)	#毎分確認
async def task():
	global status
	print("死活確認中")
	if status == 1:	#プロセスが死んでたらスルー(連投対策)
		result = subprocess.run(['ping', host , "-c", "3"], capture_output=True, text=True)
		if result.returncode == 0:
			status = 1	#生存フラグ
			print("生きてた")
		else:
			status = 0	#死亡フラグ
			for channel in client.get_all_channels():
				if channel.name == Manage_Channel:
					await channel.send("https://i.imgur.com/AXm3PRM.png")
			print("死んでた")
	elif status == 2:	#起動処理中の処理
		result = subprocess.run(['ping', host, "-c", "3"], capture_output=True, text=True)
		if result.returncode == 0:	#pingが返ってきたら生存状態にする
			status = 1	#生存フラグ
			for channel in client.get_all_channels():
				if channel.name == Manage_Channel:
					await channel.send("サーバーマシンが起動しました")
			print("サーバー起動")
		else:
			print("まだ起動してない")
	return

#コマンド処理
#死活確認
@tree.command(name="ping", description="サーバーマシンにpingを送ります")
async def check(interaction: discord.Interaction):
	global status
	await interaction.response.defer()
	if status != 2:	#サーバーが死んでたらスルー(連投対策)
		print("死活確認(コマンド)")
		result = subprocess.run(['ping', host, "-c", "3"], capture_output=True, text=True)
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
		result = subprocess.run(['ping', host, "-c", "3"], capture_output=True, text=True)
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
		result = subprocess.run(['ping', host, "-c", "3"], capture_output=True, text=True)
		if result.returncode == 0:
			await interaction.followup.send("大松「起きてるぞ」")
			print("起動済")
			status = 1
		else:
			try:
				subprocess.run(["wakeonlan", mac], check=True)
				await interaction.followup.send("起動命令を送信しました")
			except subprocess.CalledProcessError as e:
				print("subprocess例外")
				await interaction.followup.send("例外を吐きました\r\n内容は", e)
			print("WoL送信")
			status = 2
	else:
		await interaction.followup.send("鯖は起動中だ しばし待たれよ")
		print("起動待機のため中断")
	return

#デバッグ用
@tree.command(name="debug", description="状態変数を返します")
async def debug(interaction: discord.Interaction):
	global status
	if status == 0:
		state = "0(ping応答無し)"
	elif status == 1:
		state = "1(ping応答あり)"
	elif status == 2:
		state = "2(起動待機中)"
	await interaction.response.send_message("status:" + state)
	return

#終了処理
@tree.command(name="exit", description="電源管理botを終了させます")
@app_commands.default_permissions(administrator=True)
async def exit(interaction: discord.Interaction):
	print("bot終了")
	for channel in client.get_all_channels():
		if channel.name == Manage_Channel:
			await interaction.response.send_message(f'終了の時間だあああああああああああああああああああああああああああああああ！！！！！！！！！！！（ﾌﾞﾘﾌﾞﾘﾌﾞﾘﾌﾞﾘｭﾘｭﾘｭﾘｭﾘｭﾘｭ！！！！！！ﾌﾞﾂﾁﾁﾌﾞﾌﾞﾌﾞﾁﾁﾁﾁﾌﾞﾘﾘｲﾘﾌﾞﾌﾞﾌﾞﾌﾞｩｩｩｩｯｯｯ！！！！！！！）')
			await channel.send(f'Nuclear missile is launched!\r\n(意訳:botが爆発しました)')
	await client.close()
	exit()
	
#bot起動聖句
client.run(TOKEN)
