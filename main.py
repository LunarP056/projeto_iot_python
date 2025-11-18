import machine
import utime
import ujson
<<<<<<< HEAD
import os
import network
import urequests
import usocket as socket
# import umdns  <-- REMOVIDO

# ====================================================================
# ⚙️ CONFIGURAÇÕES GLOBAIS
# ====================================================================

# ID único para identificar este dispositivo.
DEVICE_ID = "PC_USER_01_LOCAL" 

# --- Configurações ThingSpeak (SUA CHAVE) ---
THINGSPEAK_API_KEY = "2RY2FMBN3TFXTYYM" 
THINGSPEAK_URL = "https://api.thingspeak.com/update"

# --- Configurações de Provisão Wi-Fi ---
CONFIG_FILE = "wifi_config.json"
AP_SSID = "ESP32_CONFIG_APP"
AP_PASS = "12345678"
SERVER_IP = '192.168.4.1' 
# MDNS_HOSTNAME = "config" <-- REMOVIDO
=======

# ====================================================================
# CONFIGURAÇÕES GLOBAIS (EDITÁVEIS)
# ====================================================================

# ID único para identificar este dispositivo.
DEVICE_ID = "PC_USER_01_STREAMING" 

# --- Pinos I2C (Verifique com seu ESP32/placa) ---
I2C_SDA_PIN = 21
I2C_SCL_PIN = 22
BH1750_I2C_ADDR = 0x23
>>>>>>> dfcd9d4964fd0cadc9b71d6be09023736a7b0c30

# --- Configuração de Log Local ---
LOG_FILE_NAME = "data_log.jsonl" # Nome do arquivo para backup na memória flash
# ====================================================================
<<<<<<< HEAD
# ⏱️ VARIÁVEIS DE CÁLCULO E TEMPORIZAÇÃO
# ====================================================================

LEITURA_INTERVALO_MS = 5000 

# --- Configurações da Média Móvel ---
NUM_AMOSTRAS = 10
dist_array = [0.0] * NUM_AMOSTRAS
lux_array = [0.0] * NUM_AMOSTRAS
indice_amostra = 0
amostras_coletadas = 0

# ====================================================================
# 🤖 DRIVERS DE SENSORES (MANTIDOS)
# ====================================================================

class BH1750:
    """Driver simplificado para o sensor de luminosidade BH1750 (I2C)"""
    def __init__(self, i2c, addr=0x23):
        self.i2c = i2c
        self.addr = addr
        self.CONTINUOUS_HIGH_RES_MODE = 0x10 
        self.i2c.writeto(self.addr, bytes([self.CONTINUOUS_HIGH_RES_MODE]))
        print("BH1750 Pronto!")

    def read_light_level(self):
        """Lê o valor de luminosidade em Lux."""
        try:
            data = self.i2c.readfrom(self.addr, 2)
            return (data[0] << 8 | data[1]) / 1.2
        except OSError as e:
            return -3.0

class HCSR04:
    """Driver para o sensor de distância ultrassônico HC-SR04"""
    def __init__(self, trig_pin, echo_pin):
        self.trig = machine.Pin(trig_pin, machine.Pin.OUT)
        self.echo = machine.Pin(echo_pin, machine.Pin.IN)
        self.trig.value(0)

    def proximidade(self):
        """Calcula a distância em centímetros (cm)"""
        self.trig.value(0)
        utime.sleep_us(2)
        self.trig.value(1)
        utime.sleep_us(10)
        self.trig.value(0)

        duration = machine.time_pulse_us(self.echo, 1, 30000) 

        if duration <= 0:
            return 400.0 

        distance = (duration * 0.0343) / 2

        return distance

# ====================================================================
# 🧮 FUNÇÕES DE UTILIDADE E MÉDIA MÓVEL (MANTIDAS)
# ====================================================================

def calcular_media(arr):
    """Calcula a media da lista de arrays"""
    tamanho = len(arr)
    if tamanho > 0:
        return sum(arr) / tamanho
    return 0.0

# ====================================================================
# 🌐 FUNÇÕES DE PROVISIONAMENTO (MANTIDAS)
# ====================================================================

def load_wifi_config():
    """Carrega as credenciais de Wi-Fi salvas na flash."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return ujson.load(f)
    except:
        return None

def save_wifi_config(ssid, password):
    """Salva as novas credenciais de Wi-Fi na flash."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            ujson.dump({'ssid': ssid, 'password': password}, f)
        print("Configurações Wi-Fi salvas.")
        return True
    except:
        print("ERRO: Falha ao salvar configurações.")
        return False

