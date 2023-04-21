from web3 import Web3
import datetime
from termcolor import cprint
import time
import random
import sys
from consts import *
import configparser
from utils import *
from abi import *
import pandas as pd

config = configparser.ConfigParser()
config.read("config.ini", "utf-8")

WALLET_RESULTS = {}


def api_1inch_is_stable():
    _1inchurl = f"{base_url}/healthcheck"
    json_data = get_api_call_data(_1inchurl)

    if json_data["status"] == "OK":
        return True

    cprint(f"\nAPI 1inch не доступно! Дальнейшая работа не возможна!", "red")
    return False


def inch_swap(
    web3: Web3, private_key, NETWORK, swap_out_str, swap_in_str, my_address, amount
):
    if not api_1inch_is_stable():
        return 1

    now = datetime.datetime.now()
    now_dt = now.strftime("%d-%m-%Y %H:%M")
    amount_d = 0
    amount_str = 0
    swap_out_adr = Web3.to_checksum_address(network_erc20_addr[NETWORK][swap_out_str])
    swap_in_adr = Web3.to_checksum_address(network_erc20_addr[NETWORK][swap_in_str])
    try:
        if swap_out_str != "ETH":
            swap_out_ABI = network_erc20_abi[NETWORK][swap_out_str]
            swap_out_contract = get_erc20_contract(web3, swap_out_adr, swap_out_ABI)
            out_decimals = swap_out_contract.functions.decimals().call()
            amount_d = int_to_decimal(amount, out_decimals)
            amount_str = float_str(amount, out_decimals)

            out_allowance = inch_allowance(swap_out_adr, my_address)

            if int(out_allowance) <= amount_d:
                state = inch_set_approve(
                    web3, private_key, NETWORK, swap_out_adr, my_address
                )
                if not state:
                    return state
        else:
            amount_d = int_to_decimal(amount, 18)
            amount_str = float_str(amount, 18)
        _1inchurl = f"{base_url}/swap?fromTokenAddress={swap_out_adr}&toTokenAddress={swap_in_adr}&amount={amount_d}&fromAddress={my_address}&slippage={SLIPPAGE_1INCH}"
        json_data = get_api_call_data(_1inchurl)

        tx = json_data["tx"]
        tx["nonce"] = web3.eth.get_transaction_count(my_address)
        tx["to"] = Web3.to_checksum_address(tx["to"])
        tx["gasPrice"] = int(tx["gasPrice"])
        tx["value"] = int(tx["value"])
        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        txn_text = tx_hash.hex()

        cprint(
            f"\n{now_dt} {my_address} | УСПЕШНО обмен {amount_str} {swap_out_str} на {swap_in_str} tx {txn_explorer[NETWORK]}{txn_text}",
            "green",
        )
        return True

    except Exception as e:
        error_str = f"\n{now_dt} {my_address} | НЕУДАЧНО обмен {amount_str} {swap_out_str} на {swap_in_str} | {e}"
        if "description" in json_data.keys():
            error_des = json_data["description"]
            error_str += f"| {error_des}"

        cprint(error_str, "red")
        return False


def inch_set_approve(web3: Web3, private_key, NETWORK, swap_out_str, my_address):
    now = datetime.datetime.now()
    now_dt = now.strftime("%d-%m-%Y %H:%M")

    try:
        _1inchurl = f"{base_url}/approve/transaction?tokenAddress={swap_out_str}"
        tx = get_api_call_data(_1inchurl)

        tx["gasPrice"] = int(tx["gasPrice"])
        tx["from"] = Web3.to_checksum_address(my_address)
        tx["to"] = Web3.to_checksum_address(tx["to"])
        tx["value"] = int(tx["value"])
        tx["nonce"] = web3.eth.get_transaction_count(my_address)

        # Если транза зафейлиться, можно попробовать код ниже, увеличит на 25% объем газа который рекомендует сеть
        # можно применять в любой функции и контракте, оставляю здесь для заметки
        estimate = web3.eth.estimate_gas(tx)
        gas_limit = estimate
        tx["gas"] = gas_limit

        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        txn_text = tx_hash.hex()

        cprint(
            f"\n{now_dt} {my_address} | УСПЕШНО апрув на 1inch {swap_out_str} tx {txn_explorer[NETWORK]}{txn_text}",
            "green",
        )
        return True

    except Exception as e:
        error_str = (
            f"\n{now_dt} {my_address} | НЕУДАЧНО апрув на 1inch {swap_out_str} | {e}"
        )
        if "description" in tx.keys():
            error_des = tx["description"]
            error_str += f"| {error_des}"

        cprint(error_str, "red")
        return False


