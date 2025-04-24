import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from config import BOT_TOKEN
from states import TradeForm, CloseDealForm
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import database as db
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import CallbackQuery


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Главное меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить сделку")],
        [KeyboardButton(text="📂 Открытые сделки")],
        [KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="ℹ️ Помощь")]
    ],
    resize_keyboard=True
)

# Команда /start - приветственное сообщение
@dp.message(F.text == "/start")
async def start_handler(message: Message):
    await message.answer("Привет! Я трейд-журнал. Выбери действие:", reply_markup=main_menu)

# Черновик-шаблон для добавления новой сделки
def render_trade_template(data: dict) -> str:
    return (
        f"📝 Черновик сделки\n\n"
        f"🪙 Монета: {data.get('coin') or '-'}\n"
        f"⏱ Таймфрейм: {data.get('timeframe') or '-'}\n"
        f"📥 Вход: {data.get('entry') or '-'}\n"
        f"💵 Сумма: {data.get('usdt_amount') or '-'}\n"
        f"📉 Комиссия: {data.get('fee_entry_percent') or '-'}\n"
        f"🎯 Цель: {data.get('targets') or '-'}\n"
        f"🛑 Стоп: {data.get('stop') or '-'}\n"
        f"📚 Причина: {data.get('reason') or '-'}\n"
        f"📌 Статус: {data.get('status') or '-'}\n"
    )

# Черновик-шаблон для закрытия сделки

async def render_trade_info_message(callback_or_message, trade_id: int):
    async with aiosqlite.connect("trades.db") as db:
        cursor = await db.execute('''
            SELECT coin, timeframe, entry, targets, stop, usdt_amount, fee_entry_percent, reason, created_at
            FROM trades
            WHERE id = ?
        ''', (trade_id,))
        trade = await cursor.fetchone()

    if not trade:
        await callback_or_message.answer("❌ Сделка не найдена.")
        return

    coin, tf, entry, targets, stop, amount, fee, reason, created = trade
    text = (
        f"🧾 Сделка #{trade_id}\n\n"
        f"🪙 Монета: #{coin}\n"
        f"⏱ Таймфрейм: {tf or '-'}\n"
        f"📥 Вход: ${entry:.2f}\n"
        f"💵 Сумма: {amount} USDT\n"
        f"📉 Комиссия: {fee}%\n"
        f"🎯 Цель: {targets or '-'}\n"
        f"🛑 Стоп: {stop or '-'}\n"
        f"📚 Причина: {reason or '-'}\n"
        f"📅 Дата: {created.split()[0]}"
    )

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔒 Закрыть сделку", callback_data=f"start_close:{trade_id}")],
        [InlineKeyboardButton(text="🔙 Назад к списку", callback_data="back_to_open_trades")]
    ])

    if isinstance(callback_or_message, CallbackQuery):
        await callback_or_message.message.edit_text(text, reply_markup=markup)
    else:
        await callback_or_message.answer(text, reply_markup=markup)



async def show_trade_draft(message_or_callback, state: FSMContext):
    data = await state.get_data()
    text = render_trade_template(data)

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪙 Монета", callback_data="set_coin")],
        [InlineKeyboardButton(text="⏱ Таймфрейм", callback_data="set_timeframe")],
        [InlineKeyboardButton(text="📥 Цена входа", callback_data="set_entry")],
        [InlineKeyboardButton(text="💵 Сумма сделки", callback_data="set_usdt")],
        [InlineKeyboardButton(text="📉 Комиссия", callback_data="set_fee")],
        [InlineKeyboardButton(text="🎯 Цель", callback_data="set_targets")],
        [InlineKeyboardButton(text="🛑 Стоп", callback_data="set_stop")],
        [InlineKeyboardButton(text="📚 Причина", callback_data="set_reason")],
        [InlineKeyboardButton(text="📌 Статус", callback_data="set_status")],
        [InlineKeyboardButton(text="✅ Сохранить сделку", callback_data="save_trade")]
    ])

    # Автоматически различаем callback и обычное сообщение
    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=markup)
    else:
        await message_or_callback.answer(text, reply_markup=markup)


