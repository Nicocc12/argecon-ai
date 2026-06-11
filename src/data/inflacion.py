# src/data/inflacion.py

import requests
import urllib3
from dataclasses import dataclass
from datetime import date, timedelta
from collections import defaultdict

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ─── MODELO DE DATOS ──────────────────────────────────────────────────────────

@dataclass
class DatoMensual:
    """Representa el valor del índice IPC al cierre de un mes."""
    mes: str      # "2025-05"
    valor: float  # valor del índice al último día del mes

    def to_dict(self) -> dict:
        return {"mes": self.mes, "valor": self.valor}


# ─── CONSTANTES ───────────────────────────────────────────────────────────────

ID_IPC = 40
URL_BASE = "https://api.bcra.gob.ar/estadisticas/v4.0/monetarias"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "es-AR,es;q=0.9",
}


# ─── FUNCIÓN DE ACCESO A LA API ───────────────────────────────────────────────

def obtener_datos_diarios(meses: int = 13) -> list[dict]:
    """
    Trae los datos diarios del IPC desde la API del BCRA.

    LECCIÓN APRENDIDA: la API v4.0 tiene una estructura distinta a lo esperado:
    - Los datos no están en results[] directamente
    - Están en results[0]["detalle"] como lista de {fecha, valor}
    - La frecuencia es diaria, no mensual
    """
    hoy = date.today()
    fecha_hasta = hoy.strftime("%Y-%m-%d")
    fecha_desde = (hoy - timedelta(days=meses * 31)).strftime("%Y-%m-%d")

    url = f"{URL_BASE}/{ID_IPC}"
    params = {"desde": fecha_desde, "hasta": fecha_hasta}

    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=10, verify=False)
        response.raise_for_status()

        resultados = response.json().get("results", [])

        if not resultados:
            return []

        # ─ ESTRUCTURA REAL DE LA API v4.0 ─────────────────────────────────────
        # results es una lista de UN solo objeto que contiene "detalle"
        # results = [
        #   {
        #     "idVariable": 40,
        #     "detalle": [                    <- acá están los datos reales
        #       {"fecha": "2026-05-27", "valor": 33.12},
        #       ...
        #     ]
        #   }
        # ]
        detalle = resultados[0].get("detalle", [])
        return detalle

    except requests.exceptions.Timeout:
        raise ConnectionError("Timeout al consultar datos de inflación.")
    except requests.exceptions.ConnectionError:
        raise ConnectionError("No se pudo conectar a la API del BCRA.")
    except requests.exceptions.HTTPError as e:
        raise ConnectionError(f"Error HTTP al consultar inflación: {e}")


def agrupar_por_mes(datos_diarios: list[dict]) -> list[DatoMensual]:
    """
    Agrupa los datos diarios tomando el ÚLTIMO valor de cada mes.

    Como la API devuelve datos diarios, necesitamos "resamplear" a mensual.
    Tomamos el último día disponible de cada mes como representativo.

    Ej: de 30 registros de junio, nos quedamos con el del 30/06.
    """
    # defaultdict(list) crea automáticamente una lista vacía para claves nuevas
    # Así no necesitamos chequear "if mes in dict" antes de hacer append
    por_mes = defaultdict(list)

    for item in datos_diarios:
        fecha = item.get("fecha", "")
        valor = item.get("valor", 0)
        if fecha:
            mes = fecha[:7]  # "2025-06-15" -> "2025-06"
            por_mes[mes].append(valor)

    # Tomamos el máximo valor de cada mes como representativo del cierre
    datos_mensuales = []
    for mes in sorted(por_mes.keys()):
        valor_cierre = max(por_mes[mes])  # el valor más alto = el más reciente del mes
        datos_mensuales.append(DatoMensual(mes=mes, valor=valor_cierre))

    return datos_mensuales


# ─── FUNCIÓN DE ANÁLISIS ──────────────────────────────────────────────────────

def obtener_resumen_para_ia() -> dict:
    """
    Construye un resumen del IPC con variaciones mensuales y tendencia.
    """
    datos_diarios = obtener_datos_diarios(meses=13)

    if not datos_diarios:
        return {"error": "No se pudieron obtener datos de inflación."}

    mensuales = agrupar_por_mes(datos_diarios)

    if len(mensuales) < 2:
        return {"error": "Datos insuficientes para calcular variaciones."}

    # Calculamos la variación porcentual mes a mes
    # Var% = (valor_actual - valor_anterior) / valor_anterior * 100
    variaciones = []
    for i in range(1, len(mensuales)):
        anterior = mensuales[i - 1].valor
        actual   = mensuales[i].valor
        if anterior > 0:
            variacion = round((actual - anterior) / anterior * 100, 2)
            variaciones.append({"mes": mensuales[i].mes, "variacion_pct": variacion})

    if not variaciones:
        return {"error": "No se pudieron calcular variaciones mensuales."}

    ultimo = variaciones[-1]
    valores_var = [v["variacion_pct"] for v in variaciones]
    promedio = round(sum(valores_var) / len(valores_var), 2)

    # Tendencia: últimos 3 meses vs 3 anteriores
    tendencia = "sin datos suficientes"
    if len(valores_var) >= 6:
        reciente  = sum(valores_var[-3:]) / 3
        anterior  = sum(valores_var[-6:-3]) / 3
        if reciente > anterior * 1.05:
            tendencia = "acelerando"
        elif reciente < anterior * 0.95:
            tendencia = "desacelerando"
        else:
            tendencia = "estable"

    # Acumulado anual con los últimos 12 meses de variaciones
    ultimos_12 = valores_var[-12:]
    factor = 1.0
    for v in ultimos_12:
        factor *= (1 + v / 100)
    acumulado = round((factor - 1) * 100, 2)

    return {
        "ultimo_mes": ultimo,
        "promedio_mensual": promedio,
        "tendencia": tendencia,
        "acumulado_anual_estimado": acumulado,
        "historial": variaciones,
    }


# ─── BLOQUE DE PRUEBA ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("📈 Consultando inflación (BCRA v4.0)...\n")

    try:
        resumen = obtener_resumen_para_ia()

        if "error" in resumen:
            print(f"⚠️  {resumen['error']}")
        else:
            print(f"📅 Último mes:      {resumen['ultimo_mes']['mes']}")
            print(f"📊 Variación:       {resumen['ultimo_mes']['variacion_pct']}%")
            print(f"📉 Tendencia:       {resumen['tendencia']}")
            print(f"📆 Promedio mensual:{resumen['promedio_mensual']}%")
            print(f"🔥 Acumulado anual: {resumen['acumulado_anual_estimado']}%")
            print(f"\n📋 Historial ({len(resumen['historial'])} meses):")
            for v in resumen["historial"]:
                barra = "█" * int(v["variacion_pct"])
                print(f"   {v['mes']}  {v['variacion_pct']:5.2f}%  {barra}")

    except ConnectionError as e:
        print(f"❌ Error: {e}")