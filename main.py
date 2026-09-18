import asyncio
import io
import logging
import requests
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
import yfinance as yf
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

logging.basicConfig(level=logging.INFO)

# --- CONFIGURACIÓN DE SEGURIDAD EXCLUSIVA ---
TOKEN = "8882275126:AAG4joJlFJCCz1wFoWxPHm8pL9CfrvAJiZg"
MI_TELEGRAM_ID = 581924626  # 👈 REEMPLAZA ESTO CON TU ID NUMÉRICO REAL

bot = Bot(token=TOKEN)
dp = Dispatcher()

def analizar_activo(asset_type):
    df = pd.DataFrame()
    
    if asset_type == "BTC":
        url = "https://binance.com"
        params = {"symbol": "BTCUSDT", "interval": "15m", "limit": 100}
        try:
            response = requests.get(url, params=params).json()
            df = pd.DataFrame(response, columns=[
                'Open_time', 'Open', 'High', 'Low', 'Close', 'Volume', 
                'Close_time', 'Quote_asset_volume', 'Number_of_trades', 
                'Taker_buy_base_asset_volume', 'Taker_buy_quote_asset_volume', 'Ignore'
            ])
            df['Date'] = pd.to_datetime(df['Open_time'], unit='ms')
            df.set_index('Date', inplace=True)
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']].astype(float)
            nombre_activo = "Bitcoin (BTC/USDT) - 15m"
        except Exception:
            return None, "Error de conexión con Binance."

    elif asset_type == "EURUSD":
        try:
            ticker = yf.Ticker("EURUSD=X")
            df = ticker.history(period="5d", interval="15m")
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
            nombre_activo = "Euro / Dólar (EUR/USD) - 15m"
        except Exception:
            return None, "Error de conexión con Yahoo Finance."
    
    if df.empty:
        return None, "No se encontraron datos disponibles."

    # Indicadores técnicos adicionales para mejorar tus pruebas
    df.ta.rsi(length=14, append=True)
    df.ta.ema(length=20, append=True) # Media Móvil Exponencial de 20 períodos
    
    ultimo_rsi = df['RSI_14'].iloc[-1]
    ultimo_close = df['Close'].iloc[-1]
    ultima_ema = df['EMA_20'].iloc[-1]
    
    # Lógica combinada (Precio vs EMA + RSI)
    if ultimo_rsi > 70 and ultimo_close > ultima_ema:
        diagnostico = "⚠️ SOBRECOMPRA + TENDENCIA ALTA: Estiramiento alcista, buscar posibles reversiones cortas o salidas."
    elif ultimo_rsi < 30 and ultimo_close < ultima_ema:
        diagnostico = "✅ SOBREVENTA + TENDENCIA BAJA: Estiramiento bajista, buscar posibles rebotes alcistas."
    else:
        diagnostico = "🔄 CONSOLIDACIÓN: El mercado se mantiene dentro de la media móvil."

    buf = io.BytesIO()
    
    # Dibujar velas con la EMA_20 superpuesta en el gráfico
    apds = [mpf.make_addplot(df['EMA_20'].tail(40), color='orange', width=1.5)]
    
    mpf.plot(
        df.tail(40), 
        type='candle', 
        style='charles', 
        title=f"\n{nombre_activo}",
        addplot=apds,
        volume=True, 
        savefig=dict(fname=buf, bbox_inches='tight')
    )
    buf.seek(0)
    
    caption = (
        f"📊 **Telemetría de Prueba: {nombre_activo}**\n\n"
        f"💵 Precio Actual: `{ultimo_close:.4f}`\n"
        f"📈 EMA (20): `{ultima_ema:.4f}`\n"
        f"📉 RSI (14): `{ultimo_rsi:.2f}`\n\n"
        f"💡 **Diagnóstico Algorítmico:**\n{diagnostico}"
    )
    
    return buf, caption

# --- FILTRO DE AUDITORÍA: CONTROL DE ACCESO ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Verificación estricta de identidad
    if message.from_user.id != MI_TELEGRAM_ID:
        logging.warning(f"Acceso denegado al ID no autorizado: {message.from_user.id}")
        return # El bot ignora silenciosamente a cualquier intruso

    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🔶 Analizar Bitcoin (BTC)", callback_data="analizar_BTC"),
        types.InlineKeyboardButton(text="💶 Analizar Forex (EUR/USD)", callback_data="analizar_EURUSD")
    )
    
    await message.answer(
        "⚙️ **Entorno de Prueba Privado Activo**\n\n"
        "Selecciona el activo para generar el análisis bajo demanda:",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(lambda c: c.data.startswith("analizar_"))
async def procesar_analisis(callback_query: types.CallbackQuery):
    # Verificación de identidad en las interacciones de botones
    if callback_query.from_user.id != MI_TELEGRAM_ID:
        await callback_query.answer("No tienes autorización para usar este entorno.", show_alert=True)
        return

    activo = callback_query.data.split("_")[1]
    await callback_query.answer("Calculando indicadores de mercado...")
    mensaje_espera = await callback_query.message.answer("🔄 Extrayendo datos y graficando...")
    
    try:
        grafico_buffer, texto_caption = await asyncio.to_thread(analizar_activo, activo)
        
        if grafico_buffer is None:
            await mensaje_espera.edit_text(texto_caption)
            return

        foto = types.BufferedInputFile(grafico_buffer.read(), filename=f"{activo}.png")
        await callback_query.message.answer_photo(photo=foto, caption=texto_caption, parse_mode="Markdown")
        
    except Exception as e:
        logging.error(f"Error en el análisis: {e}")
        await callback_query.message.answer("❌ Error al procesar el gráfico en el servidor.")
    
    finally:
        await mensaje_espera.delete()

async def main():
    print("Bot privado iniciado de manera segura. Solo respondiendo a tu ID.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
          