# Кнопка "Добавить сделку"
@dp.message(F.text == "➕ Добавить сделку")
async def new_trade(message: Message, state: FSMContext):
    await state.set_state(TradeForm.creating_trade)
    # создаём начальные пустые данные
    await state.update_data(
        coin=None, timeframe=None, entry=None,
        usdt_amount=None, fee_entry_percent=None,
        targets=None, stop=None, reason=None,
        status=None, close_price=None, pnl=None,
        tags=None, comment=None
    )

    # отправляем шаблон
    await show_trade_draft(message, state)


#Обрботчик нажатия на кнопку "Монета"
@dp.callback_query(F.data == "set_coin")
async def set_coin_callback(callback: CallbackQuery, state: FSMContext):
    coins = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "TON/USDT", "DOGE/USDT", "XRP/USDT", "Другая монета"]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=coin, callback_data=f"coin:{coin}")] for coin in coins
    ])
    await callback.message.edit_text("Выбери монету:", reply_markup=keyboard)

#Обработчик нажатия на одну из монет
@dp.callback_query(F.data.startswith("coin:"))
async def coin_chosen(callback: CallbackQuery, state: FSMContext):
    coin = callback.data.split(":")[1]
    if coin == "Другая монета":
        await state.set_state(TradeForm.coin_manual)
        await callback.message.edit_text("Введи монету вручную (например, BTC/USDT):")
    else:
        await state.update_data(coin=coin)
        await state.set_state(TradeForm.creating_trade)

        # Обновлённый шаблон
        await show_trade_draft(callback, state)


#Обработчик тектового ввода монеты
@dp.message(TradeForm.coin_manual)
async def trade_coin_manual(message: Message, state: FSMContext):
    await state.update_data(coin=message.text)
    await state.set_state(TradeForm.creating_trade)

    # Возвращаемся в меню с обновлённым шаблоном
    await show_trade_draft(message, state)

# Ввод таймфрейма
@dp.callback_query(F.data == "set_timeframe")
async def set_timeframe_callback(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1H", callback_data="tf:1H"), InlineKeyboardButton(text="4H", callback_data="tf:4H")],
        [InlineKeyboardButton(text="1D", callback_data="tf:1D"), InlineKeyboardButton(text="1W", callback_data="tf:1W")]
    ])
    await callback.message.edit_text("Выбери таймфрейм:", reply_markup=keyboard)

#Обработка таймфрейма
@dp.callback_query(F.data.startswith("tf:"))
async def timeframe_chosen(callback: CallbackQuery, state: FSMContext):
    tf = callback.data.split(":")[1]
    await state.update_data(timeframe=tf)
    await state.set_state(TradeForm.creating_trade)

    # Обновлённый шаблон и возврат в меню
    await show_trade_draft(callback, state)

# Кнопка "Цена входа"
@dp.callback_query(F.data == "set_entry")
async def set_entry_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TradeForm.entry)
    await callback.message.edit_text("Введи цену входа ($):")

# Пользователь вручную вводит цену входа
@dp.message(TradeForm.entry)
async def trade_entry(message: Message, state: FSMContext):
    try:
        entry_price = float(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи корректную цену входа ($).")
        return

    await state.update_data(entry=entry_price)
    await state.set_state(TradeForm.creating_trade)

    # Обновляем шаблон
    await show_trade_draft(message, state)

# Кнопка суммы сделки
@dp.callback_query(F.data == "set_usdt")
async def set_usdt_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TradeForm.usdt_amount)
    await callback.message.edit_text("Введи сумму сделки в USDT:")

# Пользователь вручную вводит сумму сделки
@dp.message(TradeForm.usdt_amount)
async def trade_usdt_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи корректную сумму в USDT.")
        return

    await state.update_data(usdt_amount=amount)
    await state.set_state(TradeForm.creating_trade)

    # Обновляем шаблон
    await show_trade_draft(message, state)

# Хэндлер кнопки "Комиссия"
# При нажатии на кнопку — показ вариантов выбора
@dp.callback_query(F.data == "set_fee")
async def set_fee_callback(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="0.1%", callback_data="fee:0.1"), InlineKeyboardButton(text="0.18%", callback_data="fee:0.18")],
        [InlineKeyboardButton(text="Другой процент", callback_data="fee:custom")]
    ])
    await callback.message.edit_text("Выбери комиссию при входе:", reply_markup=keyboard)

# Обработка выбранной комиссии
# Пользователь нажал одну из кнопок с комиссией
@dp.callback_query(F.data.startswith("fee:"))
async def fee_chosen(callback: CallbackQuery, state: FSMContext):
    fee_value = callback.data.split(":")[1]

    if fee_value == "custom":
        await state.set_state(TradeForm.fee_entry_custom)
        await callback.message.edit_text("Введи комиссию вручную (%):")
    else:
        await state.update_data(fee_entry_percent=float(fee_value))
        await state.set_state(TradeForm.creating_trade)

        # Возврат к шаблону после выбора
        await show_trade_draft(callback, state)

# Если пользователь вручную вводит значение комиссии
@dp.message(TradeForm.fee_entry_custom)
async def fee_entry_custom_manual(message: Message, state: FSMContext):
    try:
        fee = float(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи корректное число.")
        return

    await state.update_data(fee_entry_percent=fee)
    await state.set_state(TradeForm.creating_trade)

    # Возврат к шаблону
    await show_trade_draft(message, state)


# Обработчик кнопки цели
@dp.callback_query(F.data == "set_targets")
async def set_targets_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TradeForm.targets)
    await callback.message.edit_text("Введи цели (например: 2500 / 2700):")

# Обработчик ввода цели
@dp.message(TradeForm.targets)
async def trade_targets(message: Message, state: FSMContext):
    await state.update_data(targets=message.text)
    await state.set_state(TradeForm.creating_trade)

    await show_trade_draft(message, state)


# Обработчик кнопки стопа
@dp.callback_query(F.data == "set_stop")
async def set_stop_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TradeForm.stop)
    await callback.message.edit_text("Введи стоп ($):")

# Обработчик ввода стопа
@dp.message(TradeForm.stop)
async def trade_stop(message: Message, state: FSMContext):
    try:
        stop = float(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи число.")
        return

    await state.update_data(stop=stop)
    await state.set_state(TradeForm.creating_trade)

    await show_trade_draft(message, state)

# Обработчик кнопки причины входа
@dp.callback_query(F.data == "set_reason")
async def set_reason_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TradeForm.reason)
    await callback.message.edit_text("Напиши причину входа:")

# Обработчик ввод причины входа
@dp.message(TradeForm.reason)
async def trade_reason(message: Message, state: FSMContext):
    await state.update_data(reason=message.text)
    await state.set_state(TradeForm.creating_trade)

    await show_trade_draft(message, state)

# Обработка кнопки "Статус"
@dp.callback_query(F.data == "set_status")
async def set_status_callback(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📍 В позиции", callback_data="status:В позиции")],
        [InlineKeyboardButton(text="✅ Закрыто с прибылью", callback_data="status:Закрыто с прибылью")],
        [InlineKeyboardButton(text="🛑 Закрыто по стопу", callback_data="status:Закрыто по стопу")],
        [InlineKeyboardButton(text="✋ Закрыто вручную", callback_data="status:manual_close")]
    ])
    await callback.message.edit_text("Выбери статус сделки:", reply_markup=keyboard)


# Обработка выбора статуса
@dp.callback_query(F.data.startswith("status:"))
async def status_chosen(callback: CallbackQuery, state: FSMContext):
    status_value = callback.data.split(":", 1)[1]

    if status_value == "manual_close":
        await state.set_state(TradeForm.manual_close_price)
        await callback.message.edit_text("🔒 Введи цену закрытия ($) для ручного закрытия:")
    else:
        await state.update_data(status=status_value)
        await state.set_state(TradeForm.creating_trade)
        await show_trade_draft(callback, state)

#Если закрыто вручную
# Обработка ввода цены закрытия
@dp.message(TradeForm.manual_close_price)
async def manual_close_price_handler(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи корректную цену закрытия ($).")
        return

    await state.update_data(manual_close_price=price)

    # Кнопки комиссии
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="0.1%", callback_data="manualfee:0.1"),
         InlineKeyboardButton(text="0.18%", callback_data="manualfee:0.18")],
        [InlineKeyboardButton(text="Ввести вручную", callback_data="manualfee:custom")]
    ])

    await state.set_state(TradeForm.manual_close_fee_select)
    await message.answer("📉 Выбери комиссию при закрытии:", reply_markup=keyboard)


