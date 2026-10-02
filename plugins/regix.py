#progress filled ◉ ○ █  ▒
# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import os
import sys 
import math
import time
import re
import asyncio 
import logging
import random
from .utils import STS
from database import Db, db
from .test import CLIENT, get_client, iter_messages
from config import Config, temp
from script import Script
from pyrogram import Client, filters 
from pyrogram.errors import FloodWait, MessageNotModified, ChannelInvalid, ChannelPrivate
from pyrogram.errors.exceptions.not_acceptable_406 import ChannelPrivate as PrivateChat
from pyrogram.errors.exceptions.bad_request_400 import UsernameInvalid, UsernameNotModified
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message 
from .db import connect_user_db
from pyrogram.types import Message
from .linkremoveforwd import strip_urls, strip_anchors_and_urls

CLIENT = CLIENT()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
TEXT = Script.TEXT


# ============ EXACT KEYWORD MATCHING FUNCTIONS ============

async def keyword_filter(keywords, content):
    if keywords is None:
        return False
    if not content:
        return True
    
    keyword_list = keywords.split('|')
    exact_patterns = []
    for kw in keyword_list:
        if not kw:
            continue
        escaped_kw = re.escape(kw)
        exact_patterns.append(r'\b' + escaped_kw + r'\b')
    
    if not exact_patterns:
        return False
    
    exact_pattern = '|'.join(exact_patterns)
    
    if re.search(exact_pattern, content, re.IGNORECASE):
        return False
    else:
        return True

async def should_filter_by_keywords(keywords, message):
    if keywords is None:
        return False
    all_content = get_keyword_content(message)
    if not all_content:
        return True if keywords else False
    return await keyword_filter(keywords, all_content)

def get_keyword_content(message):
    content_list = []
    
    if message.document:
        if message.document.file_name:
            content_list.append(message.document.file_name)
        if message.caption:
            content_list.append(message.caption)
    elif message.video:
        if message.video.file_name:
            content_list.append(message.video.file_name)
        if message.caption:
            content_list.append(message.caption)
    elif message.photo:
        if message.caption:
            content_list.append(message.caption)
    elif message.text:
        content_list.append(message.text)
    elif message.audio:
        if message.audio.file_name:
            content_list.append(message.audio.file_name)
        if message.caption:
            content_list.append(message.caption)
    elif message.animation:
        if message.animation.file_name:
            content_list.append(message.animation.file_name)
        if message.caption:
            content_list.append(message.caption)
    elif message.voice:
        if message.caption:
            content_list.append(message.caption)
    elif message.sticker:
        if message.sticker.emoji:
            content_list.append(message.sticker.emoji)
        if message.caption:
            content_list.append(message.caption)
    
    if content_list:
        return " ".join(content_list)
    return None

async def extension_filter(extensions, file_name):
    if extensions is None:
        return False
    if not file_name:
        return False
    return bool(re.search(extensions, file_name, re.IGNORECASE))

def clean_html_tags(text):
    """Remove HTML tags but preserve line breaks and spacing"""
    if not text:
        return text
    text = re.sub(r'<[^>]+>', '', text)
    text = text.strip()
    return text

def modify_caption(message, caption, link_remove, replace_link):
    base_caption = custom_caption(message, caption, strip_links=False)
    if not base_caption:
        return None

    if link_remove:
        base_caption = strip_anchors_and_urls(base_caption)
    elif replace_link:
        base_caption = clean_html_tags(base_caption)
        url_pattern = re.compile(r'(https?://\S+|t\.me/\S+|@\S+)', re.IGNORECASE)
        if replace_link.startswith('@'):
            base_caption = url_pattern.sub(replace_link, base_caption)
        else:
            base_caption = url_pattern.sub(replace_link, base_caption)
    else:
        pass

    return base_caption

# ============ TURBO SLEEP HELPER ============

async def turbo_sleep_with_status(user, m, sts, sleep_seconds, user_db=None):
    if sleep_seconds <= 0:
        return
    remaining = sleep_seconds
    while remaining > 0:
        if temp.CANCEL.get(user, False):
            return
        i = sts.get(full=True)
        if i.total > 0:
            percentage = "{:.0f}".format(float(i.fetched) * 100 / float(i.total))
        else:
            percentage = "0"
        status_text = f"sleeping {remaining} s"
        text = TEXT.format(i.fetched, i.total_files, i.duplicate, i.deleted,
                           i.skip, i.filtered, status_text, percentage, "sʟᴇᴇᴘɪɴɢ")
        progress = "●{0}{1}".format(
            ''.join(["●" for _ in range(math.floor(int(percentage) / 4))]),
            ''.join(["○" for _ in range(24 - math.floor(int(percentage) / 4))]))
        button = [[InlineKeyboardButton(progress, f'fwrdstatus#sleep#{remaining}#{percentage}#{sts.id}')]]
        button.append([InlineKeyboardButton('• ᴄᴀɴᴄᴇʟ', 'terminate_frwd')])
        await msg_edit(m, text, InlineKeyboardMarkup(button))
        await asyncio.sleep(1)
        remaining -= 1
    await edit(user, m, 'sʟᴇᴇᴘɪɴɢ', 5, sts, None)


# ============ LIVE CONFIG RELOAD FUNCTION ============

async def reload_turbo_config(user, bot_id, current_datas):
    """Reload user config from database and update turbo/delay settings."""
    configs = await db.get_bot_configs(user, bot_id)
    new_datas = current_datas.copy()
    new_datas['turbo_count'] = configs.get('turbo_count', 20)
    new_datas['turbo_sleep'] = configs.get('turbo_sleep', 30)
    new_datas['forward_delay'] = configs.get('forward_delay', 0)
    return new_datas


@Client.on_callback_query(filters.regex(r'^start_public'))
async def pub_(bot, message):
    user = message.from_user.id
    temp.CANCEL[user] = False
    frwd_id = message.data.split("_")[2]
    
    sts = STS(frwd_id)
    if not sts.verify():
      await message.answer("your are clicking on my old button", show_alert=True)
      return await message.message.delete()
    i = sts.get(full=True)
    if i.TO in temp.IS_FRWD_CHAT:
      return await message.answer("In Target chat a task is progressing. please wait until task complete", show_alert=True)
    m = await msg_edit(message.message, "<code>verifying your data's, please wait.</code>")
    
    # ============ GET BOT_ID FROM STS ============
    bot_id = i.bot_id
    if bot_id is None:
        # Fallback: get first enabled bot
        bots = await db.get_bots(user)
        for b in bots:
            if b.get('enabled', True):
                if 'bot_id' in b:
                    bot_id = b['bot_id']
                    break
        if bot_id is None:
            return await msg_edit(m, "<code>No bot found. Please add a bot using /settings !</code>", wait=True)
    
    # ============ CHECK IF BOT IS BUSY ============
    if temp.BOT_BUSY.get(bot_id, False):
        return await message.answer("This bot is currently busy with another forward. Please wait or use another bot.", show_alert=True)
    temp.BOT_BUSY[bot_id] = True
    
    # ============ GET BOT DATA USING BOT_ID ============
    _bot, caption, forward_tag, datas, protect, button = await sts.get_data(user, bot_id)
    
    if not _bot:
        temp.BOT_BUSY[bot_id] = False
        return await msg_edit(m, "<code>You didn't added any bot. Please add a bot using /settings !</code>", wait=True)
    
    filter = datas['filters']
    max_size = datas['max_size']
    min_size = datas['min_size']
    keyword = datas['keywords']
    exten = datas['extensions']
    keywords = ""
    extensions = ""
    if keyword:
        for key in keyword:
            keywords += f"{key}|"
        keywords = keywords.rstrip("|")
    else:
        keywords = None
    if exten:
        for ext in exten:
            extensions += f"{ext}|"
        extensions = extensions.rstrip("|")
    else:
        extensions = None
    
    if _bot['is_bot'] == True:
        data = _bot['token']
        is_bot_type = True
    else:
        data = _bot['session']
        is_bot_type = False
    
    try:
      client = await get_client(data, is_bot=is_bot_type)
      await client.start()
    except Exception as e:  
      temp.BOT_BUSY[bot_id] = False
      return await m.edit(e)
    
    await msg_edit(m, "<code>processing..</code>")
    
    # ============ Try to access source chat, switch bot if needed ============
    try: 
       await client.get_messages(sts.get("FROM"), sts.get("limit"))
    except (ChannelInvalid, ChannelPrivate) as e:
        if _bot and _bot.get('is_bot', True):
            userbots = await db.get_bots(user, is_bot=False)
            userbot = next((u for u in userbots if u.get('enabled', True)), None)
            if userbot:
                await msg_edit(m, "<code>Switching to userbot for private channel...</code>")
                try:
                    await client.stop()
                    if userbot['is_bot'] == True:
                        udata = userbot['token']
                        u_is_bot = True
                    else:
                        udata = userbot['session']
                        u_is_bot = False
                    client = await get_client(udata, is_bot=u_is_bot)
                    await client.start()
                    await client.get_messages(sts.get("FROM"), sts.get("limit"))
                    _bot = userbot
                    bot_id = userbot['bot_id']
                    _bot, caption, forward_tag, datas, protect, button = await sts.get_data(user, bot_id)
                except Exception as second_error:
                    await msg_edit(m, f"**Both bot and userbot failed.**\n\n{second_error}", retry_btn(frwd_id), True)
                    return await stop_client(client, user, bot_id)
            else:
                await msg_edit(m, f"**Source chat may be private. Please enable a userbot in /settings**", retry_btn(frwd_id), True)
                return await stop_client(client, user, bot_id)
        else:
            await msg_edit(m, f"**Cannot access source chat. Make sure your userbot is a member.**\n\n{str(e)}", retry_btn(frwd_id), True)
            return await stop_client(client, user, bot_id)
    except Exception as e:
        await msg_edit(m, f"**Source chat error: {str(e)[:200]}**", retry_btn(frwd_id), True)
        return await stop_client(client, user, bot_id)
    
    # Check target channel access
    try:
       k = await client.send_message(i.TO, "Testing")
       await k.delete()
    except Exception as e:
       await msg_edit(m, f"**Please make your {'UserBot' if not is_bot_type else 'Bot'} admin in target channel with full permissions.**\n\nError: {str(e)[:100]}", retry_btn(frwd_id), True)
       return await stop_client(client, user, bot_id)
    
    user_have_db = False
    dburi = datas['db_uri']
    if dburi is not None:
        connected, user_db = await connect_user_db(user, dburi, i.TO)
        if not connected:
            await msg_edit(m, "<code>Cannot Connected Your db Errors Found Dup files Have Been Skipped after Restart</code>")
        else:
            user_have_db = True
    
    temp.forwardings += 1
    await db.add_frwd(user, bot_id)
    await send(client, user, "<b>Fᴏʀᴡᴀʀᴅɪɴɢ sᴛᴀʀᴛᴇᴅ 🔥</b>")
    sts.add(time=True)
    
    # Initial turbo & delay values
    turbo_count = datas.get('turbo_count', 20)
    turbo_sleep = datas.get('turbo_sleep', 30)
    forward_delay_cfg = datas.get('forward_delay', 0)
    
    await msg_edit(m, "<code>processing...</code>") 
    temp.IS_FRWD_CHAT.append(i.TO)
    
    turbo_counter = 0
    dup_files = []
    MSG = []
    pling = 0
    msg_counter = 0
    link_remove = datas['link_remove']
    replace_link = datas['replace_link']
    
    # Define sleep before loop
    if forward_delay_cfg > 0:
        sleep = forward_delay_cfg
    else:
        sleep = 3 if _bot['is_bot'] else 6
    
    await edit(user, m, 'sᴛᴀʀᴛɪɴɢ', 5, sts, bot_id)
    
    try:
        async for message in iter_messages(client, chat_id=sts.get("FROM"), limit=sts.get("limit"), offset=sts.get("skip"), filters=filter, max_size=max_size):
            if await is_cancelled(client, user, m, sts, bot_id):
                if user_have_db:
                    await user_db.drop_all()
                    await user_db.close()
                return
            
            # Reload config every 10 messages to apply live changes
            msg_counter += 1
            if msg_counter % 10 == 0:
                new_datas = await reload_turbo_config(user, bot_id, datas)
                if new_datas['turbo_count'] != turbo_count:
                    turbo_count = new_datas['turbo_count']
                    await msg_edit(m, f"<code>⚡ Turbo count updated to {turbo_count}</code>", wait=False)
                if new_datas['turbo_sleep'] != turbo_sleep:
                    turbo_sleep = new_datas['turbo_sleep']
                    await msg_edit(m, f"<code>😴 Turbo sleep updated to {turbo_sleep}s</code>", wait=False)
                if new_datas['forward_delay'] != forward_delay_cfg:
                    forward_delay_cfg = new_datas['forward_delay']
                    await msg_edit(m, f"<code>⏱️ Forward delay updated to {forward_delay_cfg if forward_delay_cfg>0 else 'auto'}</code>", wait=False)
                    if forward_delay_cfg > 0:
                        sleep = forward_delay_cfg
                    else:
                        sleep = 3 if _bot['is_bot'] else 6
                datas = new_datas
            
            if pling % 20 == 0: 
                await edit(user, m, 'sᴛᴀʀᴛɪɴɢ', 5, sts, bot_id)
            pling += 1
            sts.add('fetched')
            
            if message == "DUPLICATE":
                sts.add('duplicate')
                continue
            elif message == "FILTERED":
                sts.add('filtered')
                continue 
            elif message.empty or message.service:
                sts.add('deleted')
                continue
            
            if await should_filter_by_keywords(keywords, message):
                sts.add('filtered')
                continue
            
            if message.document and await extension_filter(extensions, message.document.file_name):
                sts.add('filtered')
                continue 
            
            if message.document and await size_filter(max_size, min_size, message.document.file_size):
                sts.add('filtered')
                continue 
            
            # Use file_unique_id for duplicate detection
            file_unique_id_to_check = None
            if message.document:
                file_unique_id_to_check = message.document.file_unique_id
            elif message.video:
                file_unique_id_to_check = message.video.file_unique_id
            elif message.photo:
                file_unique_id_to_check = message.photo.file_unique_id
            elif message.audio:
                file_unique_id_to_check = message.audio.file_unique_id
            elif message.animation:
                file_unique_id_to_check = message.animation.file_unique_id
            
            if file_unique_id_to_check and file_unique_id_to_check in dup_files:
                sts.add('duplicate')
                continue
            
            if file_unique_id_to_check and datas['skip_duplicate']:
                dup_files.append(file_unique_id_to_check)
                if user_have_db:
                    await user_db.add_file(file_unique_id_to_check)
            
            use_batch = forward_tag and not (link_remove or replace_link)
            
            if use_batch:
                MSG.append(message.id)
                notcompleted = len(MSG)
                completed = sts.get('total') - sts.get('fetched')
                if (notcompleted >= 100 or completed <= 100): 
                    await forward(user, client, MSG, m, sts, protect)
                    sts.add('total_files', notcompleted)
                    
                    if turbo_count > 0:
                        turbo_counter += notcompleted
                        if turbo_counter >= turbo_count:
                            await turbo_sleep_with_status(user, m, sts, turbo_sleep, user_db if user_have_db else None)
                            turbo_counter = 0
                    
                    await asyncio.sleep(10)
                    MSG = []
            else:
                new_caption = modify_caption(message, caption, link_remove, replace_link)
                details = {"msg_id": message.id, "media": media(message), "caption": new_caption, 'button': button, "protect": protect}
                await copy(user, client, details, m, sts)
                sts.add('total_files')
                
                if turbo_count > 0:
                    turbo_counter += 1
                    if turbo_counter >= turbo_count:
                        await turbo_sleep_with_status(user, m, sts, turbo_sleep, user_db if user_have_db else None)
                        turbo_counter = 0
                
                await asyncio.sleep(sleep) 
    except Exception as e:
        await msg_edit(m, f'<b>ERROR:</b>\n<code>{e}</code>', wait=True)
        print(e)
        if user_have_db:
            await user_db.drop_all()
            await user_db.close()
        temp.IS_FRWD_CHAT.remove(sts.TO)
        return await stop_client(client, user, bot_id)
    
    temp.IS_FRWD_CHAT.remove(sts.TO)
    await send(client, user, "<b>🎉 Tʜᴀɴᴋ ʏᴏᴜ ꜰᴏʀ ᴜsɪɴɢ ᴍᴇ</b>")
    await edit(user, m, 'ᴄᴏᴍᴘʟᴇᴛᴇᴅ', "completed", sts, bot_id) 
    if user_have_db:
        await user_db.drop_all()
        await user_db.close()
    await stop_client(client, user, bot_id)
        

