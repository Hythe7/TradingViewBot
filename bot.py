import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from config import BOT_TOKEN
from states import TradeForm
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import database as db

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Команда /start - приветственное сообщение
@dp.message(F.text == "/start")
async def start_handler(message: Message):
    await message.answer("Привет! Я трейд-журнал. Напиши /newtrade чтобы добавить сделку.")

# Команда /newtrade - начало ввода новой сделки
@dp.message(F.text == "/newtrade")
async def new_trade(message: Message, state: FSMContext):
    await state.set_state(TradeForm.coin)
    await message.answer("Монета (например, ETH/USDT):")

# Ввод монеты
@dp.message(TradeForm.coin)
async def trade_coin(message: Message, state: FSMContext):
    await state.update_data(coin=message.text)
    await state.set_state(TradeForm.timeframe)
    await message.answer("Таймфрейм (1H, 4H, D1):")

# Ввод таймфрейма
@dp.message(TradeForm.timeframe)
async def trade_timeframe(message: Message, state: FSMContext):
    await state.update_data(timeframe=message.text)
    await state.set_state(TradeForm.entry)
    await message.answer("Цена входа ($):")

# Ввод цены входа
@dp.message(TradeForm.entry)
async def trade_entry(message: Message, state: FSMContext):
    await state.update_data(entry=float(message.text))
    await state.set_state(TradeForm.usdt_amount)
    await message.answer("💵 Введи сумму сделки в USDT:")

# Ввод суммы сделки
@dp.message(TradeForm.usdt_amount)
async def trade_usdt_amount(message: Message, state: FSMContext):
    await state.update_data(usdt_amount=float(message.text))
    await state.set_state(TradeForm.fee_entry)
    await message.answer("📉 Введи комиссию при входе (%):")

# Ввод комиссии на вход
@dp.message(TradeForm.fee_entry)
async def trade_fee_entry(message: Message, state: FSMContext):
    await state.update_data(fee_entry_percent=float(message.text))
    await state.set_state(TradeForm.targets)
    await message.answer("Цель (пример: 2500 / 2700):")

# Ввод целей
@dp.message(TradeForm.targets)
async def trade_targets(message: Message, state: FSMContext):
    await state.update_data(targets=message.text)
    await state.set_state(TradeForm.stop)
    await message.answer("Стоп ($):")

# Ввод стопа
@dp.message(TradeForm.stop)
async def trade_stop(message: Message, state: FSMContext):
    await state.update_data(stop=float(message.text))
    await state.set_state(TradeForm.reason)
    await message.answer("Причина входа:")

# Ввод причины входа
@dp.message(TradeForm.reason)
async def trade_reason(message: Message, state: FSMContext):
    await state.update_data(reason=message.text)
    await state.set_state(TradeForm.status)
    await message.answer("Статус: В позиции / Закрыто с прибылью / Закрыто по стопу / Закрыто вручную")

# Ввод статуса
@dp.message(TradeForm.status)
async def trade_status(message: Message, state: FSMContext):
    await state.update_data(status=message.text)
    await state.set_state(TradeForm.close_price)
    await message.answer("Цена закрытия ($), если применимо. Или напиши -")

# Ввод цены закрытия
@dp.message(TradeForm.close_price)
async def trade_close_price(message: Message, state: FSMContext):
    close_text = message.text.strip()
    close_price = float(close_text) if close_text != "-" else None
    await state.update_data(close_price=close_price)
    await state.set_state(TradeForm.pnl)
    await message.answer("PnL (%), если знаешь. Или напиши -")

# Ввод PnL
@dp.message(TradeForm.pnl)
async def trade_pnl(message: Message, state: FSMContext):
    pnl_text = message.text.strip()
    pnl = float(pnl_text) if pnl_text != "-" else None
    await state.update_data(pnl=pnl)
    await state.set_state(TradeForm.tags)
    await message.answer("Теги (например: #TON #откат):")

# Ввод тегов
@dp.message(TradeForm.tags)
async def trade_tags(message: Message, state: FSMContext):
    await state.update_data(tags=message.text)
    await state.set_state(TradeForm.comment)
    await message.answer("Комментарий (или -):")

# Ввод комментария и сохранение сделки в базу
@dp.message(TradeForm.comment)
async def trade_comment(message: Message, state: FSMContext):
    comment = message.text.strip()
    if comment == "-":
        comment = ""
    await state.update_data(comment=comment)

    data = await state.get_data()
    await db.insert_trade(
        user_id=message.from_user.id,
        chat_id=message.chat.id,
        data=data
    )

    await message.answer("✅ Сделка сохранена!\n\nХочешь статистику? Напиши /stats")
    await state.clear()

