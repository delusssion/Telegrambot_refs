from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    InputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from .config import Settings
from .db import Database


class SubmissionForm(StatesGroup):
    bank = State()
    comment = State()
    evidence = State()

class SupportForm(StatesGroup):
    question = State()

class ReportForm(StatesGroup):
    report = State()


def _is_admin(user_id: int, settings: Settings) -> bool:
    return user_id in (settings.admin_ids or [])


def setup_bot(settings: Settings, database: Database) -> Dispatcher:
    dp = Dispatcher()

    start_text = (
        "💰 Заработай до нескольких тысяч рублей на реферальной системе известных банков!\n\n"
        "💸Ты — оформляешь карту и получаешь бонус. Мы — получаем бонус за то, что привели тебя и сразу делимся с тобой.\n\n"
        " • ✅ Карты продавать не надо\n"
        " • ✅ Мы не берем никакие данные\n"
        " • ✅ Выплаты сразу — в тот же день\n"
        " • ✅ Без вложений\n"
        " • ✅ 300+ успешных выплат\n"
        " • ✅ Работаем уже полгода\n\n"
        "🔻 Нажми «➡Далее» и забери своё первое задание прямо сейчас."
    )

    next_button_text = "➡ Далее"
    start_earn_button = "💰 Приступить к заработку"
    ask_button = "❓ Задать вопрос"
    profile_button = "👤 Профиль"
    tasks_button = "📜 Задания"
    report_card_button = "✔️ Получил карту"
    referral_button = "🤝 Реферальная программа"
    support_button = "🆘 Тех. поддержка"
    reviews_button = "⭐ Отзывы"
    age_14_button = "🧒 14+"
    age_18_button = "🔞 18+"
    other_tasks_button = "➕ Остальные задания"
    emoji_button = "😊"
    alpha_display = "💳 Карта Альфа Банк ~~2000 Р~~ 2500 Р"
    tbank_display = "💳 Карта Т-Банк 3ООО Р"
    mts_display = "💳 Карта МТС 3ОО Р"

    bank_14_buttons = [
        tbank_display,
        alpha_display,
    ]
    bank_18_buttons = [
        tbank_display,
        mts_display,
        alpha_display,
    ]
    next_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=next_button_text, callback_data="next_submit")]]
    )
    actions_inline_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=start_earn_button, callback_data="start_earn")],
            [InlineKeyboardButton(text=ask_button, callback_data="ask")],
        ]
    )

    start_report_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить получение", callback_data="start_report_message")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_report")],
        ]
    )
    start_support_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✉️ Написать сообщение", callback_data="start_support")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_support")],
        ]
    )
    after_send_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🏠 В главное меню", callback_data="go_main"),
                InlineKeyboardButton(text="📜 К заданиям", callback_data="menu_tasks"),
            ]
        ]
    )
    cancel_support_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_support")]
        ]
    )
    cancel_report_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_report")]
        ]
    )

    def main_menu_inline() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=profile_button, callback_data="menu_profile"),
                    InlineKeyboardButton(text=tasks_button, callback_data="menu_tasks"),
                ],
                [InlineKeyboardButton(text=report_card_button, callback_data="menu_report_card")],
                [
                    InlineKeyboardButton(text=referral_button, callback_data="menu_referral"),
                    InlineKeyboardButton(text=support_button, callback_data="menu_support"),
                ],
                [InlineKeyboardButton(text=reviews_button, callback_data="menu_reviews")],
            ]
        )

    main_menu_reply = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=profile_button), KeyboardButton(text=tasks_button)],
            [KeyboardButton(text=report_card_button)],
            [KeyboardButton(text=referral_button), KeyboardButton(text=support_button)],
            [KeyboardButton(text=reviews_button)],
        ],
        resize_keyboard=True,
    )

    async def clear_state_keep_age(state: FSMContext) -> None:
        data = await state.get_data()
        age = data.get("preferred_age")
        await state.clear()
        if age:
            await state.update_data(preferred_age=age)

    def _special_banks():
        return {
            alpha_display: {"name": "Альфа-Банк", "link": "https://alfa.me/aw4D3D", "custom": "alpha"},
            tbank_display: {"name": "Т-Банк", "link": "https://tbank.ru/baf/1BgRcSNOGAp", "custom": "tbank"},
        }

    async def _clear_menu_message(state: FSMContext, msg_obj) -> None:
        data = await state.get_data()
        last_id = data.get("menu_msg_id")
        chat_id = msg_obj.chat.id
        if last_id:
            try:
                await msg_obj.bot.delete_message(chat_id=chat_id, message_id=last_id)
            except Exception:
                pass

    async def _send_menu(obj, state: FSMContext, text: str, reply_markup=None):
        msg_obj = obj.message if isinstance(obj, CallbackQuery) else obj
        await _clear_menu_message(state, msg_obj)
        sent = await msg_obj.answer(text, reply_markup=reply_markup)
        await state.update_data(menu_msg_id=sent.message_id)

    def _instruction_text(bank_name: str, link: str, custom: Optional[str] = None) -> str:
        if custom == "tbank":
            return (
                f"▌ Шаг 1: Переход по <a href=\"{link}\">реферальной ссылке</a>\n\n"
                f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
                f"▌ Шаг 2: Регистрация и заполнение анкеты\n\n"
                f"Введите ваши личные данные: ФИО, номер телефона, e-mail.\n"
                f"Заполните короткую анкету для выпуска карты.\n"
                f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
                f"▌ Шаг 3: Ожидание одобрения\n\n"
                f"Банк проверит заявку. Обычно решение приходит быстро — уведомление появится в приложении или по SMS.\n"
                f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
                f"▌ Шаг 4: Выбор способа доставки карты\n\n"
                f"Т-Банк предложит удобный способ получения карты:\n"
                f"Курьерская доставка на дом или в офис.\n"
                f"Самовывоз в одном из пунктов выдачи.\n"
                f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
                f"▌ Шаг 5: Активация карты\n\n"
                f"После получения карты активируйте её через приложение Т-Банка. Это откроет доступ ко всем функциям и бонусам.\n"
                f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
                f"▌ Шаг 6: Выполнение ТЗ от банка (для получения бонуса)\n\n"
                f"Совершить покупку по карте хоть на 1 рубль\n\n"
                f"Важно: операция должна быть офлайн или обычной онлайн-покупкой — переводы и снятие наличных не учитываются."
            )

        extra = ""
        return (
            f"▌ Инструкция по оформлению дебетовой карты {bank_name} по реферальной ссылке\n\n"
            f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
            f"▌ Шаг 1: Переход по <a href=\"{link}\">реферальной ссылке</a>\n\n"
            f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
            f"▌ Шаг 2: Регистрация и заполнение анкеты\n\n"
            f"- Регистрация: Укажите ваши личные данные (ФИО, номер телефона, электронную почту).\n"
            f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
            f"▌ Шаг 3: Ожидание одобрения\n\n"
            f"Банк проверит вашу заявку. Обычно решение принимается достаточно быстро. "
            f"После подтверждения вам поступит уведомление о статусе вашей заявки.\n\n"
            f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
            f"▌ Шаг 4: Выбор способа доставки карты\n\n"
            f"- Доставка курьером домой или в офис.\n"
            f"- Самовывоз в ближайшем отделении банка.\n\n"
            f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
            f"▌ Шаг 5: Активация карты\n\n"
            f"Получив карту, активируйте её через мобильное приложение или банкомат. "
            f"Это позволит начать пользоваться преимуществами карты.\n\n"
            f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
            f"▌ Шаг 6: Выполнение ТЗ от банка\n\n"
            f"- Совершите любую покупку от 1 рубля\n\n"
            f"ВАЖНО❗️: Покупка, сделанная онлайн, не будет засчитана."
        )

    async def _show_banks_by_age(state: FSMContext, obj) -> None:
        data = await state.get_data()
        age_label = data.get("preferred_age")
        if age_label:
            await _store_age_and_show(age_label, obj, state)
        else:
            await _send_menu(obj, state, "Выберите ваш возраст:", reply_markup=age_inline_keyboard())
            if isinstance(obj, CallbackQuery):
                await obj.answer()

    async def _send_menu(obj, state: FSMContext, text: str, reply_markup=None):
        # удаляем предыдущее меню, если было
        data = await state.get_data()
        last_id = data.get("menu_msg_id")
        msg_obj = obj.message if isinstance(obj, CallbackQuery) else obj
        chat_id = msg_obj.chat.id
        if last_id:
            try:
                await msg_obj.bot.delete_message(chat_id=chat_id, message_id=last_id)
            except Exception:
                pass
        sent = await msg_obj.answer(text, reply_markup=reply_markup)
        await state.update_data(menu_msg_id=sent.message_id)

    async def show_tasks_or_main(obj, state: FSMContext) -> None:
        data = await state.get_data()
        preferred_age = data.get("preferred_age")
        if preferred_age:
            prompt = f"Доступные задания для {preferred_age}:"
            kb = banks_inline_keyboard(preferred_age)
            await _send_menu(obj, state, prompt, reply_markup=kb)
            if isinstance(obj, CallbackQuery):
                await obj.answer()
        else:
            await _send_menu(obj, state, "Главное меню:", reply_markup=main_menu_reply)
            if isinstance(obj, CallbackQuery):
                await obj.answer()

    def age_inline_keyboard() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=age_14_button, callback_data="age_14"),
                    InlineKeyboardButton(text=age_18_button, callback_data="age_18"),
                ],
                [InlineKeyboardButton(text=ask_button, callback_data="ask")],
            ]
        )

    def banks_inline_keyboard(age_label: str) -> InlineKeyboardMarkup:
        buttons = bank_14_buttons if age_label == "14+" else bank_18_buttons
        other_age = "18+" if age_label == "14+" else "14+"
        rows = [[InlineKeyboardButton(text=btn, callback_data=f"bank::{btn}")] for btn in buttons]
        rows.append([InlineKeyboardButton(text=emoji_button, callback_data="emoji")])
        rows.append([InlineKeyboardButton(text=other_tasks_button, callback_data="other_tasks")])
        rows.append([InlineKeyboardButton(text=ask_button, callback_data="ask")])
        rows.append([InlineKeyboardButton(text=f"🔄 Показать задания {other_age}", callback_data=f"switch_age::{other_age}")])
        return InlineKeyboardMarkup(inline_keyboard=rows)

    def all_banks_inline_keyboard() -> InlineKeyboardMarkup:
        seen = set()
        rows = []
        for btn in bank_14_buttons + bank_18_buttons:
            if btn in seen:
                continue
            seen.add(btn)
            rows.append([InlineKeyboardButton(text=btn, callback_data=f"bank::{btn}")])
        rows.append([InlineKeyboardButton(text=ask_button, callback_data="ask")])
        return InlineKeyboardMarkup(inline_keyboard=rows)

    async def send_start(message: Message, state: FSMContext):
        await _clear_menu_message(state, message)
        photo_sent = False
        if settings.start_photo_file_id:
            sent = await message.answer_photo(photo=settings.start_photo_file_id, caption=start_text, reply_markup=next_keyboard)
            photo_sent = True
            await state.update_data(menu_msg_id=sent.message_id)
        elif settings.start_photo_path:
            try:
                sent = await message.answer_photo(photo=InputFile(settings.start_photo_path), caption=start_text, reply_markup=next_keyboard)
                photo_sent = True
                await state.update_data(menu_msg_id=sent.message_id)
            except FileNotFoundError:
                photo_sent = False
        if not photo_sent:
            await _send_menu(message, state, start_text, reply_markup=next_keyboard)

    @dp.message(CommandStart())
    async def handle_start(message: Message, state: FSMContext) -> None:
        await database.add_action(
            action="start",
            user_id=message.from_user.id if message.from_user else None,
            username=message.from_user.username if message.from_user else None,
            details={},
        )
        await send_start(message, state)

    @dp.callback_query(F.data == "next_submit")
    async def handle_next(call, state: FSMContext):
        await clear_state_keep_age(state)
        await call.message.answer(
            "Выберите ваш возраст:",
            reply_markup=age_inline_keyboard(),
        )
        await call.answer()

    @dp.message(F.text == next_button_text)
    async def handle_next_text(message: Message, state: FSMContext) -> None:
        step_text = (
            "🧱 Как ты зарабатываешь деньги — шаг за шагом:\n\n"
            "📌 1. Банк хочет клиента — ты им становишься\n"
            " Ты оформляешь бесплатный продукт: карту, счёт или бонусную услугу через нашу ссылку.\n\n"
            "📌 2. Мы получаем вознаграждение\n"
            " Банк платит нам за твою регистрацию — это маркетинговый бюджет\n\n"
            "📌 3. Мы платим тебе\n"
            " Сразу в день выполнения. Без задержек. Без лишних вопросов."
        )
        why_text = (
            "💼 Почему это работает?\n\n"
            "Банкам всё равно, будешь ли ты пользоваться их картой или нет.\n"
            " Им важно одно — чтобы ты просто оформил карту.\n"
            " За это они платят нам.\n"
            " 👌А мы делимся деньгами с тобой."
        )
        await message.answer(step_text)
        await message.answer(why_text)
        await message.answer(
            "👉Сделай шаг — и заработай.",
            reply_markup=actions_inline_keyboard,
        )
        await clear_state_keep_age(state)

    async def _show_tasks(message_obj, state: FSMContext) -> None:
        data = await state.get_data()
        preferred_age = data.get("preferred_age")
        if preferred_age:
            prompt = f"Доступные задания для {preferred_age}:"
            kb = banks_inline_keyboard(preferred_age)
            await _send_menu(message_obj, state, prompt, reply_markup=kb)
            if isinstance(message_obj, CallbackQuery):
                await message_obj.answer()
        else:
            await _send_menu(message_obj, state, "Выберите ваш возраст:", reply_markup=age_inline_keyboard())
            if isinstance(message_obj, CallbackQuery):
                await message_obj.answer()

    @dp.message(F.text == start_earn_button)
    async def handle_start_earn(message: Message, state: FSMContext) -> None:
        await database.add_action(
            action="start_earn",
            user_id=message.from_user.id if message.from_user else None,
            username=message.from_user.username if message.from_user else None,
            details={},
        )
        await state.set_state(None)
        await _show_tasks(message, state)

    @dp.callback_query(F.data == "start_earn")
    async def handle_start_earn_cb(call: CallbackQuery, state: FSMContext) -> None:
        await database.add_action(
            action="start_earn",
            user_id=call.from_user.id if call.from_user else None,
            username=call.from_user.username if call.from_user else None,
            details={},
        )
        await state.set_state(None)
        await _show_tasks(call, state)

    def _get_user_obj(obj):
        if isinstance(obj, CallbackQuery):
            return obj.from_user
        if isinstance(obj, Message):
            return obj.from_user
        return None

    async def _store_age_and_show(age_label: str, message_obj, state: FSMContext) -> None:
        data = await state.get_data()
        data["preferred_age"] = age_label
        await state.set_state(None)
        await state.set_data(data)
        u = _get_user_obj(message_obj)
        await database.add_action(
            action="age_selected",
            user_id=u.id if u else None,
            username=u.username if u else None,
            details={"age": age_label},
        )
        kb = banks_inline_keyboard(age_label)
        prompt = "Доступные задания для 14+:" if age_label == "14+" else "Доступные задания для 18+:"
        await _send_menu(message_obj, state, prompt, reply_markup=kb)
        if isinstance(message_obj, CallbackQuery):
            await message_obj.answer()

    @dp.message(F.text == age_14_button)
    async def handle_age_14(message: Message, state: FSMContext) -> None:
        await _store_age_and_show("14+", message, state)

    @dp.message(F.text == age_18_button)
    async def handle_age_18(message: Message, state: FSMContext) -> None:
        await _store_age_and_show("18+", message, state)

    @dp.message(F.text == ask_button)
    async def handle_question(message: Message, state: FSMContext) -> None:
        await database.add_action(
            action="ask_question_start",
            user_id=message.from_user.id if message.from_user else None,
            username=message.from_user.username if message.from_user else None,
            details={},
        )
        await state.set_state(SupportForm.question)
        await message.answer(
            "Напиши свой вопрос или отправь файл/скрин. После отправки вопрос будет сохранен для админов.",
            reply_markup=cancel_support_keyboard,
        )

    async def _handle_bank_selection(obj, state: FSMContext, bank_name: str) -> None:
        special = _special_banks()
        if bank_name in special:
            info = special[bank_name]
            text = (
                f"{bank_name}\n\n"
                f"Нажми «Начать выполнение», чтобы получить инструкцию. "
                f"Если передумал — «Назад» вернет к списку карт."
            )
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🚀 Начать выполнение", callback_data=f"start_task::{bank_name}")],
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_banks")],
                ]
            )
            await _send_menu(obj, state, text, reply_markup=kb)
            return
        if bank_name == mts_display:
            text = "Скоро добавим инструкцию для МТС Банка..."
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_banks")],
                ]
            )
            await _send_menu(obj, state, text, reply_markup=kb)
            return

        await state.update_data(bank=bank_name)
        await state.set_state(SubmissionForm.comment)
        u = _get_user_obj(obj)
        await database.add_action(
            action="bank_selected",
            user_id=u.id if u else None,
            username=u.username if u else None,
            details={"bank": bank_name},
        )
        await _send_menu(obj, state, "Добавь комментарий или условия (можно пропустить, отправив '-'):")

    @dp.message(F.text.in_(bank_14_buttons + bank_18_buttons))
    async def handle_bank_shortcut(message: Message, state: FSMContext) -> None:
        bank_name = message.text.strip()
        await _handle_bank_selection(message, state, bank_name)

    @dp.message(F.text == emoji_button)
    async def handle_emoji(message: Message) -> None:
        await database.add_action(
            action="emoji_clicked",
            user_id=message.from_user.id if message.from_user else None,
            username=message.from_user.username if message.from_user else None,
            details={},
        )
        await message.answer("Выбери задание или задай вопрос.", reply_markup=age_inline_keyboard())

    @dp.message(F.text == other_tasks_button)
    async def handle_other_tasks(message: Message) -> None:
        await message.answer("Скоро добавим новые задания. Пока выбери из доступных или задай вопрос.")

    @dp.message(F.text == tasks_button)
    async def handle_tasks_menu(message: Message, state: FSMContext) -> None:
        await _show_tasks(message, state)

    @dp.callback_query(F.data == "age_14")
    async def handle_age_14_cb(call: CallbackQuery, state: FSMContext) -> None:
        await _store_age_and_show("14+", call, state)

    @dp.callback_query(F.data == "age_18")
    async def handle_age_18_cb(call: CallbackQuery, state: FSMContext) -> None:
        await _store_age_and_show("18+", call, state)

    @dp.callback_query(F.data.startswith("bank::"))
    async def handle_bank_cb(call: CallbackQuery, state: FSMContext) -> None:
        bank_name = call.data.split("::", 1)[1]
        await _handle_bank_selection(call, state, bank_name)
        await call.answer()

    @dp.callback_query(F.data.startswith("start_task::"))
    async def handle_start_task(call: CallbackQuery, state: FSMContext) -> None:
        bank_name = call.data.split("::", 1)[1]
        info = _special_banks().get(bank_name)
        if not info:
            await call.answer()
            return
        text = _instruction_text(info["name"], info["link"], info.get("custom"))
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Карта заказана", callback_data="card_ordered")],
                [InlineKeyboardButton(text="❌ Отказаться от выполнения", callback_data="refuse_task")],
            ]
        )
        await _send_menu(call, state, text, reply_markup=kb)
        await call.answer()

    @dp.callback_query(F.data == "refuse_task")
    async def handle_refuse_task(call: CallbackQuery, state: FSMContext) -> None:
        await _show_banks_by_age(state, call)
        await call.answer()

    @dp.callback_query(F.data == "card_ordered")
    async def handle_card_ordered(call: CallbackQuery, state: FSMContext) -> None:
        await _send_menu(
            call,
            state,
            "✅После получения карты, нажмите кнопку \"Получил карту\" в главном меню, и мы с вами свяжемся!",
            reply_markup=main_menu_reply,
        )
        await call.answer()

    @dp.callback_query(F.data.startswith("switch_age::"))
    async def handle_switch_age(call: CallbackQuery, state: FSMContext) -> None:
        _, target_age = call.data.split("::", 1)
        await _store_age_and_show(target_age, call, state)

    @dp.callback_query(F.data == "emoji")
    async def handle_emoji_cb(call: CallbackQuery) -> None:
        await database.add_action(
            action="emoji_clicked",
            user_id=call.from_user.id if call.from_user else None,
            username=call.from_user.username if call.from_user else None,
            details={},
        )
        await call.message.answer("Выбери возраст и задание.", reply_markup=age_inline_keyboard())
        await call.answer()

    @dp.callback_query(F.data == "other_tasks")
    async def handle_other_tasks_cb(call: CallbackQuery) -> None:
        await call.message.answer("Скоро добавим новые задания. Пока выбери из доступных или задай вопрос.")
        await call.answer()

    @dp.callback_query(F.data == "ask")
    async def handle_ask_cb(call: CallbackQuery, state: FSMContext) -> None:
        await database.add_action(
            action="ask_question_start",
            user_id=call.from_user.id if call.from_user else None,
            username=call.from_user.username if call.from_user else None,
            details={},
        )
        await state.set_state(SupportForm.question)
        await _send_menu(call, state, "Напиши свой вопрос или отправь файл/скрин. После отправки вопрос будет сохранен для админов.", reply_markup=cancel_support_keyboard)
        await call.answer()

    @dp.callback_query(F.data == "start_support")
    async def handle_start_support(call: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(SupportForm.question)
        await _send_menu(call, state, "Напиши свой вопрос или отправь файл/скрин. Можно отменить кнопкой ниже.", reply_markup=cancel_support_keyboard)
        await call.answer()

    @dp.callback_query(F.data == "start_report_message")
    async def handle_start_report_message(call: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(ReportForm.report)
        await _send_menu(
            call,
            state,
            "👉Если УЖЕ получил карту\n"
            "👉Нажмите на кнопку ниже и отправьте\n"
            "_________________________________\n"
            "1️⃣Скриншот заказа карты с сайта\n"
            "2️⃣Название банка карты, который заказали\n"
            "3️⃣Номер телефона на который заказали карту, для выплаты",
            reply_markup=cancel_report_keyboard,
        )
        await call.answer()

    @dp.callback_query(F.data == "go_main")
    async def handle_go_main(call: CallbackQuery, state: FSMContext) -> None:
        await clear_state_keep_age(state)
        await _send_menu(call, state, "Главное меню:", reply_markup=main_menu_reply)
        await call.answer()

    @dp.callback_query(F.data == "cancel_support")
    async def handle_cancel_support(call: CallbackQuery, state: FSMContext) -> None:
        await clear_state_keep_age(state)
        await show_tasks_or_main(call, state)

    @dp.callback_query(F.data == "cancel_report")
    async def handle_cancel_report(call: CallbackQuery, state: FSMContext) -> None:
        await clear_state_keep_age(state)
        await show_tasks_or_main(call, state)

    @dp.callback_query(F.data == "back_to_banks")
    async def handle_back_to_banks(call: CallbackQuery, state: FSMContext) -> None:
        await _show_banks_by_age(state, call)
        await call.answer()

    def _profile_text(obj) -> str:
        u = obj.from_user if isinstance(obj, CallbackQuery) else obj.from_user
        lines = ["Профиль"]
        if u:
            lines.append(f"ID: {u.id}")
            if u.username:
                lines.append(f"Username: @{u.username}")
        else:
            lines.append("Нет данных пользователя")
        return "\n".join(lines)

    @dp.callback_query(F.data == "menu_profile")
    async def handle_profile_cb(call: CallbackQuery) -> None:
        back_kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="go_main")]]
        )
        await call.message.answer(_profile_text(call), reply_markup=back_kb)
        await call.answer()

    @dp.callback_query(F.data == "menu_referral")
    async def handle_referral_cb(call: CallbackQuery) -> None:
        await database.add_action(
            action="referral_open",
            user_id=call.from_user.id if call.from_user else None,
            username=call.from_user.username if call.from_user else None,
            details={},
        )
        back_kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="go_main")]]
        )
        await call.message.answer(
            "Реферальная программа: приглашай друзей, они оформляют задания — получаешь % от их вознаграждения. "
            "Скоро добавим персональные ссылки и учет начислений.",
            reply_markup=back_kb,
        )
        await call.answer()

    @dp.message(F.text == profile_button)
    async def handle_profile_msg(message: Message) -> None:
        back_kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="go_main")]]
        )
        await message.answer(_profile_text(message), reply_markup=back_kb)

    @dp.message(F.text == referral_button)
    async def handle_referral_msg(message: Message) -> None:
        await database.add_action(
            action="referral_open",
            user_id=message.from_user.id if message.from_user else None,
            username=message.from_user.username if message.from_user else None,
            details={},
        )
        back_kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="go_main")]]
        )
        await message.answer(
            "Реферальная программа: приглашай друзей, они оформляют задания — получаешь % от их вознаграждения. "
            "Скоро добавим персональные ссылки и учет начислений.",
            reply_markup=back_kb,
        )

    @dp.message(F.text == support_button)
    async def handle_support_msg(message: Message, state: FSMContext) -> None:
        await database.add_action(
            action="support_open",
            user_id=message.from_user.id if message.from_user else None,
            username=message.from_user.username if message.from_user else None,
            details={},
        )
        await clear_state_keep_age(state)
        await message.answer(
            "Техподдержка. Нажми «✉️ Написать сообщение», затем отправь текст или файл. Можно отменить.",
            reply_markup=start_support_keyboard,
        )

    @dp.message(F.text == report_card_button)
    async def handle_report_card_msg(message: Message, state: FSMContext) -> None:
        await database.add_action(
            action="report_card",
            user_id=message.from_user.id if message.from_user else None,
            username=message.from_user.username if message.from_user else None,
            details={},
        )
        await clear_state_keep_age(state)
        await message.answer(
            "👉Если УЖЕ получил карту\n"
            "👉Нажмите на кнопку ниже и отправьте\n"
            "_________________________________\n"
            "1️⃣Скриншот заказа карты с сайта\n"
            "2️⃣Название банка карты, который заказали\n"
            "3️⃣Номер телефона на который заказали карту, для выплаты",
            reply_markup=start_report_keyboard,
        )

    @dp.message(F.text == tasks_button)
    async def handle_tasks_msg(message: Message, state: FSMContext) -> None:
        await _show_tasks(message, state)

    @dp.message(F.text == reviews_button)
    async def handle_reviews_msg(message: Message) -> None:
        back_kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="go_main")]]
        )
        await message.answer(
            "⭐ Отзывы: скоро добавим витрину отзывов. Пока можешь написать вопрос в поддержку.",
            reply_markup=back_kb,
        )

    @dp.callback_query(F.data == "menu_support")
    async def handle_support_cb(call: CallbackQuery, state: FSMContext) -> None:
        await database.add_action(
            action="support_open",
            user_id=call.from_user.id if call.from_user else None,
            username=call.from_user.username if call.from_user else None,
            details={},
        )
        await clear_state_keep_age(state)
        await call.message.answer(
            "Техподдержка. Нажми «✉️ Написать сообщение», затем отправь текст или файл.",
            reply_markup=start_support_keyboard,
        )
        await call.answer()

    @dp.callback_query(F.data == "menu_report_card")
    async def handle_report_card_cb(call: CallbackQuery, state: FSMContext) -> None:
        await database.add_action(
            action="report_card",
            user_id=call.from_user.id if call.from_user else None,
            username=call.from_user.username if call.from_user else None,
            details={},
        )
        await clear_state_keep_age(state)
        await call.message.answer(
            "👉Если УЖЕ получил карту\n"
            "👉Нажмите на кнопку ниже и отправьте\n"
            "_________________________________\n"
            "1️⃣Скриншот заказа карты с сайта\n"
            "2️⃣Название банка карты, который заказали\n"
            "3️⃣Номер телефона на который заказали карту, для выплаты",
            reply_markup=start_report_keyboard,
        )
        await call.answer()

    @dp.callback_query(F.data == "menu_tasks")
    async def handle_tasks_cb(call: CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()
        preferred_age = data.get("preferred_age")
        if preferred_age:
            await _send_menu(call, state, f"Доступные задания для {preferred_age}:", reply_markup=banks_inline_keyboard(preferred_age))
        else:
            await _send_menu(call, state, "Выберите ваш возраст:", reply_markup=age_inline_keyboard())
        await call.answer()

    @dp.callback_query(F.data == "menu_reviews")
    async def handle_reviews_cb(call: CallbackQuery) -> None:
        back_kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="go_main")]]
        )
        await call.message.answer(
            "⭐ Отзывы: скоро добавим витрину отзывов. Пока можешь написать вопрос в поддержку.",
            reply_markup=back_kb,
        )
        await call.answer()

    @dp.message(Command("help"))
    async def handle_help(message: Message) -> None:
        await message.answer(
            "Доступные команды:\n"
            "/submit — отправить новую заявку\n"
            "/my — посмотреть последние отправленные заявки\n"
            "/actions — последние события (для админов)"
        )

    @dp.message(Command("submit"))
    async def handle_submit(message: Message, state: FSMContext) -> None:
        await state.set_state(SubmissionForm.bank)
        await message.answer("Укажи название банка, по которому хочешь оставить реферальную заявку:")

    @dp.message(SubmissionForm.bank)
    async def handle_bank(message: Message, state: FSMContext) -> None:
        await state.update_data(bank=message.text.strip())
        await state.set_state(SubmissionForm.comment)
        await message.answer("Добавь комментарий или условия (можно пропустить, отправив '-'):")

    @dp.message(SubmissionForm.comment)
    async def handle_comment(message: Message, state: FSMContext) -> None:
        comment = None if message.text.strip() == "-" else message.text.strip()
        await state.update_data(comment=comment)
        await state.set_state(SubmissionForm.evidence)
        await message.answer("Отправь скрин/файл подтверждения. Можно пропустить, отправив слово 'нет'.")

    @dp.message(SubmissionForm.evidence, F.document | F.photo | F.text)
    async def handle_evidence(message: Message, state: FSMContext) -> None:
        file_id: Optional[str] = None
        if message.photo:
            file_id = message.photo[-1].file_id
        elif message.document:
            file_id = message.document.file_id
        elif message.text and message.text.lower().strip() in {"нет", "no"}:
            file_id = None
        else:
            await message.answer("Нужно отправить фото/файл или написать 'нет'. Попробуй снова.")
            return

        data = await state.get_data()
        bank = data.get("bank")
        comment = data.get("comment")

        submission_id = await database.add_submission(
            user_id=message.from_user.id if message.from_user else 0,
            username=message.from_user.username if message.from_user else None,
            bank=bank,
            comment=comment,
            file_id=file_id,
        )
        await database.add_action(
            action="submission_created",
            user_id=message.from_user.id if message.from_user else None,
            username=message.from_user.username if message.from_user else None,
            details={"submission_id": submission_id, "bank": bank},
        )
        await clear_state_keep_age(state)
        await message.answer(
            "Заявка отправлена! Мы свяжемся с тобой после проверки.\n"
            "Посмотреть последние заявки: /my"
        )

    # Support/question flow
    @dp.message(SupportForm.question, F.text | F.photo | F.document)
    async def handle_support_question(message: Message, state: FSMContext) -> None:
        file_id: Optional[str] = None
        text = None
        if message.photo:
            file_id = message.photo[-1].file_id
            text = message.caption
        elif message.document:
            file_id = message.document.file_id
            text = message.caption
        else:
            text = message.text

        if not text and not file_id:
            await message.answer("Отправь текст или прикрепи файл/фото.")
            return

        await database.add_question(
            user_id=message.from_user.id if message.from_user else None,
            username=message.from_user.username if message.from_user else None,
            message=text or "",
            file_id=file_id,
        )
        await database.add_action(
            action="question_submitted",
            user_id=message.from_user.id if message.from_user else None,
            username=message.from_user.username if message.from_user else None,
            details={"file_id": file_id},
        )
        await clear_state_keep_age(state)
        await message.answer("Вопрос сохранен, админ скоро ответит.", reply_markup=after_send_keyboard)

    # Report flow
    @dp.message(F.text == report_card_button)
    async def handle_report_card_msg(message: Message, state: FSMContext) -> None:
        await database.add_action(
            action="report_card",
            user_id=message.from_user.id if message.from_user else None,
            username=message.from_user.username if message.from_user else None,
            details={},
        )
        await clear_state_keep_age(state)
        await message.answer(
            "Сообщи о получении карты. Нажми «✉️ Написать сообщение», затем отправь текст или скрин.",
            reply_markup=start_report_keyboard,
        )

    @dp.callback_query(F.data == "menu_report_card")
    async def handle_report_card_cb(call: CallbackQuery, state: FSMContext) -> None:
        await database.add_action(
            action="report_card",
            user_id=call.from_user.id if call.from_user else None,
            username=call.from_user.username if call.from_user else None,
            details={},
        )
        await clear_state_keep_age(state)
        await call.message.answer(
            "Сообщи о получении карты. Нажми «✉️ Написать сообщение», затем отправь текст или скрин.",
            reply_markup=start_report_keyboard,
        )
        await call.answer()

    @dp.message(ReportForm.report, F.text | F.photo | F.document)
    async def handle_report_payload(message: Message, state: FSMContext) -> None:
        file_id: Optional[str] = None
        text = None
        if message.photo:
            file_id = message.photo[-1].file_id
            text = message.caption
        elif message.document:
            file_id = message.document.file_id
            text = message.caption
        else:
            text = message.text

        if not text and not file_id:
            await message.answer("Отправь текст или прикрепи файл/фото.")
            return

        await database.add_report(
            user_id=message.from_user.id if message.from_user else None,
            username=message.from_user.username if message.from_user else None,
            message=text or "",
            file_id=file_id,
        )
        await database.add_action(
            action="report_submitted",
            user_id=message.from_user.id if message.from_user else None,
            username=message.from_user.username if message.from_user else None,
            details={"file_id": file_id},
        )
        await clear_state_keep_age(state)
        await message.answer("Отчет принят, спасибо! Админ проверит и свяжется.", reply_markup=after_send_keyboard)

    @dp.message(Command("my"))
    async def handle_my(message: Message) -> None:
        submissions = await database.list_submissions(limit=10)
        user_subs = [
            s for s in submissions if s["user_id"] == (message.from_user.id if message.from_user else None)
        ]
        if not user_subs:
            await message.answer("У тебя пока нет заявок. Попробуй команду /submit.")
            return

        lines = []
        for item in user_subs:
            lines.append(
                f"#{item['id']} • {item['bank']} • статус: {item['status']} • отправлено {item['created_at']}"
            )
        await message.answer("\n".join(lines))

    @dp.message(Command("actions"))
    async def handle_actions(message: Message) -> None:
        if not message.from_user or not _is_admin(message.from_user.id, settings):
            await message.answer("Недостаточно прав.")
            return
        actions = await database.list_actions(limit=15)
        if not actions:
            await message.answer("Событий пока нет.")
            return
        lines = []
        for item in actions:
            lines.append(
                f"{item['created_at']} • {item['action']} • user:{item['user_id']} • details:{item['details']}"
            )
        await message.answer("\n".join(lines))

    return dp