async def copy(user, bot, msg, m, sts):
   try:                               
     if msg.get("media") and msg.get("caption"):
        await bot.send_cached_media(
              chat_id=sts.get('TO'),
              file_id=msg.get("media"),
              caption=msg.get("caption"),
              reply_markup=msg.get('button'),
              protect_content=msg.get("protect"))
     else:
        await bot.copy_message(
              chat_id=sts.get('TO'),
              from_chat_id=sts.get('FROM'),    
              caption=msg.get("caption"),
              message_id=msg.get("msg_id"),
              reply_markup=msg.get('button'),
              protect_content=msg.get("protect"))
   except FloodWait as e:
     await edit(user, m, 'sʟᴇᴇᴘɪɴɢ', e.value, sts, None)
     await asyncio.sleep(e.value)
     await edit(user, m, 'sᴛᴀʀᴛɪɴɢ', 5, sts, None)
     await copy(user, bot, msg, m, sts)
   except Exception as e:
     print(e)
     sts.add('deleted')

async def forward(user, bot, msg, m, sts, protect):
   try:                             
     await bot.forward_messages(
           chat_id=sts.get('TO'),
           from_chat_id=sts.get('FROM'), 
           protect_content=protect,
           message_ids=msg)
   except FloodWait as e:
     await edit(user, m, 'sʟᴇᴇᴘɪɴɢ', e.value, sts, None)
     await asyncio.sleep(e.value)
     await edit(user, m, 'sᴛᴀʀᴛɪɴɢ', 5, sts, None)
     await forward(user, bot, msg, m, sts, protect)

