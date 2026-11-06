"""JARVIS para PC (Windows 11). Python 3.12 / 3.13
Instalar:  python -m pip install vosk SpeechRecognition PyAudio pyttsx3 psutil pillow
Cerebro local:  Ollama abierto y el modelo descargado:  ollama pull qwen2.5:1.5b
Voz sin internet (respaldo):  carpeta `modelo_voz_es` junto a este archivo (vosk-model-small-es-0.42).
Ejecutar:  python JARVIS_COMPLETO.py      (Esc = salir; clic en la burbuja = alternar pantalla completa)
Opciones (más abajo, en la configuración): RECONOCIMIENTO, VOZ, CEREBRO, MODELO_LOCAL, MICROFONO.
"""
import os, sys, re, ast, json, math, time, random, operator, datetime, difflib
import threading, subprocess, unicodedata, webbrowser, queue, shutil
import urllib.request, urllib.parse
import tkinter as tk

import speech_recognition as sr
import pyttsx3

try:
    import psutil
except ImportError:
    psutil = None
try:
    from PIL import ImageGrab
except ImportError:
    ImageGrab = None

LANG = "es-ES"  # idioma del reconocimiento de voz (es-MX, es-AR, ...)
WAKES = ("jarvis", "yarvis", "harvis", "jarbis", "yarbis", "travis", "yaris", "charvis", "garvis", "jarvi", "jervis")
MICROFONO = None  # número del micrófono (None = el predeterminado de Windows; si falla, prueba los demás solo)
ACTIVACION = True  # True = solo responde si dices "Jarvis" (así no gasta CPU con cualquier ruido); False = responde a todo
RECONOCIMIENTO = "auto"  # "auto" = Google (más preciso, con internet) y sin internet usa Vosk | "google" | "vosk" = siempre sin internet
VOZ = "sistema"          # "sistema" = voz de Windows, sin internet | "neural" = voz natural por internet (edge-tts)
CEREBRO = "local"        # "local" = solo Ollama | "auto" = Claude/ChatGPT si hay claves (y si no, Ollama)
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODELO_LOCAL = "qwen2.5:1.5b"  # debe estar descargado:  ollama pull qwen2.5:1.5b
KEEP_ALIVE = "30m"       # tiempo que Ollama mantiene el modelo en memoria
MAX_TOKENS = 140         # largo máximo de cada respuesta (menos = más rápido)
NUM_CTX = 2048           # memoria de la conversación (menos = más rápido)
CLAVES = {"claude": os.environ.get("ANTHROPIC_API_KEY"), "chatgpt": os.environ.get("OPENAI_API_KEY")}
NOMBRES = {"claude": "Claude", "chatgpt": "ChatGPT", "ollama": "Ollama local"}
MODELOS = {"claude": "claude-haiku-5-5", "chatgpt": "gpt-4.1-mini"}  # cámbialos si quieres otro modelo
MODO_IA = "carrera"  # "carrera": preguntan las dos y habla la primera que conteste | "alternar" | "claude" | "chatgpt"
TEMAS = {"claude": "#e2815e", "chatgpt": "#19c9a0", "ollama": "#19c9a0"}  # color de la burbuja de cada cerebro
VOCES = ["es-AR-TomasNeural", "es-MX-JorgeNeural", "es-ES-AlvaroNeural", "es-CO-GonzaloNeural", "es-US-AlonsoNeural"]
RUTA_VOZ = os.path.join(os.path.expanduser("~"), "jarvis_voz.txt")
LIMITE_RECONOCER = 12  # segundos máximos esperando a Google para entenderte
LIMITE_ORDEN = 180     # segundos máximos para ejecutar una orden (el cerebro local puede tardar)
SISTEMA = ("Eres JARVIS, un asistente de voz para niños, jóvenes y adultos. Responde en español claro y respetuoso, "
           "en 2 o 3 frases cortas y completas. Responde directo a lo que preguntan; si es una pregunta escolar, "
           "explica fácil con un ejemplo. Si no se entiende la pregunta, pide que la repitan. Si no sabes algo, dilo. "
           "No uses listas ni formato especial.")
WIN = sys.platform.startswith("win")
HOME = os.path.expanduser("~")
BG = "#02060c"
COLORES = {"idle": "#3fe0d6", "listening": "#4dff9a", "thinking": "#ffb347", "speaking": "#3fd0ff"}
ESTADOS = {"idle": "●  EN ESPERA", "listening": "●  ESCUCHANDO", "thinking": "●  PROCESANDO", "speaking": "●  HABLANDO"}
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]

SITIOS = {"youtube": "https://youtube.com", "google": "https://google.com",
          "gmail": "https://mail.google.com", "correo": "https://mail.google.com",
          "facebook": "https://facebook.com", "instagram": "https://instagram.com",
          "whatsapp": "https://web.whatsapp.com", "netflix": "https://netflix.com",
          "spotify": "https://open.spotify.com", "mapas": "https://maps.google.com",
          "claude": "https://claude.ai", "chatgpt": "https://chatgpt.com", "chat gpt": "https://chatgpt.com", "wikipedia": "https://es.wikipedia.org",
          "traductor": "https://translate.google.com", "drive": "https://drive.google.com"}
JUEGOS = {  # nombre : número del juego (None = lo busca en Roblox)
    "montar una mascota": None,
    "rompe y roba un huevo": None,
}
APPS = {"calculadora": "calc", "bloc de notas": "notepad", "paint": "mspaint",
        "explorador": "explorer", "word": "winword", "excel": "excel",
        "powerpoint": "powerpnt", "administrador de tareas": "taskmgr",
        "configuracion": "ms-settings:", "simbolo del sistema": "cmd", "cmd": "cmd",
        "panel de control": "control", "chrome": "chrome", "edge": "msedge", "firefox": "firefox"}
CARPETAS = {"descargas": "Downloads", "documentos": "Documents", "escritorio": "Desktop",
            "imagenes": "Pictures", "fotos": "Pictures", "musica": "Music", "videos": "Videos"}
CERRAR = {"chrome": "chrome.exe", "edge": "msedge.exe", "firefox": "firefox.exe",
          "word": "winword.exe", "excel": "excel.exe", "bloc de notas": "notepad.exe",
          "paint": "mspaint.exe", "calculadora": "CalculatorApp.exe"}
