import os
import asyncio
import datetime
import time
from dotenv import load_dotenv  # Load environment variables
from motor.motor_asyncio import AsyncIOMotorClient
from pyrogram import Client, filters
from pyrogram.errors import InputUserDeactivated, UserNotParticipant, FloodWait, UserIsBlocked, PeerIdInvalid
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Load environment variables
load_dotenv()

# Fetch variables from .env
API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
DB_URL = os.getenv('DB_URL', '')
ADMINS = list(map(int, os.getenv('ADMINS', '').split(',')))  # Convert ADMINS to a list

# Check if DB_URL is valid
if not DB_URL:
    raise ValueError("❌ ERROR: `DB_URL` is missing or not set in the .env file!")

# Initialize Bot & Database
Dbclient = AsyncIOMotorClient(DB_URL)
Cluster = Dbclient['Cluster0']
Data = Cluster['users']
Bot = Client(name='AutoAcceptBot', api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Messages
ACCEPTED_TEXT = "Hey {user}\n\nYour Request For {chat} Is Accepted ✅"
START_TEXT = "Hi {}\n\nI am an Auto Request Accept Bot. Add me to your channel to use my features!"

# Start Command
@Bot.on_message(filters.command("start") & filters.private)
async def start_handler(c, m):
    user_id = m.from_user.id
    if not await Data.find_one({'id': user_id}):
        await Data.insert_one({'id': user_id})
    
    button = [
        [InlineKeyboardButton('Updates', url='https://t.me/QuantumEthics')],
        [InlineKeyboardButton('Support', url='https://t.me/InfoSecInsiders')]
    ]
    
    await m.reply_text(
        text=START_TEXT.format(m.from_user.mention),
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(button)
    )

# Broadcast & User Count
@Bot.on_message(filters.command(["broadcast", "users"]) & filters.user(ADMINS))
async def broadcast(c, m):
    if m.text == "/users":
        total_users = await Data.count_documents({})
        return await m.reply_text(f"Total Users: {total_users}")

    b_msg = m.reply_to_message
    if not b_msg:
        return await m.reply_text("Reply to a message to broadcast.")

    sts = await m.reply_text("📢 Broadcasting your message...")
    users = Data.find({})
    total_users = await Data.count_documents({})
    
    done, failed, success = 0, 0, 0
    start_time = time.time()

    async for user in users:
        user_id = int(user['id'])
        try:
            await b_msg.copy(chat_id=user_id)
            success += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
            try:
                await b_msg.copy(chat_id=user_id)
                success += 1
            except Exception:
                failed += 1
        except (InputUserDeactivated, PeerIdInvalid):
            await Data.delete_one({'id': user_id})
            failed += 1
        except UserIsBlocked:
            failed += 1
        except Exception as e:
            print(f"Error broadcasting to {user_id}: {e}")
            failed += 1
        done += 1
        
        if done % 20 == 0:
            await sts.edit(f"📢 Broadcast Progress:\n\n👥 Total Users: {total_users}\n✅ Success: {success}\n❌ Failed: {failed}")

    time_taken = str(datetime.timedelta(seconds=int(time.time() - start_time)))
    await sts.delete()
    
    await m.reply_text(f"✅ **Broadcast Completed**:\n\n⏳ Time Taken: {time_taken}\n👥 **Total Users**: {total_users}\n✅ **Success**: {success}\n❌ **Failed**: {failed}")

# Auto Accept Join Requests
@Bot.on_chat_join_request()
async def req_accept(c, m):
    user_id = m.from_user.id
    chat_id = m.chat.id
    
    if not await Data.find_one({'id': user_id}):
        await Data.insert_one({'id': user_id})

    await c.approve_chat_join_request(chat_id, user_id)
    
    try:
        await c.send_message(
            user_id, 
            ACCEPTED_TEXT.format(user=m.from_user.mention, chat=m.chat.title)
        )
    except Exception as e:
        print(f"Error sending message to {user_id}: {e}")

# Run Bot
Bot.run()