async def msg_edit(msg, text, button=None, wait=None):
    try:
        return await msg.edit(text, reply_markup=button)
    except MessageNotModified:
        pass 
    except FloodWait as e:
        if wait:
           await asyncio.sleep(e.value)
           return await msg_edit(msg, text, button, wait)

async def edit(user, msg, title, status, sts, bot_id):
   i = sts.get(full=True)
   status = 'Forwarding' if status == 5 else f"sleeping {status} s" if str(status).isnumeric() else status
   percentage = "{:.0f}".format(float(i.fetched)*100/float(i.total)) if i.total > 0 else "0"
   
   # ============ ETA REMOVED ============
   text = TEXT.format(i.fetched, i.total_files, i.duplicate, i.deleted, i.skip, i.filtered, status, percentage, title)
   await update_forward(user_id=user, last_id=None, start_time=i.start, limit=i.limit, chat_id=i.FROM, toid=i.TO, forward_id=None, msg_id=msg.id, fetched=i.fetched, deleted=i.deleted, total=i.total_files, duplicate=i.duplicate, skip=i.skip, filterd=i.filtered, bot_id=bot_id)
   
   progress = "◉{0}{1}".format(
       ''.join(["◉" for i in range(math.floor(int(percentage) / 4))]),
       ''.join(["○" for i in range(24 - math.floor(int(percentage) / 4))]))
   
   button = [[InlineKeyboardButton(progress, f'fwrdstatus#{status}#0#{percentage}#{i.id}')]]
   
   if status in ["cancelled", "completed"]:
      button.append([InlineKeyboardButton('• ᴄᴏᴍᴘʟᴇᴛᴇᴅ •', url='https://t.me/VJ_BOTZ')])
   else:
      button.append([InlineKeyboardButton('• ᴄᴀɴᴄᴇʟ', 'terminate_frwd')])
   
   await msg_edit(msg, text, InlineKeyboardMarkup(button))