CHISTES = ["¿Qué le dice un bit a otro? Nos vemos en el bus.",
           "¿Por qué los programadores confunden Halloween con Navidad? Porque OCT 31 es igual a DEC 25.",
           "Tengo un chiste sobre UDP, pero no sé si te va a llegar."]


class E:  # estado compartido entre la voz y la animación
    modo, oido, dicho, salir = "idle", "", "Iniciando...", False
    mini = False  # True = burbuja pequeña a la derecha
    tema = None      # "claude" | "chatgpt" mientras esa IA responde
    voz = VOCES[0]   # voz neural actual


LOCK = threading.Lock()
HIST, TURNO = [], [0]
try:
    with open(RUTA_VOZ, encoding="utf-8") as _f:
        _v = _f.read().strip()
    if _v in VOCES:
        E.voz = _v
except OSError:
    pass


def norm(t):
    t = t.lower().replace("opera x", "opera gx").replace("operas x", "opera gx")
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def reproducir_mp3(ruta):  # reproduce un mp3 en Windows sin instalar nada extra
    import ctypes
    mci = ctypes.windll.winmm.mciSendStringW
    mci("close jarvisvoz", None, 0, 0)
    if mci(f'open "{ruta}" type mpegvideo alias jarvisvoz', None, 0, 0):
        raise RuntimeError("no pude reproducir el audio")
    try:
        con_limite(lambda: mci("play jarvisvoz wait", None, 0, 0), 60, "el audio se trabó")
    finally:
        mci("close jarvisvoz", None, 0, 0)


def voz_neural(texto):  # voz natural de Microsoft Edge (necesita internet y el paquete edge-tts)
    import asyncio, tempfile
    import edge_tts
    ruta = os.path.join(tempfile.gettempdir(), f"jarvis_{os.getpid()}_{threading.get_ident()}.mp3")
    try:
        asyncio.run(asyncio.wait_for(edge_tts.Communicate(texto, E.voz, rate="+5%").save(ruta), 20))
        reproducir_mp3(ruta)
    finally:
        try:
            os.remove(ruta)
        except OSError:
            pass


_sapi = threading.local()


def _voz_sapi():
    """Voz de Windows (SAPI) reutilizada en cada hilo: evita reiniciar el motor en cada frase."""
    v = getattr(_sapi, "voz", None)
    if v is None:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        v = win32com.client.Dispatch("SAPI.SpVoice")
        elegida = None
        for t in v.GetVoices():
            desc = t.GetDescription().lower()
            if "spanish" in desc or "español" in desc:
                elegida = t
                break
        if elegida is not None:
            v.Voice = elegida
        else:
            print("No hay voz en español instalada en Windows (Configuración > Hora e idioma > Voz).")
        v.Rate = 1
        _sapi.voz = v
    return v


def voz_sistema(texto):  # voz de Windows (sin internet)
    if WIN:
        try:
            _voz_sapi().Speak(texto)  # bloquea hasta terminar de hablar
            return
        except Exception as e:
            print("La voz SAPI directa falló, uso pyttsx3:", e)
    try:
        try:
            import comtypes
            comtypes.CoInitialize()
        except Exception:
            pass
        motor = pyttsx3.init()
        for v in motor.getProperty("voices"):
            s = (v.name + v.id).lower()
            if "spanish" in s or "español" in s or "es-" in s or "es_" in s:
                motor.setProperty("voice", v.id)
                break
        motor.setProperty("rate", 175)
        motor.say(texto)
        motor.runAndWait()
        motor.stop()
    except Exception as e:
        print("Error de voz:", e)
        E.dicho = f"{texto}   (sin voz: {str(e)[:70]})"
        time.sleep(min(len(texto) * 0.05, 5))


def hablar(texto):
    if not LOCK.acquire(timeout=40):  # si la voz quedó trabada, no bloquea a Jarvis para siempre
        print("La voz está ocupada, omito:", texto)
        return
    try:
        E.dicho, E.modo = texto, "speaking"
        try:
            if not WIN or VOZ != "neural":
                raise ImportError
            voz_neural(texto)
        except Exception as e:
            if not isinstance(e, ImportError):
                print("La voz neural falló, uso la del sistema:", e)
            voz_sistema(texto)
        E.modo = "idle"
    finally:
        LOCK.release()


# ---------- utilidades ----------
def http_json(url, data=None, headers=None, timeout=8):
    req = urllib.request.Request(url, data=data, headers=headers or {"User-Agent": "Jarvis/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def run(cmd):
    subprocess.Popen(cmd, shell=True)


def abrir_opera_gx(url=None):
    """Abre Opera GX (si está instalado), con la dirección si se indica. Devuelve False si no lo encuentra."""
    local = os.environ.get("LOCALAPPDATA", "")
    candidatos = [os.path.join(local, "Programs", "Opera GX", "opera.exe"),
                  r"C:\Program Files\Opera GX\opera.exe",
                  r"C:\Program Files (x86)\Opera GX\opera.exe"]
    exe = next((c for c in candidatos if os.path.isfile(c)), None) or shutil.which("opera")
    if not exe:
        return False
    subprocess.Popen([exe] + ([url] if url else []))
    return True


def web(url):
    """Abre una página y reduce Jarvis a su burbuja flotante."""
    E.mini = True
    if not abrir_opera_gx(url):
        webbrowser.open(url)


def abrir_juego_ppt():
    """Abre el minijuego local si el archivo existe junto a Jarvis."""
    E.mini = True
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "piedra_papel_tijera.html")
    if not os.path.isfile(ruta):
        return False
    url = "file:" + urllib.request.pathname2url(ruta)
    if not abrir_opera_gx(url):
        webbrowser.open(url)
    return True

def abrir(destino):
    E.mini = True
    destino = destino.replace('"', "")
    if WIN:
        run(f'start "" "{destino}"')
    elif sys.platform == "darwin":
        subprocess.Popen(["open", destino])
    else:
        subprocess.Popen(["xdg-open", destino])


def tecla(*vks):
    if not WIN:
        return
    import ctypes
    k = ctypes.windll.user32.keybd_event
    for v in vks:
        k(v, 0, 0, 0)
    for v in reversed(vks):
        k(v, 0, 2, 0)


def despues(n, *claves):
    for k in claves:
        if k in n:
            return n.split(k, 1)[1].strip(" ,.")
    return ""


OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg}