# ====================================================================
# 📶 FUNÇÕES DE SERVIDOR WEB (PORTAL CATIVO) - OTIMIZADA
# ====================================================================

def start_ap_server():
    """Inicia o ESP32 em modo AP e um servidor web simples para provisionamento."""
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=AP_SSID, password=AP_PASS)
    ap.ifconfig((SERVER_IP, '255.255.255.0', SERVER_IP, SERVER_IP))
    print(f"Modo AP ativado. Conecte-se a: {AP_SSID} (Senha: {AP_PASS})")
    print(f"Acesse o navegador: http://{SERVER_IP}") 

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', 80))
    s.listen(1)

    while True:
        try:
            conn, addr = s.accept()
            
            # Lê a primeira parte da requisição (cabeçalhos)
            request = conn.recv(1024)
            request = str(request)
            
            # --- Limpeza de Buffer ---
            while True:
                try:
                    conn.recv(1024)
                except OSError as e:
                    break
            
            # Lógica de extração e salvamento de dados do formulário
            if "POST" in request and "ssid" in request:
                # Lógica de POST
                try:
                    params_start = request.find("\r\n\r\n") 
                    params = request[params_start:].strip()
                    
                    ssid_val = params.split('&')[0].split('=')[1]
                    pass_val = params.split('&')[1].split('=')[1]
                    
                    ssid = socket.url_decode(ssid_val).replace('+', ' ')
                    password = socket.url_decode(pass_val).replace('+', ' ')

                    save_wifi_config(ssid, password)
                    response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<h1>Configuracao salva!</h1><p>O dispositivo ira reiniciar e tentar conectar.</p>"
                    conn.send(response.encode())
                    conn.close()
                    machine.reset() 

                except Exception as e:
                    print(f"Erro ao processar POST: {e}")
                    
            else:
                # Lógica de GET (Página HTML e requisições secundárias)
                html = """
                <!DOCTYPE html>
                <html>
                <head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
                <body>
                    <h2>Configuracao Wi-Fi ESP32</h2>
                    <form method="POST">
                        <label for="ssid">Rede (SSID):</label><br>
                        <input type="text" id="ssid" name="ssid" required><br><br>
                        <label for="password">Senha:</label><br>
                        <input type="password" id="password" name="password"><br><br>
                        <input type="submit" value="Conectar">
                    </form>
                </body>
                </html>
                """
                response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + html
                conn.send(response.encode())
                conn.close() 

        except OSError as e:
            if 'ETIMEDOUT' not in str(e):
                print(f"Erro no servidor: {e}")

# ====================================================================
# 🚀 FUNÇÃO DE ENVIO PARA THINGSPEAK (MANTIDA)
# ====================================================================

def enviar_dados_thingspeak(distancia, lux):
    """Envia os dados para o ThingSpeak via HTTP GET (Query String)."""
    try:
        payload_url = (
            f"{THINGSPEAK_URL}?"
            f"api_key={THINGSPEAK_API_KEY}"
            f"&field1={distancia:.2f}" 
            f"&field2={lux:.2f}" 		
        )
        
        response = urequests.get(payload_url)
        
        if response.status_code == 200:
            print(f"  [TS] Dados enviados. Entry ID: {response.text}")
            success = True
        else:
            print(f"  [TS ERRO] Falha: Status {response.status_code}, Resposta: {response.text}")
            success = False
            
        response.close() 
        return success
    except Exception as e:
        print(f"ERRO THINGSPEAK: {e}")
        return False

# ====================================================================
# 🟢 FUNÇÃO PRINCIPAL (CORREÇÕES MANTIDAS, mDNS REMOVIDO)
# ====================================================================

