from aiogram.fsm.state import StatesGroup, State

class TradeForm(StatesGroup):
    creating_trade = State()          # Общий режим создания сделки
    coin = State()                    # Выбор монеты
    coin_manual = State()             # Ввод монеты вручную
    timeframe = State()              # Таймфрейм
    entry = State()                  # Цена входа
    usdt_amount = State()            # Сумма сделки в USDT
    fee_entry = State()              # Комиссия на вход
    fee_entry_custom = State()       # Ручная комиссия на вход
    targets = State()                # Цели
    stop = State()                   # Стоп
    reason = State()                 # Причина входа
    status = State()                 # Статус сделки
    close_price = State()            # Цена закрытия
    pnl = State()                    # PnL
    tags = State()                   # Теги
    comment = State()                # Комментарий
    close_trade_id = State()
    close_price_input = State()     # При ручном закрытии
    fee_exit = State()
    manual_close_price = State()    # Для статуса закрыто вручную 
    manual_close_fee = State()      # Для статуса закрыто вручную 
    manual_close_fee_select = State()   # Для статуса закрыто вручную 
    manual_close_fee_custom = State()   # Для статуса закрыто вручную 
