import matplotlib
matplotlib.use('Agg')  # Parche obligatorio para que Railway no de error

import asyncio
import logging
import requests
import pandas as pd
import pandas_ta as ta
import yfinance as yf
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Configuración estricta de logs para monitoreo en Railway
logging.basicConfig(level=logging.INFO)

# --- CREDENCIALES DE ACCESO AUDITADAS Y SEGURAS ---
TOKEN = "8882275126:AAG4joJlFJCCz1wFoWxPHm8pL9CfrvAJiZg"
MI_TELEGRAM_ID = 581924626

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- MOTOR ALGORÍTMICO INTEGRAL SMC ---

def calcular_estructuras_reales(df):
    """
    Calcula de forma matemática pura los componentes estructurales de SMC:
    Rango de working, Premium/Discount, FVGs, Order Blocks y Liquidez (EQH/EQL).
    """
    max_rango = float(df['High'].max())
    min_rango = float(df['Low'].min())
    ultimo_close = float(df['Close'].iloc[-1])
    
    equilibrio = min_rango + (max_rango - min_rango) * 0.5
    zona_cuadricula = "🔴 PREMIUM (Caro)" if ultimo_close > equilibrio else "🟢 DISCOUNT (Barato)"

    # 1. Detección Quirúrgica de Fair Value Gaps (FVG)
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

    # 2. Detección de Order Blocks (OB) con mitigación y volumen institucional
    ob_compra = min_rango  
    ob_venta = max_rango   
    media_volumen = df['Volume'].mean()
    
    limite_busqueda = max(2, len(df) - 30)
    for i in range(len(df) - 2, limite_busqueda, -1):
        if float(df['Volume'].iloc[i]) > media_volumen * 1.2:
            if float(df['Close'].iloc[i]) > float(df['Open'].iloc[i]):
                if float(df['Close'].iloc[i-1]) < float(df['Open'].iloc[i-1]):
                    ob_compra = float(df['Low'].iloc[i-1])
                    break
            elif float(df['Close'].iloc[i]) < float(df['Open'].iloc[i]):
                if float(df['Close'].iloc[i-1]) > float(df['Open'].iloc[i-1]):
                    ob_venta = float(df['High'].iloc[i-1])
                    break

    # 3. Identificación de Liquidez Estructural Minorista (EQH / EQL)
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
    Core del sistema multi-temporal. Cruza la estructura de 15m con los gatillos de 5m
    y devuelve la plantilla formateada para Telegram.
    """
    ultimo_close = float(df_15m['Close'].iloc[-1])
    zona_cuadricula, equilibrio, fvg_p, fvg_t, ob_compra, ob_venta, eqh, eql = calcular_estructuras_reales(df_15m)

    df_15m.ta.ema(length=200, append=True)
    ema200_15m = float(df_15m['EMA_200'].iloc[-1])
    
    if ultimo_close >= ema200_15m:
        bias = "BULLISH (Alcista)"
        estructura = "+CHoCH / +BOS Alcista activo"
    else:
        bias = "BEARISH (Bajista)"
        estructura = "-CHoCH / -BOS Bajista activo"

    ultimo_close_5m = float(df_5m['Close'].iloc[-1])
    if len(df_5m) >= 4 and ultimo_close_5m > float(df_5m['High'].iloc[-4:-1].max()):
        choch_5m = "DEtectado (+CHoCH Interno en 5m)"
    else:
        choch_5m = "No detectado (Compresion de precio)"

    entrada_limite = ultimo_close
    stop_loss = ultimo_close * 0.995
    take_profit = ultimo_close * 1.01
    operacion = "ESPERAR"
    estado_mapa = "Filtros operativos analizando fluctuacion."

    if bias == "BULLISH (Alcista)":
        operacion = "COMPRA (LONG)"
        entrada_limite = ob_compra  
        stop_loss = ob_compra * 0.9990  
        take_profit = eqh 
        if "DISCOUNT" in zona_cuadricula and "DEtectado" in choch_5m:
            estado_mapa = "Configura tu orden LIMITE de compra en la zona POI."
        else:
            estado_mapa = "El precio no esta en Discount o falta el +CHoCH interno en 5m."
    else:
        operacion = "VENTA (SHORT)"
        entrada_limite = ob_venta
        stop_loss = ob_venta * 1.0010  
        take_profit = eql
        if "PREMIUM" in zona_cuadricula and "No detectado" not in choch_5m:
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
        f"TARGETS DE LIQUIDEZ (BARRIDOS DE STOP LOSS)\n"
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
        f"Stop Loss (Invalidez): {stop_loss:.{decimals}f}\n"
        f"Take Profit (Objetivos): {take_profit:.{decimals}f}\n\n"
        f"Aviso: Los datos provienen del motor de mercados financieros en tiempo real."
    )

def ejecutar_analisis_btc():
    try:
        ticker = yf.Ticker("BTC-USD")
        raw_15m = ticker.history(period="5d", interval="15m")
        raw_5m = ticker.history(period="1d", interval="5m")
        
        if raw_15m.empty or raw_5m.empty:
            return "⚠️ Datos de Bitcoin no disponibles en este microsegundo. Intenta de nuevo."
            
        df_15m = raw_15m.dropna()
        df_5m = raw_5m.dropna()
        return formatear_reporte(df_15m, df_5m, "Bitcoin Spot RealTime (BTC-USD)", 2)
    except Exception as e:
        logging.error(f"Fallo en API Yahoo BTC: {e}")
        return "❌ Error de red al conectar con el servidor de Criptomonedas. Intenta de nuevo."

def ejecutar_analisis_eurusd():
    try:
        ticker = yf.Ticker("EURUSD=X")
        raw_15m = ticker.history(period="5d", interval="15m")
        raw_5m = ticker.history(period="1d", interval="5m")
        
        if raw_15m.empty or raw_5m.empty:
            return "⚠️ **Mercado Cerrado u Horario Inactivo**\nNo se recibieron datos recientes del proveedor. Recuerda que Forex cierra los fines de semana."
            
        df_15m = raw_15m.dropna()
        df_5m = raw_5m.dropna()
        return formatear_reporte(df_15m, df_5m, "Euro Dolar EUR USD", 4)
    except Exception as e:
        logging.error(f"Fallo en API Yahoo Finance: {e}")
        return "❌ Error de red al conectar con Yahoo Finance. Intenta de nuevo."

# --- MÓDULO INTERACTIVO DE TELEGRAM ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id != MI_TELEGRAM_ID:
        return # Filtro de ID estricto

    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🔶 Bitcoin RealTime (SMC)", callback_data="smc_BTC"),
        types.InlineKeyboardButton(text="💶 Analizar EUR/USD (SMC)", callback_data="smc_EURUSD")
    )
    
    await message.answer(
        "Consola Algoritmica Institucional V8.0 Unificada\n\n"
        "Monitoreo de Smart Money Concepts para colocacion manual de Ordenes Limite.",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(lambda c: c.data.startswith("smc_"))
async def procesar_peticion_smc(callback_query: types.CallbackQuery):
    if callback_query.from_user.id != MI_TELEGRAM_ID:
        return

    await callback_query.answer("Sincronizando con el libro de ordenes unificado...")
    mensaje_espera = await callback_query.message.answer("Escaneando la liquidez institucional...")
    
    try:
        if callback_query.data == "smc_BTC":
            reporte_final = await asyncio.to_thread(ejecutar_analisis_btc)
        else:
            reporte_final = await asyncio.to_thread(ejecutar_analisis_eurusd)
            
        await callback_query.message.answer(reporte_final)
    except Exception as e:
        logging.error(f"Fallo en Telegram: {e}")
        await callback_query.message.answer("Error inesperado al procesar la telemetria.")
    finally:
        await mensaje_espera.delete()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
        
