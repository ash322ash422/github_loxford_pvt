"""
toolkits/blacklist_toolkit.py
Blacklist tools used by the Blacklist Agent.
  • check_email     — check if email is blacklisted
  • check_merchant  — check if merchant is blacklisted
  • check_ip        — check if IP address is blacklisted
  • check_card      — check if card number is blacklisted
"""

import json
from langchain_core.tools import tool
from utils.db import fetch_one


def _check(entry_type: str, value: str) -> dict:
    row = fetch_one(
        "SELECT reason, added_date FROM blacklist WHERE entry_type=? AND value=?",
        (entry_type, value),
    )
    if row:
        return {"hit": True, "type": entry_type, "value": value, **row}
    return {"hit": False, "type": entry_type, "value": value}


@tool
def check_email(email: str) -> str:
    """Check if an email address appears on the fraud blacklist."""
    return json.dumps(_check("email", email))


@tool
def check_merchant(merchant: str) -> str:
    """Check if a merchant name appears on the fraud blacklist."""
    return json.dumps(_check("merchant", merchant))


@tool
def check_ip(ip_address: str) -> str:
    """Check if an IP address appears on the fraud blacklist."""
    return json.dumps(_check("ip", ip_address))


@tool
def check_card(card_number: str) -> str:
    """Check if a card number appears on the stolen/cloned card blacklist."""
    return json.dumps(_check("card", card_number))
