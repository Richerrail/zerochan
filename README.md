# Zero-chan 🎌

**Assistante vocale manga overlay** — Avatar animé multi-GIF + Whisper local + NVIDIA Nemotron (cloud) + TTS pré-enregistré

![Zero-chan](image.gif)

---

## ✨ Fonctionnalités

| Fonction | Techno |
|----------|--------|
| **Reconnaissance vocale (STT)** | `faster-whisper` base (local, CPU, int8) |
| **LLM Conversation** | `nvidia/nemotron-mini-4b-instruct` via NVIDIA NIM API (gratuit, ~100-200 tok/s) |
| **Synthèse vocale (TTS)** | WAV pré-enregistrés (clone vocal Qwen3-TTS, style anime JP → texte FR) |
| **Actions système** | YouTube, Terminal, LibreOffice, Gmail, YouTube Music, Discord, Navigateur, VS Code, Kimi AI, Zer0Cod, GitHub, Hugging Face, Telegram, pi-cli, qwen-cli |
| **Émotions** | 10+ émotions détectées (love, happy, excited, sad, confused, thinking, blush, proud, cute, surprised) |
| **Interface** | PyQt6 overlay frameless, always-on-top, **12 GIFs animés**, bulle chat, barre de saisie |
| **Avatar GIF** | **Rotation aléatoire 3s** au repos + **GIF spécifique par action** (retour auto 5s) |
| **Hotkey globale** | `Ctrl+Shift+Z` (via `xbindkeys`) |
| **Entrée texte** | Barre de chat intégrée |
| **Navigateur** | Firefox (défaut système via `webbrowser`) |
| **Fermeture** | Touche `Échap` ou bouton `✕` rouge |

---

## 🚀 Installation

### Prérequis
- Linux (testé Ubuntu/Debian/Arch)
- Python 3.10+
- PipeWire (`pw-play`) pour l'audio
- `xbindkeys` pour le hotkey global
- Microphone fonctionnel

### 1. Cloner & installer
```bash
cd /home/k00/Bureau/zerochan
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Dépendances système
```bash
# Ubuntu/Debian
sudo apt install python3-venv portaudio19-dev libportaudio2 xbindkeys