# Обработка выбора комиссии
@dp.callback_query(F.data.startswith("manualfee:"))
async def manual_close_fee_handler(callback: CallbackQuery, state: FSMContext):
    fee_value = callback.data.split(":")[1]

    if fee_value == "custom":
        await state.set_state(TradeForm.manual_close_fee_custom)
        await callback.message.edit_text("📉 Введи комиссию при ручном закрытии (%):")
    else:
        price = (await state.get_data()).get("manual_close_price")
        await state.update_data(
            status=f"Закрыто вручную ${price}, комиссия {fee_value}%",
            manual_close_price=None
        )
        await state.set_state(TradeForm.creating_trade)
        await show_trade_draft(callback, state)


# Обработка ручного ввода комиссии
@dp.message(TradeForm.manual_close_fee_custom)
async def manual_fee_custom_entry(message: Message, state: FSMContext):
    try:
        fee = float(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи корректное число (%).")
        return

    price = (await state.get_data()).get("manual_close_price")
    await state.update_data(
        status=f"Закрыто вручную ${price}, комиссия {fee}%",
        manual_close_price=None
    )
    await state.set_state(TradeForm.creating_trade)
    await show_trade_draft(message, state)


# Обработка кнопки "Сохранить сделку"
@dp.callback_query(F.data == "save_trade")
async def ask_comment_choice(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data="comment:yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data="comment:no")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="comment:back")]
    ])
    await callback.message.edit_text("Хочешь добавить комментарий к сделке?", reply_markup=keyboard)


# Обработка выбора комментария (да/нет)
@dp.callback_query(F.data.startswith("comment:"))
async def comment_choice(callback: CallbackQuery, state: FSMContext):
    choice = callback.data.split(":")[1]

    if choice == "yes":
        await state.set_state(TradeForm.comment)
        await callback.message.edit_text("✍️ Напиши комментарий к сделке:")
    elif choice == "no":
        await state.update_data(comment=None)
        await finalize_trade(callback, state)
    elif choice == "back":
        await state.set_state(TradeForm.creating_trade)
        await show_trade_draft(callback, state)

# Функция проверки заполненности полей
def validate_trade_data(data: dict) -> tuple[bool, list[str]]:
    missing_fields = []

    # Обязательные поля для всех сделок
    if not data.get('coin'):
        missing_fields.append("монета")
    if not data.get('entry'):
        missing_fields.append("цена входа")
    if not data.get('usdt_amount'):
        missing_fields.append("сумма сделки (USDT)")
    if not data.get('fee_entry_percent'):
        missing_fields.append("комиссия на входе")
    if not data.get('status'):
        missing_fields.append("статус")

    # Дополнительные условия по статусу
    status = data.get('status')
    if status == "Закрыто с прибылью" and not data.get('targets'):
        missing_fields.append("цель")
    if status == "Закрыто по стопу" and not data.get('stop'):
        missing_fields.append("стоп")

    return len(missing_fields) == 0, missing_fields


# Кнопка возврата к черновику
@dp.callback_query(F.data == "back_to_draft")
async def back_to_draft(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TradeForm.creating_trade)
    await show_trade_draft(callback, state)

