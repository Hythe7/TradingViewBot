from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def coin_keyboard():
    buttons = [
        [InlineKeyboardButton(text="BTC/USDT", callback_data="coin:BTC/USDT")],
        [InlineKeyboardButton(text="ETH/USDT", callback_data="coin:ETH/USDT")],
        [InlineKeyboardButton(text="SOL/USDT", callback_data="coin:SOL/USDT")],
        [InlineKeyboardButton(text="TON/USDT", callback_data="coin:TON/USDT")],
        [InlineKeyboardButton(text="DOGE/USDT", callback_data="coin:DOGE/USDT")],
        [InlineKeyboardButton(text="XRP/USDT", callback_data="coin:XRP/USDT")],
        [InlineKeyboardButton(text="Другая монета", callback_data="coin:custom")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def timeframe_keyboard():
    buttons = [
        [InlineKeyboardButton(text="1H", callback_data="tf:1H")],
        [InlineKeyboardButton(text="4H", callback_data="tf:4H")],
        [InlineKeyboardButton(text="1D", callback_data="tf:1D")],
        [InlineKeyboardButton(text="1W", callback_data="tf:1W")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def fee_entry_keyboard():
    buttons = [
        [InlineKeyboardButton(text="0.1%", callback_data="fee:0.1")],
        [InlineKeyboardButton(text="0.18%", callback_data="fee:0.18")],
        [InlineKeyboardButton(text="Другая", callback_data="fee:custom")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
