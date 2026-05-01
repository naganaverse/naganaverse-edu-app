"""
handlers/owner/fee_handler.py
─────────────────────────────────────────────────────────────
Owner: Fee Management System
- Log Payment (with Screenshot)
- Generate Class Dues (Monthly/Quarterly)
- View Defaulters & Stats
- Automated Parent Notifications
─────────────────────────────────────────────────────────────
"""

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from handlers.common.paywall import enterprise_only
import pandas as pd
import io


from core.filters import IsOwner
from core.loader import bot
from database.repositories.fee_repo import FeeRepository
from database.repositories.student_repo import StudentRepository
from keyboards.common_kb import nav_only_keyboard, nav_row
from keyboards.teacher_kb import class_select_keyboard

router = Router()
router.message.filter(IsOwner())
router.callback_query.filter(IsOwner())

_fee_repo = FeeRepository()
_student_repo = StudentRepository()

class FeeFSM(StatesGroup):
    # Payment Flow
    pay_enter_id = State()
    pay_enter_amount = State()
    pay_await_screenshot = State()
    
    # Bulk Due Flow
    bulk_select_class = State()
    bulk_enter_amount = State()

# ── 💰 Fee Dashboard ──────────────────────────────────────

@router.callback_query(F.data == "owner:fees")
async def cb_fee_dashboard(callback: CallbackQuery, user_session: dict):
    await callback.answer()
    org_id = user_session["org_id"]
    stats = await _fee_repo.get_org_financial_stats(org_id)
    
    text = (
        "💰 <b>Fee Management</b>\n\n"
        f"💵 <b>Total Collected:</b> ₹{stats['total_collected']:,}\n"
        f"⚠️ <b>Total Pending:</b>  ₹{stats['total_pending']:,}\n\n"
        "What would you like to do?"
    )
    
    

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Log Payment", callback_data="fee:log_pay")],
        [InlineKeyboardButton(text="🔄 Generate Dues", callback_data="fee:bulk_due")],
        [InlineKeyboardButton(text="📋 Defaulters List", callback_data="fee:defaulters")],
        [InlineKeyboardButton(text="📊 Export to Excel", callback_data="fee:export")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="owner:dashboard")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb)

# ── 💵 Log Payment Flow ───────────────────────────────────

@router.callback_query(F.data == "fee:log_pay")
async def cb_log_pay_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(FeeFSM.pay_enter_id)
    await callback.message.edit_text(
        "💵 <b>Log Payment</b>\n\nEnter the <b>Student ID</b> (e.g., STD101):",
        reply_markup=nav_only_keyboard()
    )

@router.message(FeeFSM.pay_enter_id)
async def msg_pay_id(message: Message, state: FSMContext, user_session: dict):
    std_id = message.text.strip().upper()
    student = await _student_repo.get_by_student_id(std_id, user_session["org_id"])
    
    if not student:
        await message.answer(f"❌ Student {std_id} not found.", reply_markup=nav_only_keyboard())
        return

    await state.update_data(std_id=std_id, std_name=student.name, current_due=student.current_due)
    await state.set_state(FeeFSM.pay_enter_amount)
    
    await message.answer(
        f"👤 <b>{student.name}</b>\n"
        f"📅 Class: {student.class_name}\n"
        f"⚠️ <b>Current Due: ₹{student.current_due}</b>\n\n"
        "How much is being paid now?",
        reply_markup=nav_only_keyboard()
    )

@router.message(FeeFSM.pay_enter_amount)
async def msg_pay_amount(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Please enter a valid number.")
        return
    
    amount = int(message.text)
    await state.update_data(pay_amount=amount)
    await state.set_state(FeeFSM.pay_await_screenshot)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Paid in Cash (Skip)", callback_data="fee:skip_screenshot")],
        [InlineKeyboardButton(text="🔙 Cancel", callback_data="owner:fees")]
    ])
    
    await message.answer(
        f"📸 <b>Step 3: Proof of Payment</b>\n\n"
        f"Please upload the <b>Screenshot/Photo</b> of the ₹{amount} payment.\n"
        "<i>If paid in cash, tap 'Skip'.</i>",
        reply_markup=kb
    )