def inch_allowance(swap_out_adr, my_address):
    _1inchurl = f"{base_url}/approve/allowance?tokenAddress={swap_out_adr}&walletAddress={my_address}"
    json_data = get_api_call_data(_1inchurl)
    out_allowance = None

    if "allowance" in json_data.keys():
        out_allowance = json_data["allowance"]

    return out_allowance


def approve_contract(web3: Web3, private_key, NETWORK, adr_dict, my_address):
    try:
        approve_amount = 2**256 - 1
        now = datetime.datetime.now()
        now_dt = now.strftime("%d-%m-%Y %H:%M")

        contract = get_erc20_contract(web3, adr_dict["to_adr"])
        allowance = contract.functions.allowance(
            my_address, adr_dict["spender_adr"]
        ).call()

        if allowance == approve_amount:
            return True

        contract_txn = contract.functions.approve(
            adr_dict["spender_adr"], approve_amount
        ).build_transaction(
            {
                "from": my_address,
                "value": 0,
                "gasPrice": gas_price,
                "nonce": web3.eth.get_transaction_count(my_address),
            }
        )

        # Если транза зафейлиться, можно попробовать код ниже, увеличит на 25% объем газа который рекомендует сеть
        # можно применять в любой функции и контракте, оставляю здесь для заметки
        estimate = web3.eth.estimate_gas(contract_txn)
        gas_limit = estimate
        contract_txn["gas"] = gas_limit

        signed_txn = web3.eth.account.sign_transaction(contract_txn, private_key)
        txn_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        txn_text = txn_hash.hex()

        cprint(
            f"\n{now_dt} {my_address} | УСПЕШНО апрув {adr_dict['to_ticker']} для {adr_dict['spender_ticker']} tx {txn_explorer[NETWORK]}{txn_text}",
            "green",
        )
        return True

    except Exception as error:
        cprint(
            f"\n{now_dt} {my_address} | НЕУДАЧНО апрув {adr_dict['to_ticker']} для {adr_dict['spender_ticker']} | {error}",
            "red",
        )
        return False


def lock_STG(web3: Web3, private_key, NETWORK, my_address, amount):
    try:
        now = datetime.datetime.now()
        now_dt = now.strftime("%d-%m-%Y %H:%M")

        contr_addr = Web3.to_checksum_address(network_erc20_addr[NETWORK]["veSTG"])
        contr_addr_ABI = network_erc20_abi[NETWORK]["veSTG"]
        contr = get_erc20_contract(web3, contr_addr, contr_addr_ABI)
        out_decimals = contr.functions.decimals().call()
        amount_d = int_to_decimal(amount, out_decimals)
        amount_str = float_str(amount)
        rand_month = getRandomMonth()
        WALLET_RESULTS[my_address]["stg_lock_time"] = rand_month
        time = monthsToEpoch(rand_month)
        contract_txn = contr.functions.create_lock(amount_d, time).build_transaction(
            {
                "from": my_address,
                "value": 0,
                "gasPrice": web3.eth.gas_price,
                "nonce": web3.eth.get_transaction_count(my_address),
            }
        )

        signed_txn = web3.eth.account.sign_transaction(contract_txn, private_key)
        txn_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        txn_text = txn_hash.hex()

        cprint(
            f"\n{now_dt} {my_address} | УСПЕШНО lock {amount_str} STG tx {txn_explorer[NETWORK]}{txn_text}",
            "green",
        )

    except Exception as error:
        cprint(
            f"\n{now_dt} {my_address} | НЕУДАЧНО lock {amount_str} STG | {error}", "red"
        )


