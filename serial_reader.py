import serial
import json
import requests
import time
import logging


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


PORTA = 'COM3'          
BAUD  = 9600
URL   = 'http://localhost:5000/leituras'

def ler_serial():
    logging.info(f"🚀 Iniciando Leitor Serial IoT na porta {PORTA} a {BAUD} bps...")
    logging.info(f"📡 Despachando métricas para: {URL}")
    logging.info("Aguardando conexão com o Arduino (Certifique-se de que nenhum outro programa está usando a COM3)...")

    try:
        with serial.Serial(PORTA, BAUD, timeout=2) as ser:
            logging.info("✅ Conexão Serial estabelecida com sucesso!")
            
            while True:
                try:
                    linha = ser.readline().decode('utf-8').strip()
                    if linha:
                        try:
                            dados = json.loads(linha)
                            
                            response = requests.post(URL, json=dados)
                            
                            if response.status_code == 201:
                                logging.info(f"✔️ Enviado c/ sucesso: {dados}")
                            else:
                                logging.error(f"❌ Erro da API ({response.status_code}): {response.text}")

                        except json.JSONDecodeError:
                            logging.warning(f"⚠️ Linha recebida ignorada (formato inválido): {linha}")
                        except requests.exceptions.ConnectionError:
                            logging.error("🚫 Falha ao conectar com a API Flask. O servidor app.py está rodando?")
                            
                except serial.SerialException as e:
                    logging.error(f"Erro na leitura serial (Arduino desconectado?): {e}")
                    break
                    
                time.sleep(0.1)

    except serial.SerialException as err:
        logging.critical(f"FATAL: Não foi possível abrir a porta serial {PORTA}.")
        logging.critical("Verifique se a porta física está correta no script, se o Arduino está plugado, ou se a IDE do Arduino / Monitor Serial não está travando a porta.")
        logging.critical(f"Detalhes: {err}")
    except KeyboardInterrupt:
        logging.info("🛑 Leitor interrompido pelo usuário.")

if __name__ == '__main__':
    ler_serial()