async def is_cancelled(client, user, msg, sts, bot_id):
   if temp.CANCEL.get(user)==True:
      if sts.TO in temp.IS_FRWD_CHAT:
         temp.IS_FRWD_CHAT.remove(sts.TO)
      await edit(user, msg, 'ᴄᴀɴᴄᴇʟʟᴇᴅ', "cancelled", sts, bot_id)
      await send(client, user, "<b>❌ Fᴏʀᴡᴀʀᴅɪɴɢ ᴄᴀɴᴄᴇʟʟᴇᴅ</b>")
      await stop_client(client, user, bot_id)
      return True 
   return False 

async def stop_client(client, user, bot_id=None):
   try:
     await client.stop()
   except:
     pass 
   await db.rmve_frwd(user)
   temp.forwardings -= 1
   if bot_id:
       temp.BOT_BUSY[bot_id] = False

async def send(bot, user, text):
   try:
      await bot.send_message(user, text=text)
   except:
      pass 

def custom_caption(msg, caption, strip_links=False):
  if msg.media:
    if (msg.video or msg.document or msg.audio or msg.photo or msg.animation):
      fcaption = getattr(msg, 'caption', '')
      if fcaption:
        fcaption = fcaption.html
      if strip_links:
        fcaption = strip_urls(fcaption)
      
      file_name = ""
      file_size = 0
      
      if msg.animation:
        file_name = getattr(msg.animation, 'file_name', 'animation.gif')
        file_size = getattr(msg.animation, 'file_size', 0)
      elif msg.video:
        file_name = getattr(msg.video, 'file_name', '')
        file_size = getattr(msg.video, 'file_size', 0)
      elif msg.document:
        file_name = getattr(msg.document, 'file_name', '')
        file_size = getattr(msg.document, 'file_size', 0)
      elif msg.audio:
        file_name = getattr(msg.audio, 'file_name', '')
        file_size = getattr(msg.audio, 'file_size', 0)
      elif msg.photo:
        file_size = getattr(msg.photo, 'file_size', 0)
        file_name = 'photo.jpg'
      
      if caption:
        try:
          return caption.format(filename=file_name, size=get_size(file_size), caption=fcaption)
        except KeyError as e:
          return fcaption
      return fcaption
  return None

def get_size(size):
  units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
  size = float(size)
  i = 0
  while size >= 1024.0 and i < len(units):
     i += 1
     size /= 1024.0
  return "%.2f %s" % (size, units[i]) 

async def size_filter(max_size, min_size, file_size):
    file_size = file_size / 1024 / 1024
    if max_size and min_size == 0:
        return False
    if max_size == 0:
        return file_size < min_size
    if min_size == 0:
        return file_size > max_size
    if not min_size <= file_size <= max_size:
        return True
    else:
        return False

def media(msg):
  if msg.media:
     media = getattr(msg, msg.media.value, None)
     if media:
        return getattr(media, 'file_id', None)
  return None 

def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "") + \
        ((str(milliseconds) + "ms, ") if milliseconds else "")
    return tmp[:-2]

def retry_btn(id):
    return InlineKeyboardMarkup([[InlineKeyboardButton('♻️ RETRY ♻️', f"start_public_{id}")]])

@Client.on_callback_query(filters.regex(r'^terminate_frwd$'))
async def terminate_frwding(bot, m):
    user_id = m.from_user.id 
    temp.CANCEL[user_id] = True 
    await m.answer("Forwarding cancelled !", show_alert=True)

