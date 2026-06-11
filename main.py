<<<<<<< HEAD
# main.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os
from dotenv import load_dotenv
from groq import Groq

# Importamos nuestros tres módulos de datos
from src.data import dolar, bcra, inflacion

# ─── CONFIGURACIÓN INICIAL ────────────────────────────────────────────────────

# load_dotenv() lee el archivo .env y carga las variables de entorno
# Así GROQ_API_KEY queda disponible con os.getenv()
load_dotenv()

app = FastAPI(
    title="ArgEcon AI",
    description="Agente de análisis económico argentino con IA",
    version="1.0.0",
)

# CORS permite que el frontend (HTML/JS) pueda llamar a la API
# Sin esto, el browser bloquea las requests por seguridad
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializamos el cliente de Groq con la API key del .env
cliente_groq = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ─── PROMPT DEL SISTEMA ───────────────────────────────────────────────────────
#
# El "system prompt" define el ROL y COMPORTAMIENTO del agente.
# Es la instrucción base que el LLM recibe antes del mensaje del usuario.
# Un buen system prompt es la diferencia entre una IA genérica y un agente útil.

SYSTEM_PROMPT = """
Sos un economista argentino experto, con profundo conocimiento del mercado cambiario,
la política monetaria del BCRA y la dinámica inflacionaria de Argentina.

Tu tarea es analizar datos económicos en tiempo real y generar un resumen claro,
preciso y útil para un ciudadano argentino promedio que quiere entender qué está
pasando con la economía.

REGLAS:
- Respondé siempre en español rioplatense (usá "vos", no "tú")
- Sé directo y concreto, evitá la jerga técnica innecesaria
- Destacá lo más relevante primero
- Si hay señales de alerta (inflación acelerando, reservas cayendo), mencionalo claramente
- Usá emojis con moderación para facilitar la lectura
- Máximo 300 palabras en tu análisis

Formato de respuesta:
📌 SITUACIÓN ACTUAL
[2-3 oraciones con el panorama general]

💵 TIPO DE CAMBIO
[análisis de las cotizaciones más importantes]

📈 INFLACIÓN
[análisis de la tendencia inflacionaria]

🏦 VARIABLES BCRA
[análisis de reservas y política monetaria]

⚠️ PUNTOS DE ATENCIÓN
[1-3 alertas o tendencias a seguir]
"""


# ─── ENDPOINTS ────────────────────────────────────────────────────────────────

@app.get("/api/datos")
async def obtener_datos():
    """
    Endpoint que recolecta y devuelve todos los datos económicos en tiempo real.
    
    'async def' en vez de 'def' permite que FastAPI maneje múltiples requests
    simultáneas sin bloquear. Importante cuando hay llamadas a APIs externas.
    """
    errores = []
    resultado = {}

    # Recolectamos datos de cada módulo de forma independiente
    # Si uno falla, el resto sigue funcionando
    try:
        resultado["dolar"] = dolar.obtener_resumen_para_ia()
    except Exception as e:
        errores.append(f"dolar: {str(e)}")
        resultado["dolar"] = {}

    try:
        resultado["bcra"] = bcra.obtener_resumen_para_ia()
    except Exception as e:
        errores.append(f"bcra: {str(e)}")
        resultado["bcra"] = {}

    try:
        resultado["inflacion"] = inflacion.obtener_resumen_para_ia()
    except Exception as e:
        errores.append(f"inflacion: {str(e)}")
        resultado["inflacion"] = {}

    if errores:
        resultado["advertencias"] = errores

    return resultado


@app.get("/api/analisis")
async def obtener_analisis():
    """
    Endpoint principal: recolecta datos y genera análisis con IA.
    
    Flujo:
    1. Llama a /api/datos para obtener el contexto económico
    2. Arma un prompt con esos datos
    3. Se lo manda a Groq (LLaMA 3)
    4. Devuelve el análisis generado
    """
    # Paso 1: obtener datos frescos
    datos = await obtener_datos()

    # Paso 2: convertir los datos a texto legible para el LLM
    # Los LLMs entienden mejor texto estructurado que JSON crudo
    contexto = _formatear_datos_para_llm(datos)

    # Paso 3: llamar a Groq
    try:
        respuesta = cliente_groq.chat.completions.create(
            model="llama-3.3-70b-versatile",  # modelo más capaz de Groq
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": f"Analizá estos datos económicos de Argentina:\n\n{contexto}"},
            ],
            temperature=0.4,   # 0=determinista, 1=creativo. 0.4 = balance
            max_tokens=600,    # límite de respuesta
        )

        analisis = respuesta.choices[0].message.content

        return {
            "analisis": analisis,
            "datos_utilizados": datos,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar el modelo de IA: {str(e)}"
        )


