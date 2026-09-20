"""Connect to MetaTrader paper account via MetaApi SDK and print account state."""
import os, asyncio, json
from dotenv import load_dotenv
from metaapi_cloud_sdk import MetaApi

load_dotenv()


async def main():
    api = MetaApi(os.getenv("META_API_TOKEN"))
    account = await api.metatrader_account_api.get_account(os.getenv("META_ACCOUNT_ID"))
    print("name:", account.name, "| type:", account.type, "| state:", account.state,
          "| connection:", account.connection_status, "| region:", account.region)
    if account.state != "DEPLOYED":
        print("deploying...")
        await account.deploy()
    await account.wait_connected()
    conn = account.get_rpc_connection()
    await conn.connect()
    await conn.wait_synchronized()
    info = await conn.get_account_information()
    print("ACCOUNT_INFO:", json.dumps(info, indent=1, default=str))
    positions = await conn.get_positions()
    print("POSITIONS:", json.dumps(positions, indent=1, default=str))
    orders = await conn.get_orders()
    print("ORDERS:", json.dumps(orders, indent=1, default=str))
    price = await conn.get_symbol_price("XAUUSD")
    print("XAUUSD PRICE:", json.dumps(price, indent=1, default=str))
    await conn.close()


asyncio.run(main())
