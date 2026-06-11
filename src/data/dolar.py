# src/data/dolar.py

import requests
from dataclasses import dataclass  # Módulo estándar de Python para crear clases de datos

# ─── MODELO DE DATOS ──────────────────────────────────────────────────────────
#
# @dataclass es un decorador que genera automáticamente __init__, __repr__
# y __eq__ para nuestra clase. En vez de escribir def __init__(self, nombre, compra...)
# a mano, Python lo hace solo. Ideal para objetos que solo guardan datos.

@dataclass
class Cotizacion:
    """Representa una cotización del dólar en un momento dado."""
    nombre: str          # "Blue", "Oficial", "MEP", etc.
    compra: float        # Precio al que el mercado compra dólares
    venta: float         # Precio al que el mercado vende dólares

    def spread(self) -> float:
        """
        El spread es la diferencia entre venta y compra.
        Es un indicador de cuánto gana el intermediario (o la brecha del mercado).
        
        -> float indica el tipo de retorno. No es obligatorio, pero es buena práctica.
        """
        return round(self.venta - self.compra, 2)

    def to_dict(self) -> dict:
        """
        Convierte la cotización a diccionario.
        Útil para enviarle los datos al modelo de IA más adelante.
        """
        return {
            "nombre": self.nombre,
            "compra": self.compra,
            "venta": self.venta,
            "spread": self.spread(),
        }


# ─── FUNCIONES DE ACCESO A LA API ─────────────────────────────────────────────

def obtener_todas_las_cotizaciones() -> list[Cotizacion]:
    """
    Consulta dolarapi.com y devuelve TODAS las cotizaciones disponibles.
    
    Esta función es 'de bajo nivel': trae todo, sin filtrar.
    list[Cotizacion] es type hint: le decimos que devuelve una lista de Cotizacion.
    """
    URL = "https://dolarapi.com/v1/dolares"

    try:
        # timeout=10: si la API no responde en 10 segundos, lanzamos error.
        # Sin timeout, el programa podría quedarse colgado para siempre.
        response = requests.get(URL, timeout=10)
        
        # raise_for_status() lanza una excepción si el servidor devolvió
        # un error HTTP (404 Not Found, 500 Server Error, etc.)
        response.raise_for_status()
        
        # La API devuelve una lista de objetos JSON, cada uno con:
        # { "nombre": "Blue", "compra": 1200.0, "venta": 1205.0, ... }
        datos_json = response.json()

        # Convertimos cada diccionario del JSON en un objeto Cotizacion
        cotizaciones = []
        for item in datos_json:
            cotizacion = Cotizacion(
                nombre=item.get("nombre", "Desconocido"),
                compra=float(item.get("compra", 0)),
                venta=float(item.get("venta", 0)),
            )
            cotizaciones.append(cotizacion)

        return cotizaciones

    except requests.exceptions.Timeout:
        # Creamos un error descriptivo para que quien use esta función
        # sepa exactamente qué salió mal
        raise ConnectionError("Timeout: dolarapi.com tardó más de 10 segundos.")
    
    except requests.exceptions.ConnectionError:
        raise ConnectionError("No se pudo conectar a dolarapi.com. Verificá tu internet.")
    
    except requests.exceptions.HTTPError as e:
        raise ConnectionError(f"Error HTTP al consultar dolarapi.com: {e}")


def obtener_resumen_para_ia() -> dict:
    """
    Función de 'alto nivel': filtra y formatea los datos para el agente de IA.
    
    Solo devuelve las cotizaciones más relevantes para el análisis económico.
    Esta es la función que va a usar FastAPI para armar el contexto del agente.
    """
    todas = obtener_todas_las_cotizaciones()
    
    # Filtramos solo las cotizaciones que aportan valor al análisis
    RELEVANTES = {"Blue", "Oficial", "MEP", "Tarjeta", "Cripto"}
    
    resumen = {}
    for cotizacion in todas:
        if cotizacion.nombre in RELEVANTES:
            resumen[cotizacion.nombre] = cotizacion.to_dict()
    
    return resumen


# ─── BLOQUE DE PRUEBA ─────────────────────────────────────────────────────────
#
# Este bloque SOLO se ejecuta cuando corrés el archivo directamente:
#   python src/data/dolar.py
#
# Cuando el módulo es importado desde otro archivo, este bloque NO se ejecuta.
# Es la forma estándar de Python para escribir "código de prueba" dentro del módulo.

if __name__ == "__main__":
    print("🔍 Consultando dolarapi.com...\n")
    
    try:
        resumen = obtener_resumen_para_ia()
        
        if not resumen:
            print("No se encontraron cotizaciones relevantes.")
        else:
            for nombre, datos in resumen.items():
                print(f"💵 {nombre}")
                print(f"   Compra: ${datos['compra']:,.2f}")
                print(f"   Venta:  ${datos['venta']:,.2f}")
                print(f"   Spread: ${datos['spread']:,.2f}")
                print()
                
    except ConnectionError as e:
        print(f"❌ Error: {e}")