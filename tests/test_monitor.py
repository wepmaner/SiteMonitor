# tests/test_monitor.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

from site_monitor import SiteMonitor, SiteConfig
from database import Database

# ----------------------------
# Асинхронные фикстуры через pytest_asyncio
# ----------------------------
import pytest_asyncio

@pytest_asyncio.fixture
async def db():
    test_db = Database(asyncio.get_running_loop())
    await test_db.create_pool()
    await test_db.create_tables()
    yield test_db
    test_db.pool.close()
    await test_db.pool.wait_closed()

@pytest_asyncio.fixture
async def monitor(db):
    mock_bot = AsyncMock()
    site_monitor = SiteMonitor(bot=mock_bot, db=db)
    yield site_monitor

# ----------------------------
# Тест 1: добавление сайта
# ----------------------------
@pytest.mark.asyncio
async def test_add_site(monitor):
    site = SiteConfig(name="TestSite", url="https://example.com", check_interval=60)
    await monitor.add_site(site)
    assert site in monitor.sites
    await monitor.delete_site(site.name)

# ----------------------------
# Тест 2: удаление сайта
# ----------------------------
@pytest.mark.asyncio
async def test_delete_site(monitor):
    site = SiteConfig(name="DeleteSite", url="https://example.com", check_interval=60)
    await monitor.add_site(site)
    await monitor.delete_site(site.name)
    assert all(s.name != site.name for s in monitor.sites)

# ----------------------------

# ----------------------------
# Тест 3: несуществующий сайт
# ----------------------------
@pytest.mark.asyncio
async def test_create_report_invalid_site(monitor):
    report = await monitor.create_report("NonExistentSite")
    assert report == "❌ Сайт не найден."

# ----------------------------
# Тест 5: проверка таймаута
# ----------------------------
@pytest.mark.asyncio
async def test_check_site_availability_timeout(monitor):
    site = SiteConfig(name="TimeoutSite", url="http://10.255.255.1", check_interval=1, timeout=1)
    await monitor.add_site(site)

    task = asyncio.create_task(monitor.check_site_availability(site))
    await asyncio.sleep(2)
    task.cancel()

    assert site.last_status is None
