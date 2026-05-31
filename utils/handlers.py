import html
import os
import tempfile

from utils import domain_service, geolocation, history, message_logger, stats, users, user_state
from utils import telegram_api


def _chat_id(message: dict) -> int:
    res = message["chat"]["id"]
    return res


def _user(message: dict) -> dict:
    u = message.get("from")
    if u is None:
        return {}
    return u


def _reply(chat_id: int, text: str) -> None:
    telegram_api.send_message(chat_id, text)
    message_logger.log_message(chat_id, text, direction="out")


def _notice(chat_id: int, text: str) -> None:
    try:
        telegram_api.send_message(chat_id, text)
    except Exception as e:
        print(f"[api] не удалось отправить уведомление: {e}")


def _h(value) -> str:
    return html.escape(str(value))


def _history_screen(chat_id: int):
    items = history.get_history(chat_id)
    watched = set(domain_service.get_user_watchlist(chat_id))
    if not items:
        text = "🕓 <b>История проверок</b>\n\nПока пусто. Проверьте какой-нибудь домен!"
        buttons = [[telegram_api.make_inline_button("← Назад", "menu")]]
        return text, buttons
    text = "🕓 <b>История проверок</b>\n\n"
    buttons = []
    for d in items:
        star = " ★" if d in watched else ""
        text += f"• <code>{_h(d)}</code>{star}\n"
        buttons.append([telegram_api.make_inline_button(f"🔁 {d}", f"check_{d}")])
    text += "\n★ — уже в отслеживании"
    buttons.append([telegram_api.make_inline_button("🗑 Очистить", "history_clear")])
    buttons.append([telegram_api.make_inline_button("← Назад", "menu")])
    return text, buttons


def _export_watchlist(chat_id: int) -> None:
    domains = domain_service.get_user_watchlist(chat_id)
    if not domains:
        _reply(chat_id, "📭 Ваш список отслеживания пуст, экспортировать нечего.")
        return
    tmp_dir = tempfile.gettempdir()
    path = os.path.join(tmp_dir, f"watchlist_{chat_id}.txt")
    with open(path, "w", encoding="utf-8") as f:
        for d in domains:
            f.write(d + "\n")
    try:
        telegram_api.send_document(chat_id, path, caption="📤 Ваш список отслеживания")
        message_logger.log_message(chat_id, "export watchlist", direction="out")
    except Exception as e:
        print(f"[export] ошибка: {e}")
        _reply(chat_id, "⚠️ Не удалось отправить файл.")
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def _safe_edit(chat_id: int, message_id: int, text: str, reply_markup: dict = None) -> None:
    try:
        telegram_api.edit_message_text(chat_id, message_id, text, reply_markup)
    except Exception as e:
        if "message is not modified" in str(e).lower():
            return
        print(f"[api] Ошибка editMessageText: {e}")


def _register_user(message: dict) -> None:
    u = _user(message)
    chat_id = _chat_id(message)
    is_new = users.save_user(
        chat_id=chat_id,
        username=u.get("username", ""),
        first_name=u.get("first_name", ""),
        last_name=u.get("last_name", ""),
    )
    if is_new:
        stats.inc("users_new")


def handle_update(update: dict) -> None:
    if "callback_query" in update:
        _handle_callback(update["callback_query"])
        return

    if "message" not in update:
        return

    message = update["message"]
    chat_id = _chat_id(message)
    _register_user(message)

    stats.inc("messages")

    if "text" in message:
        text = message["text"].strip()
        message_logger.log_message(chat_id, text, direction="in")
        _handle_text(chat_id, text, message)
        return

    if "location" in message:
        loc = message["location"]
        message_logger.log_message(chat_id, f"location {loc}", direction="in")
        address = geolocation.get_address(loc["latitude"], loc["longitude"])
        
        
        txt = f"📍 <b>Ваша локация</b>\n"
        txt = txt + f"Широта: <code>{loc['latitude']}</code>\n"
        txt = txt + f"Долгота: <code>{loc['longitude']}</code>\n\n"
        txt = txt + f"Адрес:\n{address}"
        
        _reply(chat_id, txt)
        return

    if "photo" in message:
        _reply(chat_id, "🖼 Получил фото. Используйте /help для команд.")
        return
    elif "document" in message:
        _reply(chat_id, "📎 Получил документ. Используйте /help для команд.")
        return
    elif "voice" in message:
        _reply(chat_id, "🎤 Получил голос. Используйте /help для команд.")
        return
    elif "video" in message:
        _reply(chat_id, "🎬 Получил видео. Используйте /help для команд.")
        return
    elif "sticker" in message:
        _reply(chat_id, "😀 Получил стикер. Используйте /help для команд.")
        return
    elif "contact" in message:
        _reply(chat_id, "👤 Получил контакт. Используйте /help для команд.")
        return
    elif "audio" in message:
        _reply(chat_id, "🎵 Получил аудио. Используйте /help для команд.")
        return


def _handle_callback(callback_query: dict) -> None:
    callback_id = callback_query.get("id")
    data = callback_query.get("data", "")
    message = callback_query.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")

    if not chat_id or not data:
        return

    message_logger.log_message(chat_id, f"callback: {data}", direction="in")

    if data == "watch_add":
        user_state.set_state(chat_id, "waiting_domain_watch")
        telegram_api.answer_callback(callback_id)
        reply_text = "👁️ <b>Введите домен для отслеживания</b>\n\nПример: <code>apple.com</code>"
        buttons = [[telegram_api.make_inline_button("← Отмена", "menu_watch")]]
        reply_markup = telegram_api.make_inline_keyboard(buttons)
        if message_id and chat_id:
            _safe_edit(chat_id, message_id, reply_text, reply_markup)
        else:
            _reply(chat_id, reply_text)
        return

    elif data == "watch_delete_menu":
        watchlist = domain_service.get_user_watchlist(chat_id)
        if not watchlist:
            telegram_api.answer_callback(callback_id, "⚠️ Список пуст")
            return

        text = "🗑 <b>Выберите домен для удаления:</b>"
        buttons = []
        for domain in watchlist:
            buttons.append([telegram_api.make_inline_button(f"❌ {domain}", f"watch_remove_{domain}")])
        buttons.append([telegram_api.make_inline_button("← Отмена", "menu_watch")])
        reply_markup = telegram_api.make_inline_keyboard(buttons)

        if message_id and chat_id:
            _safe_edit(chat_id, message_id, text, reply_markup)
        else:
            telegram_api.send_message(chat_id, text, reply_markup=reply_markup)
            message_logger.log_message(chat_id, text, direction="out")
        telegram_api.answer_callback(callback_id)
        return

    elif data.startswith("watch_remove_"):
        domain = data.replace("watch_remove_", "")
        domain_service.remove_watch(chat_id, domain)
        telegram_api.answer_callback(callback_id, f"🗑 {domain} удален")
        
        watchlist = domain_service.get_user_watchlist(chat_id)
        if watchlist:
            text = f"👁️ <b>Мой список отслеживания</b>\n\nДоменов: <code>{len(watchlist)}</code>\n\n"
            for d in watchlist:
                text = text + f"• <code>{_h(d)}</code>\n"
            buttons = [
                [telegram_api.make_inline_button("➕ Добавить новый", "watch_add")],
                [telegram_api.make_inline_button("🗑 Удалить домен", "watch_delete_menu")],
                [telegram_api.make_inline_button("← Назад", "menu")],
            ]
        else:
            text = "👁️ <b>Отслеживание доменов</b>\n\nСписок пуст."
            buttons = [[telegram_api.make_inline_button("➕ Добавить домен", "watch_add")], 
                       [telegram_api.make_inline_button("← Назад", "menu")]]

        reply_markup = telegram_api.make_inline_keyboard(buttons)
        if message_id and chat_id:
            _safe_edit(chat_id, message_id, text, reply_markup)
        return

    elif data.startswith("watch_"):
        domain = data.replace("watch_", "")
        if domain in ["add", "delete_menu", "remove"]: return

        result = domain_service.add_watch(chat_id, domain)
        telegram_api.answer_callback(callback_id, "✓ Добавлено!")

        watchlist = domain_service.get_user_watchlist(chat_id)
        if watchlist:
            text = f"👁️ <b>Мой список отслеживания</b>\n\nДоменов в списке: <code>{len(watchlist)}</code>\n\n"
            for d in watchlist:
                text = text + f"• <code>{_h(d)}</code>\n"
            text += "\n\nЧто делать?"
            buttons = [
                [telegram_api.make_inline_button("➕ Добавить новый", "watch_add")],
                [telegram_api.make_inline_button("🗑 Удалить домен", "watch_delete_menu")],
                [telegram_api.make_inline_button("← Назад", "menu")],
            ]
        else:
            text = "👁️ <b>Отслеживание доменов</b>\n\nВ вашем списке нет доменов."
            buttons = [[telegram_api.make_inline_button("← Назад", "menu")]]

        reply_markup = telegram_api.make_inline_keyboard(buttons)
        if message_id and chat_id:
            _safe_edit(chat_id, message_id, text, reply_markup)
        else:
            telegram_api.send_message(chat_id, text, reply_markup=reply_markup)
            message_logger.log_message(chat_id, text, direction="out")
        return

    if data.startswith("check_"):
        domain = data.replace("check_", "")
        telegram_api.answer_callback(callback_id, "🔎 Проверяю...")
        result = domain_service.check_domain(domain)
        history.add_entry(chat_id, domain.lower())
        reply_text = f"✅ <b>Проверка домена: {_h(domain)}</b>\n\n{result}"
        if message_id and chat_id:
            _safe_edit(chat_id, message_id, reply_text)
        else:
            _reply(chat_id, reply_text)

    elif data.startswith("unwatch_"):
        domain = data.replace("unwatch_", "")
        result = domain_service.remove_watch(chat_id, domain)
        telegram_api.answer_callback(callback_id, "✓ Домен удален из отслеживания")
        if message_id and chat_id:
            _safe_edit(chat_id, message_id, f"❌ {result}")
        else:
            _reply(chat_id, result)

    elif data.startswith("search_"):
        keyword = data.replace("search_", "")
        telegram_api.answer_callback(callback_id, "🔍 Ищу...")
        result = domain_service.search_available(keyword)
        reply_text = f"🔍 <b>Поиск доменов: {_h(keyword)}</b>\n\n{result}"
        if message_id and chat_id:
            _safe_edit(chat_id, message_id, reply_text)
        else:
            _reply(chat_id, reply_text)

    elif data == "menu":
        user_state.clear_state(chat_id)
        menu_text = (
            "👋 <b>Главное меню</b>\n\n"
            "Выберите действие:"
        )
        buttons = [
            [telegram_api.make_inline_button("✅ Проверить домен", "menu_check")],
            [telegram_api.make_inline_button("🔍 Найти домены", "menu_search")],
            [telegram_api.make_inline_button("👁️ Отслеживание", "menu_watch")],
            [telegram_api.make_inline_button("🕓 История", "menu_history")],
            [telegram_api.make_inline_button("📤 Экспорт списка", "menu_export")],
            [telegram_api.make_inline_button("🪪 Мой профиль", "menu_profile")],
        ]
        reply_markup = telegram_api.make_inline_keyboard(buttons)
        if message_id and chat_id:
            _safe_edit(chat_id, message_id, menu_text, reply_markup)
        else:
            telegram_api.send_message(chat_id, menu_text, reply_markup=reply_markup)
            message_logger.log_message(chat_id, menu_text, direction="out")
        telegram_api.answer_callback(callback_id)

    elif data == "menu_check":
        user_state.set_state(chat_id, "waiting_domain_check")
        telegram_api.answer_callback(callback_id)
        if message_id and chat_id:
            reply_text = "🔎 <b>Введите домен для проверки</b>\n\nПример: <code>google.com</code>"
            buttons = [[telegram_api.make_inline_button("← Отмена", "menu")]]
            reply_markup = telegram_api.make_inline_keyboard(buttons)
            _safe_edit(chat_id, message_id, reply_text, reply_markup)
        else:
            _reply(chat_id, "🔎 Введите домен для проверки (пример: google.com)")

    elif data == "menu_search":
        user_state.set_state(chat_id, "waiting_keyword_search")
        telegram_api.answer_callback(callback_id)
        if message_id and chat_id:
            reply_text = "🔍 <b>Введите ключевое слово</b>\n\nБот найдет похожие свободные домены.\nПример: <code>shop</code>"
            buttons = [[telegram_api.make_inline_button("← Отмена", "menu")]]
            reply_markup = telegram_api.make_inline_keyboard(buttons)
            _safe_edit(chat_id, message_id, reply_text, reply_markup)
        else:
            _reply(chat_id, "🔍 Введите ключевое слово для поиска (пример: shop)")

    elif data == "menu_watch":
        user_state.clear_state(chat_id)
        watchlist = domain_service.get_user_watchlist(chat_id)

        if watchlist:
            text = f"👁️ <b>Мой список отслеживания</b>\n\nДоменов в списке: <code>{len(watchlist)}</code>\n\n"
            for d in watchlist:
                text = text + f"• <code>{_h(d)}</code>\n"
            text += "\n\nЧто делать?"
            buttons = [
                [telegram_api.make_inline_button("➕ Добавить новый", "watch_add")],
                [telegram_api.make_inline_button("🗑 Удалить домен", "watch_delete_menu")],
                [telegram_api.make_inline_button("← Назад", "menu")],
            ]
        else:
            text = "👁️ <b>Отслеживание доменов</b>\n\nВ вашем списке нет доменов.\n\nДобавьте первый домен!"
            buttons = [
                [telegram_api.make_inline_button("➕ Добавить домен", "watch_add")],
                [telegram_api.make_inline_button("← Назад", "menu")],
            ]

        reply_markup = telegram_api.make_inline_keyboard(buttons)
        if message_id and chat_id:
            _safe_edit(chat_id, message_id, text, reply_markup)
        else:
            telegram_api.send_message(chat_id, text, reply_markup=reply_markup)
            message_logger.log_message(chat_id, text, direction="out")
        telegram_api.answer_callback(callback_id)

    elif data == "menu_profile":
        u = callback_query.get("from", {})
        username = u.get("username") or "—"
        profile_text = (
            f"🪪 <b>Ваш профиль</b>\n"
            f"ID: <code>{chat_id}</code>\n"
            f"Username: @{_h(username)}\n"
            f"Имя: {_h(u.get('first_name', '—'))}"
        )
        buttons = [[telegram_api.make_inline_button("← Назад в меню", "menu")]]
        reply_markup = telegram_api.make_inline_keyboard(buttons)
        telegram_api.answer_callback(callback_id)
        if message_id and chat_id:
            _safe_edit(chat_id, message_id, profile_text, reply_markup)
        else:
            _reply(chat_id, profile_text)

    elif data == "menu_history":
        text_out, buttons = _history_screen(chat_id)
        reply_markup = telegram_api.make_inline_keyboard(buttons)
        telegram_api.answer_callback(callback_id)
        if message_id and chat_id:
            _safe_edit(chat_id, message_id, text_out, reply_markup)
        else:
            telegram_api.send_message(chat_id, text_out, reply_markup=reply_markup)
            message_logger.log_message(chat_id, text_out, direction="out")

    elif data == "history_clear":
        history.clear_history(chat_id)
        telegram_api.answer_callback(callback_id, "🗑 История очищена")
        text_out, buttons = _history_screen(chat_id)
        reply_markup = telegram_api.make_inline_keyboard(buttons)
        if message_id and chat_id:
            _safe_edit(chat_id, message_id, text_out, reply_markup)

    elif data == "menu_export":
        telegram_api.answer_callback(callback_id, "📤 Готовлю файл...")
        _export_watchlist(chat_id)


