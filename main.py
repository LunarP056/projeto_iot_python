import machine
import utime
import ujson

# ====================================================================
# CONFIGURAÇÕES GLOBAIS (EDITÁVEIS)
# ====================================================================

# ID único para identificar este dispositivo.
DEVICE_ID = "PC_USER_01_STREAMING" 

# --- Pinos I2C (Verifique com seu ESP32/placa) ---
I2C_SDA_PIN = 21
I2C_SCL_PIN = 22
BH1750_I2C_ADDR = 0x23

# --- Configuração de Log Local ---
LOG_FILE_NAME = "data_log.jsonl" # Nome do arquivo para backup na memória flash
# ====================================================================
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