def main():
    global indice_amostra, amostras_coletadas
    
    # --- SETUP: Sensores e I2C ---
    i2c = machine.I2C(1, sda=machine.Pin(21), scl=machine.Pin(22)) 
    
    try:
        lightmeter = BH1750(i2c)
    except Exception as e:
        print(f"Erro ao inicializar BH1750: {e}. Usando sensor dummy.")
        class DummyBH1750:
             def read_light_level(self): return 0.0
        lightmeter = DummyBH1750()
        
    ultrassonic = HCSR04(trig_pin=12, echo_pin=14)
    ultimo_tempo_leitura = utime.ticks_ms()
    
    # --- PROVISIONAMENTO E CONEXÃO WI-FI ---
    
    config = load_wifi_config()
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if config and 'ssid' in config:
        print(f"Tentando conectar ao Wi-Fi: {config['ssid']}")
        wlan.connect(config['ssid'], config['password'])
        
        # Lógica de conexão com timeout ativo (máx. 10s)
        timeout_count = 0
        while not wlan.isconnected() and timeout_count < 20: 
            utime.sleep_ms(500)
            timeout_count += 1
    
    if not wlan.isconnected():
        print("Falha na conexão Wi-Fi. Iniciando modo AP para provisionamento...")
        start_ap_server() # BLOQUEANTE.
        return 
    
    print(f"Conectado ao Wi-Fi. IP: {wlan.ifconfig()[0]}")
    
    # umdns.init() <-- REMOVIDO
    # umdns.set_name(MDNS_HOSTNAME) <-- REMOVIDO
    
    # --- Loop Contínuo (ENVIO THINGSPEAK ATIVO)---
    while True:
        tempo_atual = utime.ticks_ms()

        if utime.ticks_diff(tempo_atual, ultimo_tempo_leitura) >= LEITURA_INTERVALO_MS:
            ultimo_tempo_leitura = tempo_atual

            distancia = ultrassonic.proximidade()
            lux = lightmeter.read_light_level() 

            if lux < 0:
                print("Leitura de LUX inválida. Pulando amostra.")
                utime.sleep_ms(100) 
                continue
            
            print(f"\n[COLETA] Distância: {distancia:.2f} cm | Lux: {lux:.2f} lx")
            if not enviar_dados_thingspeak(distancia, lux):
                print("Falha ao enviar dados para o ThingSpeak.")

            # ** Ação: Média Móvel **
            dist_array[indice_amostra] = distancia 
            lux_array[indice_amostra] = lux
            
            proximo_indice = (indice_amostra + 1) % NUM_AMOSTRAS
            indice_amostra = proximo_indice
            if amostras_coletadas < NUM_AMOSTRAS:
                amostras_coletadas += 1

            if amostras_coletadas == NUM_AMOSTRAS and proximo_indice == 0:
                 avg_dist = calcular_media(dist_array)
                 avg_lux = calcular_media(lux_array)
                 print(f"  [MÉDIA MÓVEL] Dist: {avg_dist:.2f} | Lux: {avg_lux:.2f}")

        utime.sleep_ms(50)

if __name__ == "__main__":
    main()
=======
# VARIÁVEIS DE CÁLCULO E TEMPORIZAÇÃO
# ====================================================================

LEITURA_INTERVALO_MS = 10000 
NUM_AMOSTRAS = 10  
LIMIAR_DISTANCIA_CM = 50.0  
LIMIAR_LUX = 30.0           

dist_array = [0.0] * NUM_AMOSTRAS
lux_array = [0.0] * NUM_AMOSTRAS
indice_amostra = 0
amostras_coletadas = 0

# ====================================================================
# DRIVERS DE SENSORES
# ====================================================================

class BH1750:
    """Driver simplificado e robusto para o sensor de luminosidade BH1750 (I2C)"""
    def __init__(self, i2c, addr=BH1750_I2C_ADDR):
        self.i2c = i2c
        self.addr = addr
        self.ready = False 
        
        self.POWER_ON = 0x01
        self.RESET = 0x07
        self.CONTINUOUS_HIGH_RES_MODE = 0x10

        print(f"Tentando inicializar BH1750 em 0x{self.addr:X}...")
        try:
            self.i2c.writeto(self.addr, bytes([self.POWER_ON]))
            self.i2c.writeto(self.addr, bytes([self.RESET]))
            self.i2c.writeto(self.addr, bytes([self.CONTINUOUS_HIGH_RES_MODE]))
            
            utime.sleep_ms(180) 
            self.ready = True
            print("BH1750: Comunicação OK. Sensor pronto.")
        except OSError as e:
            print(f"BH1750: Erro Crítico de I2C durante a inicialização: {e}")
            self.ready = False

    def read_light_level(self):
        """Lê o valor de luminosidade em Lux. Retorna -3.0 se não estiver pronto."""
        if not self.ready:
            return -3.0
            
        try:
            data = self.i2c.readfrom(self.addr, 2)
            return (data[0] << 8 | data[1]) / 1.2
        except OSError:
            return -3.0  

