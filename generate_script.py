# -*- coding: utf-8 -*-
"""
Cerebro del canal FUTBOL (formato viral de 'datos curiosos', que es lo que mas
peta en Shorts de futbol):
  - Titulo con NUMERO + palabra potente / hueco de curiosidad ("no vas a creer").
  - Gancho fuerte en la primera linea.
  - Datos/curiosidades reales, del mas flojo al mas fuerte.
  - Cebo de comentarios al final.
Los VISUALES son escenas de futbol GENERICAS y cinematograficas recreadas con IA
(jugadores anonimos, estadios, trofeos), NUNCA caras de futbolistas reales.
Rotacion determinista de tema/formato para que no se repita.
"""
import os, sys, json, datetime, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.environ.get("GEMINI_MODEL", "").strip()
_MODEL_CANDIDATES = [
    "gemini-flash-latest", "gemini-2.5-flash", "gemini-2.0-flash",
    "gemini-2.5-flash-lite", "gemini-2.0-flash-001", "gemini-1.5-flash",
]
BGS = ["blue", "green", "orange", "purple", "teal", "red"]

# Tema (rotativo) + pista de ESCENA generica a recrear con IA (sin personas reales).
TEMAS = [
    ("leyendas y records imposibles del futbol", "a lone footballer silhouette in a huge empty stadium at golden hour"),
    ("los Mundiales mas locos de la historia", "a packed world cup stadium with fans and confetti at night"),
    ("fichajes que cambiaron la historia", "stacks of money and a football boot on green grass, dramatic light"),
    ("rivalidades legendarias del futbol", "two teams facing off in a floodlit stadium, intense atmosphere"),
    ("reglas y curiosidades que casi nadie sabe", "close up of a football on the penalty spot, stadium lights bokeh"),
    ("historias tragicas y oscuras del futbol", "an empty rainy stadium at night, single spotlight, melancholic"),
    ("remontadas imposibles", "a roaring crowd celebrating, scarves raised, dramatic floodlights"),
    ("los goles que pararon el mundo", "a football hitting the net in slow motion, stadium exploding"),
    ("supersticiones de los futbolistas", "a dim locker room with boots and a jersey hanging, moody light"),
    ("estadios y aficiones miticas", "a massive tifo and sea of fans in a historic stadium"),
    ("el dinero oculto del futbol", "a golden trophy under spotlights with falling confetti"),
    ("selecciones sorpresa que asombraron al mundo", "a small national flag waving in a giant stadium, underdog vibe"),
    ("porteros legendarios y paradas imposibles", "a goalkeeper diving in slow motion under floodlights, generic"),
    ("la Champions y las noches magicas", "a champions-style night stadium glowing, anthem atmosphere"),
    ("entrenadores geniales y sus jugadas", "a tactical chalkboard and a football on a dark table, cinematic"),
]

FORMATOS = [
    "LISTA DE 3: tres datos curiosos alucinantes sobre el tema, del mas normal al mas fuerte.",
    "LISTA DE 4: cuatro datos rapidos y sorprendentes, ritmo agil.",
    "UN DATO BRUTAL: una sola historia/dato impactante contado con giro final.",
    "LO QUE NO SABIAS: 3 cosas que casi nadie conoce sobre el tema.",
    "ADIVINA: plantea 3 datos y reta a adivinar cual es mentira en los comentarios.",
]

GANCHOS = [
    "El noventa por ciento de los aficionados no sabe esto.",
    "Esto paso de verdad en el futbol.",
    "El ultimo dato te va a dejar loco.",
    "Prepara la cabeza, futbolero.",
    "Nadie habla de esto, pero es real.",
    "Esto no lo viste en ningun resumen.",
    "Agarrate, que esto es historia del futbol.",
]

