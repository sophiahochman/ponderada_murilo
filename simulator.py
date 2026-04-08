"""
simulator.py
============
Simulador de Dados IoT - Estação Meteorológica
===============================================
Substitui o serial_reader.py (sem hardware físico Arduino).

Possui dois modos de operação:

    Modo 1 - Seed Inicial  (--seed ou --seed --count N):
        Popula o banco com N leituras retroativas com timestamps
        distribuídos nas últimas 48 horas. Útil para pré-carregar
        dados históricos realistas para demonstração.

    Modo 2 - Loop Contínuo (padrão, sem argumentos):
        Entra em loop infinito, gerando uma leitura nova a cada
        INTERVALO_SEGUNDOS e fazendo POST para a API Flask.

Uso:
    # Seed com 30 leituras (padrão):
    python simulator.py --seed

    # Seed com quantidade personalizada:
    python simulator.py --seed --count 100

    # Loop contínuo (envia a cada 5 segundos):
    python simulator.py

    # Loop contínuo com seed inicial automático:
    python simulator.py --seed --loop
"""

import argparse
import logging
import random
import sys
import time
from datetime import datetime, timedelta

import requests

# ---------------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------------

# URL base da API Flask (deve estar rodando)
API_BASE_URL = "http://localhost:5000"
ENDPOINT_LEITURAS = f"{API_BASE_URL}/leituras"

# Intervalo entre leituras no loop contínuo (segundos)
INTERVALO_SEGUNDOS = 5

# Quantidade padrão de leituras para o seed inicial
SEED_DEFAULT_COUNT = 30

# Janela retroativa para distribuir os timestamps do seed (em horas)
SEED_RETROATIVO_HORAS = 48

# ---------------------------------------------------------------------------
# Configuração do Logger
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Geração de Dados Realistas
# ---------------------------------------------------------------------------

# Localizações disponíveis para simular sensores em diferentes pontos
LOCALIZACOES = ["Lab", "Externo", "Sala de Servidores", "Corredor"]


def gerar_leitura_realista(timestamp: str = None, localizacao: str = None) -> dict:
    """
    Gera um dicionário com dados meteorológicos realistas e aleatórios,
    simulando sensores reais com variações suaves.

    Faixas baseadas em ambientes internos/externos típicos:
        - Temperatura: 15°C – 35°C  (com variação suave)
        - Umidade:     40%  – 80%   (umidade relativa do ar)
        - Pressão:     1000 – 1025 hPa (pressão atmosférica ao nível do mar)

    Args:
        timestamp   (str, optional): ISO 8601. Se None, usa horário atual.
        localizacao (str, optional): Local do sensor. Se None, escolhe aleatoriamente.

    Returns:
        dict: Payload pronto para enviar via POST para a API.
    """
    # Temperatura com suavização gaussiana para parecer mais realista
    temperatura = round(random.gauss(mu=25.0, sigma=4.5), 2)
    temperatura = max(15.0, min(35.0, temperatura))  # Clipa no range permitido

    # Umidade com distribuição normal centrada em 60%
    umidade = round(random.gauss(mu=60.0, sigma=10.0), 2)
    umidade = max(40.0, min(80.0, umidade))

    # Pressão com pequenas variações ao redor de 1013 hPa (padrão)
    pressao = round(random.gauss(mu=1013.0, sigma=5.0), 2)
    pressao = max(1000.0, min(1025.0, pressao))

    if localizacao is None:
        localizacao = random.choice(LOCALIZACOES)

    payload = {
        "temperatura": temperatura,
        "umidade":     umidade,
        "pressao":     pressao,
        "localizacao": localizacao,
    }

    if timestamp is not None:
        payload["timestamp"] = timestamp

    return payload


# ---------------------------------------------------------------------------
# Comunicação com a API
# ---------------------------------------------------------------------------

