"""
services/referral_service.py
─────────────────────────────────────────────────────────────
Referral Engine.

Each coaching gets a unique referral_code (e.g. KINETIC102).
When a new institution registers with a valid referral code:
  1. Validate referral_code exists
  2. Insert referral record linking referrer ↔ referred
  3. Apply 5% discount to referrer's next subscription
─────────────────────────────────────────────────────────────
"""

import random
import string
from typing import Optional

from loguru import logger

from database.connection import get_pool
from database.repositories.user_repo_security import AuditLogRepository

_audit = AuditLogRepository()


def generate_referral_code(org_name: str) -> str:
    """
    Generate unique referral code: first 6 letters of org name + 3 random digits.
    Example: KINETIC102, MUKESH834
    """
    prefix = "".join(c.upper() for c in org_name if c.isalpha())[:6]
    suffix = "".join(random.choices(string.digits, k=3))
    return f"{prefix}{suffix}"


async def validate_and_apply_referral(
    referral_code: str,
    referred_org_id: str,
) -> dict:
    """
    Validate a referral code during institution registration.
    If valid, create referral record and mark discount for referrer.
    """
    pool = await get_pool()

    async with pool.acquire() as conn:
        # Find the referring org by code
        row = await conn.fetchrow(
            "SELECT org_id FROM organizations WHERE referral_code = $1 AND status IN ('active','approved')",
            referral_code,
        )

    if not row:
        return {
            "valid": False,
            "message": "❌ Invalid referral code. Continuing without referral.",
        }

    referrer_org_id = row["org_id"]

    if referrer_org_id == referred_org_id:
        return {"valid": False, "message": "❌ Cannot use your own referral code."}

    # Check if this org was already referred (prevent double referral)
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT referral_id FROM referrals WHERE referred_org_id = $1",
            referred_org_id,
        )

    if existing:
        return {"valid": False, "message": "❌ Referral already applied."}

    # Insert referral record
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO referrals
                (org_id, referral_code, referring_org_id, referred_org_id, discount_percent)
            VALUES ($1, $2, $3, $4, 5.00)
            """,
            referrer_org_id, referral_code, referrer_org_id, referred_org_id,
        )

    await _audit.log(
        "REFERRAL_APPLIED",
        org_id=referrer_org_id,
        details={
            "referral_code": referral_code,
            "referred_org": referred_org_id,
            "discount": "5%",
        },
    )

    logger.info(f"Referral applied | referrer={referrer_org_id} | referred={referred_org_id}")

    return {
        "valid": True,
        "referrer_org_id": referrer_org_id,
        "discount_percent": 5.0,
        "message": "✅ Referral code applied! The referring coaching earned a 5% discount.",
    }


async def get_referral_info(org_id: str) -> str:
    """Display referral dashboard for an owner."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        org_row = await conn.fetchrow(
            "SELECT referral_code FROM organizations WHERE org_id = $1", org_id
        )
        referral_count = await conn.fetchval(
            "SELECT COUNT(*) FROM referrals WHERE referring_org_id = $1", org_id
        )
        total_discount = await conn.fetchval(
            "SELECT COALESCE(SUM(discount_percent), 0) FROM referrals WHERE referring_org_id = $1",
            org_id,
        )

    code = org_row["referral_code"] if org_row else "—"

    return (
        f"🎁 <b>Referral Program</b>\n\n"
        f"Your Referral Code: <code>{code}</code>\n\n"
        f"📊 Total Referrals: {referral_count}\n"
        f"💰 Total Discount Earned: {total_discount}%\n\n"
        f"Share your code with other coaching owners.\n"
        f"Each successful referral = <b>5% subscription discount</b>."
    )