class HCSR04:
    """Driver para o sensor de distância ultrassônico HC-SR04"""
    def __init__(self, trig_pin, echo_pin):
        self.trig = machine.Pin(trig_pin, machine.Pin.OUT)
        self.echo = machine.Pin(echo_pin, machine.Pin.IN)
        self.trig.value(0)

    def proximidade(self):
        """Calcula a distância em centímetros."""
        self.trig.value(0)
        utime.sleep_us(2)
        self.trig.value(1)
        utime.sleep_us(10)
        self.trig.value(0)

        duration = machine.time_pulse_us(self.echo, 1, 30000) 
        
        if duration <= 0:
            return 400.0 

        distance = (duration * 0.0343) / 2
        
        return distance

# ====================================================================
# FUNÇÕES DE UTILIDADE E LOGGING
# ====================================================================

def setup_local_system():
    """Inicializa o sistema local e instrui sobre a coleta de dados."""
    print("\n========================================================")
    print("SISTEMA DE MONITORAMENTO ATIVO:")
    print("========================================================")
    print("STREAMING SERIAL: Cada leitura (JSON) é enviada ao PC.")
    print(f"LOG LOCAL: Dados salvos em '{LOG_FILE_NAME}' no ESP32 (Backup).")
    print("\n>>> Para BAITAR o log, PARE (Ctrl+C) e digite 'dump_local_log()' <<<")
    print("========================================================")

def get_current_timestamp():
    """Retorna o timestamp Unix (segundos desde 1/1/1970)."""
    UNIX_OFFSET = 946684800 
    return utime.time() + UNIX_OFFSET

def calcular_media(arr):
    """Calcula a média de uma lista de floats."""
    tamanho = len(arr)
    if tamanho > 0:
        return sum(arr) / tamanho
    return 0.0

def format_data_to_jsonl(timestamp, distance, lux):
    """Cria o objeto JSON e o serializa para uma linha JSON pura."""
    try:
        record = {
            "ts": timestamp,
            "id": DEVICE_ID,
            "dist_cm": round(distance, 2),
            "lux_lx": round(lux, 2)
        }
        return ujson.dumps(record)
    except Exception as e:
        print(f"ERRO DE FORMATAÇÃO: Falha ao serializar dados: {e}")
        return None

def log_data_to_file(json_line):
    """Salva a linha JSON no arquivo data_log.jsonl na memória do ESP32."""
    try:
        with open(LOG_FILE_NAME, 'a') as f:
            f.write(json_line)
            f.write('\n') # Adiciona uma quebra de linha para formatar JSON Lines (JSONL)
        return True
    except Exception as e:
        print(f"ERRO DE ARQUIVO: Falha ao salvar no log local: {e}")
        return False
        
def dump_local_log():
    """
    Imprime todo o conteúdo do arquivo de log na saída serial (terminal do PC).
    O usuário deve estar capturando o log no PC antes de chamar esta função.
    """
    print("\n========================================================")
    print(f"INÍCIO DA TRANSFERÊNCIA DO ARQUIVO: {LOG_FILE_NAME}")
    print("========================================================")
    
    utime.sleep_ms(500) 
    
    try:
        with open(LOG_FILE_NAME, 'r') as f:
            # Imprime linha por linha para evitar MemoryError
            for line in f:
                print(line.strip()) 
        
        print("\n========================================================")
        print(f"FIM DA TRANSFERÊNCIA DO ARQUIVO: {LOG_FILE_NAME} - SUCESSO")
        print("========================================================")
        
    except OSError as e:
        print(f"\nERRO DE LEITURA: O arquivo {LOG_FILE_NAME} pode estar vazio ou não existe: {e}")
        print("========================================================")

# ====================================================================
# FUNÇÃO PRINCIPAL
# ====================================================================