def _ev(n):
    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
        return n.value
    if isinstance(n, ast.BinOp) and type(n.op) in OPS:
        a, b = _ev(n.left), _ev(n.right)
        if isinstance(n.op, ast.Pow) and abs(b) > 100:
            raise ValueError
        return OPS[type(n.op)](a, b)
    if isinstance(n, ast.UnaryOp) and type(n.op) in OPS:
        return OPS[type(n.op)](_ev(n.operand))
    raise ValueError


def calcular(t):
    for a, b in (("multiplicado por", "*"), ("dividido entre", "/"), ("dividido por", "/"),
                 ("elevado a", "**"), ("mas", "+"), ("menos", "-"), ("por", "*"), ("entre", "/")):
        t = re.sub(rf"\b{a}\b", b, t)
    t = t.replace(" x ", "*").replace(",", ".")
    expr = "".join(c for c in t if c in "0123456789+-*/.() ").strip()
    try:
        v = round(_ev(ast.parse(expr, mode="eval").body), 4)
        return f"El resultado es {int(v) if v == int(v) else v}."
    except Exception:
        return "No pude calcular eso."


def decir_hora():
    a = datetime.datetime.now()
    h = a.hour % 12 or 12
    parte = ("de la madrugada" if a.hour < 6 else "de la mañana" if a.hour < 12
             else "de la tarde" if a.hour < 19 else "de la noche")
    ini = "Es la una" if h == 1 else f"Son las {h}"
    return f"{ini} y {a.minute} {parte}." if a.minute else f"{ini} en punto {parte}."


def clima(ciudad=""):
    try:
        d = http_json("https://wttr.in/" + urllib.parse.quote(ciudad) + "?format=j1&lang=es")
        c = d["current_condition"][0]
        desc = (c.get("lang_es") or c["weatherDesc"])[0]["value"].lower()
        donde = f"En {ciudad}" if ciudad else "Ahora"
        return f"{donde} hay {c['temp_C']} grados, {desc}, con sensación de {c['FeelsLikeC']}."
    except Exception:
        return "No pude obtener el clima."


def wikipedia(tema):
    if not tema:
        return "¿Qué quieres que busque?"
    try:
        b = http_json("https://es.wikipedia.org/w/api.php?action=opensearch&limit=1&format=json&search="
                      + urllib.parse.quote(tema))
        if not b[1]:
            return f"No encontré nada sobre {tema}."
        r = http_json("https://es.wikipedia.org/api/rest_v1/page/summary/"
                      + urllib.parse.quote(b[1][0].replace(" ", "_")))
        return ". ".join(r.get("extract", "").split(". ")[:2]).strip()
    except Exception:
        return "No pude consultar Wikipedia ahora."


def consultar(ia, mensajes):
    """Pregunta a una IA. Devuelve el texto, o None si falla."""
    clave = CLAVES[ia]
    try:
        if ia == "claude":
            cuerpo = {"model": MODELOS[ia], "max_tokens": 300, "system": SISTEMA, "messages": mensajes}
            r = http_json("https://api.anthropic.com/v1/messages", json.dumps(cuerpo).encode(),
                          {"x-api-key": clave, "anthropic-version": "2023-06-01",
                           "content-type": "application/json"}, 25)
            return r["content"][0]["text"]
        cuerpo = {"model": MODELOS[ia], "max_completion_tokens": 400,
                  "messages": [{"role": "system", "content": SISTEMA}] + mensajes}
        r = http_json("https://api.openai.com/v1/chat/completions", json.dumps(cuerpo).encode(),
                      {"Authorization": "Bearer " + clave, "content-type": "application/json"}, 25)
        return r["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Error con {NOMBRES[ia]}:", e)
        if hasattr(e, "read"):
            try:
                print(e.read()[:400].decode("utf-8", "ignore"))
            except Exception:
                pass
        return None


def preguntar_ia(texto):
    """Devuelve (IA que respondió, respuesta). (None, None) si no hay claves o ambas fallan."""
    disp = [ia for ia in ("claude", "chatgpt") if CLAVES[ia]]
    if not disp:
        return None, None
    if MODO_IA in disp:
        elegidas = [MODO_IA]
    elif MODO_IA == "alternar":
        TURNO[0] += 1
        elegidas = [disp[TURNO[0] % len(disp)]]
    else:  # carrera: preguntan las dos y vale la primera que conteste bien
        elegidas = disp
    mensajes = HIST[-6:] + [{"role": "user", "content": texto}]
    cola = queue.Queue()
    for ia in elegidas:
        threading.Thread(target=lambda ia=ia: cola.put((ia, consultar(ia, mensajes))), daemon=True).start()
    for _ in elegidas:
        try:
            ia, resp = cola.get(timeout=35)
        except queue.Empty:
            break
        if resp:
            HIST.extend([{"role": "user", "content": texto}, {"role": "assistant", "content": resp}])
            del HIST[:-8]
            return ia, resp
    return None, None


def ollama_vivo():
    try:
        urllib.request.urlopen(OLLAMA_URL.replace("/api/chat", "/"), timeout=2).read()
        return True
    except Exception:
        return False