def _formatear_datos_para_llm(datos: dict) -> str:
    """
    Convierte el JSON de datos en texto legible para el LLM.
    
    Los modelos de lenguaje procesan mejor el texto natural que JSON crudo.
    Esta función hace esa traducción.
    
    El guión bajo al inicio (_formatear...) es convención Python para indicar
    que es una función "privada" (solo para uso interno de este módulo).
    """
    lineas = []

    # Dólar
    dolar_data = datos.get("dolar", {})
    if dolar_data:
        lineas.append("=== COTIZACIONES DEL DÓLAR ===")
        for nombre, vals in dolar_data.items():
            lineas.append(
                f"- {nombre}: compra ${vals.get('compra', 0):,.0f} / "
                f"venta ${vals.get('venta', 0):,.0f} / "
                f"spread ${vals.get('spread', 0):,.0f}"
            )

    # BCRA
    bcra_data = datos.get("bcra", {})
    if bcra_data:
        lineas.append("\n=== VARIABLES BCRA ===")
        for nombre, vals in bcra_data.items():
            lineas.append(
                f"- {nombre}: {vals.get('valor', 0):,.2f} (al {vals.get('fecha', 'N/A')})"
            )

    # Inflación
    inf_data = datos.get("inflacion", {})
    if inf_data and "error" not in inf_data:
        lineas.append("\n=== INFLACIÓN ===")
        lineas.append(f"- Último mes ({inf_data.get('ultimo_mes', {}).get('mes', '')}): "
                      f"{inf_data.get('ultimo_mes', {}).get('variacion_pct', 0)}%")
        lineas.append(f"- Promedio mensual 12m: {inf_data.get('promedio_mensual', 0)}%")
        lineas.append(f"- Acumulado anual estimado: {inf_data.get('acumulado_anual_estimado', 0)}%")
        lineas.append(f"- Tendencia: {inf_data.get('tendencia', 'N/A')}")

    return "\n".join(lineas)


# ─── FRONTEND ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def frontend():
    """Sirve el frontend HTML. Lo construimos en el próximo paso."""
    with open("frontend/index.html", "r", encoding="utf-8") as f:
=======
# main.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os
from dotenv import load_dotenv
from groq import Groq

# Importamos nuestros tres módulos de datos
from src.data import dolar, bcra, inflacion

# ─── CONFIGURACIÓN INICIAL ────────────────────────────────────────────────────

# load_dotenv() lee el archivo .env y carga las variables de entorno
# Así GROQ_API_KEY queda disponible con os.getenv()
load_dotenv()

app = FastAPI(
    title="ArgEcon AI",
    description="Agente de análisis económico argentino con IA",
    version="1.0.0",
)

# CORS permite que el frontend (HTML/JS) pueda llamar a la API
# Sin esto, el browser bloquea las requests por seguridad
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializamos el cliente de Groq con la API key del .env
cliente_groq = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ─── PROMPT DEL SISTEMA ───────────────────────────────────────────────────────
#
# El "system prompt" define el ROL y COMPORTAMIENTO del agente.
# Es la instrucción base que el LLM recibe antes del mensaje del usuario.
# Un buen system prompt es la diferencia entre una IA genérica y un agente útil.

SYSTEM_PROMPT = """
Sos un economista argentino experto, con profundo conocimiento del mercado cambiario,
la política monetaria del BCRA y la dinámica inflacionaria de Argentina.

Tu tarea es analizar datos económicos en tiempo real y generar un resumen claro,
preciso y útil para un ciudadano argentino promedio que quiere entender qué está
pasando con la economía.

REGLAS:
- Respondé siempre en español rioplatense (usá "vos", no "tú")
- Sé directo y concreto, evitá la jerga técnica innecesaria
- Destacá lo más relevante primero
- Si hay señales de alerta (inflación acelerando, reservas cayendo), mencionalo claramente
- Usá emojis con moderación para facilitar la lectura
- Máximo 300 palabras en tu análisis

Formato de respuesta:
📌 SITUACIÓN ACTUAL
[2-3 oraciones con el panorama general]

💵 TIPO DE CAMBIO
[análisis de las cotizaciones más importantes]

📈 INFLACIÓN
[análisis de la tendencia inflacionaria]

🏦 VARIABLES BCRA
[análisis de reservas y política monetaria]

⚠️ PUNTOS DE ATENCIÓN
[1-3 alertas o tendencias a seguir]
"""


# ─── ENDPOINTS ────────────────────────────────────────────────────────────────

