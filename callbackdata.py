from aiogram.filters.callback_data import CallbackData

class SitesList(CallbackData, prefix="siteslist"):
    name: str

class SiteAction(CallbackData, prefix="SiteAction"):
    name: str
    action: str