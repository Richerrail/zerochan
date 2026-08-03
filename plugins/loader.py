"""
Plugin Loader pour Zero-chan — Charge les actions depuis des fichiers YAML
"""
import yaml
import re
import subprocess
import webbrowser
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from enum import Enum


class ActionType(Enum):
    WEB = "web"           # Ouvre URL (webbrowser)
    SYSTEM = "system"     # Lance commande locale (subprocess)
    TERMINAL = "terminal" # Lance dans terminal
    DESKTOP = "desktop"   # Lance fichier .desktop (gtk-launch)
    MUSIC = "music"       # YouTube Music avec artistes spéciaux


@dataclass
class ActionPlugin:
    """Représente une action déclarative"""
    id: str
    name: str
    category: str
    triggers: List[str]
    gif_index: int
    wav: str
    response: str
    
    # Type d'action (déduit de category si non spécifié)
    action_type: Optional[ActionType] = None
    
    # Web
    url: Optional[str] = None
    url_template: Optional[str] = None
    extract_query: bool = False
    query_cleanup: str = ""
    fallback_wav: Optional[str] = None
    fallback_response: Optional[str] = None
    
    # System/Terminal/Desktop
    command: Optional[List[str]] = None
    command_args: Optional[Dict[str, List[str]]] = None
    command_template: Optional[str] = None
    terminals: Optional[List[str]] = None
    fallback_command: Optional[List[str]] = None
    fallback_command_web: Optional[List[str]] = None
    fallback_wav: Optional[str] = None
    fallback_response: Optional[str] = None
    
    # Desktop
    desktop_name: Optional[str] = None
    desktop_paths: Optional[List[str]] = None
    
    # Music
    artists: List[Dict[str, Any]] = field(default_factory=list)
    
    # Priorité (plus haut = plus prioritaire)
    priority: int = 0
    
    def __post_init__(self):
        # Auto-déduire action_type depuis category
        if self.action_type is None:
            cat = self.category.lower()
            if cat in ("web", "music"):
                self.action_type = ActionType.WEB if cat == "web" else ActionType.MUSIC
            elif cat == "system":
                self.action_type = ActionType.SYSTEM
            elif cat == "dev":
                if self.desktop_name:
                    self.action_type = ActionType.DESKTOP
                elif self.command_template:
                    self.action_type = ActionType.TERMINAL
                else:
                    self.action_type = ActionType.SYSTEM
            else:
                self.action_type = ActionType.SYSTEM
        
        # Calculer priorité : plus de triggers = plus spécifique
        if self.priority == 0:
            self.priority = len(self.triggers) * 10
    
    def matches(self, text: str) -> bool:
        """Vérifie si le texte déclenche cette action"""
        t = text.lower()
        return any(trigger in t for trigger in self.triggers)
    
    def extract_args(self, text: str) -> Dict[str, Any]:
        """Extrait les arguments depuis le texte"""
        args = {}
        if self.extract_query and self.query_cleanup:
            query = re.sub(self.query_cleanup, '', text.lower()).strip()
            args['query'] = query or "musique"
            
            # Détection artiste pour musique
            if self.action_type == ActionType.MUSIC and self.artists:
                for artist in self.artists:
                    for trigger in artist.get('triggers', []):
                        if trigger in query:
                            args['artist'] = artist['name']
                            args['artist_response'] = artist.get('response')
                            break
        return args
    
    def _resolve_path(self, base_dir: Path, path_str: str) -> Path:
        """Résout un chemin relatif au dossier du projet"""
        return (base_dir / path_str).resolve()
    
    def execute(self, args: Dict[str, Any], base_dir: Path) -> tuple:
        """
        Exécute l'action et retourne (wav_path, response_text)
        """
        # 1. WEB / MUSIC — Ouvre URL
        if self.action_type in (ActionType.WEB, ActionType.MUSIC):
            return self._execute_web(args, base_dir)
        
        # 2. DESKTOP — Lance fichier .desktop
        if self.action_type == ActionType.DESKTOP:
            return self._execute_desktop(base_dir)
        
        # 3. TERMINAL — Lance commande dans terminal
        if self.action_type == ActionType.TERMINAL:
            return self._execute_terminal(base_dir)
        
        # 4. SYSTEM — Lance commande directe
        return self._execute_system(base_dir)
    
    def _execute_web(self, args: Dict[str, Any], base_dir: Path) -> tuple:
        """Ouvre une URL dans le navigateur par défaut"""
        if self.url:
            webbrowser.open(self.url)
            return self._resolve_path(base_dir, self.wav), self.response
        
        if self.url_template and 'query' in args:
            query = args['query']
            url = self.url_template.format(query=query.replace(' ', '+'))
            webbrowser.open(url)
            
            # Réponse custom pour artiste (musique)
            if 'artist_response' in args:
                return self._resolve_path(base_dir, self.wav), args['artist_response']
            
            # Fallback response avec query
            if self.fallback_response and '{query}' in self.fallback_response:
                response = self.fallback_response.format(query=args['query'])
            else:
                response = self.response
            
            wav = self.fallback_wav if (self.fallback_wav and args['query'] != "musique") else self.wav
            return self._resolve_path(base_dir, wav), response
        
        return self._error_response(base_dir, "URL manquante")
    
    def _execute_desktop(self, base_dir: Path) -> tuple:
        """Lance une application via son fichier .desktop (gtk-launch)"""
        if self.desktop_name:
            # Essaie gtk-launch d'abord
            try:
                subprocess.Popen(["gtk-launch", self.desktop_name])
                return self._resolve_path(base_dir, self.wav), self.response
            except FileNotFoundError:
                pass
        
        if self.desktop_paths:
            for path_str in self.desktop_paths:
                desktop_path = Path(path_str).expanduser()
                if desktop_path.exists():
                    try:
                        subprocess.Popen(["gtk-launch", self.desktop_name or desktop_path.stem])
                        return self._resolve_path(base_dir, self.wav), self.response
                    except FileNotFoundError:
                        continue
        
        # Fallback
        return self._execute_fallback(base_dir)
    
    def _execute_terminal(self, base_dir: Path) -> tuple:
        """Lance une commande dans un terminal"""
        if self.command_template and self.terminals:
            for term in self.terminals:
                try:
                    cmd = self.command_template.format(terminal=term)
                    subprocess.Popen(cmd.split())
                    return self._resolve_path(base_dir, self.wav), self.response
                except FileNotFoundError:
                    continue
        
        return self._error_response(base_dir, "Aucun terminal trouvé")
    
    def _execute_system(self, base_dir: Path) -> tuple:
        """Lance une commande système directe"""
        if self.command:
            for cmd in self.command:
                try:
                    # Args spécifiques par commande
                    cmd_args = self.command_args.get(cmd, []) if self.command_args else []
                    subprocess.Popen([cmd] + cmd_args)
                    return self._resolve_path(base_dir, self.wav), self.response
                except FileNotFoundError:
                    continue
        
        return self._execute_fallback(base_dir)
    
    def _execute_fallback(self, base_dir: Path) -> tuple:
        """Exécute le fallback (commande ou web)"""
        # Fallback commande
        if self.fallback_command:
            for cmd in self.fallback_command:
                try:
                    subprocess.Popen([cmd])
                    wav = self.fallback_wav or self.wav
                    resp = self.fallback_response or self.response
                    return self._resolve_path(base_dir, wav), resp
                except FileNotFoundError:
                    continue
        
        # Fallback web
        if self.fallback_command_web:
            try:
                subprocess.Popen(self.fallback_command_web)
                wav = self.fallback_wav or self.wav
                resp = self.fallback_response or self.response
                return self._resolve_path(base_dir, wav), resp
            except FileNotFoundError:
                pass
        
        return self._error_response(base_dir, "Fallback échoué")
    
    def _error_response(self, base_dir: Path, msg: str) -> tuple:
        error_wav = base_dir / "audio_zerochan/errors/not_found.wav"
        return error_wav, f" ❌ {msg}..."


