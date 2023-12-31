"""クランメンバーの所持艦艇をCSVに出力する
使い方: python own_ships_writer.py -- -K2-
"""
from datetime import datetime
import argparse
import util

REGION = "asia"
APPID = "13c400cd6d56dfe666688d93a2a45759"


class Player:
    ign: str
    owned_ship_ids: list[int]


class Warship:
    tier: int
    type: str
    typeShort: str
    name: str

    def __init__(self, tier: int, type: str, name: str):
        self.tier = tier
        self.type = type
        self.name = name


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


def fetch_clan_id(clan_tag: str) -> int:
    response = util.request_get(
        f"https://{API_DOMAINS[REGION]}/wows/clans/list/",
        params={
            "application_id": APPID,
            "search": clan_tag,
            "fields": ",".join(["tag", "clan_id"]),
        },
    )

    clan_id = next(
        (clan["clan_id"] for clan in response["data"] if clan["tag"] == clan_tag), 0
    )
    if clan_id == 0:
        raise ValueError(f"クランタグが見つかりませんでした: {clan_tag}")

    return clan_id


def fetch_account_ids_of_clan(clan_id: int) -> list[int]:
    response = util.request_get(
        f"https://{API_DOMAINS[REGION]}/wows/clans/info/",
        params={
            "application_id": APPID,
            "clan_id": str(clan_id),
            "fields": "members_ids",
        },
    )

    return response["data"][str(clan_id)]["members_ids"]


def fetch_ign(account_ids: list[int]) -> dict[int, str]:
    response = util.request_get(
        f"https://{API_DOMAINS[REGION]}/wows/account/info/",
        params={
            "application_id": APPID,
            "account_id": ",".join(map(str, account_ids)),
            "field": "nickname",
        },
    )

    return {
        account_id: response["data"][str(account_id)]["nickname"]
        for account_id in account_ids
    }


def fetch_ships() -> dict[int, Warship]:
    def fetch(pageNo):
        return util.request_get(
            f"https://{API_DOMAINS[REGION]}/wows/encyclopedia/ships/",
            params={
                "application_id": APPID,
                "language": "ja",
                "fields": ",".join(["type", "tier", "name"]),
                "page_no": pageNo,
            },
        )

    response = fetch(1)
    page_total = int(response["meta"]["page_total"])

    ships = []
    for i in range(2, page_total + 1):
        response = fetch(i)
        ships.extend(
            {
                "id": ship_id,
                "tier": value["tier"],
                "type": value["type"],
                "name": value["name"],
            }
            for ship_id, value in response["data"].items()
        )

    ships.sort(
        key=lambda x: (
            x["tier"],
            SHIP_TYPE_PRIORITY[x["type"]],
            x["name"],
        )
    )

    result = {
        int(ship["id"]): Warship(ship["tier"], ship["type"], ship["name"])
        for ship in ships
        if not (ship["name"].startswith("[") and ship["name"].endswith("]"))
    }

    return result


def fetch_owned_ship_ids(account_ids) -> dict[int, list[int]]:
    result = {}
    for account_id in account_ids:
        response = util.request_get(
            f"https://{API_DOMAINS[REGION]}/wows/ships/stats/",
            params={
                "application_id": APPID,
                "account_id": account_id,
                "fields": "ship_id",
                "extra": ",".join(
                    [
                        "club",
                        "oper_div",
                        "oper_div_hard",
                        "oper_solo,pve",
                        "rank_div2",
                        "rank_div3",
                        "rank_solo",
                    ]
                ),
            },
        )

        result[account_id] = [
            int(ship["ship_id"]) for ship in response["data"][str(account_id)]
        ]

    return result


def output_as_csv(
    filename: str,
    account_ids: list[int],
    player_map: dict[int, Player],
    ship_map: dict[int, Warship],
):
    headers = ["Tier", "艦名", "艦種"] + [
        player_map[account_id].ign for account_id in account_ids
    ]

    rows = [
        [
            util.to_roman_tier(ship.tier),
            ship.name,
            SHIP_TYPE_SHORT[ship.type],
        ]
        + [
            "◯" if ship_id in player_map[account_id].owned_ship_ids else ""
            for account_id in account_ids
        ]
        for ship_id, ship in ship_map.items()
    ]

    util.save_as_csv(filename, headers, rows)


def main():
    # コマンドライン引数の取得
    parser = argparse.ArgumentParser()
    parser.add_argument("clan_tag", type=str, help="クランタグ")
    args = parser.parse_args()
    clan_tag = args.clan_tag

    allStep = 5
    currentStep = 0

    # 艦情報の取得
    currentStep += 1
    print(f"({currentStep}/{allStep}) 艦情報を取得中...", end="", flush=True)
    ship_map = fetch_ships()
    print("完了")

    # クランIDの取得
    currentStep += 1
    print(f"({currentStep}/{allStep}) クランIDを取得中...", end="", flush=True)
    clan_id = fetch_clan_id(clan_tag)
    print("完了")

    # クランメンバーのアカウントIDの取得
    currentStep += 1
    print(f"({currentStep}/{allStep}) クランメンバーのアカウントIDを取得中...", end="", flush=True)
    account_ids = fetch_account_ids_of_clan(clan_id)
    player_map = {account_id: Player() for account_id in account_ids}
    print("完了")

    # IGNの取得
    currentStep += 1
    print(f"({currentStep}/{allStep}) IGNを取得中...", end="", flush=True)
    ign_map = fetch_ign(account_ids)
    for account_id in account_ids:
        player_map[account_id].ign = ign_map[account_id]
    print("完了")

    # 保持艦のIDを取得
    currentStep += 1
    print(f"({currentStep}/{allStep}) プレイヤーの所持艦艇を取得中...", end="", flush=True)
    owned_ship_id_map = fetch_owned_ship_ids(account_ids)
    for account_id in account_ids:
        player_map[account_id].owned_ship_ids = owned_ship_id_map[account_id]
    print("完了")

    # 出力
    output_file_name = f"shiplist_{int(datetime.now().timestamp())}.csv"
    output_as_csv(output_file_name, account_ids, player_map, ship_map)
    print(f"CSVに出力しました: {output_file_name}")


if __name__ == "__main__":
    main()
