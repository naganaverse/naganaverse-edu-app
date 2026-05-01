from functools import wraps
from aiogram.types import Message, CallbackQuery
from database.repositories.subscription_repo import SubscriptionRepository

# Initialize your exact repo
sub_repo = SubscriptionRepository()

def enterprise_only(func):
    """
    A decorator (VIP Bouncer) that checks if the institute is on the Enterprise plan.
    It reads the 'user_session' injected by the global AuthMiddleware.
    """
    @wraps(func)
    async def wrapper(event, *args, **kwargs):
        # 1. Grab the session that AuthMiddleware already prepared for us!
        session = kwargs.get("user_session")
        
        if not session or not session.get("org_id"):
            # If there's no session, let it pass so AuthMiddleware can handle the error
            return await func(event, *args, **kwargs)

        org_id = session.get("org_id")

        # 2. Check the real-time subscription status from Supabase
        sub = await sub_repo.get_by_org(org_id)

        # 3. The Paywall Logic
        if sub and sub.plan.lower() == 'enterprise' and sub.status == 'active' and not sub.is_expired:
            # VIP Pass Granted! Run the premium feature.
            return await func(event, *args, **kwargs)
        else:
            # Block Starter users and show the upsell
            upsell_text = (
                "🔒 *Enterprise Feature*\n\n"
                "This action is only available on the *Enterprise Plan*.\n\n"
                "Upgrade for just ₹200 more to unlock:\n"
                "✅ Unlimited Excel Exports\n"
                "✅ Automated Parent WhatsApp Alerts\n"
                "✅ Online MCQ Tests\n"
                "✅ VIP Naganaverse Group Access\n\n"
                "💬 _Contact @NOTESVERSE_SUPPORT to upgrade._"
            )
            
            # Handle both Text Messages and Button Clicks cleanly in Aiogram
            if isinstance(event, Message):
                await event.answer(upsell_text, parse_mode='Markdown')
            elif isinstance(event, CallbackQuery):
                await event.message.answer(upsell_text, parse_mode='Markdown')
                await event.answer()
            
            # Return without running the function (blocks them from the feature)
            return

    return wrapper
              
