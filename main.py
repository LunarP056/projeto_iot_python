# -*- coding: utf-8 -*-
"""
Teste Simples do Sensor Ultrassônico HC-SR04 (MicroPython)
---------------------------------------------------------
Este script lê a distância do sensor HC-SR04 e imprime o resultado
no console a cada 2 segundos.
"""
import utime
from machine import Pin, time_pulse_us

# ====================================================================
# CONFIGURAÇÃO DE PINOS
# 
# NOTA: Estes pinos (GPIO 12 e 14) são apenas exemplos.
# Mude-os para os pinos que você conectou ao seu ESP32.
# ====================================================================

TRIG_PIN = 12 # Pino Trigger (OUTPUT) - Conecte ao Trig do HC-SR04
ECHO_PIN = 14 # Pino Echo (INPUT) - Conecte ao Echo do HC-SR04

# Inicializa os objetos de hardware
trigger = Pin(TRIG_PIN, Pin.OUT)
echo = Pin(ECHO_PIN, Pin.IN)

# ====================================================================
# FUNÇÃO DE LEITURA DO SENSOR
# ====================================================================

def medir_distancia():
    """Lê o sensor HC-SR04 (Ultrassônico) e retorna a distância em cm."""
    
    # 1. Limpa o pino TRIGGER e envia pulso de 10µs.
    trigger.value(0)
    utime.sleep_us(2) # Pequena pausa para garantir que o pino está em LOW
    
    trigger.value(1)
    utime.sleep_us(10) # Pulso de 10 microssegundos para iniciar o sensor
    trigger.value(0)

    # 2. Mede a duração do pulso de retorno no ECHO.
    # time_pulse_us é a função nativa do MicroPython para medir a duração
    # de um pulso (aqui, a duração do pulso HIGH no pino ECHO).
    duration = time_pulse_us(echo, 1, 30000) # Timeout de 30ms (para evitar travamento)
    
    # Se a duração for 0 (timeout), retorna um valor de erro alto.
    if duration == 0:
        return 400.0
    
    # 3. Calcula a distância em centímetros.
    # Distância = (duração * velocidade do som em cm/µs) / 2
    # Velocidade do som (343 m/s) ≈ 0.0343 cm/µs.
    distance = (duration * 0.0343) / 2
    
    return distance

# ====================================================================
# LOOP PRINCIPAL DE TESTE
# ====================================================================

if __name__ == "__main__":
    print("Iniciando Teste HC-SR04...")
    
    while True:
        distancia = medir_distancia()
        
        # Imprime o resultado formatado
        print(f"Distância: {distancia:.2f} cm")
        
        # Espera 2 segundos antes da próxima leitura
        utime.sleep(2)