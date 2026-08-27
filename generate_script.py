# -*- coding: utf-8 -*-
"""
Escribe el guion del dia con IA (Gemini) siguiendo PROMPT-MAESTRO.md.
Se activa solo si existe GEMINI_API_KEY. Si falla algo, devuelve None
y el sistema usa el banco de guiones (scripts.json) como reserva.
Devuelve un dict con el mismo formato que usa generate.py.
"""
import os, sys, json, datetime, random, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.environ.get("GEMINI_MODEL", "").strip()  # vacio = autodetectar modelo valido
# Candidatos por si ListModels no responde (de mas nuevo a mas compatible).
_MODEL_CANDIDATES = [
    "gemini-flash-latest", "gemini-2.5-flash", "gemini-2.0-flash",
    "gemini-2.5-flash-lite", "gemini-2.0-flash-001", "gemini-1.5-flash",
]
BGS = ["blue", "green", "orange", "purple", "teal", "red"]
# AMBITOS del futbol que rotan por dia (se usan como "a evitar hoy" para forzar variedad)
TEMAS = [
    "los Mundiales", "la Champions League", "las remontadas historicas",
    "las grandes rivalidades y clasicos", "las leyendas del futbol",
    "las tragedias del futbol", "los goles miticos",
    "los ascensos y gestas de equipos humildes", "la historia de las selecciones",
    "los porteros legendarios", "los entrenadores miticos", "el futbol femenino",
    "las finales inolvidables", "los fichajes que hicieron historia",
    "el futbol de los anos ochenta y noventa",
]
# ESTILOS que se intercalan cada dia (historia con emocion, no lista)
FORMATOS = [
    "la noche epica: una remontada o final inolvidable contado minuto a minuto",
    "la tragedia o el drama humano del futbol, contado con respeto",
    "el gesto que emociono: deportividad, lealtad o superacion",
    "el ascenso de una leyenda: el momento en que se hizo grande",
    "la rivalidad historica: el origen y el fuego de un clasico",
    "el dato o record brutal, pero narrado como una historia con emocion",
]

SCHEMA_INSTRUCCION = """
Devuelve UNICAMENTE un JSON valido (sin texto alrededor) con esta forma exacta:
{
  "title": "titulo epico y fiel, max 90 caracteres, puede llevar 1 emoji y #shorts",
  "description": "1-2 frases con emocion + una pregunta de debate. Anade al final: 'Basado en hechos reales.'",
  "hashtags": ["Shorts", "futbol", "leyendas", "historia"],  // 3 a 5, sin '#', el primero SIEMPRE 'Shorts'
  "bg": "uno de: green, blue, teal, purple",
  "broll": "2-4 palabras EN INGLES de escena de futbol GENERICA (ej: 'stadium night crowd')",
  "broll_list": ["3 o 4 escenas GENERICAS de futbol EN INGLES, en orden (ej: 'stadium floodlights night', 'football on grass closeup', 'cheering crowd stands')"],
  "ai_disclosure": true,
  "lines": [
    {"voice": "frase corta y con emocion (numeros en palabras: 'dos a cero', no '2-0')",
     "cap": "subtitulo MUY corto en pantalla (2-4 palabras)"}
  ]
}
Reglas del guion (formato 'Leyendas'):
- Entre 8 y 11 lineas. Cuenta UNA historia real del futbol con emocion, tension y desenlace (el video dura 30-45 s).
- NO ES UNA LISTA: prohibido 'sabias que', 'top 3' o 'datos sueltos'. Es un RELATO que emociona.
- RIGOR: hechos, fechas y resultados reales; nombres correctos; nada inventado.
- NUNCA describas ni pidas imagenes de jugadores reales identificables: el fondo son escenas GENERICAS (estadio, balon, aficion).
- APERTURA (linea 1, VARIADA cada dia, nunca identica a la de ayer): un gancho epico. Ej: 'La noche que el futbol se paro para ver esto.'
- CIERRE (ultima linea, VARIADO cada dia): remata con emocion e INVITA AL DEBATE. Ej: 'El mas grande de la historia? Dilo en comentarios.'
- Tono de narrador epico y apasionado. 'cap' sin emojis. 'voice' con numeros en letras. Respeto a todos.
"""
def _run_seed():
    try:
        return int(os.environ.get("GITHUB_RUN_NUMBER", "0"))
    except ValueError:
        return 0

def _pick(lst, salt=0):
    y = datetime.date.today().timetuple().tm_yday
    return lst[(y + _run_seed() + salt) % len(lst)]