@Client.on_callback_query(filters.regex(r'^fwrdstatus'))
async def status_msg(bot, msg):
    try:
        parts = msg.data.split("#")
        if len(parts) < 5:
            await msg.answer("Status unavailable", show_alert=True)
            return
        status = parts[1]
        if status == "sleep":
            remaining = parts[2] if len(parts) > 2 else "?"
            await msg.answer(f"🚀 Turbo sleep in progress... {remaining} seconds remaining", show_alert=True)
            return
        est_time = parts[2]
        percentage = parts[3]
        frwd_id = parts[4]
        
        sts = STS(frwd_id)
        if not sts.verify():
           fetched, forwarded, remaining = 0, 0, 0
        else:
           fetched, limit, forwarded = sts.get('fetched'), sts.get('limit'), sts.get('total_files')
           remaining = limit - fetched 
        est_time = TimeFormatter(milliseconds=est_time)
        start_time = sts.get('start')
        uptime = await get_bot_uptime(start_time)
        total = sts.get('limit') - sts.get('fetched')
        time_to_comple = await complete_time(total)
        est_time = est_time if (est_time != '' or status not in ['completed', 'cancelled']) else '0 s'
        await msg.answer(PROGRESS.format(percentage, fetched, forwarded, remaining, status, time_to_comple, uptime), show_alert=True)
    except Exception as e:
        await msg.answer(f"Status: Forwarding in progress", show_alert=True)

@Client.on_callback_query(filters.regex(r'^close_btn$'))
async def close(bot, update):
    await update.answer()
    await update.message.delete()

@Client.on_message(filters.private & filters.command(['stop']))
async def stop_forward(client, message):
    user_id = message.from_user.id
    sts = await message.reply('<code>Stoping...</code>')
    await asyncio.sleep(0.5)
    if not await db.is_forwad_exit(message.from_user.id):
        return await sts.edit('**No Ongoing Forwards To Cancel**')
    temp.CANCEL[user_id] = True
    mst = await db.get_forward_details(user_id)
    bot_id = mst.get('bot_id')
    if bot_id:
        temp.BOT_BUSY[bot_id] = False
    msg = await client.get_messages(user_id, mst['msg_id'])
    await sts.edit(f"<b>Successfully Canceled</b>", disable_web_page_preview=True)

