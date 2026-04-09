from flask import Flask, request, jsonify, abort, render_template
from flask_cors import CORS
from database import (
    init_db,
    inserir_leitura,
    listar_leituras,
    buscar_leitura,
    atualizar_leitura,
    deletar_leitura,
    obter_estatisticas,
    contar_leituras,
)
import logging

# ---------------------------------------------------------------------------
# Configuração da Aplicação Flask
# ---------------------------------------------------------------------------

app = Flask(__name__)
CORS(app) # Habilita CORS para todas as rotas

@app.after_request
def add_header(response):
    """
    Assegura que as requisições à API e ao frontend nunca fiquem cacheadas pelo navegador,
    forçando os dados em tempo real a aparecerem.
    """
    response.cache_control.no_store = True
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# Configuração do logger da aplicação
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Garante que o banco seja inicializado ao importar/rodar o módulo
with app.app_context():
    init_db()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _leitura_to_dict(leitura: dict) -> dict:
    """Garante que os tipos numéricos sejam serializáveis em JSON."""
    return {
        "id":           leitura.get("id"),
        "temperatura":  leitura.get("temperatura"),
        "umidade":      leitura.get("umidade"),
        "pressao":      leitura.get("pressao"),
        "localizacao":  leitura.get("localizacao"),
        "timestamp":    leitura.get("timestamp"),
    }


