<<<<<<< HEAD
# 🇦🇷 ArgEcon AI — Monitor Económico Argentino con IA

Agente de análisis económico en tiempo real que consume APIs públicas argentinas
y genera análisis automáticos usando LLaMA 3 (Groq).

## ¿Qué hace?
- Obtiene cotizaciones del dólar en tiempo real (Oficial, Blue, MEP, Cripto, Tarjeta)
- Consulta variables del BCRA: reservas, base monetaria, tasa de política monetaria
- Calcula inflación mensual, acumulada anual y tendencia (últimos 12 meses)
- Genera un análisis económico en lenguaje natural con IA (LLaMA 3)

## Stack
`Python` · `FastAPI` · `Groq (LLaMA 3)` · `HTML/CSS/JS` · `BCRA API` · `dolarapi.com`

## Cómo correrlo localmente

1. Clonar el repo y crear entorno virtual:
```bash
    git clone https://github.com/TU_USUARIO/argecon-ai.git
    cd argecon-ai
    python -m venv venv
    venv\Scripts\activate      # Windows
    pip install -r requirements.txt
```

=======
# 🇦🇷 ArgEcon AI — Monitor Económico Argentino con IA

Agente de análisis económico en tiempo real que consume APIs públicas argentinas
y genera análisis automáticos usando LLaMA 3 (Groq).

## ¿Qué hace?
- Obtiene cotizaciones del dólar en tiempo real (Oficial, Blue, MEP, Cripto, Tarjeta)
- Consulta variables del BCRA: reservas, base monetaria, tasa de política monetaria
- Calcula inflación mensual, acumulada anual y tendencia (últimos 12 meses)
- Genera un análisis económico en lenguaje natural con IA (LLaMA 3)

## Stack
`Python` · `FastAPI` · `Groq (LLaMA 3)` · `HTML/CSS/JS` · `BCRA API` · `dolarapi.com`

## Cómo correrlo localmente

1. Clonar el repo y crear entorno virtual:
```bash
    git clone https://github.com/TU_USUARIO/argecon-ai.git
    cd argecon-ai
    python -m venv venv
    venv\Scripts\activate      # Windows
    pip install -r requirements.txt
```

>>>>>>> dcebf359ab00daafb3fcfaa42f31ca7a1d37d74a
2. Crear archivo `.env` con tu API key de Groq: