from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.core.config import Settings
from app.filters import AdminFilter
from app.keyboards import (
    BTN_ADMIN_CONTROL_MENU,
    BTN_ADMIN_SYSTEM_MENU,
    BTN_ADMIN_USERS_MENU,
    BTN_ALL,
    BTN_APPROVE_ID,
    BTN_APPROVED,
    BTN_BACK_ADMIN,
    BTN_BLOCK_ID,
    BTN_BLOCKED,
    BTN_BROADCAST,
    BTN_CANCEL,
    BTN_DELETE_ID,
    BTN_HEALTH,
    BTN_MONITORING,
    BTN_PENDING,
    BTN_STATS,
    admin_cancel_keyboard,
    admin_control_keyboard,
    admin_panel_keyboard,
    admin_user_list_pagination_keyboard,
    admin_system_keyboard,
    admin_users_keyboard,
    back_to_admin_panel_keyboard,
)
from app.services.broadcast_service import BroadcastService
from app.services.health_service import HealthService
from app.services.live_monitor_service import LiveMonitorService
from app.services.user_service import UserService
from app.states.admin_states import AdminActionState
from app.utils import format_user_card


USER_LIST_PAGE_SIZE = 5


def register_admin_handlers(
    user_service: UserService,
    health_service: HealthService,
    broadcast_service: BroadcastService,
    live_monitor_service: LiveMonitorService,
    settings: Settings,
) -> Router:
    router = Router()
    admin_filter = AdminFilter(settings.effective_admin_ids)

    @router.message(Command("admin"), admin_filter)
    @router.message(F.text == BTN_BACK_ADMIN, admin_filter)
    async def panel(message: Message, state: FSMContext):
        await state.clear()
        await message.answer("Admin panel", reply_markup=admin_panel_keyboard())

    @router.message(F.text == BTN_ADMIN_USERS_MENU, admin_filter)
    async def admin_users_menu(message: Message, state: FSMContext):
        await state.clear()
        await message.answer("👥 Foydalanuvchilar bo'limi", reply_markup=admin_users_keyboard())

    @router.message(F.text == BTN_ADMIN_CONTROL_MENU, admin_filter)
    async def admin_control_menu(message: Message, state: FSMContext):
        await state.clear()
        await message.answer("🧭 Boshqaruv bo'limi", reply_markup=admin_control_keyboard())

    @router.message(F.text == BTN_ADMIN_SYSTEM_MENU, admin_filter)
    async def admin_system_menu(message: Message, state: FSMContext):
        await state.clear()
        await message.answer("⚙️ Tizim bo'limi", reply_markup=admin_system_keyboard())

    @router.message(StateFilter(AdminActionState), F.text == BTN_CANCEL, admin_filter)
    async def cancel_admin_action(message: Message, state: FSMContext):
        await state.clear()
        await message.answer("Amal bekor qilindi.", reply_markup=admin_users_keyboard())

    @router.message(F.text == BTN_PENDING, admin_filter)
    async def pending_users(message: Message):
        await _send_user_page(message, "pending", 1)

    @router.callback_query(F.data.startswith("admin_user:"))
    async def user_action(callback: CallbackQuery, state: FSMContext):
        if callback.from_user.id not in settings.effective_admin_ids:
            await callback.answer("Siz admin emassiz.", show_alert=True)
            return
        _, action, raw_tg_id = (callback.data or "").split(":")
        tg_id = int(raw_tg_id)
        if action == "approve":
            user = await user_service.get(tg_id)
            if not user:
                await callback.answer("Foydalanuvchi topilmadi.", show_alert=True)
                return
            await state.set_state(AdminActionState.waiting_for_approve_access_days)
            await state.update_data(approve_tg_id=tg_id)
            if callback.message:
                await callback.message.edit_reply_markup(reply_markup=None)
                await callback.message.answer(
                    f"ID: {tg_id}\nFoydalanish muddatini kunlarda kiriting.\n\nMasalan: 8",
                    reply_markup=admin_users_keyboard(),
                )
            await callback.answer("Muddatni kiriting")
            return
        elif action == "reject":
            ok = await user_service.reject(tg_id, callback.from_user.id)
            text = "So'rov bekor qilindi." if ok else "Foydalanuvchi topilmadi."
            user_text = "Tasdiqlash so'rovingiz bekor qilindi."
        elif action == "block":
            ok = await user_service.block(tg_id, callback.from_user.id)
            text = "Foydalanuvchi bloklandi." if ok else "Foydalanuvchi topilmadi."
            user_text = "Hisobingiz admin tomonidan bloklandi."
        else:
            await callback.answer("Noto'g'ri amal.", show_alert=True)
            return
        if callback.message:
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer(f"{text}\nID: {tg_id}", reply_markup=admin_users_keyboard())
        if ok:
            try:
                await callback.bot.send_message(tg_id, user_text)
            except Exception:
                pass
        await callback.answer(text)

    @router.message(F.text == BTN_APPROVED, admin_filter)
    async def approved_users(message: Message):
        await _send_user_page(message, "approved", 1)

    @router.message(F.text == BTN_BLOCKED, admin_filter)
    async def blocked_users(message: Message):
        await _send_user_page(message, "blocked", 1)

    @router.message(F.text == BTN_ALL, admin_filter)
    async def all_users(message: Message):
        await _send_user_page(message, "all", 1)

    @router.callback_query(F.data.startswith("admin_users:list:"))
    async def paged_users(callback: CallbackQuery):
        if callback.from_user.id not in settings.effective_admin_ids:
            await callback.answer("Siz admin emassiz.", show_alert=True)
            return
        parts = (callback.data or "").split(":")
        if len(parts) != 4:
            await callback.answer("Noto'g'ri sahifa.", show_alert=True)
            return
        _, _, kind, raw_page = parts
        if kind not in {"pending", "approved", "blocked", "all"} or not raw_page.isdigit():
            await callback.answer("Noto'g'ri sahifa.", show_alert=True)
            return
        if callback.message:
            await _edit_user_page(callback, kind, int(raw_page))
        await callback.answer()

    @router.callback_query(F.data == "admin_users:noop")
    async def users_pagination_noop(callback: CallbackQuery):
        if callback.from_user.id not in settings.effective_admin_ids:
            await callback.answer("Siz admin emassiz.", show_alert=True)
            return
        await callback.answer("Joriy sahifa")

    async def _send_user_page(message: Message, kind: str, page: int):
        text, page_number, total_pages, pending_user_ids = await _build_user_page(kind, page)
        if total_pages == 0:
            await message.answer(text, reply_markup=admin_users_keyboard())
            return
        await message.answer(
            text,
            reply_markup=admin_user_list_pagination_keyboard(kind, page_number, total_pages, pending_user_ids),
        )

    async def _edit_user_page(callback: CallbackQuery, kind: str, page: int):
        text, page_number, total_pages, pending_user_ids = await _build_user_page(kind, page)
        await callback.message.edit_text(
            text,
            reply_markup=admin_user_list_pagination_keyboard(kind, page_number, total_pages, pending_user_ids),
        )

    async def _build_user_page(kind: str, page: int) -> tuple[str, int, int, list[int]]:
        titles = {
            "pending": "Tasdiqlash kutilayotgan foydalanuvchilar",
            "approved": "Tasdiqlangan foydalanuvchilar",
            "blocked": "Bloklangan foydalanuvchilar",
            "all": "Barcha foydalanuvchilar",
        }
        result = await user_service.list_page(kind, page, USER_LIST_PAGE_SIZE)
        users = result["users"]
        total = int(result["total"])
        page_number = int(result["page"])
        total_pages = int(result["total_pages"])
        title = titles[kind]
        if not users:
            return f"{title}: ro'yxat bo'sh.", page_number, 0, []
        cards = "\n\n---\n\n".join(format_user_card(user) for user in users)
        header = f"{title}\nSahifa: {page_number}/{total_pages}\nJami: {total}\n\n"
        pending_user_ids = [user.tg_id for user in users] if kind == "pending" else []
        return header + cards, page_number, total_pages, pending_user_ids

    @router.message(F.text == BTN_STATS, admin_filter)
    async def stats(message: Message):
        s = await user_service.stats()
        await message.answer(
            "Statistika\n\n"
            f"Jami: {s.get('total', 0)}\n"
            f"Kutilmoqda: {s.get('pending', 0)}\n"
            f"Faol: {s.get('approved', 0)}\n"
            f"Bloklangan: {s.get('blocked', 0)}\n"
            f"Muddati tugagan: {s.get('expired', 0)}\n"
            f"Rad etilgan: {s.get('rejected', 0)}",
            reply_markup=admin_system_keyboard(),
        )

    @router.message(F.text == BTN_HEALTH, admin_filter)
    async def health(message: Message):
        result = await health_service.check()
        await message.answer(f"System health\n\nDatabase: {result['database']}\nRedis: {result['redis']}", reply_markup=admin_system_keyboard())

    @router.message(F.text == BTN_MONITORING, admin_filter)
    async def monitoring_control(message: Message, state: FSMContext):
        stats = live_monitor_service.stats()
        ids = stats["active_user_ids"]
        body = "\n".join(f"- {tg_id}" for tg_id in ids[:50]) if ids else "Faol kuzatish yo'q."
        await state.set_state(AdminActionState.waiting_for_stop_monitoring_user_id)
        await message.answer(
            "Kuzatish nazorati\n\n"
            f"Faol kuzatishlar: {stats['active_count']}\n\n"
            f"{body}\n\n"
            "Kuzatishni majburan to'xtatish uchun user ID yuboring yoki admin panelga qayting.",
            reply_markup=admin_control_keyboard(),
        )

    @router.message(AdminActionState.waiting_for_stop_monitoring_user_id, admin_filter)
    async def force_stop_monitoring(message: Message, state: FSMContext):
        if not (message.text or "").isdigit():
            await message.answer("Faqat raqamdan iborat Telegram ID yuboring.")
            return
        tg_id = int(message.text)
        await live_monitor_service.stop_monitoring(tg_id)
        await state.clear()
        await message.answer(f"Kuzatish to'xtatildi.\nID: {tg_id}", reply_markup=admin_control_keyboard())

    @router.message(F.text == BTN_APPROVE_ID, admin_filter)
    async def ask_approve(message: Message, state: FSMContext):
        await state.set_state(AdminActionState.waiting_for_approve_user_id)
        await message.answer("Tasdiqlash uchun Telegram ID yuboring.", reply_markup=admin_cancel_keyboard())

    @router.message(AdminActionState.waiting_for_approve_user_id, admin_filter)
    async def approve_by_id(message: Message, state: FSMContext):
        if not (message.text or "").isdigit():
            await message.answer("Faqat raqam yuboring.")
            return
        tg_id = int(message.text)
        user = await user_service.get(tg_id)
        if not user:
            await state.clear()
            await message.answer("Foydalanuvchi topilmadi.", reply_markup=admin_users_keyboard())
            return
        await state.set_state(AdminActionState.waiting_for_approve_access_days)
        await state.update_data(approve_tg_id=tg_id)
        await message.answer(
            f"ID: {tg_id}\nFoydalanish muddatini kunlarda kiriting.\n\nMasalan: 8",
            reply_markup=admin_cancel_keyboard(),
        )

    @router.message(AdminActionState.waiting_for_approve_access_days, admin_filter)
    async def approve_access_days(message: Message, state: FSMContext):
        raw_days = (message.text or "").strip()
        if not raw_days.isdigit():
            await message.answer("Faqat kun sonini raqam bilan yuboring. Masalan: 8")
            return
        days = int(raw_days)
        if days < 1 or days > 3650:
            await message.answer("Muddat 1 kundan 3650 kungacha bo'lishi kerak.")
            return
        data = await state.get_data()
        tg_id = int(data.get("approve_tg_id", 0))
        if not tg_id:
            await state.clear()
            await message.answer("Tasdiqlanadigan foydalanuvchi topilmadi. Qaytadan urinib ko'ring.", reply_markup=admin_users_keyboard())
            return
        ok = await user_service.approve(tg_id, message.from_user.id, access_days=days)
        await state.clear()
        if ok:
            try:
                await message.bot.send_message(tg_id, f"Hisobingiz tasdiqlandi. Botdan {days} kun foydalanishingiz mumkin.")
            except Exception:
                pass
        await message.answer(
            f"Tasdiqlandi. Muddat: {days} kun." if ok else "Foydalanuvchi topilmadi.",
            reply_markup=admin_users_keyboard(),
        )

    @router.message(F.text == BTN_BLOCK_ID, admin_filter)
    async def ask_block(message: Message, state: FSMContext):
        await state.set_state(AdminActionState.waiting_for_block_user_id)
        await message.answer("Bloklash uchun Telegram ID yuboring.", reply_markup=admin_cancel_keyboard())

    @router.message(AdminActionState.waiting_for_block_user_id, admin_filter)
    async def block_by_id(message: Message, state: FSMContext):
        if not (message.text or "").isdigit():
            await message.answer("Faqat raqam yuboring.")
            return
        ok = await user_service.block(int(message.text), message.from_user.id)
        await state.clear()
        await message.answer("Bloklandi." if ok else "Foydalanuvchi topilmadi.", reply_markup=admin_users_keyboard())

    @router.message(F.text == BTN_DELETE_ID, admin_filter)
    async def ask_delete(message: Message, state: FSMContext):
        await state.set_state(AdminActionState.waiting_for_delete_user_id)
        await message.answer(
            "O'chirish uchun Telegram ID yuboring.\n\n"
            "Diqqat: foydalanuvchi ma'lumotlari, kalit so'zlari, sessiyasi va signallari bazadan o'chiriladi.",
            reply_markup=admin_cancel_keyboard(),
        )

    @router.message(AdminActionState.waiting_for_delete_user_id, admin_filter)
    async def delete_by_id(message: Message, state: FSMContext):
        if not (message.text or "").isdigit():
            await message.answer("Faqat raqam yuboring.")
            return
        tg_id = int(message.text)
        if tg_id in settings.effective_admin_ids:
            await state.clear()
            await message.answer("Admin hisobini bu panel orqali o'chirish mumkin emas.", reply_markup=admin_users_keyboard())
            return
        await live_monitor_service.stop_monitoring(tg_id)
        ok = await user_service.delete(tg_id, message.from_user.id, reason="admin_panel_delete")
        await state.clear()
        if ok:
            try:
                await message.bot.send_message(tg_id, "Hisobingiz admin tomonidan o'chirildi.")
            except Exception:
                pass
        await message.answer("Foydalanuvchi o'chirildi." if ok else "Foydalanuvchi topilmadi.", reply_markup=admin_users_keyboard())

    @router.message(F.text == BTN_BROADCAST, admin_filter)
    async def ask_broadcast(message: Message, state: FSMContext):
        await state.set_state(AdminActionState.waiting_for_broadcast_text)
        await message.answer("Broadcast matnini yuboring. Bekor qilish uchun admin panelga qayting.", reply_markup=admin_control_keyboard())

    @router.message(AdminActionState.waiting_for_broadcast_text, admin_filter)
    async def broadcast(message: Message, state: FSMContext):
        text = (message.text or "").strip()
        if not text:
            await message.answer("Broadcast matni bo'sh bo'lmasligi kerak.")
            return
        result = await broadcast_service.send_to_approved_users(message.bot, message.from_user.id, text)
        await state.clear()
        await message.answer(
            "Broadcast yakunlandi.\n"
            f"Jami: {result['total']}\n"
            f"Yuborildi: {result['sent']}\n"
            f"Xato: {result['failed']}",
            reply_markup=admin_control_keyboard(),
        )

    @router.message(Command("admin"))
    async def deny(message: Message):
        await message.answer("Siz admin emassiz.")

    return router
