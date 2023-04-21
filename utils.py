import time
import random
import configparser
from web3 import Web3
import json
from consts import *
import requests

config = configparser.ConfigParser()
config.read("config.ini", "utf-8")


def get_erc20_contract(web3, contract_address, ERC20_ABI=""):
    """Одинаковый ABI для всех ERC20 токенов, в ликвидности могут быть другие ABI"""

    if ERC20_ABI == "":
        ERC20_ABI = json.loads(
            """[{"inputs":[{"internalType":"string","name":"_name","type":"string"},{"internalType":"string","name":"_symbol","type":"string"},{"internalType":"uint256","name":"_initialSupply","type":"uint256"}],"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":true,"internalType":"address","name":"spender","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"from","type":"address"},{"indexed":true,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Transfer","type":"event"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"subtractedValue","type":"uint256"}],"name":"decreaseAllowance","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"addedValue","type":"uint256"}],"name":"increaseAllowance","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint8","name":"decimals_","type":"uint8"}],"name":"setupDecimals","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"sender","type":"address"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transferFrom","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"}]"""
        )

    contract = web3.eth.contract(
        Web3.to_checksum_address(contract_address), abi=ERC20_ABI
    )

    return contract


def get_contract_balance(contract, user_address):
    """Получает баланс любого токена ERC20, кроме нативного токена"""

    contract_func = contract.functions

    symbol = contract_func.symbol().call()
    balance_wei = contract_func.balanceOf(user_address).call()  # in Wei
    token_decimals = contract_func.decimals().call()
    balance = balance_wei / 10**token_decimals
    # token_name = contract_func.name().call()
    # allowance = contract_func.allowance(some_contract_address, user_address).call()

    return {"symbol": symbol, "balance": balance}


def get_token_balance(web3, NETWORK, address, ticker):
    contract = get_erc20_contract(web3, network_erc20_addr[NETWORK][ticker])
    balance_dict = get_contract_balance(contract, address)
    return balance_dict["balance"]


def get_api_call_data(url):
    try:
        call_data = requests.get(url)
    except Exception as e:
        print(e)
        return get_api_call_data(url)
    try:
        api_data = call_data.json()
        return api_data
    except Exception as e:
        print(call_data.text)


def monthsToEpoch(months: int):
    return int(time.time()) + (months * 30 * 24 * 60 * 60)


def int_to_decimal(qty, decimal):
    return int(qty * int("".join(["1"] + ["0"] * decimal)))


def decimal_to_int(price, decimal):
    return price / int("".join((["1"] + ["0"] * decimal)))


def float_str(amount, decimals=18):
    temp_str = "%0.18f"
    temp_str = temp_str.replace("18", str(decimals))
    text_float = temp_str % amount
    return text_float



def getRandomMonth():
    rand_month = random.randint(
        int(config["RANGES"]["min_time_in_months"]),
        int(config["RANGES"]["max_time_in_months"]),
    )
    return rand_month


def getRandomTokensAmount():
    return random.uniform(
        float(config["RANGES"]["min_tokens_amount"]),
        float(config["RANGES"]["max_tokens_amount"]),
    )


def getRandomLiquidity():
    return random.uniform(
            float(config["RANGES"]["min_liquidity_amount"]),
            float(config["RANGES"]["max_liquidity_amount"]),
        )
