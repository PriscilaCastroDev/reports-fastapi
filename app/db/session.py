from collections.abc import Generator

import clickhouse_connect
from clickhouse_connect.driver.client import Client

from app.config import settings


def _make_client() -> Client:
    return clickhouse_connect.get_client(
        host=settings.db_host,
        port=settings.db_port,
        username=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        query_limit=0,           # sin límite de filas impuesto por el cliente
        connect_timeout=10,      # segundos para establecer conexión
        send_receive_timeout=120, # segundos máximo para recibir la respuesta
    )


def get_db() -> Generator[Client, None, None]:
    client = _make_client()
    try:
        yield client
    finally:
        client.close()


def check_connection() -> bool:
    try:
        _make_client().command("SELECT 1")
        return True
    except Exception:
        return False