# Сохранение сделки и расчеты
async def finalize_trade(source: Message | CallbackQuery, state: FSMContext):
    data = await state.get_data()

    # Проверка обязательных полей
    is_valid, missing = validate_trade_data(data)
    if not is_valid:
        missing_text = ", ".join(missing)
        warning = f"⚠️ Не хватает обязательных полей:\n\n🔸 {missing_text}"

        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к черновику", callback_data="back_to_draft")]
        ])

        if isinstance(source, CallbackQuery):
            await source.message.edit_text(warning, reply_markup=markup)
        else:
            await source.answer(warning)
            await source.answer("Нажми кнопку ниже, чтобы вернуться к редактированию:", reply_markup=markup)
        return


    entry = data.get("entry")
    usdt_amount = data.get("usdt_amount")
    entry_fee = data.get("fee_entry_percent", 0.0)
    status = data.get("status")

    close_price = None
    exit_fee = 0.0
    profit = None
    pnl = None
    trade_status = "открыта"

    try:
        # Количество купленных монет с учетом комиссии на вход
        coins = (usdt_amount / entry) * (1 - entry_fee / 100)
    except ZeroDivisionError:
        if isinstance(source, CallbackQuery):
            await source.message.edit_text("❌ Невозможно рассчитать: проверь входную цену и сумму сделки.")
        else:
            await source.answer("❌ Невозможно рассчитать: проверь входную цену и сумму сделки.")
        return

    if status == "Закрыто с прибылью":
        close_price = float(data.get("targets").split("/")[0].strip())
        exit_fee = 0.18
        trade_status = "закрыта"
    elif status == "Закрыто по стопу":
        close_price = float(data.get("stop"))
        exit_fee = 0.18
        trade_status = "закрыта"
    elif status.startswith("Закрыто вручную"):
        close_price = float(data.get("close_price"))
        exit_fee = float(data.get("fee_exit"))
        trade_status = "закрыта"

    if close_price:
        final_usdt = (coins * close_price) * (1 - exit_fee / 100)
        profit = final_usdt - usdt_amount
        pnl = (profit / usdt_amount) * 100
        data["close_price"] = close_price
        data["pnl"] = round(pnl, 2)
        data["profit_usdt"] = round(profit, 2)
        data["fee_exit_percent"] = exit_fee
    else:
        
        data["close_price"] = None
        data["pnl"] = None
        data["profit_usdt"] = None
        data["fee_exit_percent"] = None

    # Упрощаем статус до "открыта"/"закрыта"
    data["status"] = trade_status

    # Сохраняем в базу
    user_id = source.from_user.id
    chat_id = source.message.chat.id if isinstance(source, CallbackQuery) else source.chat.id
    await db.insert_trade(user_id, chat_id, data)
    await state.clear()

    # Ответ пользователю
    comment = data.get("comment") or "-"
    base_msg = (
        f"✅ Сделка сохранена\n\n"
        f"📌 Статус: {trade_status.capitalize()}\n"
        f"🪙 Монета: #{data.get('coin')}\n"
        f"⏱ Таймфрейм: {data.get('timeframe') or '-'}\n"
        f"📥 Цена входа: {entry}\n"
        f"💵 Сумма: {usdt_amount} USDT\n"
        f"🎯 Цель: {data.get('targets') or '-'}\n"
        f"🛑 Стоп: {data.get('stop') or '-'}\n"
        f"📚 Комментарий: {comment}\n"
    )

    if trade_status == "закрыта":
        base_msg += (
            f"📉 Цена закрытия: {close_price}\n"
            f"📈 PnL: {data['pnl']}%\n"
            f"💰 Профит: {data['profit_usdt']} USDT\n"
        )

    await source.message.answer(base_msg)


# Еси пользователь решил оставить комментарий
@dp.message(TradeForm.comment)
async def save_comment_and_trade(message: Message, state: FSMContext):
    await state.update_data(comment=message.text.strip())
    await finalize_trade(message, state)


@dp.message(F.text == "📂 Открытые сделки")
async def open_trades_menu(message: Message):
    trades = await db.get_open_trades(message.from_user.id)

    if not trades:
        await message.answer("😎 У вас нет открытых сделок.")
        return

    # Формируем инлайн-кнопки
    buttons = []
    for trade_id, coin, usdt_amount in trades:
        text = f"{coin} - {usdt_amount:.2f} USDT"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"openinfo:{trade_id}")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(f"📂 У вас {len(trades)} открытых сделок:", reply_markup=keyboard)


# Кнопка просмотра открытые сделки
@dp.message(F.text == "📂 Открытые сделки")
async def open_trades_menu(message: Message):
    trades = await db.get_open_trades(message.from_user.id)

    if not trades:
        await message.answer("😎 У вас нет открытых сделок.")
        return

    # Формируем инлайн-кнопки
    buttons = []
    for trade_id, coin, usdt_amount in trades:
        text = f"{coin} - {usdt_amount:.2f} USDT"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"openinfo:{trade_id}")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(f"📂 У вас {len(trades)} открытых сделок:", reply_markup=keyboard)


@dp.callback_query(F.data.startswith("openinfo:"))
async def show_trade_info(callback: CallbackQuery):
    trade_id = int(callback.data.split(":")[1])
    await render_trade_info_message(callback, trade_id)

