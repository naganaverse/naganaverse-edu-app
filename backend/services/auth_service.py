"""
services/auth_service.py
─────────────────────────────────────────────────────────────
Authentication Service — handles all login flows:

  1. Auto-login:  telegram_id found in DB → load session directly
  2. Manual login: User ID + Password → verify → bind telegram_id
  3. Logout:       NULL telegram_id + delete Redis session
  4. Brute-force:  5 failed attempts → 30-min account lock
  5. Session:      JWT stored in Redis, 24-hour expiry

Checks ALL role tables in order: students → teachers → owners
Super admin access is handled separately via telegram whitelist.
─────────────────────────────────────────────────────────────
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from loguru import logger

from config.config import settings
from core.security import (
    verify_password,
    create_access_token,
    save_session,
    delete_session,
    get_user_session,
    is_locked_out,
    record_failed_login,
    clear_login_attempts,
)
from database.repositories.student_repo import StudentRepository
from database.repositories.teacher_repo import TeacherRepository
from database.repositories.org_repo import OrgRepository
from database.repositories.user_repo import UserRepository
from database.repositories.user_repo_security import (
    AuditLogRepository,
    LoginAttemptRepository,
)

_student_repo = StudentRepository()
_teacher_repo = TeacherRepository()
_org_repo = OrgRepository()
_user_repo = UserRepository()
_audit = AuditLogRepository()
_login_log = LoginAttemptRepository()


# ─────────────────────────────────────────────
# AUTO-LOGIN
# ─────────────────────────────────────────────

async def check_user(telegram_id: int) -> Optional[dict]:
    """
    Auto-login flow.
    Checks all role tables for a matching telegram_id.
    Returns session payload dict or None if not found.

    Called by /start and /home handlers.
    """
    # Super admin whitelist check (no DB query needed)
    if telegram_id in settings.super_admin_id_list:
        session = {
            "user_id": f"superadmin_{telegram_id}",
            "org_id": None,
            "role": "super_admin",
            "name": "Super Admin",
            "telegram_id": telegram_id,
        }
        token = create_access_token(session)
        await save_session(telegram_id, token)
        logger.info(f"Super admin auto-login | tg={telegram_id}")
        return session

    # Check existing Redis session first (fast path)
    existing = await get_user_session(telegram_id)
    if existing:
        logger.debug(f"Session cache hit | tg={telegram_id} | role={existing.get('role')}")
        return existing

    # Check students
    student = await _student_repo.get_by_telegram_id(telegram_id)
    if student and student.account_status == "active":
        org = await _org_repo.get_by_org_id(student.org_id)
        if org and org.is_active:
            return await _create_student_session(student, telegram_id)

    # Check teachers
    teacher = await _teacher_repo.get_by_telegram_id(telegram_id)
    if teacher and teacher.account_status == "active":
        org = await _org_repo.get_by_org_id(teacher.org_id)
        if org and org.is_active:
            return await _create_teacher_session(teacher, telegram_id)

    # Check owners (via users table)
    user = await _user_repo.get_by_telegram_id(telegram_id)
    if user and user.role == "owner" and user.is_active:
        org = await _org_repo.get_by_org_id(user.org_id)
        if org and org.is_active:
            return await _create_owner_session(user, org, telegram_id)

    return None


# ─────────────────────────────────────────────
# MANUAL LOGIN
# ─────────────────────────────────────────────

async def login(
    telegram_id: int,
    user_id: str,
    password: str,
    org_id: str,
    ip_address: str = None,
) -> dict:
    """
    Manual login flow — called after user enters Institute Code, ID + password.
    """
    # Redis-level lockout check (fast path before DB)
    if await is_locked_out(telegram_id):
        return {
            "success": False,
            "reason": "locked",
            "message": (
                "🔒 Your account is temporarily locked.\n"
                f"Please wait {settings.LOGIN_LOCKOUT_MINUTES} minutes before trying again."
            ),
        }

    # Resolve the user across role tables securely using org_id
    role, record = await _find_user_by_id(user_id, org_id)

    if not record:
        await _handle_failed_attempt(telegram_id, user_id, None, org_id, ip_address)
        return {
            "success": False,
            "reason": "not_found",
            "message": "❌ User ID or Institute Code not found. Please check and try again.",
        }

    # Verify password
    if not verify_password(password, record.password_hash):
        attempts = await record_failed_login(telegram_id)
        attempts_left = max(0, settings.MAX_LOGIN_ATTEMPTS - attempts)

        await _login_log.log_attempt(user_id, role, org_id, "failed", ip_address)
        await _audit.log(
            "LOGIN_FAILED",
            user_id=user_id, role=role,
            org_id=org_id,
            details={"reason": "wrong_password", "attempts": attempts},
        )

        if attempts_left <= 0:
            return {
                "success": False,
                "reason": "locked",
                "message": (
                    f"🔒 Too many failed attempts.\n"
                    f"Account locked for {settings.LOGIN_LOCKOUT_MINUTES} minutes."
                ),
            }

        return {
            "success": False,
            "reason": "wrong_password",
            "message": (
                f"❌ Invalid password.\n"
                f"Attempts remaining: <b>{attempts_left}</b>"
            ),
            "attempts_left": attempts_left,
        }

    # Check account & org status
    account_status = getattr(record, "account_status", "active")
    if account_status == "frozen":
        return {
            "success": False,
            "reason": "frozen",
            "message": "🚫 Your account is suspended. Contact your institution administrator.",
        }

    org = await _org_repo.get_by_org_id(org_id)
    if not org or not org.is_active:
        return {
            "success": False,
            "reason": "org_inactive",
            "message": "🚫 Your institution is not active. Contact Naganaverse support.",
        }

    # Success — bind telegram_id and create session
    await _bind_telegram_id(role, record, telegram_id, org_id)
    await clear_login_attempts(telegram_id)

    session = await _build_session(role, record, telegram_id)
    token = create_access_token(session)
    await save_session(telegram_id, token)

    await _login_log.log_attempt(user_id, role, org_id, "success", ip_address)
    await _audit.log(
        "LOGIN_SUCCESS",
        user_id=user_id, role=role, org_id=org_id,
        details={"telegram_id": telegram_id},
    )

    logger.info(f"Login success | user={user_id} | role={role} | tg={telegram_id}")

    return {"success": True, "session": session, "role": role}


# ─────────────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────────────

async def logout(telegram_id: int, user_id: str = None, role: str = None, org_id: str = None) -> bool:
    """
    Logout flow:
    1. Delete Redis session
    2. NULL telegram_id in DB
    """
    await delete_session(telegram_id)
    await _user_repo.logout(telegram_id)

    # Also null in role-specific tables
    try:
        student = await _student_repo.get_by_telegram_id(telegram_id)
        if student:
            await _student_repo.bind_telegram_id(student.student_id, None, student.org_id)

        teacher = await _teacher_repo.get_by_telegram_id(telegram_id)
        if teacher:
            await _teacher_repo.bind_telegram_id(teacher.teacher_id, None, teacher.org_id)
    except Exception as e:
        logger.error(f"Error during logout DB update: {e}")

    await _audit.log(
        "LOGOUT",
        user_id=user_id, role=role, org_id=org_id,
        details={"telegram_id": telegram_id},
    )

    logger.info(f"Logout | tg={telegram_id}")
    return True


# ─────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────

async def _find_user_by_id(user_id: str, org_id: str):
    """
    Search for a user_id across students, teachers, and owners.
    STRICTLY scoped to org_id to prevent cross-tenant data leaks.

    FIX: Normalizes all inputs at entry and uses UPPER()/LOWER() in SQL
    to guarantee case-blind matching regardless of DB storage format.
    """
    # FIX: Normalize at entry point — single source of truth
    uid_upper = user_id.strip().upper()
    org_lower = org_id.strip().lower()

    from database.connection import get_pool

    # Student IDs typically start with STD
    if uid_upper.startswith("STD"):
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    # FIX: Case-blind matching on both columns
                    "SELECT * FROM students WHERE UPPER(student_id) = $1 AND LOWER(org_id) = $2",
                    uid_upper, org_lower,
                )
            if row:
                from database.models.student_model import Student
                return "student", Student.from_record(dict(row))
        except Exception as e:
            logger.error(f"DB Error searching for student {uid_upper} in {org_lower}: {e}")

    # Teacher IDs typically start with TCH
    if uid_upper.startswith("TCH"):
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    # FIX: Case-blind matching on both columns
                    "SELECT * FROM teachers WHERE UPPER(teacher_id) = $1 AND LOWER(org_id) = $2",
                    uid_upper, org_lower,
                )
            if row:
                from database.models.teacher_model import Teacher
                return "teacher", Teacher.from_record(dict(row))
        except Exception as e:
            logger.error(f"DB Error searching for teacher {uid_upper} in {org_lower}: {e}")

    # Owners (via users table)
    try:
        # FIX: Pass BOTH uid_upper and org_lower — prevents cross-org owner access
        user = await _user_repo.get_by_user_id(uid_upper, org_lower)
        if user and user.role == "owner":
            return "owner", user
    except Exception as e:
        logger.error(f"DB Error searching for owner {uid_upper} in {org_lower}: {e}")

    return None, None


async def _bind_telegram_id(role: str, record, telegram_id: int, org_id: str) -> None:
    try:
        # Destroy old session if rebinding to a new Telegram account
        old_telegram_id = getattr(record, "telegram_id", None)
        if old_telegram_id and old_telegram_id != telegram_id:
            from core.security import delete_session
            await delete_session(old_telegram_id)
            logger.info(f"Invalidated old session for {role} {getattr(record, 'name', '')} on TG {old_telegram_id}")

        # Proceed with normal database binding
        if role == "student":
            await _student_repo.bind_telegram_id(record.student_id, telegram_id, org_id)
        elif role == "teacher":
            await _teacher_repo.bind_telegram_id(record.teacher_id, telegram_id, org_id)
        elif role == "owner":
            await _user_repo.bind_telegram_id(record.user_id, telegram_id)
    except Exception as e:
        logger.error(f"DB Error binding telegram ID {telegram_id}: {e}")


async def _build_session(role: str, record, telegram_id: int) -> dict:
    base = {
        "role": role,
        "telegram_id": telegram_id,
        "org_id": getattr(record, "org_id", None),
    }
    if role == "student":
        base.update({
            "user_id": record.student_id,
            "name": record.name,
            "class_name": record.class_name,
            "subjects": record.subjects,
        })
    elif role == "teacher":
        base.update({
            "user_id": record.teacher_id,
            "name": record.name,
            "subjects": record.subjects,
            "assigned_classes": record.assigned_classes,
        })
    elif role == "owner":
        base.update({
            "user_id": record.user_id,
            "name": record.name,
        })
    return base


async def _create_student_session(student, telegram_id: int) -> dict:
    session = await _build_session("student", student, telegram_id)
    token = create_access_token(session)
    await save_session(telegram_id, token)
    return session


async def _create_teacher_session(teacher, telegram_id: int) -> dict:
    session = await _build_session("teacher", teacher, telegram_id)
    token = create_access_token(session)
    await save_session(telegram_id, token)
    return session


async def _create_owner_session(user, org, telegram_id: int) -> dict:
    session = await _build_session("owner", user, telegram_id)
    session["org_name"] = org.org_name
    session["plan_type"] = org.plan_type
    token = create_access_token(session)
    await save_session(telegram_id, token)
    return session


async def check_if_needs_password(user_id: str, org_id: str) -> dict:
    """
    Check if a user exists and needs to set their password.
    Called right after user enters their ID — before asking for password.
    """
    role, record = await _find_user_by_id(user_id, org_id)
    if not record:
        return {"exists": False}

    # 🛡️ CRITICAL FIX: Verify the institution is actually approved!
    # If the org is pending, suspended, or rejected, we block them right here.
    org = await _org_repo.get_by_org_id(getattr(record, "org_id", org_id))
    if not org or not org.is_active:
        return {"exists": False} # Spoofs non-existence so login handler rejects them

    needs_password = not record.password_hash or record.password_hash.strip() == ""
    return {
        "exists": True,
        "needs_password": needs_password,
        "role": role,
        "org_id": getattr(record, "org_id", None),
  }


async def set_initial_password(user_id: str, password: str, telegram_id: int, org_id: str) -> dict:

    """
    Set password for first-time owner login after approval.
    Saves hashed password, activates account, binds telegram_id, creates session.
    """
    from core.security import hash_password as _hash_password
    role, record = await _find_user_by_id(user_id, org_id)
    if not record:
        return {"success": False, "message": "❌ User not found."}

    # 🛡️ CRITICAL FIX: Double-check org status right before saving the password
    org = await _org_repo.get_by_org_id(org_id)
    if not org or not org.is_active:
        return {
            "success": False, 
            "message": f"🚫 Registration incomplete. Institution status is currently '{org.status if org else 'unknown'}'. Please wait for Admin approval."
        }

    if len(password) < 4:
        return {"success": False, "message": "❌ Password too short. Minimum 4 characters."}

    try:
        hashed = _hash_password(password)
        await _user_repo.update_password(user_id, hashed)
        await _user_repo.unfreeze_account(user_id)  # sets status = active
    except Exception as e:
        logger.error(f"DB Error setting initial password for {user_id}: {e}")
        return {"success": False, "message": "❌ Database error. Please try again."}

    # Bind telegram_id
    await _bind_telegram_id(role, record, telegram_id, org_id)
    from core.security import clear_login_attempts
    await clear_login_attempts(telegram_id)

    # Build session — re-fetch record to get updated status
    _, updated_record = await _find_user_by_id(user_id, org_id)
    session = await _build_session(role, updated_record, telegram_id)

    if role == "owner" and org_id:
        if org:
            session["org_name"] = org.org_name
            session["plan_type"] = org.plan_type

    from core.security import create_access_token, save_session
    token = create_access_token(session)
    await save_session(telegram_id, token)

    await _audit.log(
        "OWNER_PASSWORD_SET",
        user_id=user_id, role=role, org_id=org_id,
        details={"telegram_id": telegram_id},
    )

    logger.info(f"Initial password set | user={user_id} | tg={telegram_id}")
    return {"success": True, "session": session, "role": role}
  
    

async def _handle_failed_attempt(telegram_id, user_id, role, org_id, ip_address) -> None:
    await record_failed_login(telegram_id)
    await _login_log.log_attempt(user_id, role, org_id, "failed", ip_address)


# ─────────────────────────────────────────────
# PARENT LOGIN
# ─────────────────────────────────────────────

async def parent_login(
    telegram_id: int,
    parent_id: str,
    password: str,
    org_id: str,           # FIX (CRITICAL SECURITY): org_id scopes the student lookup
) -> dict:
    """
    Parent login flow.
    parent_id format: PAR_{student_id}  e.g. PAR_STD001
    password: last 6 digits of parent phone number

    SECURITY FIX: The student lookup is now scoped to org_id to prevent
    a parent in org A from authenticating as a parent in org B by
    guessing a valid student_id from another tenant.
    """
    # 1. Redis-level lockout check (Brute-force protection)
    if await is_locked_out(parent_id):
        return {
            "success": False,
            "message": f"🔒 Account locked due to too many failed attempts. Try again in {settings.LOGIN_LOCKOUT_MINUTES} minutes."
        }

    # 2. Validate PAR_ prefix
    if not parent_id.upper().startswith("PAR_"):
        await record_failed_login(parent_id)
        return {
            "success": False,
            "message": "❌ Invalid Parent ID. Format: PAR_STD001",
        }

    student_id = parent_id.upper()[4:]  # strip "PAR_"

    # FIX: Normalize org_id to lowercase to match DB storage
    org_lower = org_id.strip().lower()

    # 3. Fetch student record — SCOPED to org_id (CRITICAL SECURITY FIX)
    from database.connection import get_pool
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                # FIX: MUST include org_id scope — prevents cross-tenant parent login
                "SELECT * FROM students WHERE UPPER(student_id) = UPPER($1) AND LOWER(org_id) = LOWER($2)",
                student_id, org_lower,
            )
    except Exception as e:
        logger.error(f"DB Error fetching student {student_id} for parent login: {e}")
        return {"success": False, "message": "❌ Database error. Please try again later."}

    if not row:
        await record_failed_login(parent_id)
        return {"success": False, "message": "❌ Parent ID not found. Please check and try again."}

    student = dict(row)
    parent_phone = student.get("parent_phone", "")

    # 4. Password Check = last 6 digits of parent phone
    if not parent_phone or len(parent_phone) < 6:
        return {"success": False, "message": "❌ No parent phone on record. Contact institution owner."}

    expected_password = parent_phone[-6:]
    if password != expected_password:
        await record_failed_login(parent_id)
        return {
            "success": False,
            "message": (
                "❌ Wrong password.\n"
                "Your password is the last 6 digits of your phone number.\n"
                "<i>Example: if phone is 9876543210 → password is 543210</i>"
            ),
        }

    # 5. Check org is active — use the org_id from the fetched student row
    #    (authoritative source, avoids relying solely on user-supplied org_id)
    db_org_id = student.get("org_id")
    try:
        org = await _org_repo.get_by_org_id(db_org_id)
    except Exception as e:
        logger.error(f"DB Error fetching org {db_org_id} for parent login: {e}")
        return {"success": False, "message": "❌ Database error."}

    if not org or not org.is_active:
        return {"success": False, "message": "🚫 Institution is not active."}

    # 6. Bind parent telegram_id to student record
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE students SET parent_telegram_id = $1 WHERE UPPER(student_id) = UPPER($2) AND LOWER(org_id) = LOWER($3)",
                telegram_id, student_id, org_lower,
            )
    except Exception as e:
        logger.error(f"DB Error binding parent telegram ID {telegram_id}: {e}")
        return {"success": False, "message": "❌ Failed to link account due to database error."}

    # 7. Success! Clear brute-force counters and build session
    await clear_login_attempts(parent_id)

    session = {
        "role":         "parent",
        "user_id":      parent_id.upper(),
        "student_id":   student_id,
        "student_name": student.get("name", ""),
        "org_id":       db_org_id,
        "org_name":     org.org_name,
        "telegram_id":  telegram_id,
        "parent_phone": parent_phone,
    }

    token = create_access_token(session)
    await save_session(telegram_id, token)

    await _audit.log(
        "PARENT_LOGIN",
        user_id=parent_id,
        role="parent",
        org_id=db_org_id,
        details={"student_id": student_id, "telegram_id": telegram_id},
    )

    logger.info(f"Parent login | parent={parent_id} | student={student_id} | org={db_org_id} | tg={telegram_id}")
    return {"success": True, "session": session}