# Arch
sudo pacman -S python portaudio xbindkeys
```

### 3. Clé API NVIDIA (gratuite)
1. Va sur **[build.nvidia.com](https://build.nvidia.com)**
2. Connecte-toi → **Get API Key** → Génère une clé
3. Exporte-la :
```bash
export NVIDIA_API_KEY="nvapi-TA_CLE_ICI"
```
*(Ajoute au `~/.bashrc` ou `~/.zshrc` pour persistance)*

### 4. Fichiers audio requis
Le dossier `audio_zerochan/` doit contenir les WAV organisés ainsi :
```
audio_zerochan/
├── action/        # youtube_open, terminal_open, spotify_open, etc.
├── emotions/      # happy, sad, excited, love, thinking, etc.
├── errors/        # error, not_found, cancelled, confirm, sorry, thanks
├── greetings/     # hello, hey, bye, good_morning, good_night, welcome_back
├── music/         # (optionnel)
└── system/        # startup, listening, processing, shutdown, volume_*
```
> Les WAV fournis sont générés via **Qwen3-TTS (voice cloning)** sur HF Space `wordercom-qwen3-tts`.

### 5. GIFs animés
Place tes fichiers `image.gif`, `image1.gif` ... `image11.gif` dans le dossier du projet.
- **12 GIFs** détectés automatiquement (`image*.gif`)
- **Tri numérique** : `image.gif` (0) → `image1.gif` (1) → ... → `image11.gif` (11)

---

## ▶️ Lancement

### Option A : Terminal
```bash
cd /home/k00/Bureau/zerochan
export NVIDIA_API_KEY="nvapi-TA_CLE_ICI"
python3 zerochan.py
```

### Option B : Lanceur Bureau (sans terminal)
Double-clic sur **`Zero-chan.desktop`** sur le Bureau.
> La clé API est embarquée dans le lanceur.

---

## 🎮 Contrôles

| Action | Raccourci / UI |
|--------|----------------|
| **Parler (micro)** | `Ctrl+Shift+Z` (maintenu 5s max) |
| **Taper un message** | Clic dans la barre → texte → `Entrée` ou `✨` |
| **Micro bouton** | Clic sur `🎤` dans l'UI |
| **Fermer (clavier)** | Touche **`Échap`** |
| **Fermer (souris)** | Clic sur bouton **`✕` rouge** (barre de chat) |

---

## 🎤 Commandes vocales (Actions)

| Commande | Action | GIF |
|----------|--------|-----|
| `"ouvre youtube"` / `"regarde vidéo"` | Ouvre YouTube (recherche optionnelle) | `image1.gif` |
| `"ouvre terminal"` / `"lance console"` | Ouvre un terminal | `image2.gif` |
| `"ouvre libreoffice"` / `"éditeur"` | Ouvre Mousepad/LibreOffice | `image3.gif` |
| `"ouvre gmail"` / `"mail"` | Ouvre Gmail (nouveau message) | `image4.gif` |
| `"joue musique"` / `"mets du Korn"` | YouTube Music (détecte artiste: Korn, SOAD, Slipknot, LP, Limp Bizkit) | `image5.gif` |
| `"ouvre discord"` | Discord Web | `image6.gif` |
| `"ouvre navigateur"` / `"chrome"` / `"firefox"` | Google | `image7.gif` |
| `"ouvre vscode"` / `"code"` | VS Code (ou vscode.dev) | `image8.gif` |
| `"ouvre kimi"` | Kimi AI (https://kimi.com) | `image7.gif` |
| `"ouvre zerocod"` | Zer0Cod.desktop (fallback VS Code) | `image8.gif` |
| `"ouvre github"` | GitHub.com | `image7.gif` |
| `"ouvre huggingface"` | HuggingFace.co | `image7.gif` |
| `"ouvre telegram"` | Telegram Web | `image7.gif` |
| `"ouvre pi"` / `"pi-cli"` | Lance `pi` dans un terminal | `image9.gif` |
| `"ouvre qwen"` / `"qwen-cli"` | Lance `qwen` dans un terminal | `image10.gif` |

> **Tout le reste = Discussion libre** avec Nemotron (personnalité Zero-chan anime/metal/kawaii)

---

## 🏗️ Architecture

```
zerochan.py           # App principale (PyQt6, hotkey, pipeline audio, GIFs)
zerobrain_nvidia.py   # Cerveau : Whisper (STT) + NVIDIA Nemotron (LLM) + Actions/Émotions/GIF mapping
audio_zerochan/       # WAV TTS organisés par catégorie
image*.gif            # 12 Avatars animés (image.gif à image11.gif)
venv/                 # Environnement Python isolé
Zero-chan.desktop     # Lanceur Bureau (sans terminal)
requirements.txt      # Dépendances Python
README.md             # Cette doc
LICENSE               # MIT License
```

### Pipeline vocal
```
Micro (16kHz) → Whisper (local) → Texte
    ↓
Nemotron-mini-4B (NVIDIA NIM cloud) → Réponse + Détection action/émotion/GIF
    ↓
Exécution action (webbrowser/subprocess) → WAV contextuel (pw-play)
    ↓