class ActionRegistry:
    """Registre central des actions — charge et gère les plugins"""
    
    def __init__(self, actions_dir: Path = None):
        if actions_dir is None:
            actions_dir = Path(__file__).parent.parent / "actions"
        self.actions_dir = actions_dir
        self.actions: List[ActionPlugin] = []
        self._load_all()
    
    def _load_all(self):
        """Charge tous les fichiers YAML du dossier actions/"""
        self.actions = []
        
        if not self.actions_dir.exists():
            print(f"⚠️  Dossier actions introuvable: {self.actions_dir}")
            return
        
        for yaml_file in sorted(self.actions_dir.glob("*.yaml")):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                if not data or 'actions' not in data:
                    continue
                
                for action_data in data['actions']:
                    # Normalisation des clés
                    action_data = self._normalize_action_data(action_data)
                    plugin = ActionPlugin(**action_data)
                    self.actions.append(plugin)
                    print(f"  ✅ Action chargée: {plugin.id} ({plugin.category})")
            
            except Exception as e:
                print(f"❌ Erreur chargement {yaml_file.name}: {e}")
        
        # Tri par priorité (décroissant)
        self.actions.sort(key=lambda a: -a.priority)
        print(f"📦 Total actions chargées: {len(self.actions)}")
    
    def _normalize_action_data(self, data: Dict) -> Dict:
        """Normalise les clés YAML vers les noms de champs du dataclass"""
        # Mapping des clés YAML vers champs Python
        key_map = {
            'action_type': 'action_type',
            'command_args': 'command_args',
            'command_template': 'command_template',
            'fallback_command': 'fallback_command',
            'fallback_command_web': 'fallback_command_web',
            'fallback_response': 'fallback_response',
            'fallback_wav': 'fallback_wav',
            'desktop_name': 'desktop_name',
            'desktop_paths': 'desktop_paths',
        }
        
        # Convertit les chaînes d'action_type en enum
        if 'action_type' in data and isinstance(data['action_type'], str):
            try:
                data['action_type'] = ActionType(data['action_type'])
            except ValueError:
                data.pop('action_type')
        
        return data
    
    def reload(self):
        """Recharge toutes les actions (hot-reload)"""
        self._load_all()
    
    def find_action(self, text: str) -> Optional[ActionPlugin]:
        """Trouve la première action qui match le texte"""
        for action in self.actions:
            if action.matches(text):
                return action
        return None
    
    def find_all_matches(self, text: str) -> List[ActionPlugin]:
        """Trouve toutes les actions qui matchent (pour debug)"""
        return [a for a in self.actions if a.matches(text)]
    
    def execute(self, text: str, base_dir: Path) -> tuple:
        """Trouve et exécute l'action pour le texte donné"""
        action = self.find_action(text)
        if action:
            args = action.extract_args(text)
            return action.execute(args, base_dir)
        return None, None, -1
    
    def get_action_by_id(self, action_id: str) -> Optional[ActionPlugin]:
        """Récupère une action par son ID"""
        for action in self.actions:
            if action.id == action_id:
                return action
        return None
    
    def list_actions(self) -> List[Dict]:
        """Liste toutes les actions pour debug/UI"""
        return [
            {
                "id": a.id,
                "name": a.name,
                "category": a.category,
                "triggers": a.triggers,
                "gif_index": a.gif_index,
                "type": a.action_type.value if a.action_type else "unknown"
            }
            for a in self.actions
        ]


# Instance globale (singleton)
_registry: Optional[ActionRegistry] = None

def get_registry(actions_dir: Path = None) -> ActionRegistry:
    """Retourne l'instance singleton du registre"""
    global _registry
    if _registry is None:
        _registry = ActionRegistry(actions_dir)
    return _registry

def reload_registry(actions_dir: Path = None) -> ActionRegistry:
    """Force le rechargement du registre"""
    global _registry
    _registry = ActionRegistry(actions_dir)
    return _registry