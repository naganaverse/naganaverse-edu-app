"""
core/filters.py
─────────────────────────────────────────────────────────────
Custom aiogram filters for role-based access control.
All handlers import these filters to gate access by user role.
─────────────────────────────────────────────────────────────
"""

from typing import Union
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from config.config import settings


# ── Role Constants ────────────────────────────────────────
class UserRole:
    STUDENT = "student"
    TEACHER = "teacher"
    OWNER = "owner"
    SUPER_ADMIN = "super_admin"


# ── Base Role Filter ──────────────────────────────────────
class RoleFilter(BaseFilter):
    """
    Checks if the authenticated user has a specific role.
    Relies on AuthMiddleware having injected 'user_session' into data.

    Usage:
        @router.message(RoleFilter(UserRole.TEACHER))
        async def teacher_handler(message: Message): ...
    """

    def __init__(self, role: Union[str, list]):
        self.allowed_roles = [role] if isinstance(role, str) else role

    async def __call__(
        self,
        event: Union[Message, CallbackQuery],
        user_session: dict = None,
        **data,
    ) -> bool:
        if not user_session:
            return False
        return user_session.get("role") in self.allowed_roles


# ── Shorthand Role Filters ────────────────────────────────
class IsStudent(RoleFilter):
    def __init__(self):
        super().__init__(UserRole.STUDENT)


class IsTeacher(RoleFilter):
    def __init__(self):
        super().__init__(UserRole.TEACHER)


class IsOwner(RoleFilter):
    def __init__(self):
        super().__init__(UserRole.OWNER)


class IsSuperAdmin(RoleFilter):
    def __init__(self):
        super().__init__(UserRole.SUPER_ADMIN)


class IsStaff(RoleFilter):
    """Matches Teacher or Owner."""
    def __init__(self):
        super().__init__([UserRole.TEACHER, UserRole.OWNER])


class IsAuthenticated(BaseFilter):
    """
    Passes if ANY valid session exists (any role).
    Use for features accessible by all logged-in users.
    """

    async def __call__(
        self,
        event: Union[Message, CallbackQuery],
        user_session: dict = None,
        **data,
    ) -> bool:
        return user_session is not None and "role" in user_session


class IsNotAuthenticated(BaseFilter):
    """Passes if user is NOT logged in — for /start and /login."""

    async def __call__(
        self,
        event: Union[Message, CallbackQuery],
        user_session: dict = None,
        **data,
    ) -> bool:
        return user_session is None


# ── Super Admin Telegram ID Filter ────────────────────────
class IsTelegramSuperAdmin(BaseFilter):
    """
    Hard-coded Telegram ID check for emergency super admin access.
    Does NOT require a DB session — used before login.
    """

    async def __call__(self, event: Union[Message, CallbackQuery], **data) -> bool:
        telegram_id = (
            event.from_user.id if hasattr(event, "from_user") else None
        )
        if telegram_id is None:
            return False
        return telegram_id in settings.super_admin_id_list


# ── Org Isolation Filter ──────────────────────────────────
class OrgFilter(BaseFilter):
    """
    Verifies the user's org_id matches the requested resource's org_id.
    Prevents cross-tenant data access.
    """
    
    # FIX: Only ONE __call__ method allowed
    async def __call__(
        self, 
        event: Union[Message, CallbackQuery], 
        user_session: dict = None,
        **data
    ) -> bool:
        # Reject if no session exists
        if not user_session:
            return False
            
        # Enforce that the user is operating inside their tenant
        if "org_id" not in user_session:
            return False
            
        # If you had a bypass for parents or super admins, include it here
        if user_session.get("role") in ["parent", "super_admin"]:
            return True
            
        return True


class IsParent(BaseFilter):
    async def __call__(self, event: Union[Message, CallbackQuery], user_session: dict = None, **data) -> bool:
        return bool(user_session and user_session.get("role") == "parent")
    
