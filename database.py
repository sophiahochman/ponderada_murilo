"""
database.py
===========
Módulo de acesso ao banco de dados SQLite para o
Sistema de Medição de Estação Meteorológica IoT.

Responsabilidades:
    - Gerenciar conexões com WAL mode e busy_timeout configurados.
    - Inicializar o banco de dados aplicando o schema.sql.
    - Prover funções CRUD completas para a tabela `leituras`.

Uso:
    from database import init_db, inserir_leitura, listar_leituras
    init_db()
"""

import sqlite3
import os
import logging
from typing import Optional

# ---------------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------------

# Caminho para o banco de dados SQLite (relativo ao diretório do projeto)
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "weather.db")

# Caminho para o arquivo de schema SQL
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

# Timeout em milissegundos para aguardar o banco ser desbloqueado (permite
# escritas simultâneas sem lançar "database is locked")
BUSY_TIMEOUT_MS = 5000

# Configura o logger do módulo
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Conexão
# ---------------------------------------------------------------------------

def get_db_connection() -> sqlite3.Connection:
    """
    Abre e retorna uma conexão com o banco de dados SQLite configurada com:
        - WAL (Write-Ahead Logging): permite leituras simultâneas a escritas,
          eliminando locks exclusivos durante INSERTs/UPDATEs.
        - busy_timeout: aguarda até BUSY_TIMEOUT_MS ms antes de lançar
          OperationalError por banco ocupado, evitando travamentos em
          ambientes de alta concorrência.
        - row_factory = sqlite3.Row: retorna linhas como objetos acessíveis
          por nome de coluna (ex: row["temperatura"]).

    Returns:
        sqlite3.Connection: Conexão ativa com o banco de dados.

    Raises:
        sqlite3.OperationalError: Se o banco não puder ser aberto.
    """
    conn = sqlite3.connect(DATABASE_PATH)

    # Configura row_factory para acesso por nome de coluna
    conn.row_factory = sqlite3.Row

    # Habilita o modo WAL para suporte a escritas simultâneas
    conn.execute("PRAGMA journal_mode=WAL;")

    # Define timeout de espera por lock (em milissegundos)
    conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS};")

    # Melhora performance: sincroniza apenas em checkpoints (seguro com WAL)
    conn.execute("PRAGMA synchronous=NORMAL;")

    return conn


# ---------------------------------------------------------------------------
# Inicialização do Banco de Dados
# ---------------------------------------------------------------------------

def init_db() -> None:
    """
    Inicializa o banco de dados aplicando o schema.sql.

    Lê o arquivo schema.sql e executa seus comandos DDL contra o banco.
    Se o banco ou as tabelas já existirem, o schema usa CREATE TABLE IF NOT EXISTS,
    garantindo que a operação seja idempotente (segura para re-execuções).

    Raises:
        FileNotFoundError: Se o arquivo schema.sql não for encontrado.
        sqlite3.DatabaseError: Em caso de erro na execução do schema.
    """
    if not os.path.exists(SCHEMA_PATH):
        raise FileNotFoundError(
            f"Arquivo de schema não encontrado: {SCHEMA_PATH}\n"
            "Certifique-se de que schema.sql está no mesmo diretório que database.py."
        )

    logger.info("Inicializando banco de dados em: %s", DATABASE_PATH)

    with get_db_connection() as conn:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)
        conn.commit()

    logger.info("Banco de dados inicializado com sucesso.")


# ---------------------------------------------------------------------------
# Funções CRUD
# ---------------------------------------------------------------------------

def inserir_leitura(
    temperatura: float,
    umidade: float,
    pressao: Optional[float] = None,
    localizacao: str = "Lab",
    timestamp: Optional[str] = None,
) -> int:
    """
    Insere uma nova leitura no banco de dados.

    Args:
        temperatura (float): Temperatura em °C (obrigatório).
        umidade     (float): Umidade relativa em % (obrigatório).
        pressao     (float, optional): Pressão em hPa. Padrão: None.
        localizacao (str, optional): Local da leitura. Padrão: 'Lab'.
        timestamp   (str, optional): ISO 8601 (ex: '2024-01-15 10:30:00').
                                     Se None, usa o horário atual do banco.

    Returns:
        int: O ID (lastrowid) da linha recém-inserida.

    Raises:
        ValueError: Se temperatura ou umidade não forem fornecidos.
        sqlite3.DatabaseError: Em caso de falha na inserção.
    """
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
    """
    Retorna uma lista paginada de leituras, ordenadas da mais recente para a mais antiga.

    Args:
        limit       (int): Número máximo de registros a retornar. Padrão: 50.
        offset      (int): Número de registros a pular (para paginação). Padrão: 0.
        localizacao (str, optional): Filtra por localização. Se None, retorna todas.

    Returns:
        list[dict]: Lista de dicionários representando cada leitura.
    """
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
    """
    Busca uma leitura específica pelo seu ID.

    Args:
        id_leitura (int): ID da leitura a ser buscada.

    Returns:
        dict: Dicionário com os dados da leitura, ou None se não encontrada.
    """
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
    """
    Atualiza campos específicos de uma leitura existente (PATCH semântico).

    Apenas os campos fornecidos (não-None) serão atualizados, preservando
    os valores atuais dos demais campos.

    Args:
        id_leitura  (int):   ID da leitura a ser atualizada.
        temperatura (float, optional): Novo valor de temperatura.
        umidade     (float, optional): Novo valor de umidade.
        pressao     (float, optional): Novo valor de pressão.
        localizacao (str,   optional): Nova localização.

    Returns:
        bool: True se a atualização afetou ao menos 1 linha, False caso contrário
              (ex: ID não encontrado).

    Raises:
        ValueError: Se nenhum campo for fornecido para atualização.
    """
    # Constrói dinamicamente apenas os campos que foram fornecidos
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
    """
    Remove uma leitura do banco de dados pelo seu ID.

    Args:
        id_leitura (int): ID da leitura a ser removida.

    Returns:
        bool: True se a remoção afetou ao menos 1 linha, False caso contrário.
    """
    query = "DELETE FROM leituras WHERE id = ?"

    with get_db_connection() as conn:
        cursor = conn.execute(query, (id_leitura,))
        conn.commit()
        afetadas = cursor.rowcount

    logger.info("Leitura id=%d removida. Linhas afetadas: %d", id_leitura, afetadas)
    return afetadas > 0


def obter_estatisticas(localizacao: Optional[str] = None) -> Optional[dict]:
    """
    Calcula estatísticas agregadas (média, mínimo, máximo) para temperatura,
    umidade e pressão.

    Args:
        localizacao (str, optional): Filtra por localização. Se None, agrega tudo.

    Returns:
        dict: Dicionário com as estatísticas, ou None se não houver dados.
    """
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
    """
    Retorna o total de leituras no banco (útil para metadados de paginação).

    Args:
        localizacao (str, optional): Filtra por localização.

    Returns:
        int: Total de registros.
    """
    if localizacao:
        query = "SELECT COUNT(*) FROM leituras WHERE localizacao = ?"
        params = (localizacao,)
    else:
        query = "SELECT COUNT(*) FROM leituras"
        params = ()

    with get_db_connection() as conn:
        count = conn.execute(query, params).fetchone()[0]

    return count
