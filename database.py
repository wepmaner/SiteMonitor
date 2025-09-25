import logging
import aiomysql
import config
from datetime import datetime

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, loop):
        self.loop = loop
    async def create_pool(self):
        # создаём пул подключений к БД
        self.pool = await aiomysql.create_pool(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            db=config.db_name,
            cursorclass=aiomysql.DictCursor
        )
    async def create_tables(self):
        # создаём необходимые таблицы, если их нет
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sites (
                        id BIGINT PRIMARY KEY AUTO_INCREMENT,
                        name VARCHAR(255) NOT NULL,
                        url TEXT NOT NULL,
                        enabled TINYINT(1) NOT NULL DEFAULT 1,
                        notify_on_down TINYINT(1) NOT NULL DEFAULT 1,
                        notify_on_recovery TINYINT(1) NOT NULL DEFAULT 1,
                        check_interval INT NOT NULL DEFAULT 60,
                        timeout INT NOT NULL DEFAULT 10,
                        expected_status INT NOT NULL DEFAULT 200,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP
                    );
                    """
                )

                await cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS checks (
                        id BIGINT PRIMARY KEY AUTO_INCREMENT,
                        site_id BIGINT NOT NULL,
                        checked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        status_code INT NULL,
                        is_ok TINYINT(1) NOT NULL,
                        response_time_ms INT NULL,
                        error TEXT NULL,
                        CONSTRAINT fk_checks_site FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE
                    );
                    """
                )
                await conn.commit()

    async def update_notify_settings(self, site_name: str, notify_on_down: bool, notify_on_recovery: bool) -> bool:
        """
        Обновляет настройки уведомлений для сайта по его имени.
        Возвращает True, если обновление прошло успешно, иначе False.
        """
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE sites
                    SET notify_on_down = %s,
                        notify_on_recovery = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE name = %s
                    """,
                    (1 if notify_on_down else 0,
                     1 if notify_on_recovery else 0,
                     site_name)
                )
                await conn.commit()
                return cur.rowcount > 0 

    async def get_sites(self):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT * FROM sites")
                result = await cur.fetchall()
        return result
    
    async def add_site(self,site):
        sql = """INSERT INTO sites (name, url, enabled, check_interval, timeout, expected_status) 
                VALUES (%s, %s, %s, %s, %s, %s);"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql,(site.name, site.url, site.enabled, site.check_interval, site.timeout, site.expected_status,))
                await conn.commit()
                return cur.lastrowid
    async def delete_site_by_name(self,name):
        query = "DELETE FROM sites WHERE name = %s"
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (name,))
                await conn.commit()
                return cur.rowcount
    async def update_site(
        self, old_name: str, name: str, url: str, check_interval: int, timeout: int,expected_status: int,
        enabled: int = 1, notify_on_down: int = 1, notify_on_recovery: int = 1
    ) -> int:
        query = """
        UPDATE sites
        SET name = %s,
            url = %s,
            check_interval = %s,
            timeout = %s,
            expected_status = %s,
            enabled = %s,
            notify_on_down = %s,
            notify_on_recovery = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE name = %s
        """
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    query,
                    (name, url, check_interval, timeout, expected_status, enabled, notify_on_down, notify_on_recovery, old_name)
                )
                await conn.commit()
                return cur.rowcount
    async def get_site_id(self,name):
        query = """
        SELECT id FROM sites WHERE name = %s;
        """
        async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    try:
                        await cur.execute(query,(name,))
                        result = await cur.fetchone()
                        return result
                    except Exception as e:
                        logger.error(f"Ошибка при получении id сайта: {e}")  
                        return None
    async def add_check(self, name: str, status_code: int | None,
                    is_ok: bool, response_time_ms: float | None, error: str | None = None):
        site_id = await self.get_site_id(name)
        site_id = site_id['id']
        query = """
        INSERT INTO checks (site_id, status_code, is_ok, response_time_ms, error)
        VALUES (%s, %s, %s, %s, %s)
        """
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(query, (site_id, status_code, int(is_ok), response_time_ms, error))
                    await conn.commit()
                    logger.info(f"Добавлена запись о проверке сайта {site_id}")
                except Exception as e:
                    logger.error(f"Ошибка при добавлении записи в checks: {e}")
    
    async def get_checks_since(self, since: datetime):
        """
        Получить все проверки сайтов, начиная с указанной даты
        """
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """
                    SELECT c.id, c.site_id, s.name AS site_name, c.checked_at,
                           c.status_code, c.is_ok, c.response_time_ms, c.error
                    FROM checks c
                    JOIN sites s ON c.site_id = s.id
                    WHERE c.checked_at >= %s
                    ORDER BY c.checked_at ASC
                    """,
                    (since,)
                )
                rows = await cur.fetchall()
                return rows
