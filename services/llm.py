"""
services/llm.py
===============
Servicio LLM principal usando Groq + llama-3.3-70b-versatile.
Provee análisis de compatibilidad de hardware con razonamiento técnico.

IL2.1 - Herramienta de razonamiento integrada en el agente.
"""

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"


def analizar_con_ia(cpu, gpu, ram, mb, case, contexto: str) -> str:
    """
    Analiza la compatibilidad de los componentes de hardware seleccionados.

    Args:
        cpu: Diccionario con datos del procesador (puede ser None).
        gpu: Diccionario con datos de la GPU (puede ser None).
        ram: Diccionario con datos de la RAM (puede ser None).
        mb:  Diccionario con datos de la placa madre (puede ser None).
        case: Diccionario con datos del gabinete (puede ser None).
        contexto: Texto enriquecido con información RAG + web.

    Returns:
        Análisis técnico completo como string formateado.
    """

    def desc(comp):
        return comp["descripcion"] if comp else "No seleccionado"

    prompt = f"""Eres un experto en hardware especializado en análisis de rendimiento y compatibilidad de componentes PC.

COMPONENTES SELECCIONADOS:
- CPU: {desc(cpu)}
- GPU: {desc(gpu)}
- RAM: {desc(ram)}
- PLACA MADRE: {desc(mb)}
- GABINETE: {desc(case)}

CONTEXTO TÉCNICO (RAG + Web):
{contexto}

INSTRUCCIONES:
- Analiza TODOS los datos entregados (base de datos, RAG e internet).
- NO menciones internet ni fuentes externas en tu respuesta.
- Considera: velocidades (MHz), chipset, generación, tipo de memoria (DDR4/DDR5), tipo de memoria gráfica (GDDR6/GDDR6X), compatibilidad de socket, núcleos/hilos, arquitectura GPU (CUDA, Turing, Lovelace, RDNA).
- Usa criterio técnico real y sé claro y directo.
- Explica de forma sencilla pero sin perder rigor técnico.
- Las recomendaciones deben basarse SOLO en los componentes de la base de datos, no sugieras otros.
- Si un componente no existe en la realidad, indícalo claramente.

REGLAS ESTRICTAS:
- NO inventes especificaciones técnicas.
- NO supongas datos que no estén presentes.
- Si el componente no existe en la realidad, déjalo indicado.

Responde ÚNICAMENTE con estos apartados:
1. ¿Hay cuello de botella? (Sí/No y cuál componente)
2. Explicación técnica breve del por qué.
3. ¿Es crítico o no crítico? (Crítico = el sistema no funcionará bien; No crítico = funciona pero no al máximo)
4. Recomendación concreta.
5. Puntaje de compatibilidad (0 a 100).
6. Listado de componentes seleccionados con compatibilidad individual (indica entre paréntesis el tipo: CPU, GPU, RAM, PLACA MADRE, GABINETE).
7. (SOLO si hay componentes que no existen en la realidad) Indicar cuáles no existen.
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=1200
    )

    return response.choices[0].message.content


def chat_simple(mensaje: str, historial: list = None) -> str:
    """
    Chat simple con historial para memoria conversacional.

    Args:
        mensaje: Mensaje del usuario.
        historial: Lista de mensajes previos [{role, content}].

    Returns:
        Respuesta del modelo como string.

    IL2.2 - Memoria de corto plazo mediante historial de mensajes.
    """
    messages = [
        {
            "role": "system",
            "content": "Eres un asistente experto en hardware y componentes PC. Responde de forma clara, técnica y concisa."
        }
    ]

    if historial:
        messages.extend(historial)

    messages.append({"role": "user", "content": mensaje})

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0,
        max_tokens=800
    )

    return response.choices[0].message.content
