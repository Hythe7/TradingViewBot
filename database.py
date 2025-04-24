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
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            closed_at TIMESTAMP
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
                comment, closed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            chat_id,
            data.get('coin'),
            data.get('timeframe'),
            data.get('entry'),
            data.get('targets'),
            data.get('stop'),
            data.get('usdt_amount'),
            data.get('fee_entry_percent'),
            data.get('reason'),
            data.get('status'),
            data.get('close_price'),
            data.get('pnl'),
            data.get('profit_usdt'),
            data.get('fee_exit_percent'),
            data.get('comment'),
            data.get('closed_at')  # None, если сделка не закрыта
        ))
        await db.commit()

# Получение всех открытых сделок пользователя, отсортированных по дате
async def get_open_trades(user_id: int):
    async with aiosqlite.connect("trades.db") as db:
        cursor = await db.execute('''
            SELECT id, coin, usdt_amount
            FROM trades
            WHERE user_id = ? AND status = 'открыта'
            ORDER BY created_at ASC
        ''', (user_id,))
        return await cursor.fetchall()
