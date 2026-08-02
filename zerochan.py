#!/usr/bin/env python3
"""
Zero-chan : Assistante vocale manga overlay
Avatar animé (GIF) + Whisper local + NVIDIA Nemotron-mini-4B (cloud) + wav pré-enregistrés
"""

import sys
import os
import re
import subprocess
import threading
import queue
import numpy as np
import sounddevice as sd
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QFileSystemWatcher
from PyQt6.QtGui import QMovie, QKeySequence, QShortcut

from faster_whisper import WhisperModel


# ─── Chemins ───────────────────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).resolve().parent
IMAGE_GIF = PROJECT_DIR / "image.gif"
AUDIO_BASE = PROJECT_DIR / "audio_zerochan"
ACTION_DIR = AUDIO_BASE / "action"
EMOTIONS_DIR = AUDIO_BASE / "emotions"
ERRORS_DIR = AUDIO_BASE / "errors"
GREETINGS_DIR = AUDIO_BASE / "greetings"
MUSIC_DIR = AUDIO_BASE / "music"
SYSTEM_DIR = AUDIO_BASE / "system"
PW_PLAY = "/usr/bin/pw-play"
HOTKEY_TRIGGER = Path("/tmp/zerochan_hotkey_trigger")


# ── AudioCapture ──────────────────────────────────────────────────────────
class AudioCapture(QObject):
    """Capture audio du micro en temps réel"""
    audio_ready = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self.recording = False
        self.audio_queue = queue.Queue()
        self.stream = None

    def start_listening(self):
        self.recording = True
        self.audio_queue = queue.Queue()

        def callback(indata, frames, time_info, status):
            if self.recording:
                self.audio_queue.put(indata.copy())

        self.stream = sd.InputStream(
            samplerate=16000, channels=1, dtype=np.float32, callback=callback,
        )
        self.stream.start()

    def stop_listening(self):
        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def get_audio(self):
        chunks = []
        while not self.audio_queue.empty():
            chunks.append(self.audio_queue.get())
        return np.concatenate(chunks).flatten() if chunks else None


# ── AudioPlayer ───────────────────────────────────────────────────────────
class AudioPlayer:
    """Joue les fichiers wav via pw-play (PipeWire)"""

    def __init__(self):
        self._lock = threading.Lock()

    def play(self, wav_path: Path):
        """Joue un wav en arrière-plan"""
        if not wav_path.exists():
            return
        def _play():
            with self._lock:
                subprocess.run([PW_PLAY, str(wav_path)], capture_output=True)
        threading.Thread(target=_play, daemon=True).start()


