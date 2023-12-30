"""クランメンバーの所持艦艇をCSVに出力する
使い方: python own_ships_writer.py -- -K2-
"""
import requests
from datetime import datetime
import csv
import argparse

REGION = "asia"
APPID = "13c400cd6d56dfe666688d93a2a45759"

API_DOMAINS = {
    "eu": "api.worldofwarships.eu",
    "na": "api.worldofwarships.com",
    "asia": "api.worldofwarships.asia",
}

SHIP_TYPE_PRIORITY = {
    "Submarine": 1,
    "Destroyer": 2,
    "Cruiser": 3,
    "Battleship": 4,
    "AirCarrier": 5,
    "Auxiliary": 999,
}

SHIP_TYPE_SHORT = {
    "Submarine": "SS",
    "Destroyer": "DD",
    "Cruiser": "CL",
    "Battleship": "BB",
    "AirCarrier": "CV",
    "Auxiliary": "AUX",
}


def int_to_roman(num: int) -> str:
    if num == 11:
        return "★"

    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syb = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
    roman_num = ""
    i = 0
    while num > 0:
        for _ in range(num // val[i]):
            roman_num += syb[i]
            num -= val[i]
        i += 1

    return roman_num


def request_get(url: str, params: dict) -> dict:
    response = requests.get(url, params=params).json()
    if response["status"] != "ok":
        raise ValueError(f"API通信に失敗しました: {response}")
    return response


def fetch_clan_id(clan_tag: str) -> int:
    print("クランIDを取得中...", end="", flush=True)

    response = request_get(
        f"https://{API_DOMAINS[REGION]}/wows/clans/list/",
        params={
            "application_id": APPID,
            "search": clan_tag,
            "fields": "tag,clan_id",
        },
    )
    clan_id = next(
        (clan["clan_id"] for clan in response["data"] if clan["tag"] == clan_tag), 0
    )
    if clan_id == 0:
        raise ValueError(f"クランタグが見つかりませんでした: {clan_tag}")

    print("完了")
    return clan_id


def fetch_account_ids_of_clan(clan_id: int) -> list[int]:
    print("クランメンバーのアカウントIDを取得中...", end="", flush=True)

    response = request_get(
        f"https://{API_DOMAINS[REGION]}/wows/clans/info/",
        params={
            "application_id": APPID,
            "clan_id": clan_id,
            "fields": "members_ids",
        },
    )

    print("完了")
    return response["data"][str(clan_id)]["members_ids"]


def fetch_ign(account_ids: list[int]) -> dict[int, str]:
    print("IGNを取得中...", end="", flush=True)

    response = request_get(
        f"https://{API_DOMAINS[REGION]}/wows/account/info/",
        params={
            "application_id": APPID,
            "account_id": ",".join(map(str, account_ids)),
            "field": "nickname",
        },
    )

    print("完了")
    return {
        account_id: response["data"][str(account_id)]["nickname"]
        for account_id in account_ids
    }


def fetch_ships() -> dict[str, any]:
    print("艦情報を取得中...", end="", flush=True)

    def fetch(pageNo):
        return request_get(
            f"https://{API_DOMAINS[REGION]}/wows/encyclopedia/ships/",
            params={
                "application_id": APPID,
                "language": "ja",
                "fields": "type,tier,name",
                "page_no": pageNo,
            },
        )

    ships = []
    encyc_ships = fetch(1)
    page_total = encyc_ships["meta"]["page_total"]

    for i in range(1, page_total + 1):
        encyc_ships = fetch(i)
        ships.extend(
            {
                "id": ship_id,
                "tier": value["tier"],
                "type": value["type"],
                "name": value["name"],
            }
            for ship_id, value in encyc_ships["data"].items()
        )

    ships.sort(
        key=lambda x: (
            x["tier"],
            SHIP_TYPE_PRIORITY[x["type"]],
            x["name"],
        )
    )

    ship_map = {
        ship["id"]: {
            "tier": ship["tier"],
            "type": ship["type"],
            "name": ship["name"],
        }
        for ship in ships
        if not (ship["name"].startswith("[") and ship["name"].endswith("]"))
    }

    print("完了")
    return ship_map


def fetch_owned_ship_ids(account_ids) -> dict[int, list[int]]:
    print("プレイヤーの所持艦艇を取得中...", end="", flush=True)

    result = {}
    for account_id in account_ids:
        response = requests.get(
            f"https://{API_DOMAINS[REGION]}/wows/ships/stats/",
            params={
                "application_id": APPID,
                "account_id": account_id,
                "fields": "ship_id",
            },
        ).json()

        result[account_id] = [
            str(ship["ship_id"]) for ship in response["data"][str(account_id)]
        ]

    print("完了")
    return result


def output_as_csv(account_ids, player_map, ship_map):
    headers = ["Tier", "艦名", "艦種"] + [
        player_map[account_id]["ign"] for account_id in account_ids
    ]

    rows = [
        [
            int_to_roman(ship["tier"]),
            ship["name"],
            SHIP_TYPE_SHORT[ship["type"]],
        ]
        + [
            "◯" if str(ship_id) in player_map[account_id]["ship_ids"] else ""
            for account_id in account_ids
        ]
        for ship_id, ship in ship_map.items()
    ]

    output_file_name = f"shiplist_{int(datetime.now().timestamp())}.csv"
    with open(output_file_name, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"CSVに出力しました: {output_file_name}")


def main():
    # コマンドライン引数の取得
    parser = argparse.ArgumentParser()
    parser.add_argument("clan_tag", type=str, help="クランタグ")
    args = parser.parse_args()
    clan_tag = args.clan_tag

    # クランIDの取得
    clan_id = fetch_clan_id(clan_tag)

    # クランメンバーのアカウントIDの取得
    account_ids = fetch_account_ids_of_clan(clan_id)
    player_map = {account_id: {"ign": "", "ship_ids": []} for account_id in account_ids}

    # IGNの取得
    ign_map = fetch_ign(account_ids)
    for account_id in account_ids:
        player_map[account_id]["ign"] = ign_map[account_id]

    # 艦情報の取得
    ship_map = fetch_ships()

    # 保持艦のIDを取得
    owned_ship_ids_map = fetch_owned_ship_ids(account_ids)
    for account_id in account_ids:
        player_map[account_id]["ship_ids"] = owned_ship_ids_map[account_id]

    # 出力
    output_as_csv(account_ids, player_map, ship_map)


if __name__ == "__main__":
    main()
