def format_site_info(site) -> str:
    """Форматирует информацию о сайте для отправки пользователю."""
    status_emoji = "🟢" if site.last_status else "🔴" if site.last_status is not None else "⚪"
    enabled_emoji = "✅" if site.enabled else "❌"
    last_check_str = site.last_check.strftime("%Y-%m-%d %H:%M:%S") if site.last_check else "–"
    response_time_str = f"{site.last_response_time_ms:.0f} ms" if site.last_response_time_ms is not None else "–"

    text = (
        f"🔹 <b>{site.name}</b>\n"
        f"🌐 URL: {site.url}\n"
        f"⏱ Интервал проверки: {site.check_interval} сек\n"
        f"⏳ Таймаут: {site.timeout} сек\n"
        f"✅ Ожидаемый статус: {site.expected_status}\n"
        f"🟢 Статус: {status_emoji}\n"
        f"🟢 Включен: {enabled_emoji}\n"
        f"🕒 Последняя проверка: {last_check_str}\n"
        f"⚡ Время ответа: {response_time_str}\n"
        f"❗ Сбои подряд: {site.consecutive_failures}\n"
    )
    return text