def _paginar(items: list, total: int, limit: int, offset: int, base_url: str) -> dict:
    """Envelopa uma lista de itens com metadados de paginação."""
    pagina_atual = (offset // limit) + 1
    total_paginas = max(1, -(-total // limit))   # ceil division

    return {
        "dados":          items,
        "paginacao": {
            "total":          total,
            "limit":          limit,
            "offset":         offset,
            "pagina_atual":   pagina_atual,
            "total_paginas":  total_paginas,
            "tem_proxima":    (offset + limit) < total,
            "tem_anterior":   offset > 0,
        },
    }


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    """
    GET /
    -----
    Serve a interface do Dashboard (Frontend).
    """
    return render_template("index.html")


@app.route("/historico", methods=["GET"])
def historico():
    """
    GET /historico
    --------------
    Serve a interface de Histórico Completo de leituras.
    """
    return render_template("historico.html")


@app.route("/editar/<int:id_leitura>", methods=["GET"])
def editar(id_leitura: int):
    """
    GET /editar/<id>
    ----------------
    Serve a interface de edição de leitura. O Front usará JS
    para buscar os dados da leitura na API HTTP e preencher
    o formulário.
    """
    return render_template("editar.html", id_leitura=id_leitura)


@app.route("/api/resumo", methods=["GET"])
def api_resumo():
    """
    GET /api/resumo
    -----
    Retorna as últimas 10 leituras registradas no banco de dados.
    Ideal para um dashboard de monitoramento rápido.

    Response 200:
        {
            "mensagem": "Sistema de Medição de Estação Meteorológica IoT",
            "total_leituras": 42,
            "ultimas_leituras": [ {...}, ... ]
        }
    """
    leituras = listar_leituras(limit=10, offset=0)
    total = contar_leituras()

    return jsonify({
        "mensagem":       "Sistema de Medição de Estação Meteorológica IoT",
        "status":         "online",
        "total_leituras": total,
        "ultimas_leituras": [_leitura_to_dict(l) for l in leituras],
    }), 200


@app.route("/leituras", methods=["GET"])
def get_leituras():
    """
    GET /leituras[?limit=50&offset=0&localizacao=Lab]
    --------------------------------------------------
    Retorna o histórico completo de leituras com suporte a paginação e filtro.

    Query Params:
        limit       (int, default=50):   Registros por página (máx: 200).
        offset      (int, default=0):    Posição inicial do cursor.
        localizacao (str, optional):     Filtra por local (ex: ?localizacao=Lab).

    Response 200:
        {
            "dados": [...],
            "paginacao": { "total": 100, "limit": 50, "offset": 0, ... }
        }

    Response 400:
        { "erro": "Parâmetro inválido: ..." }
    """
    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
    except (ValueError, TypeError):
        return jsonify({"erro": "Parâmetros 'limit' e 'offset' devem ser inteiros."}), 400

    # Garante limites razoáveis
    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    localizacao = request.args.get("localizacao", None)

    leituras = listar_leituras(limit=limit, offset=offset, localizacao=localizacao)
    total = contar_leituras(localizacao=localizacao)

    response = _paginar(
        items=[_leitura_to_dict(l) for l in leituras],
        total=total,
        limit=limit,
        offset=offset,
        base_url=request.base_url,
    )

    return jsonify(response), 200


@app.route("/leituras", methods=["POST"])
def post_leitura():
    """
    POST /leituras
    --------------
    Insere uma nova leitura no banco de dados.

    Body JSON (application/json):
        {
            "temperatura":  25.4,          ← obrigatório (float)
            "umidade":      65.0,          ← obrigatório (float)
            "pressao":      1013.25,       ← opcional
            "localizacao":  "Lab A",       ← opcional (default: "Lab")
            "timestamp":    "2024-01-15 10:30:00"  ← opcional (ISO 8601)
        }

    Response 201:
        { "id": 1, "mensagem": "Leitura inserida com sucesso.", "dados": {...} }

    Response 400:
        { "erro": "Campo obrigatório ausente: ..." }
    """
    dados = request.get_json(silent=True)

    # Validação: corpo da requisição deve ser JSON válido
    if not dados:
        return jsonify({
            "erro": "Corpo da requisição deve ser JSON válido (Content-Type: application/json)."
        }), 400

    # Validação: campos obrigatórios
    campos_obrigatorios = ["temperatura", "umidade"]
    for campo in campos_obrigatorios:
        if campo not in dados:
            return jsonify({"erro": f"Campo obrigatório ausente: '{campo}'."}), 400

    # Validação: tipos numéricos
    try:
        temperatura = float(dados["temperatura"])
        umidade     = float(dados["umidade"])
        pressao     = float(dados["pressao"]) if "pressao" in dados and dados["pressao"] is not None else None
    except (ValueError, TypeError):
        return jsonify({
            "erro": "Campos 'temperatura', 'umidade' e 'pressao' devem ser numéricos."
        }), 400

    # Validação: ranges realistas (aviso, não blocking)
    localizacao = dados.get("localizacao", "Lab")
    timestamp   = dados.get("timestamp", None)

    try:
        novo_id = inserir_leitura(
            temperatura=temperatura,
            umidade=umidade,
            pressao=pressao,
            localizacao=localizacao,
            timestamp=timestamp,
        )
    except Exception as e:
        logger.error("Erro ao inserir leitura: %s", e)
        return jsonify({"erro": "Erro interno ao inserir leitura no banco."}), 500

    # Busca o registro recém-criado para retornar no response
    leitura_criada = buscar_leitura(novo_id)

    return jsonify({
        "mensagem": "Leitura inserida com sucesso.",
        "id":       novo_id,
        "dados":    _leitura_to_dict(leitura_criada),
    }), 201


@app.route("/leituras/<int:id_leitura>", methods=["GET"])
def get_leitura(id_leitura: int):
    """
    GET /leituras/<id>
    ------------------
    Retorna os detalhes de uma leitura específica pelo ID.

    Response 200:
        { "dados": { "id": 1, "temperatura": 25.4, ... } }

    Response 404:
        { "erro": "Leitura com id=<id> não encontrada." }
    """
    leitura = buscar_leitura(id_leitura)

    if leitura is None:
        return jsonify({"erro": f"Leitura com id={id_leitura} não encontrada."}), 404

    return jsonify({"dados": _leitura_to_dict(leitura)}), 200


@app.route("/leituras/<int:id_leitura>", methods=["PUT"])
def put_leitura(id_leitura: int):
    """
    PUT /leituras/<id>
    ------------------
    Atualiza campos de uma leitura existente. Funciona como PATCH:
    somente os campos informados no JSON serão atualizados.

    Body JSON (qualquer subconjunto dos campos):
        {
            "temperatura": 27.1,
            "umidade":     70.5,
            "pressao":     1010.0,
            "localizacao": "Lab B"
        }

    Response 200:
        { "mensagem": "Leitura atualizada.", "dados": {...} }

    Response 400:
        { "erro": "Nenhum campo válido fornecido para atualização." }

    Response 404:
        { "erro": "Leitura com id=<id> não encontrada." }
    """
    # Verifica se o registro existe antes de tentar atualizar
    leitura_existente = buscar_leitura(id_leitura)
    if leitura_existente is None:
        return jsonify({"erro": f"Leitura com id={id_leitura} não encontrada."}), 404

    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({
            "erro": "Corpo da requisição deve ser JSON válido (Content-Type: application/json)."
        }), 400

    # Extrai e converte os campos opcionais
    try:
        temperatura = float(dados["temperatura"]) if "temperatura" in dados else None
        umidade     = float(dados["umidade"])     if "umidade"     in dados else None
        pressao     = float(dados["pressao"])     if "pressao"     in dados else None
    except (ValueError, TypeError):
        return jsonify({
            "erro": "Campos 'temperatura', 'umidade' e 'pressao' devem ser numéricos."
        }), 400

    localizacao = dados.get("localizacao", None)

    # Garante que ao menos um campo foi enviado
    if all(v is None for v in [temperatura, umidade, pressao, localizacao]):
        return jsonify({
            "erro": "Nenhum campo válido fornecido para atualização (temperatura, umidade, pressao, localizacao)."
        }), 400

    try:
        sucesso = atualizar_leitura(
            id_leitura=id_leitura,
            temperatura=temperatura,
            umidade=umidade,
            pressao=pressao,
            localizacao=localizacao,
        )
    except Exception as e:
        logger.error("Erro ao atualizar leitura id=%d: %s", id_leitura, e)
        return jsonify({"erro": "Erro interno ao atualizar leitura."}), 500

    leitura_atualizada = buscar_leitura(id_leitura)

    return jsonify({
        "mensagem": f"Leitura id={id_leitura} atualizada com sucesso.",
        "dados":    _leitura_to_dict(leitura_atualizada),
    }), 200


@app.route("/leituras/<int:id_leitura>", methods=["DELETE"])
def delete_leitura(id_leitura: int):
    """
    DELETE /leituras/<id>
    ---------------------
    Remove permanentemente uma leitura do banco de dados.

    Response 200:
        { "mensagem": "Leitura removida com sucesso.", "id_removido": 5 }

    Response 404:
        { "erro": "Leitura com id=<id> não encontrada." }
    """
    # Verifica existência antes de deletar
    leitura_existente = buscar_leitura(id_leitura)
    if leitura_existente is None:
        return jsonify({"erro": f"Leitura com id={id_leitura} não encontrada."}), 404

    try:
        sucesso = deletar_leitura(id_leitura)
    except Exception as e:
        logger.error("Erro ao deletar leitura id=%d: %s", id_leitura, e)
        return jsonify({"erro": "Erro interno ao remover leitura."}), 500

    return jsonify({
        "mensagem":    f"Leitura id={id_leitura} removida com sucesso.",
        "id_removido": id_leitura,
    }), 200


@app.route("/api/estatisticas", methods=["GET"])
def get_estatisticas():
    """
    GET /api/estatisticas[?localizacao=Lab]
    ----------------------------------------
    Retorna estatísticas agregadas de temperatura, umidade e pressão.

    Query Params:
        localizacao (str, optional): Filtra cálculo por local.

    Response 200:
        {
            "total_leituras": 42,
            "temperatura":  { "media": 25.3, "min": 15.1, "max": 34.9 },
            "umidade":      { "media": 60.2, "min": 40.0, "max": 80.0 },
            "pressao":      { "media": 1013.0, "min": 1005.0, "max": 1020.0 },
            "periodo":      { "inicio": "2024-01-01 08:00:00", "fim": "2024-01-15 18:00:00" }
        }

    Response 404:
        { "erro": "Nenhuma leitura registrada no banco de dados." }
    """
    localizacao = request.args.get("localizacao", None)

    try:
        estatisticas = obter_estatisticas(localizacao=localizacao)
    except Exception as e:
        logger.error("Erro ao calcular estatísticas: %s", e)
        return jsonify({"erro": "Erro interno ao calcular estatísticas."}), 500

    if estatisticas is None:
        mensagem = "Nenhuma leitura registrada no banco de dados."
        if localizacao:
            mensagem = f"Nenhuma leitura encontrada para a localização '{localizacao}'."
        return jsonify({"erro": mensagem}), 404

    response = {
        "total_leituras": estatisticas["total_leituras"],
        "temperatura": {
            "media": estatisticas["temp_media"],
            "min":   estatisticas["temp_min"],
            "max":   estatisticas["temp_max"],
        },
        "umidade": {
            "media": estatisticas["umid_media"],
            "min":   estatisticas["umid_min"],
            "max":   estatisticas["umid_max"],
        },
        "pressao": {
            "media": estatisticas["pressao_media"],
            "min":   estatisticas["pressao_min"],
            "max":   estatisticas["pressao_max"],
        },
        "periodo": {
            "inicio": estatisticas["periodo_inicio"],
            "fim":    estatisticas["periodo_fim"],
        },
    }

    if localizacao:
        response["filtro_localizacao"] = localizacao

    return jsonify(response), 200


# ---------------------------------------------------------------------------
# Handler de erros globais
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return jsonify({"erro": "Rota não encontrada.", "detalhe": str(e)}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"erro": "Método HTTP não permitido para esta rota.", "detalhe": str(e)}), 405


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"erro": "Erro interno do servidor.", "detalhe": str(e)}), 500


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Iniciando API da Estação Meteorológica IoT...")
    logger.info("Endpoints disponíveis:")
    logger.info("  GET  http://localhost:5000/")
    logger.info("  GET  http://localhost:5000/leituras")
    logger.info("  POST http://localhost:5000/leituras")
    logger.info("  GET  http://localhost:5000/leituras/<id>")
    logger.info("  PUT  http://localhost:5000/leituras/<id>")
    logger.info("  DEL  http://localhost:5000/leituras/<id>")
    logger.info("  GET  http://localhost:5000/api/estatisticas")

    app.run(
        host="0.0.0.0",   # Escuta em todas as interfaces (acessível na rede local)
        port=5000,
        debug=True,        # Habilita reloader e tracebacks detalhados
    )