async def restart_pending_forwads(bot, user):
    user_id = user['user_id']
    settings = await db.get_forward_details(user_id)
    bot_id = settings.get('bot_id')
    
    # ============ FIX: If no bot_id in settings, find first enabled bot ============
    if bot_id is None:
        bots = await db.get_bots(user_id)
        for b in bots:
            if b.get('enabled', True):
                if 'bot_id' in b:
                    bot_id = b['bot_id']
                    break
        if bot_id is None:
            await db.rmve_frwd(user_id)
            return
    
    # ============ FIX: Get bot data with bot_id ============
    _bot = await db.get_bot(user_id, bot_id)
    if not _bot:
        await db.rmve_frwd(user_id)
        return
    
    try:
       skiping = settings['offset']
       fetch = settings['fetched'] - settings['skip']
       temp.forwardings += 1
       forward_id = await store_vars(user_id, bot_id)
       sts = STS(forward_id)
       if settings['chat_id'] is None:
           await db.rmve_frwd(user_id)
           temp.forwardings -= 1
           return
       if not sts.verify():
          temp.forwardings -= 1
          return 
       sts.add('fetched', value=fetch)
       sts.add('duplicate', value=settings['duplicate'])
       sts.add('filtered', value=settings['filtered'])
       sts.add('deleted', value=settings['deleted'])
       sts.add('total_files', value=settings['total'])
       
       try:
           m = await bot.get_messages(user_id, settings['msg_id'])
       except:
           await db.rmve_frwd(user_id)
           return
       
       # ============ GET BOT DATA USING BOT_ID ============
       _bot, caption, forward_tag, datas, protect, button = await sts.get_data(user_id, bot_id)
       
       if not _bot:
          await db.rmve_frwd(user_id)
          return
       
       i = sts.get(full=True)
       filter = datas['filters']
       max_size = datas['max_size']
       min_size = datas['min_size']
       keyword = datas['keywords']
       exten = datas['extensions']
       keywords = ""
       extensions = ""
       if keyword:
           for key in keyword:
               keywords += f"{key}|"
           keywords = keywords.rstrip("|")
       else:
           keywords = None
       if exten:
           for ext in exten:
               extensions += f"{ext}|"
           extensions = extensions.rstrip("|")
       else:
           extensions = None
       
       if _bot['is_bot'] == True:
          data = _bot['token']
          is_bot_type = True
       else:
          data = _bot['session']
          is_bot_type = False
       
       try:
          client = await get_client(data, is_bot=is_bot_type)
          await client.start()
       except Exception as e:
          try:
             await msg_edit(m, f"<code>Error: {str(e)[:100]}</code>", wait=True)
          except:
             pass
          await db.rmve_frwd(user_id)
          return
       
       try:
          await msg_edit(m, "<code>processing..</code>")
       except:
          await db.rmve_frwd(user_id)
          await client.stop()
          return
       
       try: 
          await client.get_messages(sts.get("FROM"), sts.get("limit"))
       except Exception as e:
          try:
             await msg_edit(m, f"**Source chat may be a private channel / group. Use userbot (user must be member over there) or make Your Bot an admin over there**", retry_btn(forward_id), True)
          except:
             pass
          await client.stop()
          await db.rmve_frwd(user_id)
          return
       
       try:
          k = await client.send_message(i.TO, "Testing")
          await k.delete()
       except Exception as e:
          try:
             await msg_edit(m, f"**Please Make Your Bot Admin In Target Channel With Full Permissions**", retry_btn(forward_id), True)
          except:
             pass
          await client.stop()
          await db.rmve_frwd(user_id)
          return
    except Exception as e:
       print(f"Restart error: {e}")
       await db.rmve_frwd(user_id)
       return
    
    user_have_db = False
    dburi = datas['db_uri']
    if dburi is not None:
        connected, user_db = await connect_user_db(user_id, dburi, i.TO)
        if not connected:
            try:
                await msg_edit(m, "<code>Cannot Connected Your db Errors Found Dup files Have Been Skipped after Restart</code>")
            except:
                pass
        else:
            user_have_db = True
    
    try:
        start = settings['start_time']
    except KeyError:
        start = None
    sts.add(time=True, start_time=start)
    
    # FORWARD DELAY - Use user setting or auto (3s bot, 6s userbot)
    forward_delay_cfg = datas.get('forward_delay', 0)
    if forward_delay_cfg > 0:
        sleep = forward_delay_cfg
    else:
        sleep = 3 if _bot['is_bot'] else 6
    
    temp.IS_FRWD_CHAT.append(i.TO)
    
    # TURBO SETTINGS
    turbo_count = datas.get('turbo_count', 20)
    turbo_sleep = datas.get('turbo_sleep', 30)
    turbo_counter = 0
    
    dup_files = []
    if user_have_db and datas['skip_duplicate']:
        old_files = await user_db.get_all_files()
        async for ofile in old_files:
            dup_files.append(ofile["file_unique_id"])
    
    MSG = []
    pling = 0
    msg_counter = 0
    link_remove = datas['link_remove']
    replace_link = datas['replace_link']
    
    try:
        await edit(user_id, m, 'sᴛᴀʀᴛɪɴɢ', 5, sts, bot_id)
    except:
        pass
    
    try:
        async for message in iter_messages(client, chat_id=sts.get("FROM"), limit=sts.get("limit"), offset=skiping, filters=filter, max_size=max_size):
            if await is_cancelled(client, user_id, m, sts, bot_id):
                if user_have_db:
                    await user_db.drop_all()
                    await user_db.close()
                return
            
            # Reload config every 10 messages (live update)
            msg_counter += 1
            if msg_counter % 10 == 0:
                new_datas = await reload_turbo_config(user_id, bot_id, datas)
                if new_datas['turbo_count'] != turbo_count:
                    turbo_count = new_datas['turbo_count']
                if new_datas['turbo_sleep'] != turbo_sleep:
                    turbo_sleep = new_datas['turbo_sleep']
                if new_datas['forward_delay'] != forward_delay_cfg:
                    forward_delay_cfg = new_datas['forward_delay']
                    sleep = forward_delay_cfg if forward_delay_cfg > 0 else (3 if _bot['is_bot'] else 6)
                datas = new_datas
            
            if pling % 20 == 0: 
                try:
                    await edit(user_id, m, 'sᴛᴀʀᴛɪɴɢ', 5, sts, bot_id)
                except:
                    pass
            pling += 1
            sts.add('fetched')
            
            if message == "DUPLICATE":
                sts.add('duplicate')
                continue
            elif message == "FILTERED":
                sts.add('filtered')
                continue 
            elif message.empty or message.service:
                sts.add('deleted')
                continue
            
            if await should_filter_by_keywords(keywords, message):
                sts.add('filtered')
                continue
            
            if message.document and await extension_filter(extensions, message.document.file_name):
                sts.add('filtered')
                continue 
            
            if message.document and await size_filter(max_size, min_size, message.document.file_size):
                sts.add('filtered')
                continue 
            
            # Use file_unique_id for duplicate detection
            file_unique_id_to_check = None
            if message.document:
                file_unique_id_to_check = message.document.file_unique_id
            elif message.video:
                file_unique_id_to_check = message.video.file_unique_id
            elif message.photo:
                file_unique_id_to_check = message.photo.file_unique_id
            elif message.audio:
                file_unique_id_to_check = message.audio.file_unique_id
            elif message.animation:
                file_unique_id_to_check = message.animation.file_unique_id
            
            if file_unique_id_to_check and file_unique_id_to_check in dup_files:
                sts.add('duplicate')
                continue
            
            if file_unique_id_to_check and datas['skip_duplicate']:
                dup_files.append(file_unique_id_to_check)
                if user_have_db:
                    await user_db.add_file(file_unique_id_to_check)
            
            use_batch = forward_tag and not (link_remove or replace_link)
            
            if use_batch:
                MSG.append(message.id)
                notcompleted = len(MSG)
                completed = sts.get('total') - sts.get('fetched')
                if (notcompleted >= 100 or completed <= 100): 
                    await forward(user_id, client, MSG, m, sts, protect)
                    sts.add('total_files', notcompleted)
                    
                    if turbo_count > 0:
                        turbo_counter += notcompleted
                        if turbo_counter >= turbo_count:
                            await turbo_sleep_with_status(user_id, m, sts, turbo_sleep, user_db if user_have_db else None)
                            turbo_counter = 0
                    
                    await asyncio.sleep(10)
                    MSG = []
            else:
                new_caption = modify_caption(message, caption, link_remove, replace_link)
                details = {"msg_id": message.id, "media": media(message), "caption": new_caption, 'button': button, "protect": protect}
                await copy(user_id, client, details, m, sts)
                sts.add('total_files')
                
                if turbo_count > 0:
                    turbo_counter += 1
                    if turbo_counter >= turbo_count:
                        await turbo_sleep_with_status(user_id, m, sts, turbo_sleep, user_db if user_have_db else None)
                        turbo_counter = 0
                
                await asyncio.sleep(sleep) 
    except Exception as e:
        try:
            await msg_edit(m, f'<b>ERROR:</b>\n<code>{str(e)[:200]}</code>', wait=True)
        except:
            pass
        if user_have_db:
            await user_db.drop_all()
            await user_db.close()
        temp.IS_FRWD_CHAT.remove(sts.TO)
        await client.stop()
        await db.rmve_frwd(user_id)
        return
    
    temp.IS_FRWD_CHAT.remove(sts.TO)
    try:
        await send(client, user_id, "<b>🎉 Tʜᴀɴᴋ ʏᴏᴜ ꜰᴏʀ ᴜsɪɴɢ ᴍᴇ</b>")
    except:
        pass
    if user_have_db:
        await user_db.drop_all()
        await user_db.close()
    try:
        await edit(user_id, m, 'ᴄᴏᴍᴘʟᴇᴛᴇᴅ', "completed", sts, bot_id) 
    except:
        pass
    await client.stop()
    await db.rmve_frwd(user_id)

