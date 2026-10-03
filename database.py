# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import motor.motor_asyncio
from config import Config

class Db:

    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.bots = self.db.bots
        self.col = self.db.users
        self.nfy = self.db.notify
        self.chl = self.db.channels

    def new_user(self, id, name):
        return dict(
            id=id,
            name=name,
            ban_status=dict(
                is_banned=False,
                ban_reason="",
            ),
        )

    async def add_user(self, id, name):
        user = self.new_user(id, name)
        await self.col.insert_one(user)

    async def is_user_exist(self, id):
        user = await self.col.find_one({'id': int(id)})
        return bool(user)

    async def total_users_count(self):
        count = await self.col.count_documents({})
        return count

    async def total_users_bots_count(self):
        bcount = await self.bots.count_documents({})
        count = await self.col.count_documents({})
        return count, bcount

    async def remove_ban(self, id):
        ban_status = dict(
            is_banned=False,
            ban_reason=''
        )
        await self.col.update_one({'id': id}, {'$set': {'ban_status': ban_status}})

    async def ban_user(self, user_id, ban_reason="No Reason"):
        ban_status = dict(
            is_banned=True,
            ban_reason=ban_reason
        )
        await self.col.update_one({'id': user_id}, {'$set': {'ban_status': ban_status}})

    async def get_ban_status(self, id):
        default = dict(
            is_banned=False,
            ban_reason=''
        )
        user = await self.col.find_one({'id': int(id)})
        if not user:
            return default
        return user.get('ban_status', default)

    async def get_all_users(self):
        return self.col.find({})

    async def delete_user(self, user_id):
        await self.col.delete_many({'id': int(user_id)})

    async def get_banned(self):
        users = self.col.find({'ban_status.is_banned': True})
        b_users = [user['id'] async for user in users]
        return b_users

    # ==================== MULTI-BOT METHODS ====================

    def _default_configs(self):
        return {
            'caption': None,
            'duplicate': True,
            'forward_tag': False,
            'min_size': 0,
            'max_size': 0,
            'extension': None,
            'keywords': None,
            'protect': None,
            'button': None,
            'db_uri': None,
            'link_remove': False,
            'replace_link': None,
            'forward_delay': 0,
            'turbo_count': 20,
            'turbo_sleep': 30,
            'filters': {
                'poll': True,
                'text': True,
                'audio': True,
                'voice': True,
                'video': True,
                'photo': True,
                'document': True,
                'animation': True,
                'sticker': True
            }
        }

    async def _generate_bot_id(self, user_id):
        existing = await self.bots.find({'user_id': user_id}).to_list(length=None)
        used = [doc.get('bot_id', 0) for doc in existing]
        for i in range(1, 5):
            if i not in used:
                return i
        return None

    async def add_bot(self, user_id, bot_data):
        existing = await self.bots.find({'user_id': user_id}).to_list(length=None)
        if len(existing) >= 4:
            return False, "You can have at most 3 bots and 1 userbot (total 4)."

        if not bot_data.get('is_bot', True):
            userbot_exists = await self.bots.find_one({'user_id': user_id, 'is_bot': False})
            if userbot_exists:
                return False, "You already have a userbot. Only one userbot is allowed."

        bot_id = await self._generate_bot_id(user_id)
        if bot_id is None:
            return False, "Bot limit reached."

        doc = {
            'user_id': user_id,
            'bot_id': bot_id,
            'is_bot': bot_data.get('is_bot', True),
            'name': bot_data['name'],
            'username': bot_data.get('username', ''),
            'enabled': True,
            'configs': self._default_configs(),
        }
        if bot_data.get('is_bot', True):
            doc['token'] = bot_data['token']
        else:
            doc['session'] = bot_data['session']

        await self.bots.insert_one(doc)
        return True, bot_id

    async def get_bots(self, user_id, is_bot=None):
        query = {'user_id': user_id}
        if is_bot is not None:
            query['is_bot'] = is_bot
        cursor = self.bots.find(query)
        return await cursor.to_list(length=None)

    async def get_bot(self, user_id, bot_id):
        return await self.bots.find_one({'user_id': user_id, 'bot_id': bot_id})

    async def remove_bot(self, user_id, bot_id):
        await self.bots.delete_one({'user_id': user_id, 'bot_id': bot_id})

    async def update_bot_status(self, user_id, bot_id, enabled):
        await self.bots.update_one(
            {'user_id': user_id, 'bot_id': bot_id},
            {'$set': {'enabled': enabled}}
        )

    async def update_bot_configs(self, user_id, bot_id, configs):
        await self.bots.update_one(
            {'user_id': user_id, 'bot_id': bot_id},
            {'$set': {'configs': configs}}
        )

    async def get_bot_configs(self, user_id, bot_id):
        bot = await self.get_bot(user_id, bot_id)
        if bot:
            return bot.get('configs', self._default_configs())
        return self._default_configs()

    async def get_filters(self, user_id, bot_id):
        configs = await self.get_bot_configs(user_id, bot_id)
        filters_dict = configs.get('filters', {})
        return [k for k, v in filters_dict.items() if v is False]

    # ==================== CHANNEL METHODS ====================

    async def in_channel(self, user_id: int, chat_id: int) -> bool:
        channel = await self.chl.find_one({"user_id": int(user_id), "chat_id": int(chat_id)})
        return bool(channel)

    async def add_channel(self, user_id: int, chat_id: int, title, username):
        channel = await self.in_channel(user_id, chat_id)
        if channel:
            return False
        return await self.chl.insert_one({"user_id": user_id, "chat_id": chat_id, "title": title, "username": username})

    async def remove_channel(self, user_id: int, chat_id: int):
        channel = await self.in_channel(user_id, chat_id)
        if not channel:
            return False
        return await self.chl.delete_many({"user_id": int(user_id), "chat_id": int(chat_id)})

    async def get_channel_details(self, user_id: int, chat_id: int):
        return await self.chl.find_one({"user_id": int(user_id), "chat_id": int(chat_id)})

    async def get_user_channels(self, user_id: int):
        channels = self.chl.find({"user_id": int(user_id)})
        return [channel async for channel in channels]

    # ==================== FORWARD SESSION METHODS (BOT-AWARE) ====================

    async def add_frwd(self, user_id, bot_id):
        # One active forward per (user, bot)
        await self.nfy.delete_many({'user_id': int(user_id), 'bot_id': bot_id})
        return await self.nfy.insert_one({'user_id': int(user_id), 'bot_id': bot_id})

    async def rmve_frwd(self, user_id=0, bot_id=None, all=False):
        if all:
            return await self.nfy.delete_many({})
        query = {'user_id': int(user_id)}
        if bot_id is not None:
            query['bot_id'] = bot_id
        return await self.nfy.delete_many(query)

    async def get_all_frwd(self):
        return self.nfy.find({})

    async def forwad_count(self):
        return await self.nfy.count_documents({})

    async def is_forwad_exit(self, user, bot_id=None):
        query = {'user_id': user}
        if bot_id is not None:
            query['bot_id'] = bot_id
        u = await self.nfy.find_one(query)
        return bool(u)

    async def get_forward_details(self, user_id, bot_id=None):
        default = {
            'chat_id': None,
            'forward_id': None,
            'toid': None,
            'last_id': None,
            'limit': None,
            'msg_id': None,
            'start_time': None,
            'fetched': 0,
            'offset': 0,
            'deleted': 0,
            'total': 0,
            'duplicate': 0,
            'skip': 0,
            'filtered': 0,
            'bot_id': None
        }
        query = {'user_id': int(user_id)}
        if bot_id is not None:
            query['bot_id'] = bot_id
        user = await self.nfy.find_one(query)
        if user:
            return user.get('details', default)
        return default

    async def update_forward(self, user_id, details):
        bot_id = details.get('bot_id')
        query = {'user_id': int(user_id)}
        if bot_id is not None:
            query['bot_id'] = bot_id
        await self.nfy.update_one(
            query,
            {'$set': {'details': details}},
            upsert=True
        )

    # ==================== MIGRATION ====================

    async def migrate_old_bots(self):
        try:
            old_bots = await self.db.bots.find({}).to_list(length=None)
            for old in old_bots:
                user_id = old['user_id']
                existing = await self.bots.find_one({'user_id': user_id, 'is_bot': True})
                if existing:
                    continue
                bot_data = {
                    'is_bot': True,
                    'name': old.get('name', 'Bot'),
                    'username': old.get('username', ''),
                    'token': old['token'],
                    'enabled': old.get('enabled', True),
                }
                await self.add_bot(user_id, bot_data)
        except:
            pass

        try:
            old_userbots = await self.db.userbot.find({}).to_list(length=None)
            for old in old_userbots:
                user_id = old['user_id']
                existing = await self.bots.find_one({'user_id': user_id, 'is_bot': False})
                if existing:
                    continue
                bot_data = {
                    'is_bot': False,
                    'name': old.get('name', 'Userbot'),
                    'username': old.get('username', ''),
                    'session': old['session'],
                    'enabled': old.get('enabled', True),
                }
                await self.add_bot(user_id, bot_data)
        except:
            pass

db = Db(Config.DATABASE_URI, Config.DATABASE_NAME)