def _handle_text(chat_id: int, text: str, message: dict) -> None:
    u = _user(message)
    lower = text.lower()
    state, state_data = user_state.get_state(chat_id)

    if state == "waiting_domain_check":
        parts = text.replace(",", " ").split()
        user_state.clear_state(chat_id)
        if len(parts) > 1:
            _notice(chat_id, "🔎 Проверяю домены, секунду...")
            result = domain_service.check_domains_bulk(parts)
            for d in parts:
                history.add_entry(chat_id, d.strip().lower().strip(","))
            buttons = [[telegram_api.make_inline_button("← Главное меню", "menu")]]
            reply_markup = telegram_api.make_inline_keyboard(buttons)
            telegram_api.send_message(chat_id, result, reply_markup=reply_markup)
            message_logger.log_message(chat_id, result, direction="out")
            return
        domain = text.strip()
        _notice(chat_id, "🔎 Проверяю домен, секунду...")
        result = domain_service.check_domain(domain)
        history.add_entry(chat_id, domain.strip().lower())
        reply_text = f"✅ <b>Результат проверки: {_h(domain)}</b>\n\n{result}"
        buttons = [
            [telegram_api.make_inline_button(f"👁️ Отслеживать", f"watch_{domain}")],
            [telegram_api.make_inline_button("← Главное меню", "menu")],
        ]
        reply_markup = telegram_api.make_inline_keyboard(buttons)
        telegram_api.send_message(chat_id, reply_text, reply_markup=reply_markup)
        message_logger.log_message(chat_id, reply_text, direction="out")
        return

    if state == "waiting_keyword_search":
        keyword = text.strip()
        _notice(chat_id, "🔍 Ищу свободные домены, это займёт несколько секунд...")
        result = domain_service.search_available(keyword)
        reply_text = f"🔍 <b>Результаты поиска: {_h(keyword)}</b>\n\n{result}"
        buttons = [
            [telegram_api.make_inline_button("🔄 Новый поиск", "menu_search")],
            [telegram_api.make_inline_button("← Главное меню", "menu")],
        ]
        reply_markup = telegram_api.make_inline_keyboard(buttons)
        telegram_api.send_message(chat_id, reply_text, reply_markup=reply_markup)
        message_logger.log_message(chat_id, reply_text, direction="out")
        user_state.clear_state(chat_id)
        return

    if state == "waiting_domain_watch":
        domain = text.strip()
        result = domain_service.add_watch(chat_id, domain)
        reply_text = f"👁️ <b>Отслеживание</b>\n\n{result}"
        buttons = [
            [telegram_api.make_inline_button(f"❌ Убрать из отслеживания", f"unwatch_{domain}")],
            [telegram_api.make_inline_button("← Главное меню", "menu")],
        ]
        reply_markup = telegram_api.make_inline_keyboard(buttons)
        telegram_api.send_message(chat_id, reply_text, reply_markup=reply_markup)
        message_logger.log_message(chat_id, reply_text, direction="out")
        user_state.clear_state(chat_id)
        return

    if lower.startswith("/start"):
        stats.inc("commands")
        user_state.clear_state(chat_id)
        text = (
            "👋 <b>Привет!</b> Я бот для проверки доменов.\n\n"
            "Команды: /check /search /watch /history /export /me\n"
            "В /check можно указать несколько доменов через пробел.\n\n"
            "Используй кнопки ниже для навигации:"
        )
        buttons = [
            [telegram_api.make_inline_button("✅ Проверить домен", "menu_check")],
            [telegram_api.make_inline_button("🔍 Найти домены", "menu_search")],
            [telegram_api.make_inline_button("👁️ Отслеживание", "menu_watch")],
            [telegram_api.make_inline_button("🕓 История", "menu_history")],
            [telegram_api.make_inline_button("📤 Экспорт списка", "menu_export")],
            [telegram_api.make_inline_button("🪪 Мой профиль", "menu_profile")],
        ]
        reply_markup = telegram_api.make_inline_keyboard(buttons)
        telegram_api.send_message(chat_id, text, reply_markup=reply_markup)
        message_logger.log_message(chat_id, text, direction="out")
        return

    if lower.startswith("/me"):
        stats.inc("commands")
        username = u.get("username") or "—"
        text = (
            f"🪪 <b>Ваш профиль</b>\n"
            f"ID: <code>{chat_id}</code>\n"
            f"Username: @{_h(username)}\n"
            f"Имя: {_h(u.get('first_name', '—'))}"
        )
        buttons = [
            [telegram_api.make_inline_button("← Назад в меню", "menu")],
        ]
        reply_markup = telegram_api.make_inline_keyboard(buttons)
        telegram_api.send_message(chat_id, text, reply_markup=reply_markup)
        message_logger.log_message(chat_id, text, direction="out")
        return

    if lower.startswith("/help"):
        stats.inc("commands")
        _handle_text(chat_id, "/start", message)
        return

    if lower.startswith("/history"):
        stats.inc("commands")
        text_out, buttons = _history_screen(chat_id)
        reply_markup = telegram_api.make_inline_keyboard(buttons)
        telegram_api.send_message(chat_id, text_out, reply_markup=reply_markup)
        message_logger.log_message(chat_id, text_out, direction="out")
        return

    if lower.startswith("/export"):
        stats.inc("commands")
        _export_watchlist(chat_id)
        return

    if lower.startswith("/check"):
        stats.inc("commands")
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            user_state.set_state(chat_id, "waiting_domain_check")
            _reply(chat_id, "🔎 <b>Введите домен для проверки</b>\n\nПример: <code>google.com</code>\nМожно несколько через пробел.")
            return
        args = parts[1].replace(",", " ").split()
        stats.inc("domains_checked")
        if len(args) > 1:
            _notice(chat_id, "🔎 Проверяю домены, секунду...")
            result = domain_service.check_domains_bulk(args)
            for d in args:
                history.add_entry(chat_id, d.strip().lower().strip(","))
            buttons = [[telegram_api.make_inline_button("← Меню", "menu")]]
            reply_markup = telegram_api.make_inline_keyboard(buttons)
            telegram_api.send_message(chat_id, result, reply_markup=reply_markup)
            message_logger.log_message(chat_id, result, direction="out")
            return
        domain = args[0].strip()
        _notice(chat_id, "🔎 Проверяю домен, секунду...")
        result = domain_service.check_domain(domain)
        history.add_entry(chat_id, domain.lower())
        reply_text = f"✅ <b>Результат проверки: {_h(domain)}</b>\n\n{result}"
        buttons = [
            [telegram_api.make_inline_button(f"👁️ Отслеживать", f"watch_{domain}")],
            [telegram_api.make_inline_button("← Меню", "menu")],
        ]
        reply_markup = telegram_api.make_inline_keyboard(buttons)
        telegram_api.send_message(chat_id, reply_text, reply_markup=reply_markup)
        message_logger.log_message(chat_id, reply_text, direction="out")
        return

    if lower.startswith("/search"):
        stats.inc("commands")
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            user_state.set_state(chat_id, "waiting_keyword_search")
            _reply(chat_id, "🔍 <b>Введите ключевое слово</b>\n\nПример: <code>shop</code>")
            return
        keyword = parts[1].strip()
        _notice(chat_id, "🔍 Ищу свободные домены, это займёт несколько секунд...")
        result = domain_service.search_available(keyword)
        reply_text = f"🔍 <b>Результаты поиска: {_h(keyword)}</b>\n\n{result}"
        buttons = [
            [telegram_api.make_inline_button("🔄 Новый поиск", "menu_search")],
            [telegram_api.make_inline_button("← Меню", "menu")],
        ]
        reply_markup = telegram_api.make_inline_keyboard(buttons)
        telegram_api.send_message(chat_id, reply_text, reply_markup=reply_markup)
        message_logger.log_message(chat_id, reply_text, direction="out")
        return

    if lower.startswith("/watch"):
        stats.inc("commands")
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            watchlist = domain_service.get_user_watchlist(chat_id)
            if watchlist:
                reply_text = f"👁️ <b>Мой список отслеживания</b>\n\nДоменов в списке: <code>{len(watchlist)}</code>\n\n"
                for d in watchlist:
                    reply_text = reply_text + f"• <code>{_h(d)}</code>\n"
                reply_text += "\n\nЧто делать?"
                buttons = [
                    [telegram_api.make_inline_button("➕ Добавить новый", "watch_add")],
                    [telegram_api.make_inline_button("🗑 Удалить домен", "watch_delete_menu")],
                    [telegram_api.make_inline_button("← Меню", "menu")],
                ]
            else:
                reply_text = "👁️ <b>Отслеживание доменов</b>\n\nВ вашем списке нет доменов.\n\nДобавьте первый домен!"
                buttons = [
                    [telegram_api.make_inline_button("➕ Добавить домен", "watch_add")],
                    [telegram_api.make_inline_button("← Меню", "menu")],
                ]
            reply_markup = telegram_api.make_inline_keyboard(buttons)
            telegram_api.send_message(chat_id, reply_text, reply_markup=reply_markup)
            message_logger.log_message(chat_id, reply_text, direction="out")
            return

        domain = parts[1].strip()
        result = domain_service.add_watch(chat_id, domain)
        reply_text = f"👁️ <b>Отслеживание</b>\n\n{result}"
        buttons = [
            [telegram_api.make_inline_button(f"❌ Убрать", f"watch_remove_{domain}")],
            [telegram_api.make_inline_button("👁️ Мой список", "menu_watch")],
            [telegram_api.make_inline_button("← Меню", "menu")],
        ]
        reply_markup = telegram_api.make_inline_keyboard(buttons)
        telegram_api.send_message(chat_id, reply_text, reply_markup=reply_markup)
        message_logger.log_message(chat_id, reply_text, direction="out")
        return

    if lower.startswith("/unwatch"):
        stats.inc("commands")
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            _reply(chat_id, "❌ Использование: /unwatch <code>example.com</code>")
            return
        domain = parts[1].strip()
        result = domain_service.remove_watch(chat_id, domain)
        reply_text = f"❌ <b>Удалено из отслеживания</b>\n\n{result}"
        buttons = [
            [telegram_api.make_inline_button(f"👁️ Отслеживать снова", f"watch_{domain}")],
            [telegram_api.make_inline_button("← Меню", "menu")],
        ]
        reply_markup = telegram_api.make_inline_keyboard(buttons)
        telegram_api.send_message(chat_id, reply_text, reply_markup=reply_markup)
        message_logger.log_message(chat_id, reply_text, direction="out")
        return

    _reply(
        chat_id,
        "🤔 Не понял. Используйте меню: /start или введите домен/ключевое слово.",
    )
