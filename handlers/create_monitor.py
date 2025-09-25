from aiogram.fsm.state import StatesGroup, State
from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
import utils
from site_monitor import SiteConfig
import gui
router = Router()

class AddSiteStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_url = State()
    waiting_for_check_interval = State()
    waiting_for_timeout = State()
    waiting_for_expected_status = State()

@router.callback_query(F.data=='addsite')
async def listsites(callback_query: types.CallbackQuery, state: FSMContext):
    await state.clear()  # очищаем предыдущее состояние
    await callback_query.message.answer("Введите название сайта:")
    await state.set_state(AddSiteStates.waiting_for_name)

# Получаем имя сайта
@router.message(AddSiteStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите URL сайта:")
    await state.set_state(AddSiteStates.waiting_for_url)

# Получаем URL
@router.message(AddSiteStates.waiting_for_url)
async def process_url(message: types.Message, state: FSMContext):
    await state.update_data(url=message.text)
    await message.answer("Введите интервал проверки в секундах (например, 60):")
    await state.set_state(AddSiteStates.waiting_for_check_interval)

# Получаем интервал проверки
@router.message(AddSiteStates.waiting_for_check_interval)
async def process_check_interval(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число.")
        return
    await state.update_data(check_interval=int(message.text))
    await message.answer("Введите таймаут в секундах (например, 10):")
    await state.set_state(AddSiteStates.waiting_for_timeout)

# Получаем таймаут
@router.message(AddSiteStates.waiting_for_timeout)
async def process_timeout(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число.")
        return
    await state.update_data(timeout=int(message.text))
    await message.answer("Введите ожидаемый HTTP-статус (например, 200):")
    await state.set_state(AddSiteStates.waiting_for_expected_status)

# Получаем ожидаемый статус и сохраняем сайт
@router.message(AddSiteStates.waiting_for_expected_status)
async def process_expected_status(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число.")
        return
    await state.update_data(expected_status=int(message.text))

    data = await state.get_data()
    # Создаём объект SiteConfig
    
    new_site = SiteConfig(
        name=data["name"],
        url=data["url"],
        check_interval=data["check_interval"],
        timeout=data["timeout"],
        expected_status=data["expected_status"]
    )
    await message.bot.monitor.add_site(new_site)
    text = utils.format_site_info(new_site)
    await message.answer(f'Сайт добавлен!\n{text}',parse_mode="HTML", disable_web_page_preview=True, reply_markup=gui.site_action(new_site))