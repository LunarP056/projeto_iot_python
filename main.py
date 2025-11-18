import machine
import utime
import ujson
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

# ====================================================================
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