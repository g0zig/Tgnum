import logging
import sqlite3
import requests
import re
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ================= CONFIG =================
BOT_TOKEN = "8051287885:AAGSq7PC5T_mF2y7xt4hntV4kimhWWpMVuo"
ADMIN_ID = 8188215655

PUBLIC_CHANNEL = "@TITANXBOTMAKING"
PRIVATE_CHANNEL_1 = -1003835289143
PRIVATE_CHANNEL_2 = -1003838020313

PRIVATE_LINK_1 = "https://t.me/+gAY3EFjVYKg3MGJl"
PRIVATE_LINK_2 = "https://t.me/+8pOj2QfLFsVjNjU1"

API_URL = "https://api.subhxcosmo.in/api?key=suryanshHacker&type=sms&term="

POINTS_PER_REFER = 2
GETNUM_COST = 2
# ===========================================

logging.basicConfig(level=logging.INFO)

# ================= DATABASE =================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    points INTEGER DEFAULT 0,
    referred_by INTEGER,
    referrals INTEGER DEFAULT 0
)
""")
conn.commit()


# ================= FORCE JOIN CHECK =================
async def is_joined(user_id, context):
    try:
        channels = [PUBLIC_CHANNEL, PRIVATE_CHANNEL_1, PRIVATE_CHANNEL_2]
        for channel in channels:
            member = await context.bot.get_chat_member(channel, user_id)
            if member.status in ["left", "kicked"]:
                return False
        return True
    except:
        return False


async def force_join_message(update, context):
    keyboard = [
        [InlineKeyboardButton("📢 Join Public Channel", url=f"https://t.me/{PUBLIC_CHANNEL.replace('@','')}")],
        [InlineKeyboardButton("🔒 Join Private Channel 1", url=PRIVATE_LINK_1)],
        [InlineKeyboardButton("🔒 Join Private Channel 2", url=PRIVATE_LINK_2)],
        [InlineKeyboardButton("✅ Joined", callback_data="check_join")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "⚠️ Bot use karne ke liye pehle sab channels join karo:",
        reply_markup=reply_markup
    )


async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if await is_joined(user_id, context):
        await query.message.delete()
        await query.message.reply_text("✅ Verified! Ab /start likho.")
    else:
        await query.answer("❌ Abhi sab join nahi kiya!", show_alert=True)


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    if not await is_joined(user.id, context):
        await force_join_message(update, context)
        return

    cursor.execute("SELECT * FROM users WHERE user_id=?", (user.id,))
    existing = cursor.fetchone()

    if not existing:
        referred_by = None

        if args:
            ref_id = int(args[0])
            if ref_id != user.id:
                cursor.execute("SELECT * FROM users WHERE user_id=?", (ref_id,))
                ref_user = cursor.fetchone()
                if ref_user:
                    referred_by = ref_id
                    cursor.execute(
                        "UPDATE users SET points=points+?, referrals=referrals+1 WHERE user_id=?",
                        (POINTS_PER_REFER, ref_id),
                    )

                    await context.bot.send_message(
                        ref_id,
                        f"🎉 New Referral Joined!\n\n💰 {POINTS_PER_REFER} Points Added!"
                    )

        cursor.execute(
            "INSERT INTO users (user_id, points, referred_by) VALUES (?, ?, ?)",
            (user.id, 0, referred_by),
        )
        conn.commit()

        await context.bot.send_message(
            ADMIN_ID,
            f"🆕 New User:\nID: {user.id}\nName: {user.full_name}"
        )

    keyboard = [
        ["💰 Balance", "🔗 Refer"],
        ["👥 My Refers", "📲 Get Num"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Welcome to Referral Bot 🚀",
        reply_markup=reply_markup
    )


# ================= BUTTON HANDLER =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if not await is_joined(user_id, context):
        await force_join_message(update, context)
        return

    if text == "💰 Balance":
        cursor.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
        points = cursor.fetchone()[0]
        await update.message.reply_text(f"💰 Your Balance: {points} Points")

    elif text == "🔗 Refer":
        link = f"https://t.me/{context.bot.username}?start={user_id}"
        await update.message.reply_text(f"🔗 Your Referral Link:\n{link}")

    elif text == "👥 My Refers":
        cursor.execute("SELECT referrals FROM users WHERE user_id=?", (user_id,))
        refs = cursor.fetchone()[0]
        await update.message.reply_text(f"👥 Total Refers: {refs}")

    elif text == "📲 Get Num":
        cursor.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
        points = cursor.fetchone()[0]

        if points < GETNUM_COST:
            await update.message.reply_text("❌ Not enough points.")
        else:
            context.user_data["awaiting_id"] = True
            await update.message.reply_text("📩 Enter Telegram User ID:")

    else:
        if context.user_data.get("awaiting_id"):
            context.user_data["awaiting_id"] = False

            cursor.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
            points = cursor.fetchone()[0]

            if points >= GETNUM_COST:
                cursor.execute(
                    "UPDATE users SET points=points-? WHERE user_id=?",
                    (GETNUM_COST, user_id),
                )
                conn.commit()

                user_input = text.strip()
                response = requests.get(API_URL + user_input)
                data = response.text

                phone_match = re.search(r"(\+?\d{6,15})", data)

                if phone_match:
                    phone = phone_match.group(1)
                    await update.message.reply_text(
                        f"📱 Country Code + Phone Number:\n{phone}"
                    )
                else:
                    await update.message.reply_text("❌ Phone number not found.")
            else:
                await update.message.reply_text("❌ Not enough points.")


# ================= ADMIN COMMANDS =================
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]
    await update.message.reply_text(f"📊 Total Users: {total}")


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    msg = " ".join(context.args)
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    for user in users:
        try:
            await context.bot.send_message(user[0], msg)
        except:
            pass

    await update.message.reply_text("✅ Broadcast Sent")


async def give(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        user_id = int(context.args[0])
        amount = int(context.args[1])

        cursor.execute(
            "UPDATE users SET points=points+? WHERE user_id=?",
            (amount, user_id)
        )
        conn.commit()

        await update.message.reply_text("✅ Coins Added Successfully")

        await context.bot.send_message(
            user_id,
            f"💎 Owner ne aapko {amount} Points diye hain!"
        )

    except:
        await update.message.reply_text("Usage: /give user_id amount")


# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("give", give))
    app.add_handler(CallbackQueryHandler(check_join_callback, pattern="check_join"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, buttons))

    app.run_polling()


if __name__ == "__main__":
    main()