# Закрытие открытой сделки
async def show_close_draft(message_or_callback, state: FSMContext):
    data = await state.get_data()
    trade = data["selected_trade"]

    close_price = data.get("close_price") or "-"
    close_fee = data.get("close_fee") or "-"

    text = (
        f"🔒 Закрытие сделки\n\n"
        f"🪙 Монета: {trade['coin']}\n"
        f"📥 Цена входа: {trade['entry']}\n"
        f"📅 Дата входа: {trade['created_at'].split()[0]}\n\n"
        f"📉 Цена закрытия: {close_price}\n"
        f"📊 Комиссия выхода: {close_fee}%\n"
    )

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📉 Ввести цену закрытия", callback_data="set_close_price")],
        [InlineKeyboardButton(text="📊 Ввести комиссию", callback_data="set_close_fee")],
        [InlineKeyboardButton(text="✅ Подтвердить закрытие", callback_data="confirm_close_trade")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_to_info:{trade['id']}")]
    ])

    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=markup)
    else:
        await message_or_callback.answer(text, reply_markup=markup)

# Обработка кнопки назад в закрытии открытой сделки
@dp.callback_query(F.data.startswith("back_to_info:"))
async def back_to_trade_info(callback: CallbackQuery, state: FSMContext):
    trade_id = int(callback.data.split(":")[1])
    await callback.answer()  # Закрыть "loading..."
    await render_trade_info_message(callback, trade_id)

@dp.callback_query(F.data.startswith("start_close:"))
async def start_close_trade(callback: CallbackQuery, state: FSMContext):
    trade_id = int(callback.data.split(":")[1])

    # Получаем ВСЕ необходимые поля для дальнейших расчетов
    async with aiosqlite.connect("trades.db") as db_conn:
        cursor = await db_conn.execute('''
            SELECT id, coin, entry, usdt_amount, fee_entry_percent, created_at
            FROM trades
            WHERE id = ?
        ''', (trade_id,))
        row = await cursor.fetchone()

    if not row:
        await callback.message.answer("❌ Сделка не найдена.")
        return

    # Разбиваем значения по переменным
    trade_id, coin, entry, usdt_amount, fee_entry_percent, created_at = row

    # Сохраняем в FSMContext
    await state.set_state(CloseDealForm.closing_trade)
    await state.update_data({
        "selected_trade": {
            "id": trade_id,
            "coin": coin,
            "entry": entry,
            "created_at": created_at
        },
        "usdt_amount": usdt_amount,
        "fee_entry_percent": fee_entry_percent
    })

    # Показываем интерфейс черновика закрытия
    await show_close_draft(callback, state)

# Обработка кнопки ввода цены закрытия
@dp.callback_query(F.data == "set_close_price")
async def prompt_close_price(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_close_draft")]
    ])
    await state.set_state(CloseDealForm.entering_close_price)
    await callback.message.edit_text("📉 Введи цену закрытия ($):", reply_markup=keyboard)


# Обработка пользовательского ввода цены закрытия
@dp.message(CloseDealForm.entering_close_price)
async def receive_close_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip())
        await state.update_data(close_price=price)
        await state.set_state(CloseDealForm.closing_trade)
        await show_close_draft(message, state)
    except ValueError:
        await message.answer("❌ Введи корректное число.")


# Обработка кнопки выбора комиссии
@dp.callback_query(F.data == "set_close_fee")
async def prompt_close_fee(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="0.1%", callback_data="close_fee:0.1"),
            InlineKeyboardButton(text="0.18%", callback_data="close_fee:0.18")
        ],
        [InlineKeyboardButton(text="✍️ Ввести вручную", callback_data="close_fee:custom")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_close_draft")]
    ])
    await callback.message.edit_text("📊 Выбери комиссию на закрытие:", reply_markup=keyboard)


# Обработка выбора фиксированной комиссии
@dp.callback_query(F.data.startswith("close_fee:"))
async def handle_close_fee(callback: CallbackQuery, state: FSMContext):
    value = callback.data.split(":")[1]

    if value == "custom":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_close_draft")]
        ])
        await state.set_state(CloseDealForm.entering_close_fee)
        await callback.message.edit_text("✍️ Введи комиссию вручную (%):", reply_markup=keyboard)
    else:
        try:
            await state.update_data(close_fee=float(value))
            await state.set_state(CloseDealForm.closing_trade)
            await show_close_draft(callback, state)
        except ValueError:
            await callback.message.answer("❌ Ошибка: некорректное значение комиссии.")

# Обработка кнопки ручного ввода комиссии
@dp.callback_query(F.data == "close_fee:custom")
async def handle_custom_fee(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_close_draft")]
    ])
    await state.set_state(CloseDealForm.entering_close_fee)
    await callback.message.edit_text("✍️ Введи комиссию вручную (%):", reply_markup=keyboard)


