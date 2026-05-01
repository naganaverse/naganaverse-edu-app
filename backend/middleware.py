from functools import wraps
from database.repositories.subscription_repo import SubscriptionRepository

# Initialize your exact repo
sub_repo = SubscriptionRepository()

def enterprise_only(func):
    @wraps(func)
    async def wrapper(message, *args, **kwargs):
        user_id = message.chat.id
        
        # 🚨 You will need to replace this with your actual function that gets the org_id
        org_id = await get_org_id_from_telegram_id(user_id) 
        
        if not org_id:
            await message.answer("Error: Could not find your institute.")
            return

        # Uses your repo's exact get_by_org method
        sub = await sub_repo.get_by_org(org_id)
        
        # Uses your exact model properties: plan, status, and is_expired!
        if sub and sub.plan.lower() == 'enterprise' and sub.status == 'active' and not sub.is_expired:
            # Let them through to the feature!
            return await func(message, *args, **kwargs)
        else:
            # Block them and send the Upsell Hook
            upsell_text = (
                "🔒 *Enterprise Feature*\n\n"
                "Exporting Fee Records to Excel is only available on the *Enterprise Plan*.\n\n"
                "Upgrade for just ₹200 more to unlock:\n"
                "✅ Unlimited Excel Exports\n"
                "✅ Automated Parent WhatsApp Alerts\n"
                "✅ Online MCQ Tests\n"
                "✅ VIP Naganaverse Group Access\n\n"
                "💬 _Contact @NOTESVERSE_SUPPORT to upgrade._"
            )
            # Send the upsell (Change message.answer to bot.send_message if using telebot)
            await message.answer(upsell_text, parse_mode='Markdown')
            
    return wrapper
    
