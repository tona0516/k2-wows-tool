import csv
import requests

def to_roman_tier(tier: int) -> str:
    if tier == 11:
        return "★"

    val = [10, 9, 5, 4, 1]
    syb = ["X", "IX", "V", "IV", "I"]
    roman_tier = ""
    i = 0
    while tier > 0:
        for _ in range(tier // val[i]):
            roman_tier += syb[i]
            tier -= val[i]
        i += 1

    return roman_tier


def request_get(url: str, params: dict[str, str]) -> any: # type: ignore
    response = requests.get(url, params=params).json()
    if response["status"] != "ok":
        raise ValueError(f"API通信に失敗しました: {response}")
    return response


def save_as_csv(filename: str, headers: list[str], rows: list[list[str]]):
    with open(filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)