# ── AvatarWidget ──────────────────────────────────────────────────────────
class AvatarWidget(QWidget):
    """Widget de l'avatar manga avec GIF animé + bulle + barre de chat"""

    chat_submitted = pyqtSignal(str)
    mic_clicked = pyqtSignal()  # Signal pour le bouton micro

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen.width() - 320, screen.height() - 520, 300, 500)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # GIF animé (scaled pour tenir dans 200x200)
        self.movie = QMovie(str(IMAGE_GIF))
        self.avatar_label = QLabel()
        self.avatar_label.setMovie(self.movie)
        self.avatar_label.setFixedSize(200, 200)
        self.avatar_label.setScaledContents(True)
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.movie.start()

        # Bulle de dialogue
        self.bubble = QLabel("Konnichiwa ! ")
        self.bubble.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bubble.setStyleSheet(
            """
            QLabel {
                background-color: rgba(255, 255, 255, 230);
                border-radius: 18px;
                padding: 12px 16px;
                color: #333;
                font-family: 'Noto Sans', 'Segoe UI', sans-serif;
                font-size: 14px;
                font-weight: 600;
                border: 2px solid #FF69B4;
            }
            """
        )
        self.bubble.setWordWrap(True)
        self.bubble.setFixedWidth(270)

        # Visualiseur audio
        self.visualizer = QLabel("∿∿∿")
        self.visualizer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.visualizer.setStyleSheet("color: #FF69B4; font-size: 18px;")

        # ── Barre de chat ──
        chat_bar = QHBoxLayout()
        chat_bar.setSpacing(4)

        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Parle à Zero-chan...")
        self.chat_input.setStyleSheet(
            """
            QLineEdit {
                background-color: rgba(255, 255, 255, 230);
                border: 2px solid #FF69B4;
                border-radius: 12px;
                padding: 8px 12px;
                color: #333;
                font-family: 'Noto Sans', sans-serif;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #FF1493;
            }
            """
        )
        self.chat_input.returnPressed.connect(self._on_chat_submit)

        self.chat_btn = QPushButton("✨")
        self.chat_btn.setFixedSize(36, 36)
        self.chat_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #FF69B4;
                border: none;
                border-radius: 18px;
                font-size: 18px;
                color: white;
            }
            QPushButton:hover {
                background-color: #FF1493;
            }
            """
        )
        self.chat_btn.clicked.connect(self._on_chat_submit)

        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setFixedSize(36, 36)
        self.mic_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #4A90E2;
                border: none;
                border-radius: 18px;
                font-size: 18px;
                color: white;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
            """
        )
        self.mic_btn.clicked.connect(self.mic_clicked.emit)

        chat_bar.addWidget(self.chat_input)
        chat_bar.addWidget(self.mic_btn)
        chat_bar.addWidget(self.chat_btn)

        layout.addWidget(self.bubble, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.avatar_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.visualizer, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(chat_bar)
        self.setLayout(layout)

        # Timers
        self.viz_timer = QTimer()
        self.viz_timer.timeout.connect(self._update_visualizer)

        self.idle_timer = QTimer()
        self.idle_timer.timeout.connect(self._idle_bounce)
        self.idle_timer.start(2000)

    def _idle_bounce(self):
        self.avatar_label.setGraphicsEffect(None)

    def _update_visualizer(self):
        import random
        bars = "".join(["▂" if random.random() > 0.5 else "▄" for _ in range(10)])
        self.visualizer.setText(bars)

    def say(self, text: str):
        self.bubble.setText(text)

    def show_listening(self):
        self.bubble.setText(" J'écoute...")
        self.viz_timer.start(100)

    def show_thinking(self):
        self.bubble.setText("💭 ...")
        self.viz_timer.stop()
        self.visualizer.setText("")

    def show_idle(self):
        self.bubble.setText("Zero-chan prête !\nCtrl+Shift+Z ou tape ici ✨")
        self.viz_timer.stop()
        self.visualizer.setText("∿∿∿")

    def _on_chat_submit(self):
        """Émis quand l'utilisateur tape du texte"""
        text = self.chat_input.text().strip()
        if text:
            self.chat_input.clear()
            self.chat_submitted.emit(text)


# Import du nouveau cerveau NVIDIA Nemotron
from zerobrain_nvidia import ZeroChanBrain


# ── ZeroChanApp ───────────────────────────────────────────────────────────
class ZeroChanApp(QObject):
    """Application principale"""

    def __init__(self):
        super().__init__()
        self.app = QApplication(sys.argv)
        self.avatar = AvatarWidget()
        self.brain = ZeroChanBrain()
        self.audio = AudioCapture()
        self.audio_player = AudioPlayer()

        # Connecter la barre de chat
        self.avatar.chat_submitted.connect(self._on_chat_input)
        
        # Connecter le bouton micro
        self.avatar.mic_clicked.connect(self._activate)

        # Configurer le hotkey global via xbindkeys
        self._setup_hotkey()

        self.avatar.show()

    def _setup_hotkey(self):
        """Configure Ctrl+Shift+Z comme raccourci global via xbindkeys"""
        trigger_path = str(HOTKEY_TRIGGER)
        
        # Lire le fichier xbindkeysrc existant
        xbindkeys_config = Path.home() / ".xbindkeysrc"
        config_lines = []
        if xbindkeys_config.exists():
            config_lines = xbindkeys_config.read_text().splitlines()
        
        # Vérifier si notre hotkey existe déjà
        zerochan_marker = "# Zero-chan hotkey"
        has_zerochan_hotkey = any(zerochan_marker in line for line in config_lines)
        
        if not has_zerochan_hotkey:
            # Ajouter notre entrée
            new_entry = [
                "",
                zerochan_marker,
                f'"/usr/bin/touch {trigger_path}"',
                "    Ctrl+Shift+Z",
            ]
            with open(xbindkeys_config, "a") as f:
                f.write("\n".join(new_entry) + "\n")
            print(f"✅ Hotkey Ctrl+Shift+Z ajouté à {xbindkeys_config}")
        
        # Redémarrer xbindkeys
        subprocess.run(["pkill", "-9", "xbindkeys"], capture_output=True)
        import time
        time.sleep(0.2)
        subprocess.Popen(["xbindkeys"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ xbindkeys redémarré")
        
        # Créer le fichier trigger s'il n'existe pas
        if not HOTKEY_TRIGGER.exists():
            HOTKEY_TRIGGER.touch()
        
        # Surveiller le fichier trigger
        self.hotkey_watcher = QFileSystemWatcher([str(HOTKEY_TRIGGER)])
        self.hotkey_watcher.fileChanged.connect(self._on_hotkey_triggered)
        print("✅ Surveillance du hotkey activée")

    def _on_hotkey_triggered(self, path):
        """Appelé quand le fichier trigger est modifié par xbindkeys"""
        print("🔥 Hotkey Ctrl+Shift+Z détecté !")
        self._activate()
        # Ré-enregistrer le fichier dans le watcher (nécessaire après modification)
        if str(HOTKEY_TRIGGER) not in self.hotkey_watcher.files():
            self.hotkey_watcher.addPath(str(HOTKEY_TRIGGER))

    def _on_chat_input(self, text: str):
        """Traite l'input texte de la barre de chat"""
        self.avatar.show_thinking()
        self.audio_player.play(SYSTEM_DIR / "processing.wav")
        self._process_text(text)

    def _activate(self):
        """Activation vocale par hotkey"""
        self.avatar.show_listening()
        self.audio_player.play(SYSTEM_DIR / "listening.wav")
        self.audio.start_listening()
        QTimer.singleShot(5000, self._process_audio)

    def _process_audio(self):
        self.audio.stop_listening()
        self.avatar.show_thinking()
        self.audio_player.play(SYSTEM_DIR / "processing.wav")

        audio = self.audio.get_audio()
        if audio is None or len(audio) < 16000:
            self.avatar.say("😅 Je n'ai rien entendu...")
            self.audio_player.play(ERRORS_DIR / "error.wav")
            return

        text = self.brain.transcribe(audio)
        print(f"🎤 Entendu : {text}")

        if not text:
            self.avatar.say("🤔 Je n'ai pas compris...")
            self.audio_player.play(ERRORS_DIR / "not_found.wav")
            return

        self._process_text(text)

    def _process_text(self, text: str):
        """Pipeline commun : audio ou texte"""
        # 1) Détecter l'action
        action = self.brain.detect_action(text)

        # 2) Réponse conversationnelle Phi-3
        personality_reply = self.brain.respond(text)
        print(f" Zero-chan dit : {personality_reply}")

        # 3) Exécuter l'action
        wav_path, action_msg = self.brain.execute(action)

        # 4) Afficher + jouer
        if action_msg:
            combined = action_msg
        else:
            combined = personality_reply

        self.avatar.say(combined)

        # Jouer le wav de l'action si dispo
        if wav_path and wav_path.exists():
            self.audio_player.play(wav_path)
        else:
            # Tenter dans l'ordre : émotion de la réponse LLM → greeting → fallback
            emotion_wav = self.brain.detect_emotion(combined) or self.brain.detect_emotion(text)
            if emotion_wav:
                self.audio_player.play(emotion_wav)
            else:
                self._play_contextual(text, combined)

    def _play_contextual(self, user_text: str, reply_text: str):
        """Joue le wav le plus pertinent selon le contexte conversationnel"""
        t = user_text.lower()
        r = reply_text.lower()

        # Greetings
        if any(w in t for w in ["salut", "bonjour", "hey", "coucou", "yo"]):
            self.audio_player.play(GREETINGS_DIR / "hello.wav")
        elif any(w in t for w in ["bye", "au revoir", "à plus", "ciao"]):
            self.audio_player.play(GREETINGS_DIR / "bye.wav")
        elif any(w in t for w in ["matin", "réveil", "bien dormi"]):
            self.audio_player.play(GREETINGS_DIR / "good_morning.wav")
        elif any(w in t for w in ["nuit", "dormir", "bonne nuit", "coucher"]):
            self.audio_player.play(GREETINGS_DIR / "good_night.wav")
        elif any(w in t for w in ["retour", "re"]):
            self.audio_player.play(GREETINGS_DIR / "welcome_back.wav")
        # Erreurs / confirmations
        elif any(w in t for w in ["merci", "thanks", "arigato"]):
            self.audio_player.play(ERRORS_DIR / "thanks.wav")
        elif any(w in t for w in ["annul", "stop", "arrête", "non"]):
            self.audio_player.play(ERRORS_DIR / "cancelled.wav")
        elif any(w in t for w in ["confirme", "oui", "vas-y", "ok"]):
            self.audio_player.play(ERRORS_DIR / "confirm.wav")
        elif any(w in t for w in ["erreur", "bug", "marche pas", "problème"]):
            self.audio_player.play(ERRORS_DIR / "error.wav")
        elif any(w in t for w in ["désolé", "pardon", "sorry"]):
            self.audio_player.play(ERRORS_DIR / "sorry.wav")
        # Fallback : hey.wav
        else:
            self.audio_player.play(GREETINGS_DIR / "hey.wav")

    def run(self):
        self.avatar.show_idle()
        self.audio_player.play(SYSTEM_DIR / "startup.wav")
        sys.exit(self.app.exec())


if __name__ == "__main__":
    app = ZeroChanApp()
    app.run()