# Обработка пользовательского ввода комиссии вручную
@dp.message(CloseDealForm.entering_close_fee)
async def receive_close_fee(message: Message, state: FSMContext):
    try:
        fee = float(message.text.strip())
        await state.update_data(close_fee=fee)
        await state.set_state(CloseDealForm.closing_trade)
        await show_close_draft(message, state)
    except ValueError:
        await message.answer("❌ Введи корректное число.")

# Обработка кнопка назад в show_trade_info
@dp.callback_query(F.data == "back_to_open_trades")
async def back_to_open_trades(callback: CallbackQuery):
    trades = await db.get_open_trades(callback.from_user.id)

    if not trades:
        await callback.message.edit_text("😎 У вас нет открытых сделок.")
        return

    buttons = []
    for trade_id, coin, usdt_amount in trades:
        text = f"{coin} - {usdt_amount:.2f} USDT"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"openinfo:{trade_id}")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(f"📂 У вас {len(trades)} открытых сделок:", reply_markup=keyboard)

# Обработка кнопок "назад" при вводе цены и комиссии закрытия
@dp.callback_query(F.data == "back_to_close_draft")
async def back_to_close_draft(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    if "selected_trade" not in data:
        await callback.message.edit_text("⚠️ Не удалось вернуться: информация о сделке не найдена.")
        return

    await state.set_state(CloseDealForm.closing_trade)
    await show_close_draft(callback, state)

# Подтверждение закрытия сделки (предупреждение + кнопка подтверждения)
@dp.callback_query(F.data == "confirm_close_trade")
async def confirm_close_warning(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    trade = data.get("selected_trade")

    if not trade:
        await callback.message.edit_text("❌ Ошибка: сделка не выбрана.")
        return

    close_price = data.get("close_price")
    close_fee = data.get("close_fee")

    # ЕСЛИ не указана цена или комиссия — предупреждаем и добавляем кнопку назад
    if close_price is None or close_fee is None:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_close_draft")]
        ])
        await callback.message.edit_text(
            "⚠️ Укажи цену закрытия и комиссию перед подтверждением.",
            reply_markup=keyboard
        )
        return

    # ЕСЛИ всё заполнено — выводим предупреждение и кнопку подтвердить
    text = (
        f"⚠️ Ты собираешься закрыть сделку по монете {trade['coin']}\n\n"
        f"📉 Цена закрытия: {close_price}\n"
        f"📊 Комиссия: {close_fee}%\n\n"
        f"❗ После закрытия сделки изменения будут невозможны.\n\n"
        f"Подтвердить закрытие?"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="final_close_trade")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_close_draft")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard)

# Финальное закрытие сделки
@dp.callback_query(F.data == "final_close_trade")
async def finalize_close_trade(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    trade = data["selected_trade"]

    entry = float(trade["entry"])
    amount = float(data["usdt_amount"])
    entry_fee = float(data["fee_entry_percent"])
    close_price = float(data["close_price"])
    close_fee = float(data["close_fee"])

    # Кол-во купленных монет с учетом комиссии на вход
    coins = (amount / entry) * (1 - entry_fee / 100)

    # Финальная сумма в USDT
    final_usdt = (coins * close_price) * (1 - close_fee / 100)

    # Расчеты
    profit = final_usdt - amount
    pnl = (profit / amount) * 100

    # Обновляем данные
    data.update({
        "status": "закрыта",
        "close_price": close_price,
        "fee_exit_percent": close_fee,
        "profit_usdt": round(profit, 2),
        "pnl": round(pnl, 2),
        "closed_at": "CURRENT_TIMESTAMP"
    })

    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    await db.insert_trade(user_id, chat_id, data)
    await state.clear()

    text = (
        f"✅ Сделка закрыта\n\n"
        f"🪙 Монета: {trade['coin']}\n"
        f"📥 Вход: ${entry}\n"
        f"📉 Закрытие: ${close_price}\n"
        f"💵 Сумма: {amount} USDT\n"
        f"📈 PnL: {data['pnl']}%\n"
        f"💰 Профит: {data['profit_usdt']} USDT"
    )
    await callback.message.edit_text(text)





# 




# 




# 



# Точка входа в приложение (запуск бота)
async def main():
    await db.init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
