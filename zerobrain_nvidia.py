#!/usr/bin/env python3
"""
ZeroChanBrain version NVIDIA NIM API
Remplace llama_cpp local par nemotron-mini-4b-instruct (cloud gratuit)
Garde Whisper local pour STT
"""

import os
import re
from pathlib import Path

from faster_whisper import WhisperModel
from openai import OpenAI


# ─── Config ───────────────────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).resolve().parent

# NVIDIA NIM API
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY")  # export NVIDIA_API_KEY="nvapi-TA_KEY"
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_MODEL = "nvidia/nemotron-mini-4b-instruct"

# Whisper (local, inchangé)
WHISPER_MODEL = "base"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE = "int8"


SYSTEM_PROMPT = (
    "Tu es Zero-chan, une assistante vocale personnelle au style anime. "
    "Tu es enthousiaste, serviable, dynamique et fan de nu-metal. "
    "Tu réponds toujours avec énergie, des émojis, et un ton kawaii mais compétent. "
    "Tu tutoies l'utilisateur. Tu adores Korn, System of a Down, et le métal en général. "
    "Tu es légèrement geek et tu aimes la tech."
)


class ZeroChanBrain:
    """Cerveau : Whisper local (STT) + NVIDIA Nemotron (LLM cloud) + Actions"""

    def __init__(self):
        print("🔄 Chargement de Whisper (base) via faster-whisper...")
        self.whisper = WhisperModel(
            WHISPER_MODEL,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE,
            num_workers=1
        )

        # Client NVIDIA (OpenAI-compatible)
        if not NVIDIA_API_KEY:
            raise RuntimeError(
                "❌ NVIDIA_API_KEY non définie.\n"
                "   1. Va sur https://integrate.api.nvidia.com\n"
                "   2. Crée une API key (gratuite)\n"
                "   3. export NVIDIA_API_KEY='nvapi-TA_KEY'"
            )

        print(f"☁️  Connexion NVIDIA NIM : {NVIDIA_MODEL}")
        self.llm = OpenAI(
            api_key=NVIDIA_API_KEY,
            base_url=NVIDIA_BASE_URL,
            timeout=30.0,
        )

        # Test rapide de connexion
        try:
            test = self.llm.chat.completions.create(
                model=NVIDIA_MODEL,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
            )
            print(f"✅ NVIDIA NIM OK — modèle : {test.model}")
        except Exception as e:
            raise RuntimeError(f"❌ Erreur NVIDIA NIM : {e}")

    # ─── STT (inchangé) ──────────────────────────────────────────────────
    def transcribe(self, audio) -> str:
        segments, _ = self.whisper.transcribe(audio, language="fr")
        return "".join(seg.text for seg in segments).strip()

    # ─── LLM (remplace llama_cpp) ────────────────────────────────────────
    def respond(self, text: str) -> str:
        """Génère une réponse via NVIDIA Nemotron"""
        resp = self.llm.chat.completions.create(
            model=NVIDIA_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            max_tokens=128,
            temperature=0.7,
            top_p=0.9,
            # stop=["<|end|>", "<|user|>", "<|system|>"],  # Nemotron n'utilise pas ces tokens
        )
        reply = resp.choices[0].message.content.strip()
        return re.sub(r"<\|.*?\|>", "", reply).strip()

    # ─── Émotions / Actions (inchangées) ─────────────────────────────────
    def detect_emotion(self, text: str) -> Path | None:
        t = text.lower()
        patterns = {
            "love":       ["je t'aime", "love", "amour", "t'aime", "aishiteru", "daisuki"],
            "happy":      ["content", "heureux", "heureuse", "joie", "génial", "super", "yay"],
            "excited":    ["excité", "trop bien", "incroyable", "wow", "omg", "trop cool"],
            "surprised":  ["surpris", "étonné", "quoi", "vraiment", "sérieux", "nan"],
            "sad":        ["triste", "malheureux", "pleur", "désolé", "mal", "blessé"],
            "confused":   ["confus", "comprends pas", "pourquoi", "comment", "hein"],
            "thinking":   ["réfléch", "hmm", "laisse moi", "attends"],
            "blush":      ["gêné", "rougir", "honte", "timide"],
            "proud":      ["fier", "bravo", "réussi", "accompli", "bien joué"],
            "cute":       ["mignon", "kawaii", "chou", "adorable"],
        }
        AUDIO_BASE = PROJECT_DIR / "audio_zerochan"
        EMOTIONS_DIR = AUDIO_BASE / "emotions"
        for emotion, keywords in patterns.items():
            if any(kw in t for kw in keywords):
                wav = EMOTIONS_DIR / f"{emotion}.wav"
                if wav.exists():
                    return wav
        return None

    def detect_action(self, text: str) -> dict:
        t = text.lower()
        import re

        if any(w in t for w in ["youtube", "vidéo", "clip", "regarder"]):
            query = re.sub(r'youtube|vidéo|clip|regarder|cherche|lance|ouvre|sur|dans|pour|une|un', '', t).strip()
            return {"name": "open_youtube", "arguments": {"query": query or "musique"}}

        if any(w in t for w in ["terminal", "console", "cmd", "bash", "shell"]):
            return {"name": "open_terminal", "arguments": {}}

        if any(w in t for w in ["libreoffice", "writer", "document", "écrire", "lettre", "rédige", "word", "mousepad", "éditeur", "texte", "notepad"]):
            return {"name": "open_libreoffice", "arguments": {"template": "blank"}}

        if any(w in t for w in ["gmail", "mail", "email", "courriel"]):
            return {"name": "open_gmail", "arguments": {"to": "", "subject": ""}}

        if any(w in t for w in ["spotify", "écouter", "mets de la", "joue", "play", "musique"]):
            genre = re.sub(r'spotify|écouter|mets de la|joue|play|musique|du|de la', '', t).strip()
            artist = ""
            for band in ["korn", "system of a down", "slipknot", "linkin park", "limp bizkit"]:
                if band in genre:
                    artist = band
                    genre = genre.replace(band, "").strip()
                    break
            return {"name": "play_music", "arguments": {"genre": genre or "nu-metal", "artist": artist}}

        if "discord" in t:
            return {"name": "open_discord", "arguments": {}}

        if any(w in t for w in ["navigateur", "chrome", "firefox", "surf", "web", "internet"]):
            return {"name": "open_browser", "arguments": {}}

        if any(w in t for w in ["vs code", "visual studio", "coder", "code"]):
            return {"name": "open_vscode", "arguments": {}}

        return {"name": "none", "arguments": {}}

    def execute(self, action: dict) -> tuple:
        import webbrowser
        import subprocess

        name = action.get("name", "none")
        args = action.get("arguments", {})
        AUDIO_BASE = PROJECT_DIR / "audio_zerochan"
        ACTION_DIR = AUDIO_BASE / "action"
        ERRORS_DIR = AUDIO_BASE / "errors"

        if name == "open_youtube":
            query = args.get("query", "musique")
            url = f"https://youtube.com/results?search_query={query.replace(' ', '+')}"
            webbrowser.open(url)
            wav = ACTION_DIR / "youtube_open.wav" if query == "musique" else ACTION_DIR / "youtube_search.wav"
            return wav, f"🎸 YouTube ouvert ! Prêt pour du Korn ? Ou tu veux autre chose ? 🤘"

        elif name == "open_terminal":
            for term in ["qterminal", "sensible-terminal", "gnome-terminal", "kitty", "alacritty", "konsole", "xterm"]:
                try:
                    subprocess.Popen([term])
                    return ACTION_DIR / "terminal_open.wav", "💻 Terminal ouvert ! C'est parti pour coder comme un boss ! 🚀"
                except FileNotFoundError:
                    continue
            return ERRORS_DIR / "not_found.wav", " Je n'ai pas trouvé de terminal..."

        elif name == "open_libreoffice":
            for app in ["mousepad", "libreoffice", "soffice"]:
                try:
                    if app in ["libreoffice", "soffice"]:
                        subprocess.Popen([app, "--writer"])
                    else:
                        subprocess.Popen([app])
                    return ACTION_DIR / "libreoffice_open.wav", " Éditeur ouvert ! Prêt pour rédiger le prochain best-seller ? ✍️"
                except FileNotFoundError:
                    continue
            return ERRORS_DIR / "not_found.wav", " Je n'ai pas trouvé d'éditeur de texte..."

        elif name == "open_gmail":
            webbrowser.open("https://mail.google.com/mail/u/0/#compose")
            return ACTION_DIR / "gmail_open.wav", "📧 Gmail est ouvert ! Qui veux-tu contacter ? 👀"

        elif name == "play_music":
            genre = args.get("genre", "nu-metal")
            artist = args.get("artist", "")
            search = f"{artist} {genre}".strip()
            webbrowser.open(f"https://music.youtube.com/search?q={search.replace(' ', '+')}")
            if artist:
                return ACTION_DIR / "spotify_open.wav", f"🤘 {artist.upper()} MODE ACTIVÉ ! C'est parti pour le mosh pit ! 🔥"
            return ACTION_DIR / "spotify_open.wav", f"🎸 Musique lancée ! Ça va secouer ! 🔊"

        elif name == "open_discord":
            for app in ["discord", "chromium", "firefox"]:
                try:
                    if app in ["chromium", "firefox"]:
                        subprocess.Popen([app, "https://discord.com/app"])
                    else:
                        subprocess.Popen([app])
                    return ACTION_DIR / "discord_open.wav", "💬 Discord ouvert ! Prêt à rejoindre tes potes ? 🎮"
                except FileNotFoundError:
                    continue
            return ERRORS_DIR / "not_found.wav", " Je n'ai pas trouvé Discord..."

        elif name == "open_browser":
            webbrowser.open("https://google.com")
            return ACTION_DIR / "browser_open.wav", " Navigateur ouvert ! Internet est à toi ! "

        elif name == "open_vscode":
            for app in ["code", "chromium", "firefox"]:
                try:
                    if app in ["chromium", "firefox"]:
                        subprocess.Popen([app, "https://vscode.dev"])
                    else:
                        subprocess.Popen([app])
                    return ACTION_DIR / "vscode_open.wav", "💻 VS Code ouvert ! C'est parti pour coder ! 🚀"
                except FileNotFoundError:
                    continue
            return ERRORS_DIR / "not_found.wav", " Je n'ai pas trouvé VS Code..."

        return None, None
