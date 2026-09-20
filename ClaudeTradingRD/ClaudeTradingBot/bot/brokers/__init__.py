"""Broker factory — execution backend selected by the BROKER env var.

BROKER=mt5      native MetaTrader5 terminal (Windows now, Windows EC2 on AWS)
BROKER=metaapi  MetaApi cloud REST (any OS — Linux/ECS/containers on AWS)
"""
import os

from dotenv import load_dotenv

load_dotenv()

_instance = None


def get_broker():
    global _instance
    if _instance is None:
        kind = os.getenv("BROKER", "mt5").lower()
        if kind in ("mt5", "mt5_native", "native"):
            from .mt5_native import Mt5NativeBroker
            _instance = Mt5NativeBroker()
        elif kind == "metaapi":
            from .metaapi import MetaApiBroker
            _instance = MetaApiBroker()
        else:
            raise ValueError(f"unknown BROKER={kind!r} (use 'mt5' or 'metaapi')")
    return _instance