CTAS = [
    "Cual te ha sorprendido mas? Dimelo en los comentarios.",
    "Sabias alguno? Comenta el numero.",
    "Cual es mentira? Adivina en los comentarios.",
    "Comenta si quieres la parte dos.",
    "Sigue el canal para mas datos de futbol.",
]

POWER = ("alucinante", "increible", "no creeras", "no vas a creer", "brutal",
         "impactante", "jamas", "nadie sabe", "loco", "oscuro", "historico",
         "que cambio el futbol", "que no sabias", "sorprendente")


def _run_seed():
    try:
        return int(os.environ.get("GITHUB_RUN_NUMBER", "0"))
    except ValueError:
        return 0

def _daykey():
    return datetime.date.today().toordinal() + _run_seed()

def _rot(lst, stride):
    return lst[(_daykey() * stride) % len(lst)]


def _list_models(key):
    try:
        url = ("https://generativelanguage.googleapis.com/v1beta/models"
               f"?key={key}&pageSize=200")
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.loads(r.read().decode())
        return [m.get("name", "").replace("models/", "") for m in data.get("models", [])
                if "generateContent" in (m.get("supportedGenerationMethods") or [])]
    except Exception:
        return []

def _model_order(key):
    order = []
    if MODEL:
        order.append(MODEL)
    for m in _MODEL_CANDIDATES:
        if m not in order:
            order.append(m)
    for m in _list_models(key):
        if m not in order:
            order.append(m)
    return order

def _post_generate(model, prompt, key):
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent?key={key}")
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 1.0, "responseMimeType": "application/json"},
    }).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode())
    return data["candidates"][0]["content"]["parts"][0]["text"]

def _call_gemini(prompt, key):
    last = None
    for model in _model_order(key):
        try:
            txt = _post_generate(model, prompt, key)
            sys.stderr.write(f"[ai] modelo usado: {model}\n")
            return txt
        except Exception as e:
            last = e
    raise RuntimeError(f"ningun modelo Gemini respondio: {last}")


def _validate(s, tema="", cta="", broll_en=""):
    assert isinstance(s.get("lines"), list) and 4 <= len(s["lines"]) <= 12, "lineas fuera de rango"
    for ln in s["lines"]:
        assert ln.get("voice"), "linea sin voz"
        ln.setdefault("cap", "")
    s.setdefault("bg", "green")
    if s["bg"] not in BGS:
        s["bg"] = "green"
    hs = [h.lstrip("#") for h in s.get("hashtags", []) if h.strip()]
    if not hs or hs[0].lower() != "shorts":
        hs = ["Shorts"] + [h for h in hs if h.lower() != "shorts"]
    s["hashtags"] = (hs + ["futbol", "datoscuriosos", "sabiasque", "football"])[:6]

    t = (s.get("title") or "").strip()
    low = t.lower()
    tiene_num = any(c.isdigit() for c in t) or any(w in low for w in ("tres", "cuatro", "cinco", "dos"))
    tiene_power = any(p in low for p in POWER)
    if not t or not (tiene_num or tiene_power):
        base = (tema or "el futbol").strip()
        t = f"3 datos de {base} que no vas a creer"
    if "#short" not in low:
        t = t + " #shorts"
    s["title"] = t

    if cta:
        last = (s["lines"][-1].get("voice", "") or "").lower()
        if "coment" not in last and "abajo" not in last and "sigue" not in last and "adivina" not in last:
            s["lines"].append({"voice": cta, "cap": "comenta abajo"})

    if not (s.get("description") or "").strip():
        s["description"] = (t.replace(" #shorts", "") + ". " + (cta or "")).strip()
    s["description"] = s["description"].rstrip()

    bl = s.get("broll_list")
    if not isinstance(bl, list) or not bl:
        bl = [broll_en] if broll_en else []
    bl = [b.strip() for b in bl if isinstance(b, str) and b.strip()][:6]
    if bl:
        s["broll_list"] = bl
        s["broll"] = bl[0]
    elif broll_en:
        s["broll_list"] = [broll_en]; s["broll"] = broll_en

    s["ai_disclosure"] = False
    s["id"] = "ia-" + datetime.date.today().isoformat()
    s.pop("chart", None)
    return s


