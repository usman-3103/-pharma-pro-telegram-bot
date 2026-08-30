import logging
import os
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from config import STATS_DB_PATH, STATS_TIMEZONE

logger = logging.getLogger(__name__)

EVENT_START = "start"
EVENT_REQUEST = "request"
EVENT_OPERATOR = "operator"
VALID_EVENTS = {EVENT_START, EVENT_REQUEST, EVENT_OPERATOR}


def _db_path() -> Path:
    return Path(STATS_DB_PATH).expanduser()


def _connect() -> sqlite3.Connection:
    path = _db_path()
    if path.parent and str(path.parent) not in ("", "."):
        path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def init_stats_db() -> bool:
    """Create the small analytics database. Bot operation must not depend on it."""
    path = _db_path()
    try:
        with _connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    first_seen INTEGER NOT NULL,
                    last_seen INTEGER NOT NULL,
                    first_source TEXT NOT NULL,
                    last_source TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_type_source ON events(event_type, source)"
            )
        logger.info("Statistics database ready: %s", path)
        return True
    except Exception:
        logger.exception("Statistics database initialization failed")
        return False


def _upsert_user(connection: sqlite3.Connection, user_id: int, source: str, now: int) -> None:
    connection.execute(
        """
        INSERT INTO users (user_id, first_seen, last_seen, first_source, last_source)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            last_seen = excluded.last_seen,
            last_source = excluded.last_source
        """,
        (user_id, now, now, source, source),
    )


def record_event(user_id: int, event_type: str, source: str) -> None:
    """Record a successful user action. Failures are logged and never break the bot."""
    if event_type not in VALID_EVENTS:
        logger.warning("Unknown statistics event ignored: %s", event_type)
        return

    source = (source or "Telegram-бот").strip() or "Telegram-бот"
    now = int(time.time())
    try:
        with _connect() as connection:
            _upsert_user(connection, user_id, source, now)
            connection.execute(
                "INSERT INTO events (user_id, event_type, source, created_at) VALUES (?, ?, ?, ?)",
                (user_id, event_type, source, now),
            )
    except Exception:
        logger.exception("Failed to record statistics event: %s", event_type)


