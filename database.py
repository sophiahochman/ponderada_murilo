import sqlite3
import os
import logging
from typing import Optional

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "weather.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")
BUSY_TIMEOUT_MS = 5000

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def get_db_connection() -> sqlite3.Connection:
    
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS};")
    conn.execute("PRAGMA synchronous=NORMAL;")

    return conn


def init_db() -> None:
    
    if not os.path.exists(SCHEMA_PATH):
        raise FileNotFoundError(
            f"Arquivo de schema não encontrado: {SCHEMA_PATH}\n"
        )

    logger.info("Inicializando banco de dados em: %s", DATABASE_PATH)

    with get_db_connection() as conn:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)
        conn.commit()

    logger.info("Banco de dados inicializado com sucesso.")


def inserir_leitura(
    temperatura: float,
    umidade: float,
    pressao: Optional[float] = None,
    localizacao: str = "Lab",
    timestamp: Optional[str] = None,
) -> int:
    
    query = """
        INSERT INTO leituras (temperatura, umidade, pressao, localizacao, timestamp)
        VALUES (?, ?, ?, ?, COALESCE(?, datetime('now', 'localtime')))
    """
    params = (temperatura, umidade, pressao, localizacao, timestamp)

    with get_db_connection() as conn:
        cursor = conn.execute(query, params)
        conn.commit()
        novo_id = cursor.lastrowid

    logger.info(
        "Leitura inserida | id=%d | temp=%.1f°C | umid=%.1f%% | loc=%s",
        novo_id, temperatura, umidade, localizacao
    )
    return novo_id


def listar_leituras(
    limit: int = 50,
    offset: int = 0,
    localizacao: Optional[str] = None,
) -> list[dict]:

    if localizacao:
        query = """
            SELECT * FROM leituras
            WHERE localizacao = ?
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """
        params = (localizacao, limit, offset)
    else:
        query = """
            SELECT * FROM leituras
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """
        params = (limit, offset)

    with get_db_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    return [dict(row) for row in rows]


def buscar_leitura(id_leitura: int) -> Optional[dict]:
    
    query = "SELECT * FROM leituras WHERE id = ?"

    with get_db_connection() as conn:
        row = conn.execute(query, (id_leitura,)).fetchone()

    return dict(row) if row else None


def atualizar_leitura(
    id_leitura: int,
    temperatura: Optional[float] = None,
    umidade: Optional[float] = None,
    pressao: Optional[float] = None,
    localizacao: Optional[str] = None,
) -> bool:
   
    campos = []
    valores = []

    if temperatura is not None:
        campos.append("temperatura = ?")
        valores.append(temperatura)
    if umidade is not None:
        campos.append("umidade = ?")
        valores.append(umidade)
    if pressao is not None:
        campos.append("pressao = ?")
        valores.append(pressao)
    if localizacao is not None:
        campos.append("localizacao = ?")
        valores.append(localizacao)

    if not campos:
        raise ValueError("Nenhum campo fornecido para atualização.")

    valores.append(id_leitura)
    query = f"UPDATE leituras SET {', '.join(campos)} WHERE id = ?"

    with get_db_connection() as conn:
        cursor = conn.execute(query, valores)
        conn.commit()
        afetadas = cursor.rowcount

    logger.info("Leitura id=%d atualizada. Linhas afetadas: %d", id_leitura, afetadas)
    return afetadas > 0


def deletar_leitura(id_leitura: int) -> bool:
    
    query = "DELETE FROM leituras WHERE id = ?"

    with get_db_connection() as conn:
        cursor = conn.execute(query, (id_leitura,))
        conn.commit()
        afetadas = cursor.rowcount

    logger.info("Leitura id=%d removida. Linhas afetadas: %d", id_leitura, afetadas)
    return afetadas > 0


def obter_estatisticas(localizacao: Optional[str] = None) -> Optional[dict]:
    
    if localizacao:
        query = """
            SELECT
                COUNT(*)            AS total_leituras,
                ROUND(AVG(temperatura), 2) AS temp_media,
                ROUND(MIN(temperatura), 2) AS temp_min,
                ROUND(MAX(temperatura), 2) AS temp_max,
                ROUND(AVG(umidade), 2)     AS umid_media,
                ROUND(MIN(umidade), 2)     AS umid_min,
                ROUND(MAX(umidade), 2)     AS umid_max,
                ROUND(AVG(pressao), 2)     AS pressao_media,
                ROUND(MIN(pressao), 2)     AS pressao_min,
                ROUND(MAX(pressao), 2)     AS pressao_max,
                MIN(timestamp)             AS periodo_inicio,
                MAX(timestamp)             AS periodo_fim
            FROM leituras
            WHERE localizacao = ?
        """
        params = (localizacao,)
    else:
        query = """
            SELECT
                COUNT(*)            AS total_leituras,
                ROUND(AVG(temperatura), 2) AS temp_media,
                ROUND(MIN(temperatura), 2) AS temp_min,
                ROUND(MAX(temperatura), 2) AS temp_max,
                ROUND(AVG(umidade), 2)     AS umid_media,
                ROUND(MIN(umidade), 2)     AS umid_min,
                ROUND(MAX(umidade), 2)     AS umid_max,
                ROUND(AVG(pressao), 2)     AS pressao_media,
                ROUND(MIN(pressao), 2)     AS pressao_min,
                ROUND(MAX(pressao), 2)     AS pressao_max,
                MIN(timestamp)             AS periodo_inicio,
                MAX(timestamp)             AS periodo_fim
            FROM leituras
        """
        params = ()

    with get_db_connection() as conn:
        row = conn.execute(query, params).fetchone()

    if row and row["total_leituras"] == 0:
        return None

    return dict(row) if row else None


def contar_leituras(localizacao: Optional[str] = None) -> int:
    
    if localizacao:
        query = "SELECT COUNT(*) FROM leituras WHERE localizacao = ?"
        params = (localizacao,)
    else:
        query = "SELECT COUNT(*) FROM leituras"
        params = ()

    with get_db_connection() as conn:
        count = conn.execute(query, params).fetchone()[0]

    return count