@router.callback_query(FeeFSM.pay_await_screenshot, F.data == "fee:skip_screenshot")
@router.message(FeeFSM.pay_await_screenshot, F.photo | F.document)
async def handle_payment_final(event: [Message, CallbackQuery], state: FSMContext, user_session: dict):
    data = await state.get_data()
    file_id = None
    
    # Handle Photo vs Callback
    if isinstance(event, Message):
        if event.photo:
            file_id = event.photo[-1].file_id
        elif event.document:
            file_id = event.document.file_id
        msg_obj = event
    else:
        await event.answer()
        msg_obj = event.message

    success = await _fee_repo.log_payment(
        org_id=user_session["org_id"],
        student_id=data["std_id"],
        amount=data["pay_amount"],
        recorded_by=user_session["user_id"],
        receipt_file_id=file_id,
        notes="Logged via Bot"
    )

    if success:
        new_due = data["current_due"] - data["pay_amount"]
        await msg_obj.answer(
            f"✅ <b>Payment Logged Successfully!</b>\n\n"
            f"👤 {data['std_name']}\n"
            f"💰 Amount: ₹{data['pay_amount']}\n"
            f"📉 New Balance: ₹{new_due}",
            reply_markup=nav_only_keyboard()
        )
        
        # 🔔 AUTOMATED PARENT NOTIFICATION (Bulletproof Reliability)
        # We fetch parent ID and send receipt automatically
        student = await _student_repo.get_by_student_id(data["std_id"], user_session["org_id"])
        if student and student.parent_telegram_id:
            try:
                caption = (
                    f"🧾 <b>Fee Receipt</b>\n"
                    f"Institute: {user_session.get('org_name', 'Coaching')}\n"
                    f"Student: {student.name}\n"
                    f"Amount Paid: ₹{data['pay_amount']}\n"
                    f"Remaining Due: ₹{new_due}\n\n"
                    "Thank you for the payment!"
                )
                if file_id:
                    await bot.send_photo(student.parent_telegram_id, file_id, caption=caption)
                else:
                    await bot.send_message(student.parent_telegram_id, caption)
            except Exception as e:
                logger.error(f"Failed to notify parent of payment: {e}")
    else:
        await msg_obj.answer("❌ Error logging payment. Please try again.", reply_markup=nav_only_keyboard())
    
    await state.clear()

# ── 🔄 Bulk Due Generation ────────────────────────────────

@router.callback_query(F.data == "fee:bulk_due")
async def cb_bulk_due_start(callback: CallbackQuery, state: FSMContext, user_session: dict):
    await callback.answer()
    # Fetch classes from student repo
    from database.connection import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT DISTINCT class_name FROM students WHERE org_id = $1", user_session["org_id"])
    
    classes = [r["class_name"] for r in rows]
    await state.set_state(FeeFSM.bulk_select_class)
    await callback.message.edit_text(
        "🔄 <b>Generate Monthly Dues</b>\n\nSelect class to add dues for:",
        reply_markup=class_select_keyboard(classes, "bulk_fee_class")
    )

@router.callback_query(FeeFSM.bulk_select_class, F.data.startswith("bulk_fee_class:"))
async def cb_bulk_fee_class(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    class_name = callback.data.split(":", 1)[1]
    await state.update_data(target_class=class_name)
    await state.set_state(FeeFSM.bulk_enter_amount)
    await callback.message.edit_text(
        f"🔄 <b>Dues for {class_name}</b>\n\n"
        "Enter amount to add to all students:\n"
        "<i>(Type '0' to use each student's specific 'Agreed Fee')</i>",
        reply_markup=nav_only_keyboard()
    )

@router.message(FeeFSM.bulk_enter_amount)
async def msg_bulk_fee_final(message: Message, state: FSMContext, user_session: dict):
    if not message.text.isdigit():
        await message.answer("❌ Please enter a valid amount.")
        return
        # ── 📊 Excel Export Flow (Enterprise Only) ──────────────────────

@router.callback_query(F.data == "fee:export")
@enterprise_only    # <--- THE MAGIC VIP LOCK!
async def cb_export_fees(callback: CallbackQuery, user_session: dict):
    # If they reach this line, they passed the Paywall!
    org_id = user_session["org_id"]
    await callback.answer()
    await callback.message.answer("Generating your Excel report... ⏳")
    
    try:
        from database.connection import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Querying the students table to get their current dues
            rows = await conn.fetch(
                "SELECT student_id, name, class_name, current_due FROM students WHERE org_id = $1", 
                org_id
            )
            
        if not rows:
            await callback.message.answer("No student records found.")
            return
            
        # Convert to Pandas and make headers look professional
        df = pd.DataFrame([dict(row) for row in rows])
        df.rename(columns={
            'student_id': 'Student ID',
            'name': 'Student Name',
            'class_name': 'Class',
            'current_due': 'Due Amount (₹)'
        }, inplace=True)
        
        # Save to virtual RAM instead of hard drive
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Fee Report')
        
        buffer.seek(0)
        buffer.name = f"Fee_Report.xlsx"
        
        # Send the file
        await callback.message.answer_document(
            document=buffer, 
            caption="📊 Here is your beautifully formatted fee report!"
        )
        
    except Exception as e:
        from loguru import logger
        logger.error(f"Excel generation error: {e}")
        await callback.message.answer("An error occurred while generating the report.")
            
    
    data = await state.get_data()
    amount = int(message.text)
    custom_amount = amount if amount > 0 else None
    
    count = await _fee_repo.generate_class_dues(
        org_id=user_session["org_id"],
        class_name=data["target_class"],
        recorded_by=user_session["user_id"],
        custom_amount=custom_amount
    )
    
    await state.clear()
    await message.answer(
        f"✅ <b>Dues Generated!</b>\n\n"
        f"📚 Class: {data['target_class']}\n"
        f"👥 Students Updated: {count}",
        reply_markup=nav_only_keyboard()
)
  