def add_liquidity_token(web3, token, amount, my_address):
    try:
        contr_addr = Web3.to_checksum_address(
            STARGATE_ROUTER_ADDR
        )  # Stargate Finance: Router
        contr = get_erc20_contract(web3, contr_addr, STARGATE_TOKEN_ROUTER_ABI)
        decimal = 6  # будет разный от суммы, в нашем случае для х.хх
        amount_d = int_to_decimal(amount, decimal)
        pool_id = POOLS[token]
        amount_str = float_str(amount_d, decimal)
        WALLET_RESULTS[my_address]["stake_amount"] = amount
        contract_txn = contr.functions.addLiquidity(
            pool_id, amount_d, my_address
        ).build_transaction(
            {
                "from": my_address,
                "value": 0,
                "gasPrice": web3.eth.gas_price,
                "nonce": web3.eth.get_transaction_count(my_address),
            }
        )
        return (contract_txn, amount)
    except Exception:
        return (amount,)


def add_liquidity_eth(web3, amount, my_address):
    try:
        contr_addr = Web3.to_checksum_address(
            STARGATE_ROUTER_ETH_ADDR
        )  # Stargate Finance: Router

        contr = get_erc20_contract(web3, contr_addr, STARGATE_ETH_ROUTER_ABI)
        decimal = 18  # будет разный от суммы, в нашем случае для х.хх
        amount_d = int_to_decimal(amount, decimal)
        amount_str = float_str(amount_d, decimal)
        WALLET_RESULTS[my_address]["stake_amount"] = amount
        contract_txn = contr.functions.addLiquidityETH().build_transaction(
            {
                "from": my_address,
                "value": amount_d,
                "gasPrice": web3.eth.gas_price,
                "nonce": web3.eth.get_transaction_count(my_address),
            }
        )
        return (contract_txn, amount)
    except Exception as e:
        return (amount,)


def add_liq(web3, private_key, NETWORK, my_address, token, amount):
    try:
        now = datetime.datetime.now()
        amount_str = 0
        contract_txn = None
        now_dt = now.strftime("%d-%m-%Y %H:%M")
        if token == "ETH":
            add_liq_result = add_liquidity_eth(web3, amount, my_address)
        else:
            add_liq_result = add_liquidity_token(token, amount)
        if len(add_liq_result) == 1:
            (amount_str,) = add_liq_result
            raise Exception("Add liquidity error")
        else:
            (contract_txn, amount_str) = add_liq_result
        signed_txn = web3.eth.account.sign_transaction(contract_txn, private_key)
        txn_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        txn_text = txn_hash.hex()

        cprint(
            f"\n{now_dt} {my_address} | УСПЕШНО add_liq_USDC {amount_str} tx {txn_explorer[NETWORK]}{txn_text}",
            "green",
        )
    except Exception as error:
        cprint(
            f"\n{now_dt} {my_address} | НЕУДАЧНО add_liq_USDC {amount_str} | {error}",
            "red",
        )


def deposit_farm(web3, private_key, NETWORK, my_address, amount):
    try:
        now = datetime.datetime.now()
        now_dt = now.strftime("%d-%m-%Y %H:%M")

        contr_addr = Web3.to_checksum_address(
            STARGATE_STAKING_ADDR
        )  # Stargate Finance: LP Staking
        contr_ABI = STARGATE_STAKING_ABI
        contr = get_erc20_contract(web3, contr_addr, contr_ABI)
        decimal = 6
        amount_d = int_to_decimal(amount, decimal)  # S*USDC
        amount_str = float_str(amount, decimal)

        contract_txn = contr.functions.deposit(0, amount_d).build_transaction(
            {
                "from": my_address,
                "value": 0,
                "gasPrice": web3.eth.gas_price,
                "nonce": web3.eth.get_transaction_count(my_address),
            }
        )

        signed_txn = web3.eth.account.sign_transaction(contract_txn, private_key)
        txn_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        txn_text = txn_hash.hex()

        cprint(
            f"\n{now_dt} {my_address} | УСПЕШНО deposit Stargate Finance: LP Staking {amount_str} S*USDC tx {txn_explorer[NETWORK]}{txn_text}",
            "green",
        )

    except Exception as error:
        cprint(
            f"\n{now_dt} {my_address} | НЕУДАЧНО deposit Stargate Finance: LP Staking {amount_str} S*USDC | {error}",
            "red",
        )


def SerializeResult():
    out = []
    for k, v in WALLET_RESULTS.items():
        out.append(v)
    pd.DataFrame(out).to_csv("output.csv", index=False)