Affichage bulle + GIF spécifique (3s) → Retour rotation aléatoire (5s)
```

---

## ⚙️ Configuration

### Modèle LLM (dans `zerobrain_nvidia.py`)
```python
NVIDIA_MODEL = "nvidia/nemotron-mini-4b-instruct"  # Rapide, 4B
# Alternatives gratuites :
# "nvidia/nvidia-nemotron-nano-9b-v2"   # 9B, plus récent
# "meta/llama-3.1-8b-instruct"          # Standard
# "nv-mistralai/mistral-nemo-12b-instruct"  # 12B, excellent FR
```

### Whisper (dans `zerobrain_nvidia.py`)
```python
WHISPER_MODEL = "base"      # tiny, base, small, medium, large-v3
WHISPER_DEVICE = "cpu"      # ou "cuda" si GPU dispo
WHISPER_COMPUTE = "int8"    # int8, int8_float16, float16, float32
```

### GIF Timer (dans `zerochan.py`)
```python
self.gif_timer.start(3000)  # Rotation aléatoire : 3 secondes
# Retour auto après action : 5 secondes (QTimer.singleShot(5000, ...))
```

### Hotkey (dans `zerochan.py`)
```python
# Modifie la ligne xbindkeys :
f'"/usr/bin/touch {trigger_path}"',
"    Ctrl+Shift+Z",   # ← Change ici (ex: Ctrl+Alt+Z)
```

### Mapping Action → GIF (dans `zerobrain_nvidia.py`)
```python
GIF_MAP = {
    "open_youtube": 1,        # image1.gif
    "open_terminal": 2,       # image2.gif
    "open_libreoffice": 3,    # image3.gif
    "open_gmail": 4,          # image4.gif
    "play_music": 5,          # image5.gif
    "open_discord": 6,        # image6.gif
    "open_browser": 7,        # image7.gif
    "open_vscode": 8,         # image8.gif
    "open_kimi": 7,
    "open_zerocod": 8,
    "open_github": 7,
    "open_huggingface": 7,
    "open_telegram": 7,
    "open_pi_cli": 9,         # image9.gif
    "open_qwen_cli": 10,      # image10.gif
}
```

---

## 🐛 Dépannage

| Problème | Solution |
|----------|----------|
| `NVIDIA_API_KEY non définie` | `export NVIDIA_API_KEY="nvapi-..."` dans le **même terminal** |
| `pw-play: not found` | `sudo apt install pipewire-audio-client-libraries` |
| `xbindkeys` ne marche pas | `pkill xbindkeys && xbindkeys` + vérifie `~/.xbindkeysrc` |
| Micro muet | `pavucontrol` → onglet "Entrée" → bon device + volume |
| Whisper lent | Réduis `WHISPER_MODEL="tiny"` ou passe `device="cuda"` |
| GIF non animé | Vérifie `n_frames > 1` avec PIL |
| Firefox pas défaut | `xdg-settings set default-web-browser firefox.desktop` |
| Lanceur ne marche pas | Clic droit → Propriétés → Permissions → "Autoriser l'exécution" |

---

## 📦 Dépendances Python (`requirements.txt`)

```txt
faster-whisper
openai
numpy
sounddevice
PyQt6
Pillow
```

---

## 📄 Licence

**MIT License** — voir [LICENSE](LICENSE)

---

## 🙏 Crédits

- **NVIDIA** — Nemotron models & NIM API gratuite
- **faster-whisper** — STT local performant
- **Qwen3-TTS** — Voice cloning (HF Space `wordercom-qwen3-tts`)
- **PyQt6** — GUI overlay
- **Phi-3 / Nemotron** — Modèles de base

---

## 💡 Idées d'amélioration

- [ ] Support multi-langues (Whisper `language=None` auto-détect)
- [ ] Streaming LLM (tokens progressifs dans la bulle)
- [ ] TTS local (piper, kokoro, bark) pour zéro cloud
- [ ] Plugins d'actions (YAML/JSON) sans modifier le code
- [ ] Mode "always listening" avec VAD (Silero)
- [ ] OverlayWayland (wlr-layer-shell) pour Hyprland/Sway
- [ ] GIFs spécifiques pour émotions (love, angry, sad, etc.)

---

**Fait avec ❤️ pour les fans d'anime & de metal** 🤘🎸