def enviar_leitura(payload: dict, tentativas: int = 3) -> bool:
    """
    Envia uma leitura para a API via HTTP POST com retry automático.

    Args:
        payload   (dict): Dados da leitura (temperatura, umidade, etc.).
        tentativas (int): Número máximo de tentativas em caso de falha de rede.

    Returns:
        bool: True se a leitura foi inserida com sucesso (HTTP 201), False caso contrário.
    """
    headers = {"Content-Type": "application/json"}

    for tentativa in range(1, tentativas + 1):
        try:
            response = requests.post(
                ENDPOINT_LEITURAS,
                json=payload,
                headers=headers,
                timeout=10,  # Timeout de 10s para não travar em caso de API fora do ar
            )

            if response.status_code == 201:
                dados = response.json()
                logger.info(
                    "✅ Leitura enviada | id=%-4d | temp=%.1f°C | umid=%.1f%% | "
                    "pressao=%.1f hPa | local=%s | ts=%s",
                    dados.get("id", "?"),
                    payload["temperatura"],
                    payload["umidade"],
                    payload.get("pressao", 0.0),
                    payload.get("localizacao", "?"),
                    payload.get("timestamp", "agora"),
                )
                return True
            else:
                logger.warning(
                    "⚠️  API retornou status %d (tentativa %d/%d): %s",
                    response.status_code, tentativa, tentativas, response.text[:200]
                )

        except requests.exceptions.ConnectionError:
            logger.error(
                "❌ Falha de conexão com a API em %s (tentativa %d/%d). "
                "Aguarde: a API está rodando?",
                ENDPOINT_LEITURAS, tentativa, tentativas
            )
        except requests.exceptions.Timeout:
            logger.error(
                "⏱️  Timeout ao conectar com a API (tentativa %d/%d).",
                tentativa, tentativas
            )
        except requests.exceptions.RequestException as e:
            logger.error("❌ Erro inesperado na requisição (tentativa %d/%d): %s", tentativa, tentativas, e)

        # Aguarda antes de tentar novamente (backoff progressivo)
        if tentativa < tentativas:
            espera = tentativa * 2
            logger.info("   Aguardando %ds antes da próxima tentativa...", espera)
            time.sleep(espera)

    return False


# ---------------------------------------------------------------------------
# Modo 1: Seed Inicial
# ---------------------------------------------------------------------------

def executar_seed(count: int = SEED_DEFAULT_COUNT) -> None:
    """
    Popula o banco de dados com `count` leituras retroativas, distribuídas
    uniformemente nas últimas SEED_RETROATIVO_HORAS horas.

    Args:
        count (int): Número de leituras a inserir (padrão: 30).
    """
    logger.info("=" * 60)
    logger.info("🌱 MODO SEED INICIAL")
    logger.info("   Inserindo %d leituras retroativas...", count)
    logger.info("   Período: últimas %dh", SEED_RETROATIVO_HORAS)
    logger.info("=" * 60)

    agora = datetime.now()
    sucesso = 0
    falha = 0

    # Gera timestamps distribuídos uniformemente no período retroativo
    timestamps = sorted([
        agora - timedelta(
            seconds=random.uniform(0, SEED_RETROATIVO_HORAS * 3600)
        )
        for _ in range(count)
    ])  # Ordena cronologicamente para inserção lógica

    for i, ts in enumerate(timestamps, start=1):
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
        payload = gerar_leitura_realista(timestamp=ts_str)

        logger.info("[%02d/%02d] Enviando leitura para %s...", i, count, ts_str)

        if enviar_leitura(payload):
            sucesso += 1
        else:
            falha += 1

        # Pequena pausa entre requisições para não sobrecarregar a API
        time.sleep(0.3)

    logger.info("=" * 60)
    logger.info("🌱 SEED concluído: %d sucesso(s), %d falha(s).", sucesso, falha)
    logger.info("=" * 60)


# ---------------------------------------------------------------------------
# Modo 2: Loop Contínuo
# ---------------------------------------------------------------------------

