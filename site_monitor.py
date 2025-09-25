import asyncio
import aiohttp
import logging
from aiogram.types import FSInputFile
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from aiogram import Bot
from time import perf_counter
from database import Database
import config
import matplotlib.pyplot as plt
import csv
logger = logging.getLogger(__name__)


@dataclass
class SiteConfig:
    """Конфигурация сайта для мониторинга"""
    url: str
    name: str
    check_interval: int  # интервал в секундах
    timeout: int = 10
    expected_status: int = 200
    enabled: bool = True
    last_check: Optional[datetime] = None
    last_status: Optional[bool] = None
    notify_on_down: bool = 1
    notify_on_recovery: bool = 1
    last_response_time_ms: Optional[float] = None
    consecutive_failures: int = 0
    notify_on_failure: bool = True

class SiteMonitor:
    def __init__(self, bot:Bot, db:Database) -> None:
        self.bot = bot
        self.db = db
        self.sites: List[SiteConfig] = []
        self.running = False
        self.site_tasks: dict[str, asyncio.Task] = {}
    async def check_site_availability(self, site: SiteConfig) -> None:
        """Выполняет проверку сайта"""
        while self.running and site.enabled:
            timeout = aiohttp.ClientTimeout(total=site.timeout)
            start_time = perf_counter()
            status_ok = False
            response_status = None
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(site.url) as response:
                        response_status = response.status
            except asyncio.TimeoutError:
                logger.warning(f"{site.name} timeout после {site.timeout}s")
            except aiohttp.ClientError as e:
                logger.warning(f"{site.name} ошибка соединения: {e}")
            except Exception as e:
                logger.error(f"{site.name} непредвиденная ошибка: {e}")
            finally:
                elapsed_ms = (perf_counter() - start_time) * 1000.0
                site.last_response_time_ms = elapsed_ms
                site.last_check = datetime.now()
                if response_status is not None and response_status == site.expected_status:
                    status_ok = True

                site.last_status = status_ok
                if status_ok:
                    if site.consecutive_failures >= 3:
                        if site.notify_on_recovery:
                            await self.bot.send_message(config.admin_id,f"{site.name} восстановлен, ответ {response_status}, {elapsed_ms:.0f} ms")
                        logger.info(f"{site.name} восстановлен, ответ {response_status}, {elapsed_ms:.0f} ms")
                    else:
                        logger.debug(f"{site.name} OK, ответ {response_status}, {elapsed_ms:.0f} ms")
                    site.consecutive_failures = 0
                    await self.db.add_check(site.name,response_status,True,elapsed_ms)
                else:
                    site.consecutive_failures += 1
                    

                    status_info = response_status if response_status is not None else 'нет ответа'
                    logger.warning(
                        f"{site.name} сбой #{site.consecutive_failures},  статус {status_info}, {elapsed_ms:.0f} ms"
                    )
                    if site.consecutive_failures == 3 and site.notify_on_down:
                        await self.bot.send_message(config.admin_id,f"{site.name} сбой, статус {status_info}, {elapsed_ms:.0f} ms")
                    if status_info == 'нет ответа':
                        status_info = None
                    await self.db.add_check(site.name,status_info,False,elapsed_ms)
            await asyncio.sleep(site.check_interval)
    async def load_sites(self) -> List[SiteConfig]:
        sites_db = await self.db.get_sites()
        sites = [SiteConfig(site["url"], site["name"], site["check_interval"], site["timeout"], site["expected_status"], site["enabled"]) for site in sites_db]
        self.sites = sites
        return self.sites
    async def add_site(self, site):
        await self.db.add_site(site)
        self.sites.append(site)
        self._start_site_task(site)
    async def delete_site(self,name):
        deleted = await self.db.delete_site_by_name(name)
        if deleted:
            self.sites = [s for s in self.sites if s.name != name]
            self._stop_site_task(name)
    
                    
    async def update_site(self, site_name:str, updated_site: SiteConfig):
        """
        Обновляет сайт в self.sites и в БД
        """
        for i, site in enumerate(self.sites):
            if site.name == updated_site.name:
                # Обновляем локально
                self.sites[i] = updated_site

                # Перезапускаем таск
                self._stop_site_task(site.name)
                if updated_site.enabled:
                    self._start_site_task(updated_site)

                # Обновляем в БД
                await self.db.update_site(
                    old_name=site_name,
                    name=updated_site.name,
                    url=updated_site.url,

                    check_interval=updated_site.check_interval,
                    timeout=updated_site.timeout,
                    expected_status=updated_site.expected_status,
                    enabled=int(updated_site.enabled),
                    notify_on_down = int(updated_site.notify_on_down),
                    notify_on_recovery = int(updated_site.notify_on_recovery)
                )
                break
    async def toggle_onoff(self, site_name):
        site = next((s for s in self.sites if s.name == site_name), None)
        if site and site.enabled:
            site.enabled = False
            self._stop_site_task(site_name)
        elif site and not site.enabled:
            site.enabled = True
            self._start_site_task(site)
        return site
        
    async def run_monitoring(self):
        self.running = True
        await self.load_sites()
        # Запускаем таски для включённых сайтов
        for site in self.sites:
            if site.enabled:
                self._start_site_task(site)

    def _start_site_task(self, site):
        if site.name in self.site_tasks:
            return
        task = asyncio.create_task(self.check_site_availability(site))
        self.site_tasks[site.name] = task

    def _stop_site_task(self, name):
        task = self.site_tasks.pop(name, None)
        if task:
            task.cancel()
    async def create_report(self, site_name: str, days: int = 7):
        """
        Генерация отчёта по сайту за указанное количество дней.
        """
        site = next((s for s in self.sites if s.name == site_name), None)
        if not site:
            return "❌ Сайт не найден."

        since = datetime.now() - timedelta(days=days)
        checks = await self.db.get_checks_since(since)
        checks = [c for c in await self.db.get_checks_since(since) if c["site_name"] == site.name]
        if not checks:
            return f"⚠️ Нет данных мониторинга за последние {days} дней."

        total = len(checks)
        ok = sum(1 for c in checks if c["is_ok"])
        fail = total - ok
        uptime = (ok / total) * 100 if total else 0
        avg_response = sum(c["response_time_ms"] for c in checks if c["response_time_ms"]) / ok if ok else 0

        report_text = f"📊 Отчёт о сайте <b>{site.name}</b>\n"
        report_text += f"Период: {since.strftime('%d.%m.%Y')} — {datetime.now().strftime('%d.%m.%Y')}\n\n"
        report_text += f"✅ Доступен: {ok} раз\n"
        report_text += f"❌ Недоступен: {fail} раз\n"
        report_text += f"📈 Uptime: {uptime:.2f}%\n"
        report_text += f"⏱ Среднее время отклика: {avg_response:.0f} ms\n"

        return report_text

    async def send_weekly_report(self):
        """
        Отправка еженедельного отчёта.
        """
        report_text = "📊 Еженедельный отчёт о мониторинге сайтов\n\n"
        for site in self.sites:
            site_report = await self.create_report(site.name, days=7)
            report_text += site_report + "\n\n"

            #await self.bot.send_message(config.admin_id, report_text, parse_mode="HTML")
            file = await self.plot_response_time(name=site.name)
            photo = FSInputFile(file)
            await self.bot.send_photo(chat_id=config.admin_id, photo=photo,caption=report_text)

    async def send_daily_report(self,name):
        """
        Отправка ежедневного отчёта.
        """
        site = next((s for s in self.sites if s.name == name), None)
        site_report = await self.create_report(site.name, days=1)
        report_text = site_report + "\n\n"
        file = await self.plot_response_time(name=site.name)
        photo = FSInputFile(file)  
        return photo, report_text
       
        #await self.bot.send_message(config.admin_id, report_text, parse_mode="HTML")

    async def weekly_report_task(self):
        """ 
        Запускается каждую неделю в понедельник 10:00.
        """
        while True:
            now = datetime.now()
            days_until_monday = (7 - now.weekday()) % 7
            next_monday = now + timedelta(days=days_until_monday)
            next_run = next_monday.replace(hour=10, minute=0, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=7)

            await asyncio.sleep((next_run - now).total_seconds())
            try:
                await self.send_weekly_report()
            except Exception as e:
                print(f"Ошибка при отправке еженедельного отчета: {e}")

    async def plot_response_time(self, name: str, days: int = 7):
        """
        Строим график времени отклика сайта за последнюю неделю.
        """
        since = datetime.now() - timedelta(days=days)
        checks = await self.db.get_checks_since(since)

        # Фильтруем только по конкретному сайту
        site_checks = [c for c in checks if c["site_name"] == name]

        if not site_checks:
            print("Нет данных для графика")
            return None

        # Подготовка данных
        times = [c["checked_at"] for c in site_checks]
        response_times = [c["response_time_ms"] or 0 for c in site_checks]
        site_name = site_checks[0]["site_name"]

        # Рисуем график
        plt.figure(figsize=(10, 5))
        plt.plot(times, response_times, marker="o", linestyle="-", label="Response time (ms)")
        plt.title(f"Время отклика сайта {site_name} за последнюю неделю")
        plt.xlabel("Дата")
        plt.ylabel("Время отклика (мс)")
        plt.xticks(rotation=45)
        plt.grid(True)
        plt.legend()

        filename = f"response_time_{name}.png"
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()

        return filename
    async def export_report_csv(self, site_name: str, days: int = 7, file_path: str = None):
        """
        Экспорт отчета по сайту за указанное количество дней в CSV.
        """
        site = next((s for s in self.sites if s.name == site_name), None)
        if not site:
            return None

        since = datetime.now() - timedelta(days=days)
        checks = await self.db.get_checks_since(since=since)
        checks = [c for c in checks if c["site_name"] == site_name]
        if not checks:
            return None

        if not file_path:
            file_path = f"{site.name}_{since.strftime('%Y%m%d')}_{datetime.now().strftime('%Y%m%d')}.csv"

        with open(file_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # Заголовки
            writer.writerow(["Дата и время", "Статус код", "Доступен", "Время отклика (ms)", "Ошибка"])
            # Данные
            for c in checks:
                writer.writerow([
                    c["checked_at"].strftime("%Y-%m-%d %H:%M:%S") if c["checked_at"] else "",
                    c.get("status_code", ""),
                    1 if c.get("is_ok") else 0,
                    c.get("response_time_ms", ""),
                    c.get("error", "")
                ])
        return file_path

