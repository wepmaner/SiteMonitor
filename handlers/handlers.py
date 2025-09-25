from datetime import datetime, timedelta
from aiogram import F, Router, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
import gui
import callbackdata as cb
import utils
import config
from aiogram.types import FSInputFile
router = Router()

@router.message(CommandStart())
async def start(message: types.Message):
    welcome_text = (
        "👋 Привет!\n\n"
        "Я бот для проверки доступности сайтов 🌐.\n"
        "Воспользуйся клавиатурой ниже, чтобы добавить сайт на проверку."
    )
    await message.answer(welcome_text,reply_markup=gui.menu())

@router.callback_query(F.data=='menu')
async def menu(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text("Главное меню",reply_markup=gui.menu())


@router.callback_query(F.data=='listsites')
async def listsites(callback_query: types.CallbackQuery):
    if len(callback_query.bot.monitor.sites) == 0:
        await callback_query.message.edit_text('Нет сайтов для мониторинга', reply_markup=gui.menu())
    else:
        await callback_query.message.edit_text('Сайты:', reply_markup=gui.sites_list(callback_query.bot.monitor.sites))


@router.callback_query(cb.SitesList.filter())
async def listsites_action(callback_query: types.CallbackQuery, callback_data: cb.SitesList):
    site = next((s for s in callback_query.bot.monitor.sites if s.name == callback_data.name), None)
    if site is None:
        await callback_query.message.edit_text('Сайт с таким именем не найден', reply_markup=gui.menu())
        return
    text = utils.format_site_info(site)
    await callback_query.message.edit_text(text, parse_mode="HTML", disable_web_page_preview=True,reply_markup=gui.site_action(site))


@router.callback_query(cb.SiteAction.filter(F.action=='delete'))
async def siteaction(callback_query: types.CallbackQuery, callback_data: cb.SiteAction):
    await callback_query.bot.monitor.delete_site(callback_data.name)
    await listsites(callback_query)

@router.callback_query(cb.SiteAction.filter(F.action=='onoff'))
async def togleonoff(callback_query: types.CallbackQuery, callback_data: cb.SiteAction):
    site = await callback_query.bot.monitor.toggle_onoff(callback_data.name)
    if site.enabled:
        enabled_text = f"Мониторинг включен\n\n"
    else:
        enabled_text = f"Мониторинг выключен\n\n"
    await callback_query.bot.monitor.update_site(site.name,site)
    enabled_text+=utils.format_site_info(site)
    await callback_query.message.edit_text(enabled_text, parse_mode="HTML", disable_web_page_preview=True,reply_markup=gui.site_action(site))

@router.callback_query(cb.SiteAction.filter(F.action=='settingsnotif'))
async def settingsnotif(callback_query: types.CallbackQuery, callback_data: cb.SiteAction):
    site = next((s for s in callback_query.bot.monitor.sites if s.name == callback_data.name), None)
    await callback_query.message.edit_text(f'Настройка уведомлений для сайта {callback_data.name}', parse_mode="HTML", disable_web_page_preview=True,reply_markup=gui.notification(site))

@router.callback_query(cb.SiteAction.filter(F.action=='notifdown'))
async def settingsnotifdown(callback_query: types.CallbackQuery, callback_data: cb.SiteAction):
    site = next((s for s in callback_query.bot.monitor.sites if s.name == callback_data.name), None)
    if site.notify_on_down:
        site.notify_on_down = False
    else:
        site.notify_on_down = True
    await callback_query.bot.monitor.update_site(site.name,site)
    await callback_query.message.edit_text(f'Настройка уведомлений для сайта {callback_data.name}', parse_mode="HTML", disable_web_page_preview=True,reply_markup=gui.notification(site))
    
@router.callback_query(cb.SiteAction.filter(F.action=='notifrecovery'))
async def notifrecovery(callback_query: types.CallbackQuery, callback_data: cb.SiteAction):
    site = next((s for s in callback_query.bot.monitor.sites if s.name == callback_data.name), None)
    if site.notify_on_recovery:
        site.notify_on_recovery = False
    else:
        site.notify_on_recovery = True
    await callback_query.bot.monitor.update_site(site.name,site)
    await callback_query.message.edit_text(f'Настройка уведомлений для сайта {callback_data.name}', parse_mode="HTML", disable_web_page_preview=True,reply_markup=gui.notification(site))
@router.callback_query(cb.SiteAction.filter(F.action=='report'))
async def notifrecovery(callback_query: types.CallbackQuery, callback_data: cb.SiteAction):
    site = next((s for s in callback_query.bot.monitor.sites if s.name == callback_data.name), None)
    await callback_query.bot.monitor.send_daily_report(site.name)

@router.callback_query(cb.SiteAction.filter(F.action=='export'))
async def notifrecovery(callback_query: types.CallbackQuery, callback_data: cb.SiteAction):
    site = next((s for s in callback_query.bot.monitor.sites if s.name == callback_data.name), None)
    file_path = await callback_query.bot.monitor.export_report_csv(site.name)
    if file_path:
        input_file = FSInputFile(file_path)
        await callback_query.bot.send_document(chat_id=config.admin_id, document=input_file)
    #await callback_query.message.edit_text(f'Настройка уведомлений для сайта {callback_data.name}', parse_mode="HTML", disable_web_page_preview=True,reply_markup=gui.notification(site))