@app.get("/api/datos")
async def obtener_datos():
    """
    Endpoint que recolecta y devuelve todos los datos económicos en tiempo real.
    
    'async def' en vez de 'def' permite que FastAPI maneje múltiples requests
    simultáneas sin bloquear. Importante cuando hay llamadas a APIs externas.
    """
    errores = []
    resultado = {}

    # Recolectamos datos de cada módulo de forma independiente
    # Si uno falla, el resto sigue funcionando
    try:
        resultado["dolar"] = dolar.obtener_resumen_para_ia()
    except Exception as e:
        errores.append(f"dolar: {str(e)}")
        resultado["dolar"] = {}

    try:
        resultado["bcra"] = bcra.obtener_resumen_para_ia()
    except Exception as e:
        errores.append(f"bcra: {str(e)}")
        resultado["bcra"] = {}

    try:
        resultado["inflacion"] = inflacion.obtener_resumen_para_ia()
    except Exception as e:
        errores.append(f"inflacion: {str(e)}")
        resultado["inflacion"] = {}

    if errores:
        resultado["advertencias"] = errores

    return resultado


@app.get("/api/analisis")
async def obtener_analisis():
    """
    Endpoint principal: recolecta datos y genera análisis con IA.
    
    Flujo:
    1. Llama a /api/datos para obtener el contexto económico
    2. Arma un prompt con esos datos
    3. Se lo manda a Groq (LLaMA 3)
    4. Devuelve el análisis generado
    """
    # Paso 1: obtener datos frescos
    datos = await obtener_datos()

    # Paso 2: convertir los datos a texto legible para el LLM
    # Los LLMs entienden mejor texto estructurado que JSON crudo
    contexto = _formatear_datos_para_llm(datos)

    # Paso 3: llamar a Groq
    try:
        respuesta = cliente_groq.chat.completions.create(
            model="llama-3.3-70b-versatile",  # modelo más capaz de Groq
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": f"Analizá estos datos económicos de Argentina:\n\n{contexto}"},
            ],
            temperature=0.4,   # 0=determinista, 1=creativo. 0.4 = balance
            max_tokens=600,    # límite de respuesta
        )

        analisis = respuesta.choices[0].message.content

        return {
            "analisis": analisis,
            "datos_utilizados": datos,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar el modelo de IA: {str(e)}"
        )


def _formatear_datos_para_llm(datos: dict) -> str:
    """
    Convierte el JSON de datos en texto legible para el LLM.
    
    Los modelos de lenguaje procesan mejor el texto natural que JSON crudo.
    Esta función hace esa traducción.
    
    El guión bajo al inicio (_formatear...) es convención Python para indicar
    que es una función "privada" (solo para uso interno de este módulo).
    """
    lineas = []

    # Dólar
    dolar_data = datos.get("dolar", {})
    if dolar_data:
        lineas.append("=== COTIZACIONES DEL DÓLAR ===")
        for nombre, vals in dolar_data.items():
            lineas.append(
                f"- {nombre}: compra ${vals.get('compra', 0):,.0f} / "
                f"venta ${vals.get('venta', 0):,.0f} / "
                f"spread ${vals.get('spread', 0):,.0f}"
            )

    # BCRA
    bcra_data = datos.get("bcra", {})
    if bcra_data:
        lineas.append("\n=== VARIABLES BCRA ===")
        for nombre, vals in bcra_data.items():
            lineas.append(
                f"- {nombre}: {vals.get('valor', 0):,.2f} (al {vals.get('fecha', 'N/A')})"
            )

    # Inflación
    inf_data = datos.get("inflacion", {})
    if inf_data and "error" not in inf_data:
        lineas.append("\n=== INFLACIÓN ===")
        lineas.append(f"- Último mes ({inf_data.get('ultimo_mes', {}).get('mes', '')}): "
                      f"{inf_data.get('ultimo_mes', {}).get('variacion_pct', 0)}%")
        lineas.append(f"- Promedio mensual 12m: {inf_data.get('promedio_mensual', 0)}%")
        lineas.append(f"- Acumulado anual estimado: {inf_data.get('acumulado_anual_estimado', 0)}%")
        lineas.append(f"- Tendencia: {inf_data.get('tendencia', 'N/A')}")

    return "\n".join(lineas)


# ─── FRONTEND ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def frontend():
    """Sirve el frontend HTML. Lo construimos en el próximo paso."""
    with open("frontend/index.html", "r", encoding="utf-8") as f:
>>>>>>> dcebf359ab00daafb3fcfaa42f31ca7a1d37d74a
        return f.read()