def _list_models(key):
    """Pregunta a Google que modelos existen de verdad para esta clave."""
    try:
        url = ("https://generativelanguage.googleapis.com/v1beta/models"
               f"?key={key}&pageSize=200")
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.loads(r.read().decode())
        out = []
        for m in data.get("models", []):
            if "generateContent" in (m.get("supportedGenerationMethods") or []):
                out.append(m.get("name", "").replace("models/", ""))
        return out
    except Exception:
        return []

def _model_order(key):
    """Orden a probar: modelo forzado por env -> candidatos -> los reales
    de la cuenta (priorizando 'flash')."""
    order = []
    if MODEL:
        order.append(MODEL)
    for m in _MODEL_CANDIDATES:
        if m not in order:
            order.append(m)
    disc = _list_models(key)
    for m in disc:
        if "flash" in m and m not in order:
            order.append(m)
    for m in disc:
        if m not in order:
            order.append(m)
    return order

def _post_generate(model, prompt, key):
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent?key={key}")
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.95, "responseMimeType": "application/json"},
    }).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode())
    return data["candidates"][0]["content"]["parts"][0]["text"]

def _call_gemini(prompt, key):
    """Prueba varios modelos y usa el primero que responda (sobrevive a que
    Google jubile un modelo). Solo falla si NINGUNO funciona."""
    last = None
    for model in _model_order(key):
        try:
            txt = _post_generate(model, prompt, key)
            sys.stderr.write(f"[ai] modelo usado: {model}\n")
            return txt
        except Exception as e:
            last = e
    raise RuntimeError(f"ningun modelo Gemini respondio: {last}")

def _validate(s):
    assert isinstance(s.get("lines"), list) and 6 <= len(s["lines"]) <= 16, "lineas fuera de rango"
    for ln in s["lines"]:
        assert ln.get("voice"), "linea sin voz"
        ln.setdefault("cap", "")
    s.setdefault("bg", "blue")
    if s["bg"] not in BGS:
        s["bg"] = "blue"
    hs = [h.lstrip("#") for h in s.get("hashtags", []) if h.strip()]
    if not hs or hs[0].lower() != "shorts":
        hs = ["Shorts"] + [h for h in hs if h.lower() != "shorts"]
    s["hashtags"] = hs[:5]
    assert s.get("title"), "sin titulo"
    s.setdefault("description", "Una historia del futbol que pone la piel de gallina. Basado en hechos reales.")
    s["id"] = "ia-" + datetime.date.today().isoformat()
    s.pop("chart", None)
    return s

def generate():
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    try:
        master = open(os.path.join(BASE, "PROMPT-MAESTRO.md"), encoding="utf-8").read()
    except Exception:
        master = "Eres un narrador epico de historias del futbol para YouTube Shorts, en espanol, que emociona y busca el debate."
    formato = random.choice(FORMATOS)
    hoy = datetime.date.today().isoformat()
    # Usamos TEMAS solo como "lo obvio a EVITAR", para empujar novedad
    evitar = ", ".join(random.sample(TEMAS, min(6, len(TEMAS)))) if TEMAS else ""
    seed = _run_seed()
    prompt = (master
              + f"\n\n---\nTAREA DE HOY ({hoy}):\n"
              + "ELIGE TU MISMO un momento REAL del futbol (una noche epica, una leyenda, un "
                "drama, una gesta) y cuentalo con emocion, como una historia. Debe ser cierto.\n"
              + (f"Para forzar variedad, HOY evita estos ambitos (elige otro distinto): {evitar}.\n" if evitar else "")
              + f"Cuentalo con este ESTILO de hoy: {formato}.\n"
              + "Apertura y cierre VARIADOS (nunca los de ayer); titulo y descripcion UNICOS de hoy. Que HOY se note claramente distinto a cualquier dia anterior. Es un RELATO con emocion, NO una lista.\n"
              + "Recuerda: para el fondo, escenas GENERICAS de estadio; nunca jugadores reales.\n"
              + SCHEMA_INSTRUCCION)
    try:
        raw = _call_gemini(prompt, key)
        s = json.loads(raw)
        s = _validate(s)
        return s
    except Exception as e:
        sys.stderr.write(f"[ai] no se pudo generar con IA ({e}); se usara el banco.\n")
        return None

if __name__ == "__main__":
    import json as _j
    s = generate()
    print(_j.dumps(s, ensure_ascii=False, indent=2) if s else "None (sin GEMINI_API_KEY o error)")
