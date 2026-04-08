# Atividade Ponderada: Sistema de Medição de Estação Meteorológica IoT

## 📖 Visão Geral
Este é um sistema "Ponta a Ponta" de IoT, criado para o Módulo 5 de Engenharia da Computação - Automação de Processos e Sistemas. Através desta aplicação, recebemos dados do hardware (placa Arduino) via Serial, persistimos de maneira otimizada (`SQLite WAL`) e demonstramos em tempo real numa interface de monitoramento (`Frontend HTML/JS`).

## 🏗️ Decisão de Arquitetura & Hardware Integrado
Utilizamos a **Placa Arduino (COM3)** para fazer leitura dos sensores DHT11. Para estabelecer a ponte de comunicação do mundo físico com a Web, implementamos o **`serial_reader.py`**. Este script atua como um Listener Serial que decodifica as métricas via porta USB (`COM3`, Bauld 9600) e repassa como requisições `POST` idênticas às de produção para a API Flask na porta local 5000.  

*(Nota: Para ambientes sem Hardware Físico, o projeto também mantém de backup um arquivo `simulator.py` que emula os envios HTTP.)*

### Tecnologias Usadas:
- **Backend:** `Python 3.10+`, `Flask`, `Flask-CORS`, `PySerial`
- **Banco de Dados:** `SQLite3` nativo, instanciado em modo Multi-process (`PRAGMA journal_mode=WAL` / `busy_timeout`) para evitar locas concorrentes.
- **Frontend:** Vanilla HTML/CSS/JS renderizados diretamente pelo próprio Flask, com Visual Glassmorphism + Bento Box e Gráficos do **Chart.JS**.

---

## 🛠️ Como Instalar e Rodar

### 1) Preparando o Ambiente
Recomenda-se criar uma Virtual Env para as dependências não entrarem em colisão.
```bash
# Crie o ambiente (Windows)
python -m venv venv
venv\Scripts\activate

# Instale os requerimentos
pip install -r requirements.txt
```

### 2) Rodando a Estação / Servidor HTTP
Este é o coração do projeto. O próprio `app.py` gera automaticamente as tabelas SQL e o arquivo `weather.db` em disco, para então montar o WebServer.
```bash
python app.py
```
> O Frontend já estará disponível! Basta acessar `http://localhost:5000` em seu navegador.

### 3) Ativando a Leitura Física (Ponte com Arduino na COM3)
Conecte o seu Arduino com o Sketch carregado na sua porta USB (o padrão do código é a *COM3* no Windows). Abra um **Novo Terminal** na mesma pasta, ative o ambiente virtual e execute o leitor:

```bash
python serial_reader.py
```
> O reader indicará no console os envios em tempo-real decodificados da porta serial USB!

---

## 🧭 Rotas e Páginas (Endpoints)

### Interface de Visualização HTML (via Browser)
- `GET /`: Painel do **Dashboard** com estatísticas animadas e tabela resumiu em tempo-real. (Antiga lista crua movida para `api/resumo`).
- `GET /historico`: Página de listagem com **edição** e **remoção** acionáveis.
- `GET /editar/<id_leitura>`: Ferramenta que recarrega configurações da telemetria sob demanda para input/correções manuais.

### API REST
| Método | Endpoint                    | Função                                                                                             |
|--------|-----------------------------|----------------------------------------------------------------------------------------------------|
| GET    | `/api/resumo`            | Últimas 10 leituras formatadas no JSON cru.                                                       |
| GET    | `/leituras`                 | Busca paginada completa listando telemetrias (`?limit=20&offset=0`).                            |
| POST   | `/leituras`                 | Adiciona nova leitura recebendo um corpo Payload `{ "temperatura": X, "umidade": Y }`.             |
| GET    | `/leituras/<id>`            | Retorna os detalhes sensíveis individuais.                                                         |
| PUT    | `/leituras/<id>`            | Atualização parcial daquela telemetria com base nos inputs json informados.                        |
| DELETE | `/leituras/<id>`            | Deleta permanentemente por ID.                                                                      |
| GET    | `/api/estatisticas`         | Consome função `AVG(), MIN(), MAX()` do SQLite e retorna os relatórios formatados em métricas JSON.  |

---

## 🎯 Avaliação (Features Implementadas)
| Item do PDF | Status | Resumo Implementação |
|:---:|:---|:---|
| Comunicação / Dados | 🟢 | Python Simulation -> Loop Rest API -> DB
| API REST Completa    | 🟢 | Todo o Schema do item 7 (+ Endpoint Resumo / Front)
| Banco de Dados        | 🟢 | CRUD Completo com Otimização WAL Concorrente
| Interface Web         | 🟢 | Layout Premium (Dashboard, Historico e Edição)
| Gráfico Temporal      | 🟢 | Gráfico de Linha Integrado com JS ChartJS
| Documentação e Arq    | 🟢 | Arquitetura modularizada bem documentada

Feito com ☕ e focado em excelência de usabilidade (UI/UX).
