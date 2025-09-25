from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup, InlineKeyboardButton
from callbackdata import SitesList, SiteAction
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def menu():
    kb = InlineKeyboardBuilder()
    kb.button(
        text='➕ Добавить сайт',
        callback_data='addsite')
    kb.button(
        text='📋 Список сайтов',
        callback_data='listsites')
    # kb.button(
    #     text='🗑️ Удаление сайта',
    #     callback_data='delsite')
    
    kb.adjust(2)
    return kb.as_markup()

def sites_list(sites):
    kb = InlineKeyboardBuilder()
    for site in sites:
        enabled = "🟢" if site.enabled else "🔴"
        kb.button(
        text= f"{enabled} {site.name}",
        callback_data=SitesList(name=site.name))
    kb.adjust(2)
    return kb.as_markup()

def site_action(site):
    if site.enabled:
        enable_button = InlineKeyboardButton(text="🔴 Отключить мониторинг", callback_data=SiteAction(name=site.name, action="onoff").pack())
    else:
        enable_button = InlineKeyboardButton(text="🟢 Включить мониторинг", callback_data=SiteAction(name=site.name, action="onoff").pack())
    return InlineKeyboardMarkup(inline_keyboard=[
        [enable_button,InlineKeyboardButton(text="🔔 Настройка уведомлений", callback_data=SiteAction(name=site.name, action="settingsnotif").pack())],
        [InlineKeyboardButton(text="📊 Получить отчет", callback_data=SiteAction(name=site.name, action="report").pack()),InlineKeyboardButton(text="📊 Экспорт отчета", callback_data=SiteAction(name=site.name, action="export").pack())],
        [InlineKeyboardButton(text="⚙️ Редактировать", callback_data=SiteAction(name=site.name, action="edit").pack()),
         InlineKeyboardButton(text="🗑️ Удалить сайт", callback_data=SiteAction(name=site.name, action="delete").pack())],
        [InlineKeyboardButton(text="🏠 Главная", callback_data="menu")]
        
    ])

def notification(site):
    kb = InlineKeyboardBuilder()
    if site.notify_on_down:
        down_text = "🟢 Уведомление о падении"
    else:
        down_text = "🔴 Уведомление о падении"
    if site.notify_on_recovery:
        up_text = "🟢 Уведомление о восстановлении"
    else:
        up_text = "🔴 Уведомление о восстановлении"
    kb.button(
        text = down_text,
        callback_data=SiteAction(name=site.name,action="notifdown"))
    kb.button(
        text= up_text,
        callback_data=SiteAction(name=site.name,action="notifrecovery"))
    kb.button(
        text= 'Назад',
        callback_data=SitesList(name=site.name))
    kb.adjust(2)
    return kb.as_markup()


def skip_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏭️ Пропустить")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )