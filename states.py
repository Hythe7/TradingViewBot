from aiogram.fsm.state import StatesGroup, State

class TradeForm(StatesGroup):
    coin = State()                # Монета (например, ETH/USDT)
    timeframe = State()           # Таймфрейм (например, 1H, 4H, D1)
    entry = State()               # Цена входа
    usdt_amount = State()         # 💵 Сумма сделки в USDT
    fee_entry = State()           # 📉 Комиссия при входе (%)
    targets = State()             # Цель (одна или несколько)
    stop = State()                # Стоп-лосс
    reason = State()              # Причина входа
    status = State()              # Статус: в позиции, закрыто и т.д.
    close_price = State()         # Цена выхода (если есть)
    pnl = State()                 # Прибыль/убыток (%)
    tags = State()                # Теги (#TON, #пробой, #откат и т.д.)
    comment = State()             # Комментарий

    close_trade_id = State()      # 🔹 Шаг 1: пользователь выбирает ID сделки для закрытия
    close_price_input = State()   # 🔹 Шаг 2: вводит цену закрытия
    fee_exit = State()            # 🔹 Шаг 3: вводит комиссию выхода (%)
