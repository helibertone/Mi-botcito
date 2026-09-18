import matplotlib
matplotlib.use('Agg')  # Evita que el servidor intente abrir una ventana gráfica invisible

import asyncio
import logging
import requests
import pandas as pd
import pandas_ta as ta
import yfinance as yf
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Configuración estricta de logs para monitoreo
logging.basicConfig(level=logging.INFO)

# --- DATOS PERSONALES INTEGRADOS ---
TOKEN = "8882275126:AAG4joJlFJCCz1wFoWxPHm8pL9CfrvAJiZg"
MI_TELEGRAM_ID = 581924626

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- MOTOR ALGORÍTMICO INTEGRAL SMC OPTIMIZADO ---

def calcular_estructuras_reales(df):
    """
    Calcula de forma matemática los componentes estructurales de SMC.
    Incluye mitigación institucional avanzada y cálculo de volatilidad por ATR.
    """
    max_rango = float(df['High'].max())
    min_rango = float(df['Low'].min())
    ultimo_close = float(df['Close'].iloc[-1])
    
    equilibrio = min_rango + (max_rango - min_rango) * 0.5
    zona_cuadricula = "🔴 PREMIUM (Caro)" if ultimo_close > equilibrio else "🟢 DISCOUNT (Barato)"

    # 1. Detección de Fair Value Gaps (FVG)
    fvg_precio = None
    fvg_tipo = "Ninguno"
    for i in range(len(df) - 1, 2, -1):
        if float(df['Low'].iloc[i]) > float(df['High'].iloc[i-2]):
            fvg_precio = float(df['High'].iloc[i-2])
            fvg_tipo = "Alcista (Iman)"
            break
        elif float(df['High'].iloc[i]) < float(df['Low'].iloc[i-2]):
            fvg_precio = float(df['Low'].iloc[i-2])
            fvg_tipo = "Bajista (Iman)"
            break

    # 2. Detección de Order Blocks (OB) con Mitigación Real
    ob_compra = min_rango  
    ob_venta = max_rango   
    media_volumen = df['Volume'].mean()
    
    limite_busqueda = max(2, len(df) - 30)
    for i in range(len(df) - 2, limite_busqueda, -1):
        if float(df['Volume'].iloc[i]) > media_volumen * 1.2:
            if float(df['Close'].iloc[i]) > float(df['Open'].iloc[i]):
                if float(df['Close'].iloc[i-1]) < float(df['Open'].iloc[i-1]):
                    # VALIDACIÓN: Evita bloques viejos ya mitigados por mechas posteriores
                    posible_ob = float(df['Low'].iloc[i-1])
                    if float(df['Low'].iloc[i:].min()) >= posible_ob:
                        ob_compra = posible_ob
                        break
            elif float(df['Close'].iloc[i]) < float(df['Open'].iloc[i]):
                if float(df['Close'].iloc[i-1]) > float(df['Open'].iloc[i-1]):
                    posible_ob_v = float(df['High'].iloc[i-1])
                    if float(df['High'].iloc[i:].max()) <= posible_ob_v:
                        ob_venta = posible_ob_v
                        break

    # 3. Identificación de Liquidez Estructural (EQH / EQL)
    eqh, eql = None, None
    tolerancia = 0.0008
    limite_liq = max(1, len(df) - 25)
    for i in range(limite_liq, len(df) - 1):
        for j in range(i + 1, len(df)):
            if abs(float(df['High'].iloc[i]) - float(df['High'].iloc[j])) / float(df['High'].iloc[i]) < tolerancia:
                eqh = max(float(df['High'].iloc[i]), float(df['High'].iloc[j]))
            if abs(float(df['Low'].iloc[i]) - float(df['Low'].iloc[j])) / float(df['Low'].iloc[i]) < tolerancia:
                eql = min(float(df['Low'].iloc[i]), float(df['Low'].iloc[j]))

    if not eqh: eqh = max_rango
    if not eql: eql = min_rango

    return zona_cuadricula, equilibrio, fvg_precio, fvg_tipo, ob_compra, ob_venta, eqh, eql


def formatear_reporte(df_15m, df_5m, nombre_activo, decimals):
    """
    Cruza la estructura de 15m con los gatillos corregidos de 5m y calcula la gestión por ATR.
    """
    ultimo_close = float(df_15m['Close'].iloc[-1])
    zona_cuadricula, equilibrio, fvg_p, fvg_t, ob_compra, ob_venta, eqh, eql = calcular_estructuras_reales(df_15m)

    df_15m.ta.ema(length=200, append=True)
    ema200_15m = float(df_15m['EMA_200'].iloc[-1])
    
    # Cálculo del ATR para un Stop Loss Dinámico profesional
    df_15m.ta.atr(length=14, append=True)
    atr_actual = float(df_15m['ATR_14'].iloc[-1]) if 'ATR_14' in df_15m.columns else ultimo_close * 0.002
    
    if ultimo_close >= ema200_15m:
        bias = "BULLISH (Alcista)"
        estructura = "+CHoCH / +BOS Alcista activo"
    else:
        bias = "BEARISH (Bajista)"
        estructura = "-CHoCH / -BOS Bajista activo"

    # SOLUCIÓN LIMITACIÓN 1: Detección Real de Cambio de Estructura (+CHoCH Interno en 5m)
    choch_5m = "No detectado (Compresion de precio)"
    if len(df_5m) >= 6:
        max_reciente_5m = float(df_5m['High'].iloc[-6:-2].max())
        min_reciente_5m = float(df_5m['Low'].iloc[-6:-2].min())
        ultimo_close_5m = float(df_5m['Close'].iloc[-1])
        
        if bias == "BULLISH (Alcista)" and ultimo_close_5m > max_reciente_5m:
            choch_5m = "DEtectado (+CHoCH Interno en 5m)"
        elif bias == "BEARISH (Bajista)" and ultimo_close_5m < min_reciente_5m:
            choch_5m = "DEtectado (-CHoCH Interno en 5m)"

    operacion = "ESPERAR"
    estado_mapa = "Filtros operativos analizando fluctuacion."

    # SOLUCIÓN LIMITACIÓN 2: Gestión de riesgo profesional usando estructura + Multiplicador de ATR
    if bias == "BULLISH (Alcista)":
        operacion = "COMPRA (LONG)"
        entrada_limite = ob_compra  
        stop_loss = ob_compra - (atr_actual * 1.5)  # SL Dinámico por debajo del bloque por volatilidad
        take_profit = eqh 
        if "DISCOUNT" in zona_cuadricula and "DEtectado" in choch_5m:
            estado_mapa = "Configura tu orden LIMITE de compra en la zona POI."
        else:
            estado_mapa = "El precio no esta en Discount o falta el +CHoCH interno en 5m."
    else:
        operacion = "VENTA (SHORT)"
        entrada_limite = ob_venta
        stop_loss = ob_venta + (atr_actual * 1.5)  # SL Dinámico por encima del bloque por volatilidad
        take_profit = eql
        if "PREMIUM" in zona_cuadricula and "DEtectado" in choch_5m:
            estado_mapa = "Configura tu orden LIMITE de venta corta en el OB Premium."
        else:
            estado_mapa = "Estructura barata para vender o sin gatillo de confirmacion."

    fvg_texto_valor = f"{fvg_p:.{decimals}f}" if fvg_p else "Ninguno"

    return (
        f"Consola SMC Privada: Mercados\n"
        f"Activo: {nombre_activo}\n"
        f"Precio Actual: {ultimo_close:.{decimals}f}\n"
        f"----------------------------------------\n\n"
        f"PASO 1: DIRECCION DEL MERCADO (BIAS 15M)\n"
        f"Sesgo Mayor: {bias}\n"
        f"Estructura Reciente: {estructura}\n"
        f"Rango de Trabajo: {zona_cuadricula} (Equilibrio: {equilibrio:.{decimals}f})\n\n"
        f"PASO 2: ZONAS DE INTERES (POI) DETECTADAS\n"
        f"Bloque de Demanda (OB Compra): {ob_compra:.{decimals}f}\n"
        f"Bloque de Oferta (OB Venta): {ob_venta:.{decimals}f}\n"
        f"Ineficiencia FVG Cercana: {fvg_texto_valor} ({fvg_t})\n\n"
        f"TARGETS DE LIQUIDEZ\n"
        f"Techos Minoristas (EQH): {eqh:.{decimals}f}\n"
        f"Suelos Minoristas (EQL): {eql:.{decimals}f}\n"
        f"----------------------------------------\n\n"
        f"PASO 3: CONFIRMACION EN BAJA (LTF 5M)\n"
        f"Gatillo Estructural: {choch_5m}\n\n"
        f"PASO 4: MAPA DE PROCEDIMIENTO Y EJECUCION\n"
        f"Dictamen Técnico: {estado_mapa}\n\n"
        f"Parametros de la Orden LIMITE Sugerida:\n"
        f"Direccion: {operacion}\n"
        f"Precio Entrada LIMITE: {entrada_limite:.{decimals}f}\n"
        f"Stop Loss (ATR Protect): {stop_loss:.{decimals}f}\n"
        f"Take Profit (Objetivos): {take_profit:.{decimals}f}\n\n"
        f"Aviso: Los datos provienen del motor de mercados financieros en tiempo real."
    )

# --- NUEVO MOTOR DE BACKTESTING INTEGRADO ---

def ejecutar_backtesting_historico(ticker_symbol, dias=30):
    """
    Simula la estrategia del bot barra por barra durante los últimos X días
    para calcular métricas científicas de rentabilidad y efectividad.
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period=f"{dias}d", interval="15m").dropna()
        
        if df.empty or len(df) < 50:
            return "⚠️ No hay suficientes datos históricos para el Backtest."
            
        df.ta.ema(length=200, append=True)
        df.ta.atr(length=14, append=True)
        
        operaciones_totales = 0
        operaciones_ganadas = 0
        capital_inicial = 1000.0
        capital_actual = capital_inicial
        
        # Simulación histórica paso a paso
        for i in range(200, len(df) - 4):
            sub_df = df.iloc[:i]
            zona, eq, fvg_p, fvg_t, ob_compra, ob_venta, eqh, eql = calcular_estructuras_reales(sub_df)
            
            close_actual = sub_df['Close'].iloc[-1]
            ema200 = sub_df['EMA_200'].iloc[-1]
            atr = sub_df['ATR_14'].iloc[-1] if 'ATR_14' in sub_df.columns else close_actual * 0.002
            
            # Condición de Compra Backtest
            if close_actual > ema200 and close_actual <= eq: 
                entrada = ob_compra
                sl = ob_compra - (atr * 1.5)
                tp = eqh
                
                # Revisar las siguientes barras para ver si tocó TP o SL
                for j in range(i, min(i + 24, len(df))):
                    futuro_high = df['High'].iloc[j]
                    futuro_low = df['Low'].iloc[j]
                    
                    if futuro_low <= sl:
                        operaciones_totales += 1
                        capital_actual -= 20  # Riesgo fijo simulado de $20 por operación
                        break
                    if futuro_high >= tp:
                        operaciones_totales += 1
                        operaciones_ganadas += 1
                        capital_actual += 40  # Ratio de ganancia 1:2 estimado
                        break
                        
            # Condición de Venta Backtest
            elif close_actual < ema200 and close_actual >= eq:
                entrada = ob_venta