def _schema(tema, broll_en, formato, gancho, cta):
    return f"""
Devuelve UNICAMENTE un JSON valido (sin texto alrededor) con esta forma exacta:
{{
  "title": "titulo IMPACTANTE con NUMERO y/o palabra potente (no vas a creer, alucinante, brutal, jamas...). Sobre el tema de HOY. Max 80 caracteres, 1 emoji opcional, incluye #shorts.",
  "description": "1-2 frases con gancho + hashtags. Termina invitando a comentar.",
  "hashtags": ["Shorts", "futbol", "datoscuriosos", "sabiasque", "football"],
  "bg": "uno de: green, blue, orange, purple",
  "broll": "{broll_en}",
  "broll_list": ["una ESCENA de futbol GENERICA y cinematografica para recrear con IA por CADA dato, EN INGLES. SIEMPRE jugadores anonimos/siluetas, estadios, trofeos, aficiones, balones. NUNCA describas a una persona real ni su cara. Ej: 'anonymous footballer scoring under floodlights, crowd roaring', 'golden trophy with confetti', 'packed stadium tifo at night'. En orden, 3 o 4."],
  "ai_disclosure": false,
  "lines": [
    {{"voice": "frase que se narra (numeros en palabras)", "cap": "subtitulo corto (2-4 palabras)"}}
  ]
}}
GUION DE HOY (canal de FUTBOL, formato viral, DISTINTO a cualquier dia anterior):
- TEMA DE HOY (obligatorio): {tema}.
- FORMATO DE HOY: {formato}
- LINEA 1 = GANCHO POTENTE (primeros 2 segundos). Empieza con algo tipo: "{gancho}" y promete sin dar aun el premio.
- Datos reales y VERACES (nada inventado), del mas flojo al mas fuerte. Puedes nombrar futbolistas reales en el TEXTO (es un dato), pero las ESCENAS visuales son genericas.
- ULTIMA LINEA = CEBO DE COMENTARIOS: algo tipo "{cta}".
- Entre 5 y 8 lineas. Frases cortas y con energia, tono futbolero cercano. Espanol de Espana.
- 'cap' sin emojis. 'voice' escribe los numeros con letras.
- RECUERDA: en 'broll_list' nunca describas la cara de un jugador real; escenas genericas de futbol.
"""


def generate():
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    try:
        master = open(os.path.join(BASE, "PROMPT-MAESTRO.md"), encoding="utf-8").read()
    except Exception:
        master = "Eres un divulgador de futbol experto en Shorts virales de datos curiosos en espanol de Espana."

    tema, broll_en = _rot(TEMAS, 1)
    formato = _rot(FORMATOS, 3)
    gancho = _rot(GANCHOS, 5)
    cta = _rot(CTAS, 7)
    hoy = datetime.date.today().isoformat()

    prompt = (master
              + f"\n\n---\nTAREA DE HOY ({hoy}):\n"
              + "Crea un Short de futbol con el formato viral de abajo. Sigue EXACTAMENTE el tema, "
                "el formato, el gancho y el cierre asignados. Datos REALES; escenas visuales genericas.\n"
              + _schema(tema, broll_en, formato, gancho, cta))
    try:
        raw = _call_gemini(prompt, key)
        s = json.loads(raw)
        s = _validate(s, tema=tema, cta=cta, broll_en=broll_en)
        return s
    except Exception as e:
        sys.stderr.write(f"[ai] no se pudo generar con IA ({e}); se usara el banco.\n")
        return None


if __name__ == "__main__":
    import json as _j
    s = generate()
    print(_j.dumps(s, ensure_ascii=False, indent=2) if s else "None (sin GEMINI_API_KEY o error)")