def executar_loop() -> None:
    """
    Entra em loop infinito, gerando e enviando uma nova leitura aleatória
    a cada INTERVALO_SEGUNDOS segundos.

    O loop pode ser interrompido com Ctrl+C (KeyboardInterrupt).
    """
    logger.info("=" * 60)
    logger.info("🔄 MODO LOOP CONTÍNUO")
    logger.info("   Intervalo: %ds | Endpoint: %s", INTERVALO_SEGUNDOS, ENDPOINT_LEITURAS)
    logger.info("   Pressione Ctrl+C para interromper.")
    logger.info("=" * 60)

    contador = 0
    erros_consecutivos = 0
    MAX_ERROS_CONSECUTIVOS = 10  # Para o loop após muitas falhas seguidas

    try:
        while True:
            contador += 1
            payload = gerar_leitura_realista()

            logger.info("─" * 50)
            logger.info("📡 Leitura #%d | Gerando e enviando...", contador)

            if enviar_leitura(payload):
                erros_consecutivos = 0
            else:
                erros_consecutivos += 1
                logger.warning(
                    "⚠️  %d erro(s) consecutivo(s). Max: %d.",
                    erros_consecutivos, MAX_ERROS_CONSECUTIVOS
                )

            if erros_consecutivos >= MAX_ERROS_CONSECUTIVOS:
                logger.error(
                    "🛑 Muitos erros consecutivos (%d). Encerrando o loop.",
                    MAX_ERROS_CONSECUTIVOS
                )
                sys.exit(1)

            logger.info("💤 Aguardando %ds para a próxima leitura...", INTERVALO_SEGUNDOS)
            time.sleep(INTERVALO_SEGUNDOS)

    except KeyboardInterrupt:
        logger.info("\n🛑 Loop interrompido pelo usuário (Ctrl+C). Total enviado: %d", contador - 1)
        sys.exit(0)


# ---------------------------------------------------------------------------
# Ponto de entrada + Parsing de Argumentos
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Configura e retorna os argumentos de linha de comando."""
    parser = argparse.ArgumentParser(
        description="Simulador de Dados IoT - Estação Meteorológica",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python simulator.py                    # Loop contínuo (a cada 5s)
  python simulator.py --seed             # Seed com 30 leituras retroativas
  python simulator.py --seed --count 100 # Seed com 100 leituras
  python simulator.py --seed --loop      # Seed + Loop contínuo em sequência
        """,
    )

    parser.add_argument(
        "--seed",
        action="store_true",
        help="Executa o seed inicial (popula o banco com leituras retroativas).",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=SEED_DEFAULT_COUNT,
        metavar="N",
        help=f"Número de leituras para o seed (padrão: {SEED_DEFAULT_COUNT}).",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Após o seed, continua em loop contínuo.",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=API_BASE_URL,
        metavar="URL",
        help=f"URL base da API Flask (padrão: {API_BASE_URL}).",
    )
    parser.add_argument(
        "--intervalo",
        type=int,
        default=INTERVALO_SEGUNDOS,
        metavar="SEG",
        help=f"Intervalo em segundos entre leituras no loop (padrão: {INTERVALO_SEGUNDOS}s).",
    )

    return parser.parse_args()


def verificar_api_disponivel(url: str) -> bool:
    """
    Verifica se a API Flask está acessível antes de iniciar o simulador.

    Args:
        url (str): URL base da API.

    Returns:
        bool: True se a API respondeu com 2xx, False caso contrário.
    """
    try:
        response = requests.get(url, timeout=5)
        if response.status_code < 500:
            logger.info("✅ API disponível em: %s (status: %d)", url, response.status_code)
            return True
        else:
            logger.error("❌ API retornou status %d em %s", response.status_code, url)
            return False
    except requests.exceptions.ConnectionError:
        logger.error(
            "❌ Não foi possível conectar à API em: %s\n"
            "   Verifique se o servidor Flask está rodando: python app.py",
            url
        )
        return False
    except Exception as e:
        logger.error("❌ Erro ao verificar API: %s", e)
        return False


if __name__ == "__main__":
    args = parse_args()

    # Atualiza as URLs globais se o usuário informou uma URL customizada
    if args.url != API_BASE_URL:
        API_BASE_URL = args.url.rstrip("/")
        ENDPOINT_LEITURAS = f"{API_BASE_URL}/leituras"

    # Atualiza o intervalo global se o usuário informou
    if args.intervalo != INTERVALO_SEGUNDOS:
        INTERVALO_SEGUNDOS = args.intervalo

    logger.info("🌦️  Simulador de Estação Meteorológica IoT iniciado.")
    logger.info("   Endpoint alvo: %s", ENDPOINT_LEITURAS)

    # Verifica se a API está no ar antes de começar
    if not verificar_api_disponivel(API_BASE_URL):
        logger.error("Abortando. Inicie a API com: python app.py")
        sys.exit(1)

    # Determina o modo de operação
    if args.seed:
        # Modo Seed (obrigatório com --seed)
        executar_seed(count=args.count)

        # Opcionalmente continua em loop após o seed
        if args.loop:
            logger.info("▶️  Iniciando loop contínuo após o seed...")
            executar_loop()
    else:
        # Modo padrão: apenas loop contínuo
        executar_loop()