def asegurar_ollama():
    """Si Ollama está apagado, lo enciende en segundo plano y espera a que responda."""
    if ollama_vivo():
        return True
    print("Ollama está apagado; intento encenderlo...")
    exe = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe")
    for cmd in ("ollama", exe):
        try:
            subprocess.Popen([cmd, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             creationflags=0x08000000 if WIN else 0)  # sin ventana
            break
        except OSError:
            continue
    else:
        print("No encuentro Ollama. Ábrelo desde el menú Inicio.")
        return False
    for _ in range(40):
        time.sleep(1)
        if ollama_vivo():
            print("Ollama encendido.")
            return True
    print("Ollama no respondió a tiempo.")
    return False


def recortar_frase(t):
    """Si la respuesta quedó cortada a medias, la recorta en la última frase completa."""
    t = t.strip()
    if not t or t[-1] in '.!?…")»':
        return t
    corte = max(t.rfind(". "), t.rfind("! "), t.rfind("? "), t.rfind(".\n"))
    return t[:corte + 1].strip() if corte > 5 else t + "."


def preguntar_ollama(texto):
    """Pregunta a Ollama en streaming: el texto aparece en pantalla mientras se genera y devuelve la respuesta completa."""
    asegurar_ollama()
    mensajes = HIST[-4:] + [{"role": "user", "content": texto}]
    cuerpo = {"model": MODELO_LOCAL, "stream": True, "keep_alive": KEEP_ALIVE,
              "messages": [{"role": "system", "content": SISTEMA}] + mensajes,
              "options": {"temperature": 0.4, "num_predict": MAX_TOKENS, "num_ctx": NUM_CTX}}
    req = urllib.request.Request(OLLAMA_URL, json.dumps(cuerpo, ensure_ascii=False).encode("utf-8"),
                                 {"Content-Type": "application/json"})
    completo, inicio = "", time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            for linea in r:
                if not linea.strip():
                    continue
                d = json.loads(linea.decode("utf-8"))
                completo += d.get("message", {}).get("content", "")
                E.dicho = completo.strip()  # se ve cómo va escribiendo la respuesta
                if d.get("done") or time.time() - inicio > 150:
                    break
    except Exception as e:
        print("Error conectando con Ollama:", repr(e))
    resp = recortar_frase(completo)
    if resp:
        HIST.extend([{"role": "user", "content": texto}, {"role": "assistant", "content": resp}])
        del HIST[:-8]
    return resp or None


def precalentar_ollama():
    """Carga el modelo en memoria al arrancar, para que la primera pregunta no espere al disco duro."""
    asegurar_ollama()
    try:
        cuerpo = {"model": MODELO_LOCAL, "keep_alive": KEEP_ALIVE, "options": {"num_ctx": NUM_CTX}}
        http_json(OLLAMA_URL.replace("/api/chat", "/api/generate"), json.dumps(cuerpo).encode("utf-8"),
                  {"Content-Type": "application/json"}, timeout=240)
        print("Ollama listo con el modelo", MODELO_LOCAL)
    except Exception as e:
        print("No pude precargar Ollama (¿está abierto y descargaste el modelo?):", repr(e))


# ---------- reconocimiento de voz sin Internet (Vosk) ----------
_MODELO_VOSK = None
_RUTA_MODELO_VOSK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modelo_voz_es")


def transcribir_local(audio):
    """Transcribe el audio con Vosk localmente. Requiere el modelo español descomprimido."""
    global _MODELO_VOSK
    from vosk import Model, KaldiRecognizer
    if _MODELO_VOSK is None:
        if not os.path.isdir(_RUTA_MODELO_VOSK):
            raise FileNotFoundError(
                "No encuentro la carpeta 'modelo_voz_es' junto a JARVIS. "
                "Descarga y descomprime vosk-model-small-es-0.42 y renombra su carpeta a modelo_voz_es.")
        _MODELO_VOSK = Model(_RUTA_MODELO_VOSK)
    datos = audio.get_raw_data(convert_rate=16000, convert_width=2)
    reconocedor = KaldiRecognizer(_MODELO_VOSK, 16000)
    reconocedor.AcceptWaveform(datos)
    texto = json.loads(reconocedor.FinalResult()).get("text", "").strip()
    if not texto:
        raise sr.UnknownValueError()
    return texto


def reconocer(r, audio):
    """Google (más preciso) si hay internet; si falla, Vosk sin internet."""
    if RECONOCIMIENTO in ("auto", "google"):
        try:
            return con_limite(lambda: r.recognize_google(audio, language=LANG), LIMITE_RECONOCER,
                              "Google no respondió a tiempo")
        except (sr.RequestError, TimeoutError, OSError) as e:
            if RECONOCIMIENTO == "google":
                raise
            print("Google no disponible, uso Vosk:", e)
    return transcribir_local(audio)


# ---------- cerebro: órdenes ----------
def procesar(n):
    w = set(n.split())
    pc = bool(w & {"computadora", "pc", "ordenador", "computador", "equipo", "laptop"})
    solo_win = "Esa función solo está disponible en Windows."

    m = re.search(r"(\d+)\s*(segundo|minuto|hora)", n)
    if m and any(k in n for k in ("recuerda", "avisame", "temporizador", "alarma")):
        seg = int(m[1]) * {"segundo": 1, "minuto": 60, "hora": 3600}[m[2]]
        tarea = re.sub(r"recuerdame|avisame|temporizador( de)?|alarma( de)?|"
                       r"((dentro de|en|de)\s*)?\d+\s*(segundo|minuto|hora)s?", " ", n)
        tarea = " ".join(tarea.split()) or "se acabó el tiempo"
        t = threading.Timer(seg, hablar, [f"Recordatorio: {tarea}"])
        t.daemon = True
        t.start()
        return f"Listo, te aviso en {m[1]} {m[2]}{'' if m[1] == '1' else 's'}."

    # ---------- juego piedra, papel o tijera ----------
    if any(k in n for k in ("piedra papel", "juego de piedra", "juego piedra", "papel o tijera")):
        if abrir_juego_ppt():
            return "Abriendo el juego de piedra, papel o tijera."
        return "No encuentro piedra_papel_tijera.html junto a Jarvis."

    if any(p in n for p in ("adios", "apagate", "cierrate", "hasta luego")):
        hablar("Hasta luego.")
        E.salir = True
        return None
    if any(p in n for p in ("pantalla completa", "agrandate", "maximizate")):
        E.mini = False
        return "Pantalla completa."
    if any(p in n for p in ("minimizate", "achicate", "modo pequeno")):
        E.mini = True
        return "Me minimizo."

    if "voz" in n.split() and any(k in n for k in ("cambia", "otra", "siguiente")):
        if VOZ != "neural":
            return "Uso la voz instalada en Windows. Para cambiarla, elige otra voz en la configuración de voz de Windows."
        i = (VOCES.index(E.voz) + 1) % len(VOCES)
        E.voz = VOCES[i]
        try:
            with open(RUTA_VOZ, "w", encoding="utf-8") as f:
                f.write(E.voz)
        except OSError:
            pass
        return f"Voz número {i + 1} de {len(VOCES)}. ¿Te gusta cómo sueno?"

    if "cancel" in n and "apagado" in n:
        if not WIN:
            return solo_win
        run("shutdown /a")
        return "Apagado cancelado."
    if pc and "apag" in n:
        if not WIN:
            return solo_win
        run("shutdown /s /t 60")
        return "Apagaré el equipo en un minuto. Di cancela apagado si quieres detenerlo."
    if pc and "reinici" in n:
        if not WIN:
            return solo_win
        run("shutdown /r /t 60")
        return "Reiniciaré el equipo en un minuto. Di cancela apagado para detenerlo."
    if "bloquea" in n:
        if not WIN:
            return solo_win
        run("rundll32.exe user32.dll,LockWorkStation")
        return "Equipo bloqueado."

    if "volumen" in n or "silencia" in n or "mute" in n:
        if not WIN:
            return solo_win
        if "sube" in n or "aumenta" in n:
            [tecla(0xAF) for _ in range(5)]
            return "Volumen arriba."
        if "baja" in n or "disminuye" in n:
            [tecla(0xAE) for _ in range(5)]
            return "Volumen abajo."
        tecla(0xAD)
        return "Hecho."
    if "escritorio" in n and ("muestra" in n or "minimiza" in n) or "minimiza todo" in n:
        tecla(0x5B, 0x44)
        return "Listo."
    if "captura" in n or "pantallazo" in n:
        if not ImageGrab:
            return "Instala pillow para tomar capturas."
        ruta = os.path.join(HOME, "Pictures", f"jarvis_{datetime.datetime.now():%Y%m%d_%H%M%S}.png")
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        ImageGrab.grab().save(ruta)
        return "Captura guardada en tu carpeta de imágenes."

    if "que hora" in n or "la hora" in n:
        return decir_hora()
    if "fecha" in n or "que dia es" in n:
        a = datetime.datetime.now()
        return f"Hoy es {DIAS[a.weekday()]} {a.day} de {MESES[a.month - 1]} de {a.year}."
    if "clima" in n or "temperatura" in n or "va a llover" in n:
        return clima(despues(n, " en "))

    if any(k in n for k in ("estado del sistema", "bateria", "memoria ram", "uso del cpu",
                            "uso del procesador", "como esta la pc")):
        if not psutil:
            return "Instala psutil para ver el estado del sistema."
        bat = psutil.sensors_battery()
        extra = f" Batería al {int(bat.percent)} por ciento." if bat else ""
        return (f"Procesador al {psutil.cpu_percent(interval=0.5):.0f} por ciento, "
                f"memoria al {psutil.virtual_memory().percent:.0f} por ciento.{extra}")

    if "notas" in n and any(k in n for k in ("lee", "cuales", "dime")):
        try:
            with open(os.path.join(HOME, "jarvis_notas.txt"), encoding="utf-8") as f:
                ult = [l.split("] ", 1)[-1].strip() for l in f.readlines()[-3:]]
            return "Tus últimas notas: " + ". ".join(ult) if ult else "No tienes notas."
        except FileNotFoundError:
            return "Aún no tienes notas."
    nota = despues(n, "anota ", "apunta ", "nota ")
    if nota:
        with open(os.path.join(HOME, "jarvis_notas.txt"), "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M}] {nota}\n")
        return "Anotado."

    if any(k in n for k in ("cuanto es", "cuanto son", "calcula", "cuanto da")):
        return calcular(n)

    if n.startswith(("reproduce", "ponme", "pon ")) or ("youtube" in n and "busca" in n):
        q = re.sub(r"\b(busca|buscar|reproduce|reproducir|ponme|pon|en youtube|youtube)\b", "", n).strip()
        web("https://www.youtube.com/results?search_query=" + urllib.parse.quote(q))
        return f"Buscando {q} en YouTube."
    if "wikipedia" in n:
        return wikipedia(despues(n, "wikipedia "))
    q = despues(n, "busca ", "buscar ", "googlea ", "investiga ")
    if q:
        q = q.removeprefix("en google ")
        web("https://www.google.com/search?q=" + urllib.parse.quote(q))
        return f"Buscando {q}."

    if "roblox" in n or n.startswith(("juega", "jugar")):
        juego = despues(n, "juega a ", "jugar a ", "juega ", "jugar ", "roblox ")
        for nombre, pid in JUEGOS.items():
            if nombre in juego:
                if pid:
                    abrir(f"roblox://placeId={pid}")
                    return f"Abriendo {nombre} en Roblox."
                juego = nombre
                break
        if juego:
            web("https://www.roblox.com/discover/?Keyword=" + urllib.parse.quote(juego))
            return f"Buscando {juego} en Roblox."
        web("https://www.roblox.com/home")
        return "Abriendo Roblox."

    d = despues(n, "cierra ", "cerrar ")
    if d:
        if d in CERRAR and WIN:
            run(f"taskkill /IM {CERRAR[d]} /F")
            return f"Cerrando {d}."
        return f"No sé cerrar {d}."
    d = despues(n, "abre ", "abrir ", "abreme ", "ejecuta ", "inicia ")
    if d:
        for art in ("la ", "el ", "los ", "las ", "mi ", "mis "):
            d = d.removeprefix(art)
        if d in ("opera gx", "opera"):
            E.mini = True
            abrir_opera_gx()
            return "Abriendo Opera GX."
        if d in SITIOS:
            web(SITIOS[d])
        elif d in CARPETAS:
            abrir(os.path.join(HOME, CARPETAS[d]))
        elif d in APPS:
            abrir(APPS[d])
        else:
            abrir(d)
        return f"Abriendo {d}."

    if "chiste" in n:
        return random.choice(CHISTES)
    if "hola" in w or "buenas" in w:
        return "Hola, ¿en qué te ayudo?"
    if "gracias" in w:
        return "Para eso estoy."
    if "como estas" in n:
        return "Funcionando al cien por ciento."
    if "quien eres" in n or "como te llamas" in n:
        return "Soy Jarvis, tu asistente personal."

    # preguntas generales: nube (si CEREBRO = "auto" y hay claves) o cerebro local con Ollama
    if CEREBRO == "auto" and any(CLAVES.values()):
        ia, resp = preguntar_ia(n)
        if resp:
            E.tema = ia  # la burbuja toma el color de la IA que respondió
            return resp
        print("La nube no respondió, uso Ollama local.")
    resp = preguntar_ollama(n)
    if resp:
        E.tema = "ollama"  # la burbuja indica que responde el modelo local
        return resp
    tema = despues(n, "que es ", "que son ", "quien es ", "quien fue ")
    if tema:
        return wikipedia(tema)
    return ("No pude conectar con Ollama. Comprueba que esté abierto y que hayas descargado "
            f"el modelo {MODELO_LOCAL} con: ollama pull {MODELO_LOCAL}")


# ---------- voz ----------
def con_limite(fn, segundos, aviso="tardó demasiado"):
    """Ejecuta fn() y, si no termina a tiempo, lanza TimeoutError (así Jarvis nunca se queda colgado)."""
    res = {}

    def tarea():
        try:
            res["ok"] = fn()
        except BaseException as e:
            res["err"] = e

    h = threading.Thread(target=tarea, daemon=True)
    h.start()
    h.join(segundos)
    if h.is_alive():
        raise TimeoutError(aviso)
    if "err" in res:
        raise res["err"]
    return res["ok"]


def buscar_wake(n):
    """Detecta 'jarvis' aunque Google lo escriba parecido. Devuelve (encontrada, orden)."""
    pal = n.split()
    for i, p in enumerate(pal):
        if p in WAKES or difflib.SequenceMatcher(None, p, "jarvis").ratio() >= 0.78:
            resto = pal[i + 1:] or pal[:i]
            return True, " ".join(resto).strip(" ,.")
    return False, ""


def abrir_microfono(r):
    """Abre el micrófono predeterminado; si no sirve, prueba los demás y muestra la lista en la ventana negra."""
    try:
        nombres = sr.Microphone.list_microphone_names()
    except Exception as e:
        print("No pude listar los micrófonos (¿falta PyAudio?):", e)
        return None
    print("Micrófonos que ve Python:")
    for i, nombre in enumerate(nombres):
        print(f"  {i}: {nombre}")
    candidatos = [MICROFONO] if MICROFONO is not None else [None] + list(range(len(nombres)))
    for idx in candidatos:
        try:
            mic = sr.Microphone(device_index=idx)
            with mic as fuente:
                r.adjust_for_ambient_noise(fuente, duration=1.5)
            print("Usando el micrófono:", "predeterminado" if idx is None else f"{idx}: {nombres[idx]}")
            return mic
        except Exception as e:
            print(f"  el micrófono {idx} no sirve: {str(e)[:70]}")
    return None


def bucle_voz():
    r = sr.Recognizer()
    r.dynamic_energy_threshold = True
    r.pause_threshold = 1.0       # silencio que cierra tu frase (más alto = espera más, no te corta)
    r.non_speaking_duration = 0.6  # silencio que conserva antes y después de hablar (así no pierde el inicio)
    r.phrase_threshold = 0.25
    r.operation_timeout = 8  # tope de espera de cada consulta a Google
    mic = abrir_microfono(r)
    if mic is None:
        hablar("No encuentro el micrófono.")
        return
    hablar("Sistemas en línea. Di Jarvis cuando me necesites.")
    activo_hasta = 0
    while not E.salir:
        try:
            E.modo = "listening"
            with mic as fuente:
                audio = r.listen(fuente, timeout=7, phrase_time_limit=20)
            E.modo = "thinking"
            texto = reconocer(r, audio)
            E.oido = texto
            print("Oí:", texto)
            n = norm(texto).strip()
            if not n:
                continue
            hay, orden = buscar_wake(n)
            if hay and not orden:
                hablar("Dime.")
                activo_hasta = time.time() + 8
                continue
            if not hay:
                if time.time() < activo_hasta or not ACTIVACION:
                    orden = n
                else:
                    print("Sin palabra de activación:", texto)
                    E.dicho = "No oí «Jarvis». Di por ejemplo: Jarvis, qué hora es"
                    continue
            print("Orden:", orden)
            resp = con_limite(lambda: procesar(orden), LIMITE_ORDEN, "La orden tardó demasiado")
            print("Respuesta:", resp)
            if resp:
                hablar(resp)
            E.tema = None
            activo_hasta = time.time() + 20
        except sr.WaitTimeoutError:
            pass
        except sr.UnknownValueError:
            pass
        except FileNotFoundError as e:
            print("Modelo de voz local:", e)
            hablar("Falta el modelo de reconocimiento de voz en español. Revisa la carpeta modelo voz es.")
            E.salir = True
        except ImportError:
            print("Falta Vosk. Instálalo con: python -m pip install vosk")
            hablar("Falta instalar Vosk para reconocer la voz sin internet.")
            E.salir = True
        except sr.RequestError:
            hablar("No tengo internet para entenderte.")
            time.sleep(3)
        except TimeoutError as e:
            print("Se agotó el tiempo:", e)
            E.dicho = "Eso tardó demasiado. Inténtalo de nuevo."
        except Exception as e:
            print("Error:", e)
            time.sleep(1)
        finally:
            if E.modo != "speaking":
                E.modo = "idle"


# ---------- burbuja animada (esfera de partículas) ----------
FONDO = ("#050a12", "#0b1829", "#060d16")  # degradado del fondo: arriba, centro, abajo


def mix(c1, c2, t):  # mezcla dos colores hex (t=0 -> c1, t=1 -> c2)
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def fondo_en(f):  # color del degradado a esa altura (0 = arriba, 1 = abajo)
    f = min(max(f, 0), 1)
    return mix(FONDO[0], FONDO[1], f * 2) if f < .5 else mix(FONDO[1], FONDO[2], (f - .5) * 2)


def corto(t, n=64):
    return t if len(t) <= n else t[:n - 1] + "…"


class Burbuja:
    PUNTOS = 80    # partículas de la esfera (menos = más liviano)
    RETARDO = 55   # milisegundos entre cuadros (más alto = más liviano)
    NG = 12        # capas del resplandor
    NW = 45        # barras de la onda de voz

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Jarvis")
        self.root.configure(bg=fondo_en(.5))
        self.root.bind("<Escape>", lambda e: setattr(E, "salir", True))
        self.root.bind("<Control-l>", lambda e: self.entrada.focus_set())
        self.root.protocol("WM_DELETE_WINDOW", lambda: setattr(E, "salir", True))
        self.c = tk.Canvas(self.root, bg=fondo_en(.5), highlightthickness=0)
        self.c.pack(fill="both", expand=True)
        # ---------- teclado para escribir preguntas ----------
        self.panel = tk.Frame(self.root, bg="#10243a")

        self.entrada = tk.Entry(
            self.panel,
            font=("Segoe UI", 13),
            bg="#eaf6ff",
            fg="#102030",
            insertbackground="#102030"
        )
        self.entrada.pack(
            side="left", fill="x", expand=True,
            padx=8, pady=8
        )

        self.entrada.bind("<Return>", lambda e: self.enviar_texto())

        self.boton_enviar = tk.Button(
            self.panel,
            text="Enviar",
            font=("Segoe UI", 11, "bold"),
            bg="#168bd0",
            fg="white",
            activebackground="#20aaff",
            command=self.enviar_texto
        )
        self.boton_enviar.pack(side="right", padx=8, pady=8)
        self.c.bind("<Button-1>", lambda e: setattr(E, "mini", not E.mini))  # clic: cambia tamaño
        self.c.bind("<Button-3>", lambda e: setattr(E, "salir", True))       # clic derecho: salir
        c, n = self.c, self.PUNTOS
        # puntos repartidos en una esfera (espiral de Fibonacci)
        self.pts = []
        for i in range(n):
            y = 1 - 2 * (i + .5) / n
            r = math.sqrt(1 - y * y)
            a = i * math.pi * (3 - math.sqrt(5))
            self.pts.append((r * math.cos(a), y, r * math.sin(a)))
        # cada punto se une con sus 2 vecinos más cercanos
        pares = set()
        for i, p in enumerate(self.pts):
            cerca = sorted((j for j in range(n) if j != i),
                           key=lambda j: -(p[0] * self.pts[j][0] + p[1] * self.pts[j][1] + p[2] * self.pts[j][2]))[:2]
            for j in cerca:
                pares.add((min(i, j), max(i, j)))
        self.pares = sorted(pares)
        self.largo_rayos = (1, .62, .88, .55, 1, .7, .92, .58, .85, .66, 1, .5)  # emblema de Claude
        self.petalo_pts = []  # emblema de ChatGPT: tres elipses cruzadas
        for k in range(3):
            fi = k * math.pi / 3
            pts = []
            for j in range(24):
                tt = 2 * math.pi * j / 24
                ex, ey = .62 * math.cos(tt), .24 * math.sin(tt)
                pts.append((ex * math.cos(fi) - ey * math.sin(fi), ex * math.sin(fi) + ey * math.cos(fi)))
            self.petalo_pts.append(pts)
        # capas (de atrás hacia adelante)
        self.glow = [c.create_oval(0, 0, 0, 0, width=0) for _ in range(self.NG)]
        self.lineas = [c.create_line(0, 0, 0, 0, width=1, state="hidden") for _ in self.pares]
        self.puntos = [c.create_oval(0, 0, 0, 0, width=0) for _ in range(n)]
        self.rayos = [c.create_line(0, 0, 0, 0, width=3, capstyle="round", state="hidden") for _ in range(12)]
        self.petalos = [c.create_polygon(0, 0, 0, 0, 0, 0, smooth=True, fill="", width=3, state="hidden")
                        for _ in range(3)]
        self.ondas = [c.create_line(0, 0, 0, 0, width=2, capstyle="round") for _ in range(self.NW)]
        self.pastilla = c.create_polygon(0, 0, 0, 0, 0, 0, smooth=True, fill="#0d2033", outline="#1c4766")
        self.t_oido = c.create_text(0, 0, fill="#9fd4ea")
        self.t_dicho = c.create_text(0, 0, fill="#e6f6ff", justify="center")
        self.t_estado = c.create_text(0, 0)
        self.proy = [(0, 0, 0)] * n
        self.bucket = [-1] * n
        self.lvis = [False] * len(self.pares)
        self.lineas_on = False
        self.t = self.giro = self.amp = 0.0
        self.mini = None
        self.col_clave = None
        self.ult = (None, None, None)
        self.aplicar(False)
        self.animar()

    def enviar_texto(self):
        texto = self.entrada.get().strip()
        if not texto:
            self.entrada.focus_set()
            return

        self.entrada.delete(0, "end")
        E.oido = texto
        E.dicho = "Procesando tu pregunta..."
        E.modo = "thinking"

        def responder():
            try:
                respuesta = procesar(norm(texto))
                if respuesta:
                    hablar(respuesta)
                else:
                    E.modo = "idle"
                E.tema = None
            except Exception as e:
                print("Error al responder por teclado:", e)
                E.dicho = "Ocurrió un error al procesar tu pregunta."
                E.modo = "idle"

        threading.Thread(target=responder, daemon=True).start()
        self.entrada.focus_set()

    @staticmethod
    def redondo(x0, y0, x1, y1, r):  # puntos de un rectángulo redondeado (pastilla)
        return [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
                x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]

    def aplicar(self, mini):
        """Alterna entre pantalla completa y burbuja flotante sin ocultar el teclado."""
        self.mini = mini
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.withdraw()
        self.root.overrideredirect(mini)
        self.root.attributes("-fullscreen", not mini)
        c = self.c

        if mini:
            # Ventana flotante un poco más alta para incluir burbuja + teclado.
            W, H = 270, 390
            self.root.geometry(f"{W}x{H}+{sw - W - 12}+{(sh - H) // 2}")
            self.cx, self.cy, self.base = W / 2, H * .29, W * .17
            self.wy, self.sy, self.dy, self.nw = H * .49, H * .62, H * .75, 27
            c.itemconfig(self.t_oido, state="hidden")
            c.itemconfig(self.pastilla, state="hidden")
            c.itemconfig(self.t_estado, font=("Segoe UI", 8, "bold"))
            c.itemconfig(self.t_dicho, font=("Segoe UI", 9), width=W - 20)
            panel_width = 0.94
        else:
            W, H = sw, sh
            self.cx, self.cy, self.base = W / 2, H * .37, min(W, H) * .15
            self.wy, self.sy, self.dy, self.nw = H * .61, H * .70, H * .82, self.NW
            pw, ph, py = W * .40, 34, H * .735
            c.coords(self.pastilla, *self.redondo(
                W / 2 - pw / 2, py - ph / 2, W / 2 + pw / 2, py + ph / 2, ph / 2
            ))
            c.itemconfig(self.pastilla, state="normal")
            c.itemconfig(self.t_oido, state="normal", font=("Segoe UI", 12), width=int(pw - 30))
            c.coords(self.t_oido, W / 2, py)
            c.itemconfig(self.t_estado, font=("Segoe UI", 11, "bold"))
            c.itemconfig(self.t_dicho, font=("Segoe UI", 18), width=int(W * .8))
            panel_width = 0.62

        self.W, self.H = W, H
        self.ww = self.base * 2.6
        c.coords(self.t_estado, W / 2, self.sy)
        c.coords(self.t_dicho, W / 2, self.dy)

        # El panel de escritura queda siempre visible, también al minimizar la burbuja.
        self.panel.place(
            relx=0.5, rely=0.975, anchor="s",
            relwidth=panel_width, height=46
        )
        self.panel.lift()

        # Fondo degradado.
        c.delete("fondo")
        for i in range(48):
            c.create_rectangle(
                0, H * i / 48, W, H * (i + 1) / 48 + 1,
                width=0, fill=fondo_en((i + .5) / 48), tags="fondo"
            )
        c.tag_lower("fondo")

        # Resplandor de la esfera.
        for k, g in enumerate(self.glow):
            r = self.base * (2.35 - 1.45 * k / (self.NG - 1))
            c.coords(g, self.cx - r, self.cy - r, self.cx + r, self.cy + r)

        for i, onda in enumerate(self.ondas):
            c.itemconfig(onda, state="normal" if i < self.nw else "hidden",
                         width=1 if mini else 2)
        for rayo in self.rayos:
            c.itemconfig(rayo, width=2 if mini else 3)
        for petalo in self.petalos:
            c.itemconfig(petalo, width=2 if mini else 3)

        c.configure(cursor="hand2" if mini else "none")
        self.root.attributes("-topmost", True)
        self.root.deiconify()
        self.root.lift()
        self.panel.lift()
        if not mini:
            self.root.after(500, lambda: self.root.attributes("-topmost", False))
        self.col_clave = None
        self.ult = (None, None, None)

    def colorear(self, modo, tema):
        self.col_clave = (modo, tema)
        c, col, blanco = self.c, (TEMAS[tema] if tema else COLORES[modo]), "#ffffff"
        self.fbase = fondo_en(self.cy / self.H)
        self.col = col
        self.glow_s = [.42 * (k / (self.NG - 1)) ** 1.8 for k in range(self.NG)]
        for g, s in zip(self.glow, self.glow_s):
            c.itemconfig(g, fill=mix(self.fbase, col, s))
        self.paleta = [mix(mix(col, self.fbase, .6), mix(col, blanco, .55), i / 7) for i in range(8)]
        for l in self.lineas:
            c.itemconfig(l, fill=mix(col, self.fbase, .5))
        for w in self.ondas:
            c.itemconfig(w, fill=mix(col, blanco, .25))
        c.itemconfig(self.t_estado, fill=col)
        for r in self.rayos:
            c.itemconfig(r, fill=mix(col, blanco, .25), state="hidden")
        for pt in self.petalos:
            c.itemconfig(pt, outline=mix(col, blanco, .35), state="hidden")
        self.bucket = [-1] * len(self.puntos)

    def animar(self):
        if E.salir:
            self.root.destroy()
            return
        if E.mini != self.mini:
            self.aplicar(E.mini)
        if (E.modo, E.tema) != self.col_clave:
            self.colorear(E.modo, E.tema)
        c, modo, R = self.c, E.modo, self.base
        cx, cy = self.cx, self.cy
        self.t += .05
        objetivo = {"idle": .10, "listening": .35, "thinking": .30}.get(modo, .4 + .5 * random.random())
        self.amp += (objetivo - self.amp) * .2
        self.giro += {"idle": .012, "listening": .022, "thinking": .07}.get(modo, .035)

        for k in range(self.NG - 4, self.NG):  # el centro del resplandor late con la voz
            s = min(self.glow_s[k] * (.75 + .55 * self.amp), .7)
            c.itemconfig(self.glow[k], fill=mix(self.fbase, self.col, s))

        e = .35 + .08 * math.sin(self.t * .5)  # inclinación y giro de la esfera
        ce, se = math.cos(e), math.sin(e)
        cg, sg = math.cos(self.giro), math.sin(self.giro)
        dmin, dmax = max(1.0, R * .018), max(2.0, R * .042)
        proy = self.proy
        for i, (x, y, z) in enumerate(self.pts):
            x1 = x * cg + z * sg
            z1 = -x * sg + z * cg
            y2 = y * ce - z1 * se
            z2 = y * se + z1 * ce
            r = R * (1 + self.amp * .10 * math.sin(self.t * 3 + i * 1.3))
            s = 1 + .18 * z2
            px, py = cx + x1 * r * s, cy + y2 * r * s
            prof = (z2 + 1) / 2
            d = dmin + (dmax - dmin) * prof
            c.coords(self.puntos[i], px - d, py - d, px + d, py + d)
            b = int(prof * 7.99)
            if b != self.bucket[i]:
                self.bucket[i] = b
                c.itemconfig(self.puntos[i], fill=self.paleta[b])
            proy[i] = (px, py, z2)

        if self.amp > .22:  # al hablar o pensar aparecen las líneas entre partículas
            for k, (l, (a, b)) in enumerate(zip(self.lineas, self.pares)):
                pa, pb = proy[a], proy[b]
                vis = pa[2] > -.15 and pb[2] > -.15
                if vis:
                    c.coords(l, pa[0], pa[1], pb[0], pb[1])
                if vis != self.lvis[k]:
                    self.lvis[k] = vis
                    c.itemconfig(l, state="normal" if vis else "hidden")
            self.lineas_on = True
        elif self.lineas_on:
            for k, l in enumerate(self.lineas):
                c.itemconfig(l, state="hidden")
                self.lvis[k] = False
            self.lineas_on = False

        nw, ww, wy = self.nw, self.ww, self.wy  # onda de voz punteada
        for i in range(nw):
            f = i / (nw - 1)
            env = math.sin(math.pi * f) ** 1.5
            h = R * (.03 + .30 * self.amp * env * (.45 + .55 * abs(math.sin(self.t * 5 + i * .8) * math.cos(self.t * 2.3 + i * .37))))
            x = cx - ww / 2 + ww * f
            c.coords(self.ondas[i], x, wy - h, x, wy + h)

        etiqueta = f"●  RESPONDE {NOMBRES[E.tema].upper()}" if E.tema else ESTADOS[modo]
        textos = (corto(f"»  {E.oido}") if E.oido else "Di «Jarvis» y tu orden", E.dicho, etiqueta)
        if textos != self.ult:
            self.ult = textos
            c.itemconfig(self.t_oido, text=textos[0])
            c.itemconfig(self.t_dicho, text=textos[1])
            c.itemconfig(self.t_estado, text=textos[2])
        self.root.after(self.RETARDO * 2 if modo == "thinking" else self.RETARDO, self.animar)


if __name__ == "__main__":
    ui = Burbuja()
    if CEREBRO == "local" or not any(CLAVES.values()):
        threading.Thread(target=precalentar_ollama, daemon=True).start()  # carga el modelo mientras arrancas
    threading.Thread(target=bucle_voz, daemon=True).start()
    ui.root.mainloop()
