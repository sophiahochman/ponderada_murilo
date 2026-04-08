-- =============================================================================
-- schema.sql
-- Esquema do Banco de Dados - Sistema de Medição de Estação Meteorológica IoT
-- =============================================================================
-- Este arquivo define a estrutura da tabela principal de leituras.
-- Execute via: sqlite3 weather.db < schema.sql
-- Ou deixe que database.py::init_db() gerencie isso automaticamente.
-- =============================================================================

-- Tabela principal de leituras dos sensores
-- NOTA: Não usamos DROP TABLE aqui para preservar dados em reinicializações.
CREATE TABLE IF NOT EXISTS leituras (
    -- Chave primária auto-incrementada
    id          INTEGER  PRIMARY KEY AUTOINCREMENT,

    -- Temperatura em graus Celsius (obrigatório)
    temperatura REAL     NOT NULL,

    -- Umidade relativa do ar em % (obrigatório)
    umidade     REAL     NOT NULL,

    -- Pressão atmosférica em hPa (opcional, pode ser NULL)
    pressao     REAL,

    -- Local de origem da leitura (padrão: 'Lab')
    localizacao TEXT     DEFAULT 'Lab',

    -- Timestamp ISO 8601 da leitura (gerado automaticamente se omitido)
    timestamp   DATETIME DEFAULT (datetime('now', 'localtime'))
);

-- Índice para otimização de queries por timestamp (ex: range queries, ordenação)
CREATE INDEX IF NOT EXISTS idx_leituras_timestamp
    ON leituras (timestamp DESC);

-- Índice para filtros por localização
CREATE INDEX IF NOT EXISTS idx_leituras_localizacao
    ON leituras (localizacao);