# Команда /stats - статистика по сделкам
@dp.message(F.text == "/stats")
async def stats_handler(message: Message):
    total, avg_pnl, wins, total_profit = await db.get_stats(message.from_user.id)

    if total == 0 or total is None:
        await message.answer("😕 Пока нет ни одной сделки. Добавь её через /newtrade")
        return

    avg_pnl = avg_pnl or 0
    wins = wins or 0
    total_profit = total_profit or 0
    winrate = (wins / total * 100)

    await message.answer(
        f"📊 Твоя статистика:\n\n"
        f"Всего сделок: {total}\n"
        f"Средний PnL: {avg_pnl:.2f}%\n"
        f"Winrate: {winrate:.1f}%\n"
        f"💰 Общий профит: {total_profit:.2f} USDT"
    )

# Команда /open - выводит открытые сделки
@dp.message(F.text == "/open")
async def view_open_trades(message: Message):
    open_trades = await db.get_user_open_trades(message.from_user.id)

    if not open_trades:
        await message.answer("🟢 У тебя нет открытых сделок.")
        return

    response = "🧾 Открытые сделки:\n\n"
    for i, trade in enumerate(open_trades, 1):
        coin, tf, entry, targets, stop, reason, created_at = trade
        response += (
            f"#{i} | {coin} [{tf}]\n"
            f"Вход: ${entry:.2f}\n"
            f"Цель: {targets}\n"
            f"Стоп: ${stop:.2f}\n"
            f"Причина: {reason}\n"
            f"Дата: {created_at.split(' ')[0]}\n"
            f"---\n"
        )

    await message.answer(response)

# Команда /closetrade - закрытие открытой сделки с учетом комиссии
@dp.message(F.text == "/closetrade")
async def closetrade_start(message: Message, state: FSMContext):
    trades = await db.get_open_trades(message.from_user.id)
    if not trades:
        await message.answer("😎 У тебя нет открытых сделок.")
        return

    buttons = []
    for trade in trades:
        trade_id, coin, entry, stop, targets = trade
        label = f"{trade_id}: {coin} @ {entry}$ → Цель {targets}"
        buttons.append(KeyboardButton(text=label))

    markup = ReplyKeyboardMarkup(keyboard=[buttons[i:i+1] for i in range(len(buttons))], resize_keyboard=True)
    await state.set_state(TradeForm.close_trade_id)
    await message.answer("Выбери сделку для закрытия:", reply_markup=markup)

# Обработка выбора сделки для закрытия
@dp.message(TradeForm.close_trade_id)
async def select_trade_to_close(message: Message, state: FSMContext):
    try:
        trade_id = int(message.text.split(":")[0])
    except:
        await message.answer("❌ Неверный формат. Пожалуйста, выбери из списка.")
        return

    await state.update_data(trade_id=trade_id)
    await state.set_state(TradeForm.close_price_input)
    await message.answer("Введи цену закрытия ($):", reply_markup=types.ReplyKeyboardRemove())

# Ввод цены закрытия
@dp.message(TradeForm.close_price_input)
async def input_close_price(message: Message, state: FSMContext):
    try:
        close_price = float(message.text.strip())
    except:
        await message.answer("❌ Введи число.")
        return

    await state.update_data(close_price_input=close_price)
    await state.set_state(TradeForm.fee_exit)
    await message.answer("📉 Введи комиссию при выходе (%):")

# Ввод комиссии при выходе и расчет прибыли
@dp.message(TradeForm.fee_exit)
async def input_fee_exit(message: Message, state: FSMContext):
    try:
        fee_exit_percent = float(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи число.")
        return

    await state.update_data(fee_exit_percent=fee_exit_percent)
    data = await state.get_data()

    trade_id = data["trade_id"]
    close_price = data["close_price_input"]

    # Забираем необходимые значения из базы
    async with aiosqlite.connect("trades.db") as conn:
        async with conn.execute('''
            SELECT entry, usdt_amount, fee_entry_percent
            FROM trades
            WHERE id = ?
        ''', (trade_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                await message.answer("❌ Сделка не найдена.")
                return
            entry, usdt_amount, fee_entry_percent = row

    # Расчёт купленных монет с учётом комиссии на вход
    coins_bought = (usdt_amount / entry) * (1 - fee_entry_percent / 100)

    # Расчёт финальной выручки с учётом комиссии на выход
    final_usdt = (coins_bought * close_price) * (1 - fee_exit_percent / 100)

    # Расчёт итоговой прибыли
    profit_usdt = final_usdt - usdt_amount

    # PnL в процентах
    pnl = (profit_usdt / usdt_amount) * 100

    # Сохраняем результат
    await db.close_trade(
        trade_id,
        close_price,
        round(pnl, 2),
        round(profit_usdt, 2),
        fee_exit_percent
    )

    await message.answer(
        f"✅ Сделка закрыта!\n"
        f"📉 Цена закрытия: ${close_price}\n"
        f"📈 PnL: {pnl:.2f}%\n"
        f"💰 Профит: {profit_usdt:.2f} USDT"
    )
    await state.clear()







# Точка входа в приложение (запуск бота)
async def main():
    await db.init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
