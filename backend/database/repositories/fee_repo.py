"""
database/repositories/fee_repo.py
─────────────────────────────────────────────────────────────
Repository for managing student fees and the immutable ledger.
Uses ACID transactions to guarantee zero financial data loss.
Includes Async Retries (3 attempts, 0.5s interval) for DB resilience.
─────────────────────────────────────────────────────────────
"""

import asyncio
from loguru import logger
from database.connection import get_pool

class FeeRepository:
    
    async def set_agreed_fee(self, org_id: str, student_id: str, amount: int) -> bool:
        """Sets the custom bargained fee for a specific student."""
        for attempt in range(3):
            try:
                pool = await get_pool()
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE students SET agreed_fee = $1 WHERE student_id = $2 AND org_id = $3",
                        amount, student_id, org_id
                    )
                    return True
            except Exception as e:
                if attempt == 2:
                    logger.error(f"DB Error setting agreed fee for {student_id}: {e}")
                    return False
                logger.warning(f"Retry {attempt + 1}/3 for set_agreed_fee... ({e})")
                await asyncio.sleep(0.5)

    async def log_payment(self, org_id: str, student_id: str, amount: int, recorded_by: str, receipt_file_id: str = None, notes: str = "Manual Payment") -> bool:
        """
        Logs a payment AND deducts from the running balance simultaneously.
        Wrapped in a strict database transaction.
        """
        for attempt in range(3):
            try:
                pool = await get_pool()
                async with pool.acquire() as conn:
                    # 🛡️ ACID Transaction starts here
                    async with conn.transaction():
                        # 1. Write the permanent receipt to the ledger
                        await conn.execute(
                            """
                            INSERT INTO fee_transactions 
                            (org_id, student_id, amount, transaction_type, receipt_file_id, recorded_by, notes)
                            VALUES ($1, $2, $3, 'PAYMENT', $4, $5, $6)
                            """,
                            org_id, student_id, amount, receipt_file_id, recorded_by, notes
                        )
                        
                        # 2. Subtract the amount from their live due balance
                        await conn.execute(
                            """
                            UPDATE students 
                            SET current_due = current_due - $1 
                            WHERE student_id = $2 AND org_id = $3
                            """,
                            amount, student_id, org_id
                        )
                    return True
            except Exception as e:
                if attempt == 2:
                    logger.error(f"CRITICAL: Payment transaction failed for {student_id}: {e}")
                    return False
                logger.warning(f"Retry {attempt + 1}/3 for log_payment... ({e})")
                await asyncio.sleep(0.5)

    async def generate_class_dues(self, org_id: str, class_name: str, recorded_by: str, custom_amount: int = None) -> int:
        """
        Mass-adds dues to a whole class at the start of the month.
        If custom_amount is given, uses that. Otherwise uses each student's 'agreed_fee'.
        Returns the number of students updated.
        """
        for attempt in range(3):
            try:
                pool = await get_pool()
                async with pool.acquire() as conn:
                    async with conn.transaction():
                        # Get the students to log the ledger entries (FIXED: class_name -> class)
                        students = await conn.fetch(
                            "SELECT student_id, agreed_fee FROM students WHERE org_id = $1 AND class = $2",
                            org_id, class_name
                        )
                        
                        if not students:
                            return 0
                            
                        count = 0
                        for s in students:
                            amount_to_add = custom_amount if custom_amount is not None else s['agreed_fee']
                            
                            if amount_to_add > 0:
                                # Log ledger
                                await conn.execute(
                                    """
                                    INSERT INTO fee_transactions 
                                    (org_id, student_id, amount, transaction_type, recorded_by, notes)
                                    VALUES ($1, $2, $3, 'DUE_ADDED', $4, $5)
                                    """,
                                    org_id, s['student_id'], amount_to_add, recorded_by, f"Bulk Due Added for {class_name}"
                                )
                                # Update balance
                                await conn.execute(
                                    "UPDATE students SET current_due = current_due + $1 WHERE student_id = $2",
                                    amount_to_add, s['student_id']
                                )
                                count += 1
                                
                        return count
            except Exception as e:
                if attempt == 2:
                    logger.error(f"DB Error generating dues for {class_name}: {e}")
                    return 0
                logger.warning(f"Retry {attempt + 1}/3 for generate_class_dues... ({e})")
                await asyncio.sleep(0.5)

    async def get_defaulters(self, org_id: str):
        """Fetches all students who currently owe money."""
        for attempt in range(3):
            try:
                pool = await get_pool()
                async with pool.acquire() as conn:
                    # FIXED: class_name -> class in SELECT and ORDER BY
                    rows = await conn.fetch(
                        """
                        SELECT student_id, name, class, parent_phone, current_due, agreed_fee
                        FROM students 
                        WHERE org_id = $1 AND current_due > 0
                        ORDER BY class, name
                        """,
                        org_id
                    )
                    return [dict(row) for row in rows]
            except Exception as e:
                if attempt == 2:
                    logger.error(f"DB Error fetching defaulters for {org_id}: {e}")
                    return []
                logger.warning(f"Retry {attempt + 1}/3 for get_defaulters... ({e})")
                await asyncio.sleep(0.5)

    async def get_student_ledger(self, org_id: str, student_id: str, limit: int = 10):
        """Gets the transaction history for a single student."""
        for attempt in range(3):
            try:
                pool = await get_pool()
                async with pool.acquire() as conn:
                    rows = await conn.fetch(
                        """
                        SELECT amount, transaction_type, created_at, receipt_file_id, notes
                        FROM fee_transactions 
                        WHERE org_id = $1 AND student_id = $2
                        ORDER BY created_at DESC LIMIT $3
                        """,
                        org_id, student_id, limit
                    )
                    return [dict(row) for row in rows]
            except Exception as e:
                if attempt == 2:
                    logger.error(f"DB Error fetching ledger for {student_id}: {e}")
                    return []
                logger.warning(f"Retry {attempt + 1}/3 for get_student_ledger... ({e})")
                await asyncio.sleep(0.5)
                
    async def get_org_financial_stats(self, org_id: str):
        """Calculates quick stats for the owner dashboard."""
        for attempt in range(3):
            try:
                pool = await get_pool()
                async with pool.acquire() as conn:
                    # Total Pending
                    pending_row = await conn.fetchrow(
                        "SELECT SUM(current_due) as total_pending FROM students WHERE org_id = $1 AND current_due > 0",
                        org_id
                    )
                    
                    # Total Collected (All time)
                    collected_row = await conn.fetchrow(
                        "SELECT SUM(amount) as total_collected FROM fee_transactions WHERE org_id = $1 AND transaction_type = 'PAYMENT'",
                        org_id
                    )
                    
                    return {
                        "total_pending": pending_row['total_pending'] or 0,
                        "total_collected": collected_row['total_collected'] or 0
                    }
            except Exception as e:
                if attempt == 2:
                    logger.error(f"DB Error fetching financial stats for {org_id}: {e}")
                    return {"total_pending": 0, "total_collected": 0}
                logger.warning(f"Retry {attempt + 1}/3 for get_org_financial_stats... ({e})")
                await asyncio.sleep(0.5)
            
