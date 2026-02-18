import logging
import sqlite3
import requests
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================= CONFIG =================
BOT_TOKEN = "8051287885:AAGSq7PC5T_mF2y7xt4hntV4kimhWWpMVuo"
ADMIN_ID = 8188215655

PUBLIC_CHANNEL = "@TITANXBOTMAKING"
PRIVATE_CHANNEL_1 = -1003835289143
PRIVATE_CHANNEL_2 = -1003838020313

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
        for channel in [PUBLIC_CHANNEL, PRIVATE_CHANNEL_1, PRIVATE_CHANNEL_2]:
            member = await context.bot.get_chat_member(channel, user_id)
            if member.status in ["left", "kicked"]:
                return False
        return True
    except:
        return False


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    if not await is_joined(user.id, context):
        await update.message.reply_text(
            f"⚠️ Pehle sab channels join karo:\n\n"
            f"{PUBLIC_CHANNEL}\n"
            f"Private channels ka link admin se lo."
        )
        return

    cursor.execute("SELECT * FROM users WHERE user_id=?", (user.id,))
    existing = cursor.fetchone()

    if not existing:
        referred_by = None

        if args:
            try:
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
            except:
                pass

        cursor.execute(
            "INSERT INTO users (user_id, points, referred_by) VALUES (?, ?, ?)",
            (user.id, 0, referred_by),
        )
        conn.commit()

        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"🆕 New User:\nID: {user.id}\nName: {user.full_name}"
            )
        except:
            pass

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
        await update.message.reply_text("⚠️ Pehle sab channels join karo.")
        return

    cursor.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
    data = cursor.fetchone()

    if not data:
        await update.message.reply_text("Please press /start first.")
        return

    points = data[0]

    if text == "💰 Balance":
        await update.message.reply_text(f"💰 Your Balance: {points} Points")

    elif text == "🔗 Refer":
        link = f"https://t.me/{context.bot.username}?start={user_id}"
        await update.message.reply_text(f"🔗 Your Referral Link:\n{link}")

    elif text == "👥 My Refers":
        cursor.execute("SELECT referrals FROM users WHERE user_id=?", (user_id,))
        refs = cursor.fetchone()[0]
        await update.message.reply_text(f"👥 Total Refers: {refs}")

    elif text == "📲 Get Num":
        if points < GETNUM_COST:
            await update.message.reply_text("❌ Not enough points.")
        else:
            context.user_data["awaiting_id"] = True
            await update.message.reply_text("📩 Enter Telegram User ID:")

    else:
        if context.user_data.get("awaiting_id"):
            context.user_data["awaiting_id"] = False

            if points >= GETNUM_COST:
                cursor.execute(
                    "UPDATE users SET points=points-? WHERE user_id=?",
                    (GETNUM_COST, user_id),
                )
                conn.commit()

                user_input = text.strip()

                try:
                    response = requests.get(API_URL + user_input, timeout=10)
                    result = response.text
                except:
                    result = "API Error ❌"

                await update.message.reply_text(f"📲 API Result:\n{result}")
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

    if not msg:
        await update.message.reply_text("Usage: /broadcast message")
        return

    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    for user in users:
        try:
            await context.bot.send_message(user[0], msg)
            await asyncio.sleep(0.1)
        except:
            pass

    await update.message.reply_text("✅ Broadcast Sent")


# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, buttons))

    print("Bot Running...")
    app.run_polling()


if __name__ == "__main__":
    main()
