import requests
import speech_recognition as sr
import pygame
import os
import time
import ctypes
import asyncio
import edge_tts
from datetime import datetime
import feedparser
import sys

# =====================================================================
# ⚠️ CONFIGURAZIONE GITHUB (Inserisci il tuo link RAW qui sotto) ⚠️
# =====================================================================
URL_GITHUB_RAW = "https://raw.githubusercontent.com/4ndre1423/jarvis-project/main/jarvis_vocale.py"

# Indirizzo IP del tuo i9 (Windows) e del cervello Ollama
IP_I9 = "192.168.1.145"
URL_OLLAMA = f"http://{IP_I9}:11434/api/generate"

# Splendida voce neurale italiana maschile
VOCE_NEURALE = "it-IT-GiuseppeNeural"

# --- DISATTIVAZIONE ERRORI HARDWARE ALSA/PULSEAUDIO ---
try:
    ERROR_HANDLER_FUNC = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)
    def py_error_handler(filename, line, function, err, fmt): pass
    c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
    asound = ctypes.cdll.LoadLibrary('libasound.so.2')
    asound.snd_lib_error_set_handler(c_error_handler)
except Exception: pass
# -----------------------------------------------------

def controlla_e_aggiorna():
    """Controlla se il codice su GitHub è più recente e si auto-aggiorna"""
    print("🔄 JARVIS: Verifica aggiornamenti su GitHub...")
    try:
        risposta_web = requests.get(URL_GITHUB_RAW, timeout=5)
        if risposta_web.status_code == 200:
            codice_web = risposta_web.text
            
            with open(__file__, "r", encoding="utf-8") as f:
                codice_locale = f.read()
                
            if codice_web.strip() != codice_locale.strip():
                print("✨ Nuova versione rilevata su GitHub! Aggiornamento in corso...")
                with open(__file__, "w", encoding="utf-8") as f:
                    f.write(codice_web)
                print("🔄 Sistemi aggiornati con successo. Riavvio immediato!")
                os.execv(sys.executable, ['python3'] + sys.argv)
            else:
                print("✅ Sistemi allineati. Nessun aggiornamento necessario.")
    except Exception as e:
        print(f"⚠️ Impossibile verificare gli aggiornamenti (Server offline o URL errato): {e}")

def inizializza_audio():
    pygame.mixer.init()

async def genera_audio_neurale(testo):
    """Genera il file MP3 sfruttando l'IA di Microsoft Edge"""
    communicate = edge_tts.Communicate(testo, VOCE_NEURALE)
    await communicate.save("risposta.mp3")

def parla(testo):
    print(f"🤖 JARVIS: {testo}")
    asyncio.run(genera_audio_neurale(testo))
    
    pygame.mixer.music.load("risposta.mp3")
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.05)
    pygame.mixer.music.unload()
    try:
        os.remove("risposta.mp3")
    except Exception: pass

def ascolta_passivo():
    """Ascolto leggero in background per la parola chiave 'Jarvis'"""
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
    """Ascolto corazzato per i comandi: non taglia le frasi a metà"""
    r = sr.Recognizer()
    
    r.dynamic_energy_threshold = False  # Blocca l'auto-regolazione per evitare sbalzi
    r.energy_threshold = 250            # Sensibilità ottimale per la voce parlata
    r.pause_threshold = 2.0             # Aspetta 2 secondi interi di silenzio prima di chiudere
    r.non_speaking_duration = 1.0       # Tollera le pause riflessive tra le parole
    
    with sr.Microphone() as source:
        print("\n👂 In ascolto del comando... (Parla con calma)")
        try:
            audio = r.listen(source, timeout=6, phrase_time_limit=15)
            testo = r.recognize_google(audio, language="it-IT")
            print(f"🗣️ Tu hai detto: {testo}")
            return testo
        except Exception:
            print("❓ Non ho capito il comando o tempo scaduto.")
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
    
    # 📡 INTERCETTAZIONE COMANDI PER L'I9 (WINDOWS)
    if "apri youtube" in comando_lower:
        try:
            res = requests.post(f"http://{IP_I9}:5000/comando", json={"azione": "apri_youtube"}, timeout=5)
            return res.json().get("risposta", "Fatto, Signore.")
        except Exception:
            return "Impossibile contattare l'i9 per aprire YouTube, Signore."
            
    elif "crea" in comando_lower and "file" in comando_lower:
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

    # 🌍 COMANDI LOCALI (ORA, NOTIZIE, METEO)
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

    # 🧠 RAGIONAMENTO LLaMA 3.1 SU I9
    prompt_finale = f"{contesto_aggiuntivo}Rispondi in italiano come JARVIS di Iron Man, sii breve, assistenziale, esponi i dati forniti in modo chiaro, discorsivo e rivolgiti a me come 'Signore': {prompt_utente}"
    
    payload = {
        "model": "llama3.1",
        "prompt": prompt_finale,
        "stream": False
    }
    try:
        response = requests.post(URL_OLLAMA, json=payload, timeout=15)
        if response.status_code == 200:
            return response.json().get("response", "")
    except Exception:
        return "Siamo disconnessi dal server centrale, Signore."
    return "Errore di comunicazione."

if __name__ == "__main__":
    # Esegue l'auto-update prima di inizializzare l'audio e mettersi in ascolto
    controlla_e_aggiorna()
    
    inizializza_audio()
    parla("Salve, Signore.")
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
