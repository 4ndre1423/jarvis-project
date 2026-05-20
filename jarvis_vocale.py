import requests
import speech_recognition as sr
import pygame
import os
import time
import ctypes
import asyncio  # Serve per gestire la libreria edge-tts
import edge_tts
from datetime import datetime
import feedparser

# --- TRUCCO PER ZITTIRE GLI ERRORI ALSA/PULSEAUDIO ---
try:
    ERROR_HANDLER_FUNC = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)
    def py_error_handler(filename, line, function, err, fmt): pass
    c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
    asound = ctypes.cdll.LoadLibrary('libasound.so.2')
    asound.snd_lib_error_set_handler(c_error_handler)
except Exception: pass
# -----------------------------------------------------

IP_I9 = "192.168.1.145"
URL_OLLAMA = f"http://{IP_I9}:11434/api/generate"

# Scegliamo la super voce neurale maschile di Microsoft
VOCE_NEURALE = "it-IT-GiuseppeNeural"

def inizializza_audio():
    pygame.mixer.init()

async def genera_audio_neurale(testo):
    """Genera il file MP3 sfruttando l'IA di Microsoft Edge"""
    communicate = edge_tts.Communicate(testo, VOCE_NEURALE)
    await communicate.save("risposta.mp3")

def parla(testo):
    print(f"🤖 JARVIS: {testo}")
    # Eseguiamo la generazione asincrona dentro la funzione normale
    asyncio.run(genera_audio_neurale(testo))

    # Riproduzione con Pygame
    pygame.mixer.music.load("risposta.mp3")
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.05)
    pygame.mixer.music.unload()
    try:
        os.remove("risposta.mp3")
    except Exception: pass

def ascolta_passivo():
    r = sr.Recognizer()
    r.dynamic_energy_threshold = False
    r.energy_threshold = 300
    r.pause_threshold = 0.5
    with sr.Microphone() as source:
        try:
            audio = r.listen(source, timeout=None, phrase_time_limit=4)
            return r.recognize_google(audio, language="it-IT").lower()
        except Exception: return ""

def ascolta_comando():
    r = sr.Recognizer()

    # 🌟 SOGLIA FISSA E TOLLERANZA MASSIMA 🌟
    r.dynamic_energy_threshold = False  # Blocchiamo l'auto-regolazione che fa danni
    r.energy_threshold = 250            # Abbassiamo la soglia per sentire anche le parole a bassa voce
    r.pause_threshold = 2.0             # Forziamo ad aspettare ben 2 SECONDI di silenzio tombale prima di chiudere
    r.non_speaking_duration = 1.0       # Tollera ampie pause tra una parola e l'altra

    with sr.Microphone() as source:
        print("\n👂 In ascolto del comando... (Parla con calma e scandisci bene)")
        # Rimuoviamo l'adjust_for_ambient_noise che alterava i valori
        try:
            # Diamo 15 secondi totali per completare la frase
            audio = r.listen(source, timeout=6, phrase_time_limit=15)
            testo = r.recognize_google(audio, language="it-IT")
            print(f"🗣️ Tu hai detto: {testo}")
            return testo
        except Exception as e:
            print("❓ Non ho capito il comando o c'è stato un timeout.")
            return None

def ottieni_meteo(citta):
    try:
        url = f"https://wttr.in/{citta}?format=j1"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            dati = res.json()
            condizione = dati['current_condition'][0]['lang_it'][0]['value']
            temp = dati['current_condition'][0]['temp_C']
            umidita = dati['current_condition'][0]['humidity']
            return f"Meteo a {citta}: {condizione}, Temperatura: {temp} gradi, Umidità: {umidita}%."
    except Exception: pass
    return f"Impossibile recuperare i dati meteo per {citta} al momento."

def ottieni_notizie():
    try:
        url_rss = "https://www.ansa.it/sito/notizie/topnews/topnews_rss.xml"
        feed = feedparser.parse(url_rss)
        if len(feed.entries) > 0:
            notizie_testo = "Ultime notizie flash dall'ANSA: "
            for i, entry in enumerate(feed.entries[:3]):
                notizie_testo += f"{i+1}) {entry.title}. "
            return notizie_testo
    except Exception: pass
    return "Impossibile collegarsi al feed delle notizie al momento, Signore."

