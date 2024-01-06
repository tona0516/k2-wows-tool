"""GUIを起動する
使い方: python gui.py
"""
import sys
import os

# ソースコード
import own_ships_writer as osw

# venv環境
# sys.path.append(".\venv\Lib")
import flet as ft

def Display(page: ft.Page):
	page.title = "k2-wows-tool gui"

	ftTF_ClanTag = ft.TextField(
		label="Clan tag"
	)

	def button_clicked(e):
		Run(ftTF_ClanTag.value)
		page.update()

	ftEB_Submit = ft.ElevatedButton(text="Submit", on_click=button_clicked)

	page.add(ftTF_ClanTag, ftEB_Submit)


def Run(clan_tag):
	# クランIDの取得
	clan_id = osw.fetch_clan_id(clan_tag)

	# クランメンバーのアカウントIDの取得
	account_ids = osw.fetch_account_ids_of_clan(clan_id)
	player_map = {account_id: {"ign": "", "ship_ids": []} for account_id in account_ids}

	# IGNの取得
	ign_map = osw.fetch_ign(account_ids)
	for account_id in account_ids:
		player_map[account_id]["ign"] = ign_map[account_id]

	# 艦情報の取得
	ship_map = osw.fetch_ships()

	# 保持艦のIDを取得
	owned_ship_ids_map = osw.fetch_owned_ship_ids(account_ids)
	for account_id in account_ids:
		player_map[account_id]["ship_ids"] = owned_ship_ids_map[account_id]

	# 出力
	osw.output_as_csv(account_ids, player_map, ship_map)


if __name__ == "__main__":
	ft.app(target=Display)