if __name__ == "__main__":
    with open("private_keys.txt", "r") as f:
        keys_list = [row.strip() for row in f]
    random.shuffle(keys_list)
    if len(keys_list) == 0:
        cprint(f"\nСначала заполни private_keys.txt", "red")
        sys.exit(1)
    SerializeResult()
    for private_key in keys_list:
        web3 = Web3(Web3.HTTPProvider(RPC[NETWORK]))
        account = web3.eth.account.from_key(private_key)
        my_address = account.address
        gas_price = web3.eth.gas_price
        chain_id = web3.eth.chain_id
        base_url = f"https://api.1inch.io/v5.0/{chain_id}"
        WALLET_RESULTS[my_address] = {
            "address": my_address,
            "stg_lock_amount": 0,
            "stg_lock_time": 0,
            "stake_amount": 0,
        }
        swap_out_str = config["OPTIONS"]["selected_token"]
        swap_in_str = "STG"
        if config["OPTIONS"]["staking"] == "true":
            # 1) покупаем STG
            tokens_amount = getRandomTokensAmount()

            state = inch_swap(
                web3,
                private_key,
                NETWORK,
                swap_out_str,
                swap_in_str,
                my_address,
                tokens_amount,
            )
            if not state:
                sys.exit(state)

            # 2) начинаем апрув в контракте  STG Token для veSTG
            if swap_out_str != "ETH":
                aprove_adr_dict = {
                    "to_ticker": "STG",
                    "to_adr": Web3.to_checksum_address(
                        network_erc20_addr[NETWORK]["STG"]
                    ),
                    "spender_ticker": "veSTG",
                    "spender_adr": Web3.to_checksum_address(
                        network_erc20_addr[NETWORK]["veSTG"]
                    ),
                }
                approve_contract(
                    web3,
                    private_key,
                    NETWORK,
                    aprove_adr_dict,
                    my_address,
                )

            # 3) лочим STG на 36 месяцев, получаем veSTG
            STG_balance = get_token_balance(web3, NETWORK, my_address, swap_in_str)
            STG_amount = STG_balance
            if STG_amount < 27:
                cprint(
                    f"STG на балансе {STG_balance}, если оставить больше 100 монет на балансе, тогджа не хватит чтобы положить в пул, там нужно монет 27 минимум. \nЗавершение работы",
                    "red",
                )
                sys.exit(1)
            WALLET_RESULTS[my_address]["stg_lock_amount"] = STG_amount
            lock_STG(web3, private_key, NETWORK, my_address, STG_amount)
            time.sleep(
                random.randint(
                    int(config["RANGES"]["min_staking_liqudity_delay"]),
                    int(config["RANGES"]["max_staking_liqudity_delay"]),
                )
            )
        if config["OPTIONS"]["liquidity"] == "true":
            if swap_out_str != "ETH":
                # 4) начинаем апрув USDC для закидывания в ликву
                aprove_adr_dict = {
                    "to_ticker": config["OPTIONS"]["selected_token"],
                    "to_adr": Web3.to_checksum_address(
                        network_erc20_addr[NETWORK][config["OPTIONS"]["selected_token"]]
                    ),
                    "spender_ticker": "Stargate Finance: Router",
                    "spender_adr": Web3.to_checksum_address(STARGATE_ROUTER_ADDR),
                }
                approve_contract(
                    web3, private_key, NETWORK, aprove_adr_dict, my_address
                )
            # 5) теперь закидываем ликвидность в USDC
            amount = getRandomLiquidity()

            add_liq(web3, private_key, NETWORK, my_address, swap_out_str, amount)

            # 6) апрув S*USDC для Stargate Finance: LP Staking
            aprove_adr_dict = {
                "to_ticker": "S*USDC",
                "to_adr": Web3.to_checksum_address(
                    network_erc20_addr[NETWORK]["SUSDC"]
                ),
                "spender_ticker": "Stargate Finance: LP Staking",
                "spender_adr": Web3.to_checksum_address(STARGATE_STAKING_ADDR),
            }
            approve_contract(web3, private_key, NETWORK, aprove_adr_dict, my_address)

            # 7) депозитим в фарм
            SUSDC_amount = get_token_balance(web3, NETWORK, my_address, "SUSDC")
            deposit_farm(web3, private_key, NETWORK, my_address, SUSDC_amount)

        time.sleep(
            random.randint(
                int(config["RANGES"]["min_delay_in_seconds"]),
                int(config["RANGES"]["max_delay_in_seconds"]),
            )
        )
        SerializeResult()
