import aiosqlite
from datetime import datetime, timedelta

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

# Обновление сделки при закрытии
async def close_trade(trade_id: int, data: dict):
    async with aiosqlite.connect("trades.db") as db_conn:
        await db_conn.execute('''
            UPDATE trades
            SET status = ?,
                close_price = ?,
                fee_exit_percent = ?,
                profit_usdt = ?,
                pnl = ?,
                closed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            data['status'],
            data['close_price'],
            data['fee_exit_percent'],
            data['profit_usdt'],
            data['pnl'],
            trade_id
        ))
        await db_conn.commit()

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

# Получение закрытых сделок пользователя за период
async def get_closed_trades_in_period(user_id: int, start_date: str, end_date: str):
    async with aiosqlite.connect("trades.db") as db_conn:
        db_conn.row_factory = aiosqlite.Row
        cursor = await db_conn.execute('''
            SELECT pnl, profit_usdt
            FROM trades
            WHERE user_id = ?
              AND status = 'закрыта'
              AND DATE(closed_at) BETWEEN DATE(?) AND DATE(?)
        ''', (user_id, start_date, end_date))
        return await cursor.fetchall()

# Подсчёт количества открытых сделок пользователя
async def get_open_trades_count(user_id: int) -> int:
    async with aiosqlite.connect("trades.db") as db_conn:
        cursor = await db_conn.execute('''
            SELECT COUNT(*)
            FROM trades
            WHERE user_id = ?
              AND status = 'открыта'
        ''', (user_id,))
        result = await cursor.fetchone()
        return result[0] if result else 0

# Получение монет, по которым были сделки за 30 дней или есть открытые сделки
async def get_active_coins(user_id: int):
    async with aiosqlite.connect("trades.db") as db:
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        cursor = await db.execute('''
            SELECT DISTINCT coin
            FROM trades
            WHERE user_id = ?
              AND (
                (status = 'открыта')
                OR
                (status = 'закрыта' AND DATE(closed_at) >= DATE(?))
              )
        ''', (user_id, thirty_days_ago))
        rows = await cursor.fetchall()
        return [row[0] for row in rows] if rows else []

# Получение статистики по монете
async def get_coin_statistics(user_id: int, coin: str):
    async with aiosqlite.connect("trades.db") as db:
        cursor = await db.execute('''
            SELECT pnl, profit_usdt, closed_at
            FROM trades
            WHERE user_id = ? AND coin = ? AND status = 'закрыта'
        ''', (user_id, coin))
        rows = await cursor.fetchall()

    if not rows:
        return None

    total_pnl = 0
    total_profit = 0
    win_count = 0
    total_count = len(rows)
    last_trade_date = None

    for row in rows:
        pnl = row[0] or 0
        profit = row[1] or 0
        closed_at = row[2]

        total_pnl += pnl
        total_profit += profit
        if pnl > 0:
            win_count += 1

        if closed_at:
            last_trade_date = closed_at.split()[0]

    average_pnl = total_pnl / total_count if total_count else 0
    winrate = (win_count / total_count) * 100 if total_count else 0

    return {
        "average_pnl": average_pnl,
        "total_profit": total_profit,
        "total_trades": total_count,
        "winrate": winrate,
        "last_trade_date": last_trade_date
    }
