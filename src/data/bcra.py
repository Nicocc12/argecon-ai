# src/data/bcra.py

import requests
from dataclasses import dataclass

# ─── MODELO DE DATOS ──────────────────────────────────────────────────────────

@dataclass
class VariableBCRA:
    """Representa una variable económica del Banco Central."""
    id: int
    descripcion: str
    fecha: str        # En v4.0 se llama "ultFechaInformada"
    valor: float      # En v4.0 se llama "ultValorInformado"

    def to_dict(self) -> dict:
        return {
            "descripcion": self.descripcion,
            "fecha": self.fecha,
            "valor": self.valor,
        }


# ─── IDs DE VARIABLES QUE NOS INTERESAN ───────────────────────────────────────
#
# La v4.0 devuelve +1000 variables. Filtramos solo las relevantes por ID.
# Los IDs se mantuvieron iguales entre versiones.

VARIABLES_RELEVANTES = {
    1:  "Reservas internacionales (millones USD)",
    5:  "Tipo de cambio mayorista ($/USD)",
    15: "Base monetaria (millones $)",
    27: "Tasa de política monetaria (% anual)",
    40: "Inflación mensual IPC (%)",
}


# ─── FUNCIONES DE ACCESO A LA API ─────────────────────────────────────────────

def obtener_todas_las_variables() -> list[VariableBCRA]:
    """
    Consulta el endpoint v4.0 de estadísticas monetarias del BCRA.

    IMPORTANTE: la v2.0 fue deprecada en junio 2025. Lección del mundo real:
    las APIs evolucionan y el código hay que mantenerlo actualizado.

    Estructura de respuesta v4.0:
    {
      "results": [
        {
          "idVariable": 1,
          "descripcion": "Reservas internacionales",
          "ultFechaInformada": "2025-05-19",   <- nombre nuevo
          "ultValorInformado": 38384            <- nombre nuevo
        },
        ...
      ]
    }
    """
    # v4.0: el endpoint ahora se llama "monetarias", no "principalesvariables"
    URL = "https://api.bcra.gob.ar/estadisticas/v4.0/monetarias"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Accept-Language": "es-AR,es;q=0.9",
    }

    try:
        response = requests.get(URL, timeout=10, verify=False, headers=headers)
        response.raise_for_status()

        datos_json = response.json().get("results", [])

        variables = []
        for item in datos_json:
            variable = VariableBCRA(
                id=item.get("idVariable", 0),
                descripcion=item.get("descripcion", ""),
                fecha=item.get("ultFechaInformada", ""),    # campo nuevo en v4.0
                valor=float(item.get("ultValorInformado", 0)),  # campo nuevo en v4.0
            )
            variables.append(variable)

        return variables

    except requests.exceptions.Timeout:
        raise ConnectionError("Timeout: la API del BCRA tardó más de 10 segundos.")
    except requests.exceptions.ConnectionError:
        raise ConnectionError("No se pudo conectar a api.bcra.gob.ar.")
    except requests.exceptions.HTTPError as e:
        raise ConnectionError(f"Error HTTP al consultar la API del BCRA: {e}")


def obtener_resumen_para_ia() -> dict:
    """
    Filtra y devuelve solo las variables económicas más relevantes.
    Esta es la función que usará FastAPI para armar el contexto del agente.
    """
    todas = obtener_todas_las_variables()

    resumen = {}
    for variable in todas:
        if variable.id in VARIABLES_RELEVANTES:
            clave = VARIABLES_RELEVANTES[variable.id]
            resumen[clave] = variable.to_dict()

    return resumen


# ─── BLOQUE DE PRUEBA ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    print("🏦 Consultando API del BCRA v4.0...\n")

    try:
        resumen = obtener_resumen_para_ia()

        if not resumen:
            print("No se encontraron variables relevantes.")
        else:
            for nombre, datos in resumen.items():
                print(f"📊 {nombre}")
                print(f"   Valor: {datos['valor']:,.2f}")
                print(f"   Fecha: {datos['fecha']}")
                print()

    except ConnectionError as e:
        print(f"❌ Error: {e}")