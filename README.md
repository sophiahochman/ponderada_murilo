# 🌦️ Sistema de Estação Meteorológica IoT (End-to-End)

## 📖 Visão Geral

Este projeto implementa um sistema completo de **Internet das Coisas (IoT)** para monitoramento ambiental, integrando **hardware físico, backend e frontend** em uma arquitetura ponta a ponta.

A solução coleta dados de sensores físicos (temperatura e umidade), processa e armazena essas informações em um servidor, e as disponibiliza em tempo real por meio de uma interface web interativa.

O grande diferencial do projeto é a **integração real entre o mundo físico e digital**, permitindo a visualização e manipulação dos dados coletados diretamente de um dispositivo físico.

---

## 🧠 Arquitetura do Sistema

O sistema é dividido em três camadas principais:

### 🔌 1. Hardware (IoT) — *Responsabilidade desenvolvida por mim*

A camada de hardware é responsável pela **coleta dos dados ambientais**.

- Utilização de **Arduino + sensor DHT11**
- Leitura de:
  - 🌡️ Temperatura
  - 💧 Umidade
- Envio dos dados via **comunicação serial (USB)**

Além disso, implementei a **ponte entre hardware e software**, garantindo que os dados físicos fossem corretamente interpretados e enviados ao sistema.

---

### 🔄 2. Camada de Integração (Serial → API)

O arquivo `serial_reader.py` atua como um **middleware**, sendo essencial para conectar o hardware ao backend.

Funções principais:
- Escuta contínua da porta serial (`COM3`, baud rate 9600)
- Decodifica os dados recebidos do Arduino
- Converte os dados em requisições HTTP (`POST`)
- Envia para a API Flask

💡 Isso simula um ambiente de produção real onde dispositivos IoT enviam dados para servidores via rede.

> Para testes sem hardware físico, o projeto inclui `simulator.py`, que simula o envio dos dados.

---

### ⚙️ 3. Backend (API + Persistência)

Desenvolvido em **Python com Flask**, o backend é responsável por:

- Receber dados do hardware
- Processar e validar informações
- Persistir os dados no banco
- Disponibilizar APIs REST

#### Tecnologias:
- Python 3.10+
- Flask
- Flask-CORS
- SQLite (modo WAL para alta concorrência)

#### Funcionalidades:
- CRUD completo de leituras
- Estatísticas (média, mínimo, máximo)
- API REST estruturada
- Suporte a múltiplas requisições simultâneas

---

### 💻 4. Frontend (Interface Web)

Interface desenvolvida com:

- HTML + CSS + JavaScript puro
- Visual moderno (Glassmorphism + Bento Grid)
- Gráficos com Chart.js

#### Funcionalidades:
- Dashboard em tempo real
- Visualização de histórico
- Edição de dados
- Exclusão de registros
- Gráficos de evolução temporal

---

## 🔗 Fluxo Completo de Dados

```text
Sensor (DHT11)
   ↓
Arduino
   ↓ (Serial USB)
serial_reader.py
   ↓ (HTTP POST)
API Flask
   ↓
Banco SQLite
   ↓
Frontend (Dashboard em tempo real)
```

## 🛠️ Como Executar o Projeto

### 1. Configurar ambiente

```bash
python -m venv venv
venv\Scripts\activate  # Windows

pip install -r requirements.txt
```
### 2. Rodar servidor

```
python app.py
```
Acesse: http://localhost:5000 

### 3. Conectar o Hardware

```
python serial_reader.py
```

## Principais rotas

| Método | Rota                | Descrição          |
| ------ | ------------------- | ------------------ |
| GET    | `/api/resumo`       | Últimas leituras   |
| GET    | `/leituras`         | Lista paginada     |
| POST   | `/leituras`         | Nova leitura       |
| GET    | `/leituras/<id>`    | Detalhes           |
| PUT    | `/leituras/<id>`    | Atualização        |
| DELETE | `/leituras/<id>`    | Remoção            |
| GET    | `/api/estatisticas` | Métricas agregadas |

## Conclusão 
Este projeto demonstra na prática como construir um sistema completo de IoT, conectando sensores físicos a uma aplicação web moderna.

A solução evidencia conhecimentos em:

Sistemas embarcados
Integração de sistemas
Backend APIs
Banco de dados
Frontend interativo

## Fotos da montagem 