async def store_vars(user_id, bot_id):
    settings = await db.get_forward_details(user_id)
    fetch = settings['fetched']
    forward_id = f'{user_id}-{fetch}'
    STS(id=forward_id).store(settings['chat_id'], settings['toid'], settings['skip'], settings['limit'], bot_id)
    return forward_id

async def restart_forwards(client):
    users = await db.get_all_frwd()
    tasks = []
    async for user in users:
        tasks.append(restart_pending_forwads(client, user))
    random_seconds = random.randint(0, 300)
    minutes = random_seconds // 60
    seconds = random_seconds % 60
    await asyncio.gather(*tasks)
    print('Done')

async def update_forward(user_id, chat_id, start_time, toid, last_id, limit, forward_id, msg_id, fetched, total, duplicate, deleted, skip, filterd, bot_id=None):
    details = {
        'chat_id': chat_id,
        'toid': toid,
        'forward_id': forward_id,
        'last_id': last_id,
        'limit': limit,
        'msg_id': msg_id,
        'start_time': start_time,
        'fetched': fetched,
        'offset': fetched,
        'deleted': deleted,
        'total': total,
        'duplicate': duplicate,
        'skip': skip,
        'filtered': filterd,
        'bot_id': bot_id
    }
    await db.update_forward(user_id, details)

async def get_bot_uptime(start_time):
    uptime_seconds = int(time.time() - start_time)
    uptime_minutes = uptime_seconds // 60
    uptime_hours = uptime_minutes // 60
    uptime_days = uptime_hours // 24
    uptime_weeks = uptime_days // 7
    uptime_string = ""
    if uptime_weeks != 0:
        uptime_string += f"{uptime_weeks % 7}w, "
    if uptime_days != 0:
        uptime_string += f"{uptime_days % 24}d, "
    if uptime_hours != 0:
        uptime_string += f"{uptime_hours % 24}h, "
    if uptime_minutes != 0:
        uptime_string += f"{uptime_minutes % 60}m, "
    uptime_string += f"{uptime_seconds % 60}s"
    return uptime_string  

async def complete_time(total_files, files_per_minute=30):
    minutes_required = total_files / files_per_minute
    seconds_required = minutes_required * 60
    weeks = seconds_required // (7 * 24 * 60 * 60)
    days = (seconds_required % (7 * 24 * 60 * 60)) // (24 * 60 * 60)
    hours = (seconds_required % (24 * 60 * 60)) // (60 * 60)
    minutes = (seconds_required % (60 * 60)) // 60
    seconds = seconds_required % 60
    time_format = ""
    if weeks > 0:
        time_format += f"{int(weeks)}w, "
    if days > 0:
        time_format += f"{int(days)}d, "
    if hours > 0:
        time_format += f"{int(hours)}h, "
    if minutes > 0:
        time_format += f"{int(minutes)}m, "
    if seconds > 0:
        time_format += f"{int(seconds)}s"
    return time_format