def main():
    global indice_amostra, amostras_coletadas
    
    # 1. Inicializa o I2C
    print(f"Inicializando I2C nos pinos SDA={I2C_SDA_PIN}, SCL={I2C_SCL_PIN}...")
    try:
        i2c = machine.I2C(1, sda=machine.Pin(I2C_SDA_PIN), scl=machine.Pin(I2C_SCL_PIN), freq=400000) 
    except ValueError as e:
        print(f"ERRO DE PINO: Falha ao inicializar o I2C: {e}")
        return

    # --- VERIFICAÇÃO DE HARDWARE (SCAN I2C) ---
    print("\n[SCAN I2C] Verificando dispositivos conectados...")
    devices = i2c.scan()
    
    if BH1750_I2C_ADDR not in devices:
        print(f"ERRO CRÍTICO: BH1750 (0x{BH1750_I2C_ADDR:X}) não encontrado no barramento.")
        print("Encerrando o programa.")
        return 
    
    print(f"BH1750 (0x{BH1750_I2C_ADDR:X}) encontrado no barramento.")
    # ----------------------------------------------------

    # 2. Inicializa o BH1750 
    lightmeter = BH1750(i2c)
    
    if not lightmeter.ready:
        print("\n*** FALHA CRÍTICA: O BH1750 falhou na inicialização. Encerrando. ***")
        return 
    
    # 3. Inicializa outros sensores (independentes)
    ultrassonic = HCSR04(trig_pin=12, echo_pin=14) 
    
    # 4. Início do Sistema
    setup_local_system()
    
    ultimo_tempo_leitura = utime.ticks_ms()

    # --- Loop Contínuo ---
    while True:
        tempo_atual = utime.ticks_ms()

        # 1. Lógica de Coleta de Dados (a cada 10 segundos)
        if utime.ticks_diff(tempo_atual, ultimo_tempo_leitura) >= LEITURA_INTERVALO_MS:
            ultimo_tempo_leitura = tempo_atual

            # ** Ação 1: Coleta dos dados dos sensores e timestamp **
            distancia = ultrassonic.proximidade()
            lux = lightmeter.read_light_level() 
            timestamp = get_current_timestamp()

            if lux < 0:
                 print("Leitura de LUX inválida. Pulando amostra.")
                 utime.sleep_ms(100) 
                 continue

            # ** Ação 2: Formatação e Streaming Serial **
            json_line = format_data_to_jsonl(timestamp, distancia, lux)

            if json_line:
                # >> STREAMING SERIAL (DADOS JSON PUROS) <<
                print(json_line)
                
                # ** Log Local **
                if log_data_to_file(json_line):
                     log_status = "Log LOCAL OK"
                else:
                     log_status = "Log LOCAL FALHOU"

            # ** Ação 3: Armazenamento circular para Média Móvel **
            dist_array[indice_amostra] = distancia 
            lux_array[indice_amostra] = lux
            
            print(f"\n[COLETA #{indice_amostra}] Dist: {distancia:.2f} cm | Lux: {lux:.2f} lx | TS: {timestamp}")
            print(f"[STATUS] SERIAL STREAMING OK | {log_status}")

            proximo_indice = (indice_amostra + 1) % NUM_AMOSTRAS
            indice_amostra = proximo_indice
            
            if amostras_coletadas < NUM_AMOSTRAS:
                amostras_coletadas += 1

            # --- 2. Lógica de Agregação e ALERTA (ACIONADA A CADA 10 AMOSTRAS) ---
            if amostras_coletadas == NUM_AMOSTRAS and proximo_indice == 0:
                
                media_distancia = calcular_media(dist_array)
                media_lux = calcular_media(lux_array)
                
                print("\n--- AGREGADO DE 10 AMOSTRAS ---")
                print(f"Média Distância: {media_distancia:.2f} cm (Limiar: {LIMIAR_DISTANCIA_CM:.2f} cm)") 
                print(f"Média Luminosidade: {media_lux:.2f} lx (Limiar: {LIMIAR_LUX:.2f} lx)")

                # Lógica de Alerta
                alerta_proximidade = media_distancia < LIMIAR_DISTANCIA_CM 
                alerta_luminosidade = media_lux < LIMIAR_LUX
                
                if alerta_proximidade or alerta_luminosidade:
                    tipos = []
                    if alerta_proximidade: tipos.append("[PROXIMIDADE]")
                    if alerta_luminosidade: tipos.append("[LUMINOSIDADE]")
                    # >>> PRINT DOS ALERTAS NO CONSOLE <<<
                    print(f"** ALERTA DETECTADO! Tipo(s): {' '.join(tipos)} **")
                else:
                    print("Condição normal. Nenhum alerta disparado.")
                
                print("------------------------------------------\n")

        utime.sleep_ms(50) 

# Execução do código principal
if __name__ == "__main__":
    main()

>>>>>>> dfcd9d4964fd0cadc9b71d6be09023736a7b0c30
