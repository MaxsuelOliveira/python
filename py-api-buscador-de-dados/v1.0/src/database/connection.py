# connection.py
import sqlite3
import os
from contextlib import contextmanager
from typing import Any, Iterable, List, Tuple, Optional

class SQLiteConnection:
    """
    Classe segura e encapsulada para conexão com SQLite3
    """

    def __init__(self, db_path: Optional[str] = None):
        # Usa variavel de ambiente se existir; senao grava o banco dentro da pasta "data"
        self._db_path = db_path or os.getenv("SQLITE_DB_PATH", "data/db.sqlite3")

    def _connect(self) -> sqlite3.Connection:
        """
        Cria conexão com configurações seguras
        """
        conn = sqlite3.connect(
            self._db_path,
            timeout=10,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        self._apply_pragmas(conn)
        return conn

    @staticmethod
    def _apply_pragmas(conn: sqlite3.Connection) -> None:
        """
        PRAGMAs de segurança e performance
        """
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("PRAGMA journal_mode = WAL;")
        cursor.execute("PRAGMA synchronous = NORMAL;")
        cursor.close()

    @contextmanager
    def connection(self):
        """
        Context manager para garantir fechamento seguro
        """
        conn = None
        try:
            conn = self._connect()
            yield conn
            conn.commit()
        except sqlite3.Error:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def execute(
        self,
        query: str,
        params: Tuple[Any, ...] = ()
    ) -> int:
        """
        Executa INSERT, UPDATE, DELETE
        Retorna número de linhas afetadas
        """
        with self.connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.rowcount

    def fetch_one(
        self,
        query: str,
        params: Tuple[Any, ...] = ()
    ) -> Optional[sqlite3.Row]:
        """
        Retorna um único registro
        """
        with self.connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchone()

    def fetch_all(
        self,
        query: str,
        params: Tuple[Any, ...] = ()
    ) -> List[sqlite3.Row]:
        """
        Retorna múltiplos registros
        """
        with self.connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchall()
