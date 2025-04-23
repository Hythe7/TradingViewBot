import aiosqlite

# Инициализация базы данных
async def init_db():
    async with aiosqlite.connect("trades.db") as db:
        await db.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            chat_id INTEGER,
            coin TEXT,
            timeframe TEXT,
            entry REAL,
            targets TEXT,
            stop REAL,
            usdt_amount REAL,
            fee_entry_percent REAL,
            fee_exit_percent REAL,
            reason TEXT,
            status TEXT,
            close_price REAL,
            pnl REAL,
            profit_usdt REAL,
            tags TEXT,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        ''')
        await db.commit()

# Добавление новой сделки
async def insert_trade(user_id, chat_id, data: dict):
    async with aiosqlite.connect("trades.db") as db:
        await db.execute('''
            INSERT INTO trades (
                user_id, chat_id, coin, timeframe, entry, targets, stop,
                usdt_amount, fee_entry_percent, reason, status,
                close_price, pnl, profit_usdt, fee_exit_percent,
                tags, comment
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            chat_id,
            data['coin'],
            data['timeframe'],
            data['entry'],
            data['targets'],
            data['stop'],
            data['usdt_amount'],
            data['fee_entry_percent'],
            data['reason'],
            data['status'],
            data.get('close_price'),
            data.get('pnl'),
            data.get('profit_usdt'),
            data.get('fee_exit_percent'),
            data['tags'],
            data['comment']
        ))
        await db.commit()

# Получение статистики пользователя
async def get_stats(user_id):
    async with aiosqlite.connect("trades.db") as db:
        async with db.execute('''
            SELECT COUNT(*), AVG(pnl),
                   SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END),
                   SUM(profit_usdt)
            FROM trades
            WHERE user_id = ?
        ''', (user_id,)) as cursor:
            return await cursor.fetchone()

# Получить открытые сделки (для /closetrade)
async def get_open_trades(user_id):
    async with aiosqlite.connect("trades.db") as db:
        async with db.execute('''
            SELECT id, coin, entry, stop, targets FROM trades
            WHERE user_id = ? AND status = 'В позиции'
            ORDER BY created_at DESC
        ''', (user_id,)) as cursor:
            return await cursor.fetchall()

# Получить открытые сделки (для /open)
async def get_user_open_trades(user_id):
    async with aiosqlite.connect("trades.db") as db:
        async with db.execute('''
            SELECT coin, timeframe, entry, targets, stop, reason, created_at
            FROM trades
            WHERE user_id = ? AND status = 'В позиции'
            ORDER BY created_at DESC
        ''', (user_id,)) as cursor:
            return await cursor.fetchall()

# Обновить сделку при закрытии (цена выхода, PnL, профит)
async def close_trade(trade_id, close_price, pnl, profit_usdt, fee_exit_percent):
    async with aiosqlite.connect("trades.db") as db:
        await db.execute('''
            UPDATE trades
            SET status = 'Закрыто вручную',
                close_price = ?,
                pnl = ?,
                profit_usdt = ?,
                fee_exit_percent = ?
            WHERE id = ?
        ''', (close_price, pnl, profit_usdt, fee_exit_percent, trade_id))
        await db.commit()