def interroga_cervello(prompt_utente):
    comando_lower = prompt_utente.lower()

    # 🌟 INTERCETTAZIONE COMANDI PER L'I9 🌟

    # Se dici "apri youtube"
    if "apri youtube" in comando_lower:
        try:
            res = requests.post(f"http://{IP_I9}:5000/comando", json={"azione": "apri_youtube"}, timeout=5)
            return res.json().get("risposta", "Fatto, Signore.")
        except Exception:
            return "Impossibile contattare l'i9 per aprire YouTube, Signore."

    # Se dici "crea un file" o "crea il file appunti"
    elif "crea" in comando_lower and "file" in comando_lower:
        # Proviamo a estrarre il nome del file (es: se dici "crea file appunti", prende "appunti")
        parole = prompt_utente.split()
        nome_file = "Nota_Jarvis"
        for i, parola in enumerate(parole):
            if parola.lower() == "file" and i+1 < len(parole):
                nome_file = parole[i+1]
                break
        try:
            res = requests.post(f"http://{IP_I9}:5000/comando", json={"azione": "crea_file", "parametri": nome_file}, timeout=5)
            return res.json().get("risposta", "File creato, Signore.")
        except Exception:
            return "Impossibile trasmettere l'ordine di creazione file all'i9."

    # --- (Tutto il resto del codice per meteo, ore e notizie rimane identico sotto) ---
    contesto_aggiuntivo = ""
    if "ora" in comando_lower or "ore" in comando_lower or "giorno" in comando_lower or "data" in comando_lower:
        ora_attuale = datetime.now().strftime("%H:%M")
        data_attuale = datetime.now().strftime("%d/%m/%Y")
        contesto_aggiuntivo = f"[INFO TEMPO REALE: Oggi è il {data_attuale} e sono le ore {ora_attuale}]. "
    elif "notizie" in comando_lower or "notiziario" in comando_lower or "succede nel mondo" in comando_lower:
        info_notizie = ottieni_notizie()
        contesto_aggiuntivo = f"[INFO TEMPO REALE CONTESTO: {info_notizie}]. "
    elif "meteo" in comando_lower or "tempo fa" in comando_lower or "piove" in comando_lower:
        parole = prompt_utente.split()
        citta = "Roma"
        for i, parola in enumerate(parole):
            if parola.lower() in ["a", "per", "di"] and i+1 < len(parole):
                citta = parole[i+1].strip("?.,")
                break
        info_meteo = ottieni_meteo(citta)
        contesto_aggiuntivo = f"[INFO TEMPO REALE CONTESTO: {info_meteo}]. "

    prompt_finale = f"{contesto_aggiuntivo}Rispondi in italiano come JARVIS di Iron Man, sii breve, assistenziale, esponi i dati forniti in modo chiaro, discorsivo e rivolgiti a me come 'Signore': {prompt_utente}"

    payload = {"model": "llama3.1", "prompt": prompt_finale, "stream": False}
    try:
        response = requests.post(URL_OLLAMA, json=payload, timeout=15)
        if response.status_code == 200:
            return response.json().get("response", "")
    except Exception:
        return "Siamo disconnessi dal server centrale, Signore."
    return "Errore di comunicazione."

if __name__ == "__main__":
    inizializza_audio()
    parla("Sistemi di sintesi vocale neurale attivati. Sono pronto, Signore.")
    print("\n💤 JARVIS è in standby. Pronuncia 'Jarvis' per attivarlo...")

    while True:
        voce_background = ascolta_passivo()

        if "jarvis" in voce_background or "ciarvis" in voce_background or "arvis" in voce_background:
            print("\n⏰ Sveglia! Parola chiave rilevata.")
            parla("Al vostro servizio, Signore.")

            comando = ascolta_comando()
            if comando:
                if "spegni" in comando.lower() or "esci" in comando.lower():
                    parla("Disattivazione dei sistemi. Arrivederci, Signore.")
                    break
                risposta = interroga_cervello(comando)
                parla(risposta)

            print("\n💤 JARVIS torna in standby...")
