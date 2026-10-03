# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import time as tm
from database import db
from .test import parse_buttons

STATUS = {}

class STS:
    def __init__(self, id):
        self.id = id
        self.data = STATUS

    def verify(self):
        return self.data.get(self.id)

    def store(self, From, to, skip, limit, bot_id=None):
        self.data[self.id] = {
            "FROM": From,
            'TO': to,
            'total_files': 0,
            'skip': skip,
            'limit': limit,
            'fetched': skip,
            'filtered': 0,
            'deleted': 0,
            'duplicate': 0,
            'total': limit,
            'start': 0,
            'bot_id': bot_id
        }
        self.get(full=True)
        return STS(self.id)

    def get(self, value=None, full=False):
        values = self.data.get(self.id)
        if values is None:
            return None
        if not full:
           return values.get(value)
        for k, v in values.items():
            setattr(self, k, v)
        return self

    def add(self, key=None, value=1, time=False, start_time=None):
        if time:
          return self.data[self.id].update({'start': tm.time() if start_time is None else start_time})
        self.data[self.id].update({key: self.get(key) + value})

    def remove(self):
        """Delete this STS entry from the shared STATUS dict."""
        if self.id in self.data:
            del self.data[self.id]

    def divide(self, no, by):
       by = 1 if int(by) == 0 else by
       return int(no) / by

    async def get_data(self, user_id, bot_id=None):
        if bot_id is None:
            bots = await db.get_bots(user_id)
            for b in bots:
                if b.get('enabled', True):
                    bot_id = b['bot_id']
                    break
            if bot_id is None:
                return None, None, None, None, None, None

        bot = await db.get_bot(user_id, bot_id)
        if bot is None:
            return None, None, None, None, None, None

        configs = bot.get('configs', {})
        filters = await db.get_filters(user_id, bot_id)
        size = configs.get('min_size', 0)
        max_size = configs.get('max_size', 0)

        # 🔥 FIX: convert button to string to avoid TypeError
        button = parse_buttons(str(configs.get('button', '')))

        return bot, configs.get('caption'), configs.get('forward_tag'), {
            'filters': filters,
            'keywords': configs.get('keywords'),
            'min_size': size,
            'max_size': max_size,
            'extensions': configs.get('extension'),
            'skip_duplicate': configs.get('duplicate', True),
            'db_uri': configs.get('db_uri'),
            'link_remove': configs.get('link_remove', False),
            'forward_delay': configs.get('forward_delay', 0),
            'replace_link': configs.get('replace_link', None),
            'turbo_count': configs.get('turbo_count', 20),
            'turbo_sleep': configs.get('turbo_sleep', 30)
        }, configs.get('protect'), button
