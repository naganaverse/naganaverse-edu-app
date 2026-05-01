"""
database/init_db.py
─────────────────────────────────────────────────────────────
Creates all database tables if they don't exist.
Called once at startup from bot.py → on_startup().

Tables created (in dependency order):
  1.  organizations
  2.  users
  3.  owners
  4.  teachers
  5.  students
  6.  classes
  7.  subjects
  8.  resources
  9.  attendance
  10. attendance_details
  11. homework
  12. tests
  13. test_questions
  14. test_attempts
  15. test_results
  16. announcements
  17. parent_notifications
  18. subscriptions
  19. referrals
  20. login_attempts
  21. audit_logs
  22. suspended_accounts
  23. bot_activity
  24. rate_limits
  25. system_settings
  26. backups
─────────────────────────────────────────────────────────────
"""

from loguru import logger
from database.connection import get_pool

# ─────────────────────────────────────────────
# DDL STATEMENTS
# ─────────────────────────────────────────────

_DDL_STATEMENTS = [

    # ── 1. Organizations ──────────────────────
    """
    CREATE TABLE IF NOT EXISTS organizations (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        org_id          VARCHAR(100) UNIQUE NOT NULL,
        org_name        VARCHAR(255) NOT NULL,
        owner_name      VARCHAR(255) NOT NULL,
        phone           VARCHAR(20),
        city            VARCHAR(100),
        referral_code   VARCHAR(50) UNIQUE,
        referred_by     VARCHAR(50),
        status          VARCHAR(20) NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending','active','approved','rejected','suspended')),
        plan_type       VARCHAR(20) NOT NULL DEFAULT 'starter'
                            CHECK (plan_type IN ('starter','enterprise')),
        created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ── 2. Users (central auth table) ─────────
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id                 VARCHAR(50) PRIMARY KEY,
        org_id                  VARCHAR(100) REFERENCES organizations(org_id) ON DELETE CASCADE,
        name                    VARCHAR(255) NOT NULL,
        role                    VARCHAR(20) NOT NULL
                                    CHECK (role IN ('student','teacher','owner','super_admin')),
        phone                   VARCHAR(20),
        telegram_id             BIGINT UNIQUE,
        password_hash           VARCHAR(255) NOT NULL,
        status                  VARCHAR(20) NOT NULL DEFAULT 'active'
                                    CHECK (status IN ('active','frozen','locked','deleted')),
        failed_attempts         INT NOT NULL DEFAULT 0,
        last_failed_attempt     TIMESTAMP WITH TIME ZONE,
        account_locked_until    TIMESTAMP WITH TIME ZONE,
        created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ── 3. Owners ─────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS owners (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        org_id          VARCHAR(100) NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
        owner_id        VARCHAR(50) UNIQUE NOT NULL,
        owner_name      VARCHAR(255) NOT NULL,
        password_hash   VARCHAR(255) NOT NULL,
        telegram_id     BIGINT UNIQUE,
        phone_number    VARCHAR(20),
        account_status  VARCHAR(20) NOT NULL DEFAULT 'active'
                            CHECK (account_status IN ('active','frozen')),
        created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ── 4. Teachers ───────────────────────────
    """
    CREATE TABLE IF NOT EXISTS teachers (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        org_id          VARCHAR(100) NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
        teacher_id      VARCHAR(50) UNIQUE NOT NULL,
        name            VARCHAR(255) NOT NULL,
        subjects        JSONB NOT NULL DEFAULT '[]',
        assigned_classes JSONB NOT NULL DEFAULT '[]',
        password_hash   VARCHAR(255) NOT NULL,
        telegram_id     BIGINT UNIQUE,
        phone           VARCHAR(20),
        account_status  VARCHAR(20) NOT NULL DEFAULT 'active'
                            CHECK (account_status IN ('active','frozen')),
        created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ── 5. Students ───────────────────────────
    """
    CREATE TABLE IF NOT EXISTS students (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        org_id          VARCHAR(100) NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
        student_id      VARCHAR(50) UNIQUE NOT NULL,
        name            VARCHAR(255) NOT NULL,
        class           VARCHAR(50) NOT NULL,
        roll_number     INT,
        subjects        JSONB NOT NULL DEFAULT '[]',
        father_name     VARCHAR(255),
        mother_name     VARCHAR(255),
        parent_phone    VARCHAR(20),
        password_hash   VARCHAR(255) NOT NULL,
        telegram_id     BIGINT UNIQUE,
        account_status  VARCHAR(20) NOT NULL DEFAULT 'active'
                            CHECK (account_status IN ('active','frozen')),
        created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ── 6. Classes ────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS classes (
        class_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        org_id      VARCHAR(100) NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
        class_name  VARCHAR(100) NOT NULL,
        section     VARCHAR(10),
        created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        UNIQUE (org_id, class_name, section)
    )
    """,

    # ── 7. Subjects ───────────────────────────
    """
    CREATE TABLE IF NOT EXISTS subjects (
        subject_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        org_id          VARCHAR(100) NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
        class_id        UUID REFERENCES classes(class_id) ON DELETE CASCADE,
        class_name      VARCHAR(100),
        subject_name    VARCHAR(100) NOT NULL,
        created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        UNIQUE (org_id, class_name, subject_name)
    )
    """,

    # ── 8. Resources ──────────────────────────
    """
    CREATE TABLE IF NOT EXISTS resources (
        resource_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        org_id          VARCHAR(100) NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
        class_name      VARCHAR(100) NOT NULL,
        subject_name    VARCHAR(100) NOT NULL,
        resource_type   VARCHAR(30) NOT NULL
                            CHECK (resource_type IN ('notes','worksheet','pyq','important_questions','practice_sheet')),
        file_name       VARCHAR(255),
        file_url        VARCHAR(500) NOT NULL,
        file_type       VARCHAR(20),
        uploaded_by     VARCHAR(50) NOT NULL,
        created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ── 9. Attendance ─────────────────────────
    """
    CREATE TABLE IF NOT EXISTS attendance (
        attendance_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        org_id          VARCHAR(100) NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
        class_name      VARCHAR(100) NOT NULL,
        subject_name    VARCHAR(100) NOT NULL,
        teacher_id      VARCHAR(50) NOT NULL,
        date            DATE NOT NULL,
        present_count   INT NOT NULL DEFAULT 0,
        absent_count    INT NOT NULL DEFAULT 0,
        created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        UNIQUE (org_id, class_name, subject_name, date)
    )
    """,

    # ── 10. Attendance Details ────────────────
    """
    CREATE TABLE IF NOT EXISTS attendance_details (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        attendance_id   UUID NOT NULL REFERENCES attendance(attendance_id) ON DELETE CASCADE,
        student_id      VARCHAR(50) NOT NULL,
        status          VARCHAR(10) NOT NULL DEFAULT 'present'
                            CHECK (status IN ('present','absent'))
    )
    """,

    # ── 11. Homework ──────────────────────────
    """
    CREATE TABLE IF NOT EXISTS homework (
        homework_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        org_id          VARCHAR(100) NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
        class_name      VARCHAR(100) NOT NULL,
        subject_name    VARCHAR(100) NOT NULL,
        teacher_id      VARCHAR(50) NOT NULL,
        description     TEXT NOT NULL,
        date            DATE NOT NULL DEFAULT CURRENT_DATE,
        created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ── 12. Tests ─────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS tests (
        test_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        org_id          VARCHAR(100) NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
        test_name       VARCHAR(255) NOT NULL,
        class_name      VARCHAR(100) NOT NULL,
        subject_name    VARCHAR(100) NOT NULL,
        topic           VARCHAR(255),
        teacher_id      VARCHAR(50) NOT NULL,
        test_date       DATE NOT NULL DEFAULT CURRENT_DATE,
        total_marks     INT NOT NULL DEFAULT 0,
        created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ── 13. Test Questions ────────────────────
    """
    CREATE TABLE IF NOT EXISTS test_questions (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        test_id         UUID NOT NULL REFERENCES tests(test_id) ON DELETE CASCADE,
        question_text   TEXT NOT NULL,
        option_a        TEXT,
        option_b        TEXT,
        option_c        TEXT,
        option_d        TEXT,
        correct_answer  VARCHAR(5) NOT NULL,
        marks           INT NOT NULL DEFAULT 1
    )
    """,

    # ── 14. Test Attempts ─────────────────────
    """
    CREATE TABLE IF NOT EXISTS test_attempts (
        id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        student_id  VARCHAR(50) NOT NULL,
        question_id UUID NOT NULL REFERENCES test_questions(id) ON DELETE CASCADE,
        test_id     UUID NOT NULL REFERENCES tests(test_id) ON DELETE CASCADE,
        answer      VARCHAR(5),
        attempted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        UNIQUE (student_id, question_id)
    )
    """,

    # ── 15. Test Results ──────────────────────
    """
    CREATE TABLE IF NOT EXISTS test_results (
        result_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        org_id          VARCHAR(100) NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
        test_id         UUID NOT NULL REFERENCES tests(test_id) ON DELETE CASCADE,
        student_id      VARCHAR(50) NOT NULL,
        marks           DECIMAL(6,2) NOT NULL DEFAULT 0,
        submitted_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        UNIQUE (test_id, student_id)
    )
    """,

    # ── 16. Announcements ─────────────────────
    """
    CREATE TABLE IF NOT EXISTS announcements (
        announcement_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        org_id          VARCHAR(100) NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
        target_class    VARCHAR(100),
        message         TEXT NOT NULL,
        created_by      VARCHAR(50) NOT NULL,
        created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ── 17. Parent Notifications ──────────────
    """
    CREATE TABLE IF NOT EXISTS parent_notifications (
        notification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        org_id          VARCHAR(100) NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
        student_id      VARCHAR(50) NOT NULL,
        parent_phone    VARCHAR(20) NOT NULL,
        notification_type VARCHAR(30) NOT NULL
                            CHECK (notification_type IN
                                ('test_result','attendance_report','absence_alert','announcement')),
        message         TEXT NOT NULL,
        sent_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ── 18. Subscriptions ─────────────────────
    """
    CREATE TABLE IF NOT EXISTS subscriptions (
        subscription_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        org_id          VARCHAR(100) NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
        plan            VARCHAR(20) NOT NULL DEFAULT 'starter'
                            CHECK (plan IN ('starter','enterprise')),
        start_date      DATE NOT NULL DEFAULT CURRENT_DATE,
        expiry_date     DATE NOT NULL,
        status          VARCHAR(20) NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active','expired','cancelled')),
        created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ── 19. Referrals ─────────────────────────
    """
    CREATE TABLE IF NOT EXISTS referrals (
        referral_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        org_id              VARCHAR(100) NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
        referral_code       VARCHAR(50) NOT NULL,
        referring_org_id    VARCHAR(100),
        referred_org_id     VARCHAR(100),
        discount_percent    DECIMAL(5,2) NOT NULL DEFAULT 5.00,
        created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ── 20. Login Attempts ────────────────────
    """
    CREATE TABLE IF NOT EXISTS login_attempts (
        attempt_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id         VARCHAR(50),
        role            VARCHAR(20),
        org_id          VARCHAR(100),
        ip_address      VARCHAR(45),
        status          VARCHAR(10) NOT NULL DEFAULT 'failed'
                            CHECK (status IN ('success','failed')),
        attempt_time    TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ── 21. Audit Logs ────────────────────────
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        log_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        event_type  VARCHAR(100) NOT NULL,
        user_id     VARCHAR(50),
        role        VARCHAR(20),
        org_id      VARCHAR(100),
        details     JSONB,
        timestamp   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ── 22. Suspended Accounts ────────────────
    """
    CREATE TABLE IF NOT EXISTS suspended_accounts (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id         VARCHAR(50) NOT NULL,
        role            VARCHAR(20) NOT NULL,
        org_id          VARCHAR(100),
        reason          TEXT,
        suspended_until TIMESTAMP WITH TIME ZONE,
        created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ── 23. Bot Activity ──────────────────────
    """
    CREATE TABLE IF NOT EXISTS bot_activity (
        id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id     VARCHAR(50),
        role        VARCHAR(20),
        org_id      VARCHAR(100),
        command     VARCHAR(100) NOT NULL,
        timestamp   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ── 24. Rate Limits ───────────────────────
    """
    CREATE TABLE IF NOT EXISTS rate_limits (
        id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id     VARCHAR(50) NOT NULL,
        command     VARCHAR(100),
        timestamp   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ── 25. System Settings ───────────────────
    """
    CREATE TABLE IF NOT EXISTS system_settings (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        org_id          VARCHAR(100),
        setting_name    VARCHAR(100) NOT NULL,
        setting_value   TEXT NOT NULL,
        updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        UNIQUE (org_id, setting_name)
    )
    """,

    # ── 26. Backups ───────────────────────────
    """
    CREATE TABLE IF NOT EXISTS backups (
        id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        backup_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        status      VARCHAR(20) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','success','failed')),
        file_path   VARCHAR(500),
        size_bytes  BIGINT,
        notes       TEXT
    )
    """,

]

# ─────────────────────────────────────────────
# INDEXES (performance-critical)
# ─────────────────────────────────────────────

_INDEX_STATEMENTS = [
    # org_id — every table
    "CREATE INDEX IF NOT EXISTS idx_users_org_id ON users(org_id)",
    "CREATE INDEX IF NOT EXISTS idx_owners_org_id ON owners(org_id)",
    "CREATE INDEX IF NOT EXISTS idx_teachers_org_id ON teachers(org_id)",
    "CREATE INDEX IF NOT EXISTS idx_students_org_id ON students(org_id)",
    "CREATE INDEX IF NOT EXISTS idx_classes_org_id ON classes(org_id)",
    "CREATE INDEX IF NOT EXISTS idx_subjects_org_id ON subjects(org_id)",
    "CREATE INDEX IF NOT EXISTS idx_resources_org_id ON resources(org_id)",
    "CREATE INDEX IF NOT EXISTS idx_attendance_org_id ON attendance(org_id)",
    "CREATE INDEX IF NOT EXISTS idx_homework_org_id ON homework(org_id)",
    "CREATE INDEX IF NOT EXISTS idx_tests_org_id ON tests(org_id)",
    "CREATE INDEX IF NOT EXISTS idx_test_results_org_id ON test_results(org_id)",
    "CREATE INDEX IF NOT EXISTS idx_announcements_org_id ON announcements(org_id)",
    "CREATE INDEX IF NOT EXISTS idx_parent_notifications_org_id ON parent_notifications(org_id)",
    "CREATE INDEX IF NOT EXISTS idx_subscriptions_org_id ON subscriptions(org_id)",
    "CREATE INDEX IF NOT EXISTS idx_audit_logs_org_id ON audit_logs(org_id)",

    # telegram_id — authentication critical
    "CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)",
    "CREATE INDEX IF NOT EXISTS idx_teachers_telegram_id ON teachers(telegram_id)",
    "CREATE INDEX IF NOT EXISTS idx_students_telegram_id ON students(telegram_id)",
    "CREATE INDEX IF NOT EXISTS idx_owners_telegram_id ON owners(telegram_id)",

    # student_id
    "CREATE INDEX IF NOT EXISTS idx_attendance_details_student_id ON attendance_details(student_id)",
    "CREATE INDEX IF NOT EXISTS idx_test_results_student_id ON test_results(student_id)",
    "CREATE INDEX IF NOT EXISTS idx_test_attempts_student_id ON test_attempts(student_id)",
    "CREATE INDEX IF NOT EXISTS idx_parent_notifications_student_id ON parent_notifications(student_id)",

    # teacher_id
    "CREATE INDEX IF NOT EXISTS idx_attendance_teacher_id ON attendance(teacher_id)",
    "CREATE INDEX IF NOT EXISTS idx_homework_teacher_id ON homework(teacher_id)",
    "CREATE INDEX IF NOT EXISTS idx_tests_teacher_id ON tests(teacher_id)",

    # test_id
    "CREATE INDEX IF NOT EXISTS idx_test_questions_test_id ON test_questions(test_id)",
    "CREATE INDEX IF NOT EXISTS idx_test_attempts_test_id ON test_attempts(test_id)",
    "CREATE INDEX IF NOT EXISTS idx_test_results_test_id ON test_results(test_id)",

    # date-based queries
    "CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date)",
    "CREATE INDEX IF NOT EXISTS idx_homework_date ON homework(date)",
    "CREATE INDEX IF NOT EXISTS idx_login_attempts_time ON login_attempts(attempt_time DESC)",
    "CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC)",
    "CREATE INDEX IF NOT EXISTS idx_bot_activity_timestamp ON bot_activity(timestamp DESC)",

    # subscriptions expiry check (scheduler)
    "CREATE INDEX IF NOT EXISTS idx_subscriptions_expiry ON subscriptions(expiry_date)",
    "CREATE INDEX IF NOT EXISTS idx_organizations_status ON organizations(status)",
]

# ─────────────────────────────────────────────
# DEFAULT SYSTEM SETTINGS SEED
# ─────────────────────────────────────────────

_SEED_SYSTEM_SETTINGS = """
    INSERT INTO system_settings (org_id, setting_name, setting_value)
    VALUES
        (NULL, 'max_login_attempts',            '5'),
        (NULL, 'login_lockout_minutes',         '30'),
        (NULL, 'command_rate_limit',            '10'),
        (NULL, 'rate_limit_window_seconds',     '60'),
        (NULL, 'abuse_block_threshold',         '30'),
        (NULL, 'abuse_block_duration_minutes',  '30'),
        (NULL, 'maintenance_mode',              'false'),
        (NULL, 'registrations_paused',          'false'),
        (NULL, 'max_students_per_institution',  '1000'),
        (NULL, 'max_teachers_per_institution',  '50'),
        (NULL, 'max_files_per_day',             '100'),
        (NULL, 'session_timeout_hours',         '24')
    ON CONFLICT (org_id, setting_name) DO NOTHING
"""


# ─────────────────────────────────────────────
# MAIN INITIALISATION FUNCTION
# ─────────────────────────────────────────────

async def initialise_tables() -> None:
    """
    Run all DDL statements and seed default data.
    Safe to call multiple times — all statements use IF NOT EXISTS.
    """
    pool = await get_pool()

    async with pool.acquire() as conn:
        async with conn.transaction():

            logger.info("Creating database tables...")
            for stmt in _DDL_STATEMENTS:
                await conn.execute(stmt)
            logger.info(f"✅ {len(_DDL_STATEMENTS)} tables ready.")

            logger.info("Creating indexes...")
            for stmt in _INDEX_STATEMENTS:
                await conn.execute(stmt)
            logger.info(f"✅ {len(_INDEX_STATEMENTS)} indexes ready.")

            logger.info("Seeding system settings...")
            await conn.execute(_SEED_SYSTEM_SETTINGS)
            logger.info("✅ System settings seeded.")

    logger.info("Database initialisation complete.")