def get_last_source(user_id: int) -> str | None:
    """Restore the user's last known source after an application restart."""
    try:
        with _connect() as connection:
            row = connection.execute(
                "SELECT last_source FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return row["last_source"] if row else None
    except Exception:
        logger.exception("Failed to read last user source")
        return None


def _local_timezone() -> ZoneInfo:
    try:
        return ZoneInfo(STATS_TIMEZONE)
    except Exception:
        logger.warning("Invalid STATS_TIMEZONE=%s; using UTC", STATS_TIMEZONE)
        return ZoneInfo("UTC")


def _period_cutoff(period: str) -> int | None:
    tz = _local_timezone()
    now_local = datetime.now(tz)
    if period == "today":
        start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "7d":
        start_local = now_local - timedelta(days=7)
    elif period == "30d":
        start_local = now_local - timedelta(days=30)
    elif period == "all":
        return None
    else:
        raise ValueError(f"Unsupported stats period: {period}")
    return int(start_local.astimezone(timezone.utc).timestamp())


def _period_rows(connection: sqlite3.Connection, cutoff: int | None):
    if cutoff is None:
        query = """
            SELECT source, event_type, COUNT(DISTINCT user_id) AS users_count
            FROM events
            GROUP BY source, event_type
        """
        return connection.execute(query).fetchall()

    query = """
        SELECT source, event_type, COUNT(DISTINCT user_id) AS users_count
        FROM events
        WHERE created_at >= ?
        GROUP BY source, event_type
    """
    return connection.execute(query, (cutoff,)).fetchall()



def _display_source_name(source: str) -> str:
    """Short labels for statistics display only. Stored source values stay unchanged."""
    labels = {
        "MAX — Лекарства из Турции купить": "Лекарства · MAX",
        "MAX — Турецкая аптека": "Турецкая аптека",
        "Лекарства из Турции — Telegram": "Лекарства · TG",
    }
    return labels.get(source, source)

def _format_period(connection: sqlite3.Connection, title: str, period: str) -> list[str]:
    """Compact period view. Recording/database logic is unchanged."""
    rows = _period_rows(connection, _period_cutoff(period))
    grouped: dict[str, dict[str, int]] = {}
    for row in rows:
        grouped.setdefault(row["source"], {EVENT_START: 0, EVENT_REQUEST: 0, EVENT_OPERATOR: 0})
        grouped[row["source"]][row["event_type"]] = int(row["users_count"])

    lines = [f"\n{title}"]
    if not grouped:
        lines.append("Нет данных.")
        return lines

    # Totals are unique across all sources, so query separately instead of summing rows.
    cutoff = _period_cutoff(period)
    where = "" if cutoff is None else " WHERE created_at >= ?"
    params = () if cutoff is None else (cutoff,)
    totals = {}
    for event_type in (EVENT_START, EVENT_REQUEST, EVENT_OPERATOR):
        query = f"SELECT COUNT(DISTINCT user_id) AS n FROM events{where}" + (
            "" if where == "" else " AND event_type = ?"
        )
        if where == "":
            query += " WHERE event_type = ?"
            event_params = (event_type,)
        else:
            event_params = params + (event_type,)
        totals[event_type] = int(connection.execute(query, event_params).fetchone()["n"])

    lines.extend(
        [
            f"👥 Вошли: {totals[EVENT_START]}",
            f"📩 Отправили запрос: {totals[EVENT_REQUEST]}",
            f"💬 Связались с оператором: {totals[EVENT_OPERATOR]}",
        ]
    )

    # Entrance sources: show only the strongest sources and combine the rest.
    entrance_sources = sorted(
        ((source, values[EVENT_START]) for source, values in grouped.items() if values[EVENT_START] > 0),
        key=lambda item: (-item[1], item[0].lower()),
    )
    if entrance_sources:
        lines.append("\n📍 Откуда пришли:")
        visible = entrance_sources[:6]
        for source, count in visible:
            lines.append(f"• {_display_source_name(source)} — {count}")
        if len(entrance_sources) > 6:
            other_count = sum(count for _, count in entrance_sources[6:])
            lines.append(f"• Ещё {len(entrance_sources) - 6} источн. — {other_count}")

    request_sources = sorted(
        ((source, values[EVENT_REQUEST]) for source, values in grouped.items() if values[EVENT_REQUEST] > 0),
        key=lambda item: (-item[1], item[0].lower()),
    )
    if request_sources:
        lines.append("\n📩 Запросы по источникам:")
        for source, count in request_sources:
            lines.append(f"• {_display_source_name(source)} — {count}")

    operator_sources = sorted(
        ((source, values[EVENT_OPERATOR]) for source, values in grouped.items() if values[EVENT_OPERATOR] > 0),
        key=lambda item: (-item[1], item[0].lower()),
    )
    if operator_sources:
        lines.append("\n💬 Оператор по источникам:")
        for source, count in operator_sources:
            lines.append(f"• {_display_source_name(source)} — {count}")

    return lines



def build_stats_summary() -> str:
    """Compact admin landing screen. Recording/database logic is unchanged."""
    try:
        with _connect() as connection:
            total_users = int(connection.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"])
            today_cutoff = _period_cutoff("today")
            today_users = int(
                connection.execute(
                    "SELECT COUNT(DISTINCT user_id) AS n FROM events WHERE created_at >= ?",
                    (today_cutoff,),
                ).fetchone()["n"]
            )
            today_requests = int(
                connection.execute(
                    "SELECT COUNT(DISTINCT user_id) AS n FROM events WHERE created_at >= ? AND event_type = ?",
                    (today_cutoff, EVENT_REQUEST),
                ).fetchone()["n"]
            )
        return (
            "📊 СТАТИСТИКА PHARMA PRO\n\n"
            f"Сегодня вошли: {today_users}\n"
            f"Сегодня отправили запрос: {today_requests}\n"
            f"Всего известных пользователей: {total_users}\n\n"
            "Выберите период для подробностей:"
        )
    except Exception:
        logger.exception("Failed to build compact statistics summary")
        return (
            "⚠️ Статистика временно недоступна. "
            "Проверьте подключение постоянного хранилища Railway."
        )


def build_stats_period_report(period: str) -> str:
    """Detailed report for one selected period only."""
    titles = {
        "today": "Сегодня",
        "7d": "7 дней",
        "30d": "30 дней",
        "all": "За всё время",
    }
    if period not in titles:
        raise ValueError(f"Unsupported stats period: {period}")
    try:
        with _connect() as connection:
            lines = ["📊 СТАТИСТИКА PHARMA PRO", *(_format_period(connection, titles[period], period))]
            return "\n".join(lines)
    except Exception:
        logger.exception("Failed to build period statistics report")
        return (
            "⚠️ Статистика временно недоступна. "
            "Проверьте подключение постоянного хранилища Railway."
        )


def build_stats_report() -> str:
    """Admin report: unique users by source for today, 7 days, 30 days and all time."""
    try:
        with _connect() as connection:
            total_users = int(connection.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"])
            lines = [
                "📊 СТАТИСТИКА PHARMA PRO",
                f"Всего известных пользователей: {total_users}",
            ]
            lines.extend(_format_period(connection, "Сегодня", "today"))
            lines.extend(_format_period(connection, "7 дней", "7d"))
            lines.extend(_format_period(connection, "30 дней", "30d"))
            lines.extend(_format_period(connection, "За всё время", "all"))
            return "\n".join(lines)
    except Exception:
        logger.exception("Failed to build statistics report")
        return (
            "⚠️ Статистика временно недоступна. "
            "Проверьте подключение постоянного хранилища Railway."
        )
