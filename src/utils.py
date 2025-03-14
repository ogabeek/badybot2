from telegram import ChatMemberUpdated

def extract_status_change(chat_member_update: ChatMemberUpdated):
    """
    Determine if the bot was added or removed from a chat.
    Returns (was_member, is_member) or None if no change.
    """
    old_status = chat_member_update.old_chat_member.status
    new_status = chat_member_update.new_chat_member.status
    if old_status == new_status:
        return None
    was_member = old_status in ['member', 'administrator', 'creator']
    is_member = new_status in ['member', 'administrator', 'creator']
    return was_member, is_member