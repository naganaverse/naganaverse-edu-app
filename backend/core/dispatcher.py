"""
core/dispatcher.py
─────────────────────────────────────────────────────────────
Registers all routers and middlewares onto the Dispatcher.
Called once at startup from bot.py.
─────────────────────────────────────────────────────────────
"""

from aiogram import Dispatcher
from loguru import logger

from core.middlewares.auth_middleware import AuthMiddleware
from core.middlewares.rate_limit_middleware import RateLimitMiddleware


def setup_dispatcher(dp: Dispatcher) -> None:
    """
    Register all routers and middlewares.
    Order matters — middlewares run in registration order.
    """
    _register_middlewares(dp)
    _register_routers(dp)
    logger.info("Dispatcher setup complete.")


# ── Middleware Registration ───────────────────────────────
def _register_middlewares(dp: Dispatcher) -> None:
    """
    Global middlewares applied to ALL incoming updates.
    Execution order: RateLimit → Auth → Handler
    """
    dp.update.outer_middleware(RateLimitMiddleware())
    dp.update.outer_middleware(AuthMiddleware())
    logger.debug("Middlewares registered: RateLimitMiddleware, AuthMiddleware")


# ── Router Registration ───────────────────────────────────
def _register_routers(dp: Dispatcher) -> None:
    """
    Import and include all role-based routers.
    Routers are imported here (not at module level) to
    avoid circular imports.
    """

    # ── Common handlers ──────────────────────────────────
    from handlers.common.start import router as start_router
    from handlers.common.login import router as login_router
    from handlers.common.help  import router as help_router
    from handlers.common.error import router as error_router

    # ── Owner handlers ────────────────────────────────────
    from handlers.owner.profile_handler import router as owner_profile_router
    from handlers.owner import fee_handler
    from handlers.owner.students_handler import router as owner_students_router
    from handlers.owner.teachers_handler import router as owner_teachers_router
    from handlers.owner.add_student_handler import router as add_student_router
    from handlers.owner.add_teacher_handler import router as add_teacher_router
    from handlers.owner.classes_handler import router as classes_router
    from handlers.owner.attendance_reports_handler import router as attendance_reports_router
    from handlers.owner.test_reports_handler import router as test_reports_router
    from handlers.owner.announcements_handler import router as owner_announcements_router
    from handlers.owner.analytics_handler import router as owner_analytics_router
    from handlers.owner.settings_handler import router as settings_router
    from handlers.owner.referral_handler import router as referral_router

    # ── Teacher handlers ──────────────────────────────────
    from handlers.teacher.attendance_handler import router as teacher_attendance_router
    from handlers.teacher.homework_handler import router as teacher_homework_router
    from handlers.teacher.tests_handler import router as teacher_tests_router
    from handlers.teacher.resource_handler import router as teacher_resource_router
    from handlers.teacher.announcements_handler import router as teacher_announcements_router
    from handlers.teacher.students_handler import router as teacher_students_router

    # ── Student handlers ──────────────────────────────────
    from handlers.student.attendance_handler import router as student_attendance_router
    from handlers.student.homework_handler import router as student_homework_router
    from handlers.student.tests_handler import router as student_tests_router
    from handlers.student.resources_handler import router as student_resources_router
    from handlers.student.announcements_handler import router as student_announcements_router
    from handlers.student.profile_handler import router as student_profile_router

    # ── Super Admin handlers ──────────────────────────────
    from handlers.superadmin.admin_handler import router as admin_router
    from handlers.superadmin.institutions_handler import router as institutions_router
    from handlers.superadmin.analytics_handler import router as superadmin_analytics_router
    from handlers.superadmin.audit_handler import router as audit_router
    from handlers.superadmin.emergency_handler import router as emergency_router
    from handlers.superadmin.admin_users_handler import router as admin_users_router
    
    # ── Parent handlers ───────────────────────────────────
    from handlers.parent.parent_handler import router as parent_router

    # ── Include routers in priority order ─────────────────
    
    # Global first (highest priority)
    dp.include_router(start_router)
    dp.include_router(login_router)
    dp.include_router(help_router)
    dp.include_router(error_router)

    # Super Admin
    dp.include_router(admin_router)
    dp.include_router(institutions_router)
    dp.include_router(superadmin_analytics_router)
    dp.include_router(audit_router)
    dp.include_router(emergency_router)
    dp.include_router(admin_users_router)
    
    # Parent
    dp.include_router(parent_router)

    # Owner
    dp.include_router(fee_handler.router)
    dp.include_router(owner_profile_router)
    dp.include_router(owner_students_router)
    dp.include_router(owner_teachers_router)
    dp.include_router(add_student_router)
    dp.include_router(add_teacher_router)
    dp.include_router(classes_router)
    dp.include_router(attendance_reports_router)
    dp.include_router(test_reports_router)
    dp.include_router(owner_announcements_router)
    dp.include_router(owner_analytics_router)
    dp.include_router(settings_router)
    dp.include_router(referral_router)

    # Teacher
    dp.include_router(teacher_attendance_router)
    dp.include_router(teacher_homework_router)
    dp.include_router(teacher_tests_router)
    dp.include_router(teacher_resource_router)
    dp.include_router(teacher_announcements_router)
    dp.include_router(teacher_students_router)

    # Student
    dp.include_router(student_attendance_router)
    dp.include_router(student_homework_router)
    dp.include_router(student_tests_router)
    dp.include_router(student_resources_router)
    dp.include_router(student_announcements_router)
    dp.include_router(student_profile_router)

    logger.debug("All routers registered successfully.")
  
