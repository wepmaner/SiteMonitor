from aiogram.fsm.state import StatesGroup, State
from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
import utils
import gui
from site_monitor import SiteConfig
import callbackdata as cb

router = Router()

class EditSiteStates(StatesGroup):
    waiting_for_name = State() 
    waiting_for_new_name = State()
    waiting_for_new_url = State()
    waiting_for_new_check_interval = State()
    waiting_for_new_timeout = State()
    waiting_for_new_expected_status = State()


@router.callback_query(cb.SiteAction.filter(F.action=="edit"))
async def edit_site_start(callback_query: types.CallbackQuery, callback_data: cb.SiteAction, state: FSMContext):
    site_name = callback_data.name
    await state.clear()
    await state.update_data(editing_site=site_name)

    await callback_query.message.answer(
        f"Редактирование сайта <b>{site_name}</b>\n\n"
        "Введите новое название сайта или нажмите «Пропустить»:", parse_mode="HTML", disable_web_page_preview=True,
        reply_markup=gui.skip_kb()
    )
    await state.set_state(EditSiteStates.waiting_for_new_name)


# новый name
@router.message(EditSiteStates.waiting_for_new_name)
async def edit_site_name(message: types.Message, state: FSMContext):
    if message.text.strip() != "⏭️ Пропустить":
        await state.update_data(new_name=message.text.strip())

    await message.answer("Введите новый URL или нажмите «Пропустить»:", reply_markup=gui.skip_kb())
    await state.set_state(EditSiteStates.waiting_for_new_url)


# новый url
@router.message(EditSiteStates.waiting_for_new_url)
async def edit_site_url(message: types.Message, state: FSMContext):
    if message.text.strip() != "⏭️ Пропустить":
        await state.update_data(new_url=message.text.strip())

    await message.answer("Введите новый интервал проверки (сек) или «Пропустить»:", reply_markup=gui.skip_kb())
    await state.set_state(EditSiteStates.waiting_for_new_check_interval)


# новый check_interval
@router.message(EditSiteStates.waiting_for_new_check_interval)
async def edit_site_interval(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text != "⏭️ Пропустить":
        if not text.isdigit():
            await message.answer("Введите число или «Пропустить».")
            return
        await state.update_data(new_check_interval=int(text))

    await message.answer("Введите новый таймаут (сек) или «Пропустить»:", reply_markup=gui.skip_kb())
    await state.set_state(EditSiteStates.waiting_for_new_timeout)


# новый timeout
@router.message(EditSiteStates.waiting_for_new_timeout)
async def edit_site_timeout(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text != "⏭️ Пропустить":
        if not text.isdigit():
            await message.answer("Введите число или «Пропустить».")
            return
        await state.update_data(new_timeout=int(text))

    await message.answer("Введите новый ожидаемый статус (например, 200) или «Пропустить»:",
                         reply_markup=gui.skip_kb())
    await state.set_state(EditSiteStates.waiting_for_new_expected_status)


# новый expected_status и сохранение
@router.message(EditSiteStates.waiting_for_new_expected_status)
async def edit_site_expected_status(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text != "⏭️ Пропустить":
        if not text.isdigit():
            await message.answer("Введите число или «Пропустить».")
            return
        await state.update_data(new_expected_status=int(text))

    data = await state.get_data()
    site_name = data["editing_site"]

    monitor = message.bot.monitor
    for site in monitor.sites:
        if site.name == site_name:
            # применяем только те поля, что реально есть в data
            if "new_name" in data: site.name = data["new_name"]
            if "new_url" in data: site.url = data["new_url"]
            if "new_check_interval" in data: site.check_interval = data["new_check_interval"]
            if "new_timeout" in data: site.timeout = data["new_timeout"]
            if "new_expected_status" in data: site.expected_status = data["new_expected_status"]

            await monitor.update_site(site_name,site)
            text = utils.format_site_info(site)
            await message.answer(
                f"✅ Сайт обновлён!\n{text}",
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=gui.site_action(site)
            )
            break
    else:
        await message.answer("⚠️ Сайт не найден.")

    await state.clear()

