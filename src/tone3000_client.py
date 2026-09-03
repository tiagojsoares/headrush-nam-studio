import os
import json
import urllib.request
import urllib.parse
import urllib.error
import headrush_manager as hm

import hashlib
import struct

CONFIG_PATH = os.path.expanduser("~/.headrush_nam_studio/config.json")
BASE_URL = "https://www.tone3000.com/api/v1"

# Chaves padrão criptografadas para acesso out-of-the-box
_MASTER_KEY = b"HeadRush_NAM_Studio_Tiago_Master_Key_2026_Secure"
_ENC_PUB = "808746ee0458d7612025c58336f525c880cf590a79c471b7bf4af68681a54e8fed8e718d0f64893b"
_ENC_SEC = "808746ee175eea5b593eb2ad72e209bbfeb25f077c9a12a2c532acda8cf872d4b0d42da20d78f67dfdb6bafb2e7dd2c6200a9d5625aaa1ff6cb69cae502bda0b14484edcb40fea13"

def _decrypt_embedded_key(hex_str: str) -> str:
    """Descriptografa a credencial interna em tempo de execução."""
    try:
        data = bytes.fromhex(hex_str)
        salt = b"hr_nam_salt_v1"
        key = hashlib.sha256(_MASTER_KEY + salt).digest()
        out = bytearray()
        for i, b in enumerate(data):
            block = hashlib.sha256(key + struct.pack("<I", i // 32)).digest()
            out.append(b ^ block[i % 32])
        return out.decode("utf-8")
    except Exception:
        return ""

class Tone3000Client:
    def __init__(self, public_key=None, secret_key=None):
        config = self._load_config()
        # 1. Configuração do usuário local (se houver)
        # 2. Variável de ambiente
        # 3. Chave padrão interna descriptografada em tempo de execução
        self.public_key = (
            public_key or
            os.environ.get("TONE3000_PUBLIC_KEY") or
            config.get("public_key") or
            _decrypt_embedded_key(_ENC_PUB)
        )
        self.secret_key = (
            secret_key or
            os.environ.get("TONE3000_SECRET_KEY") or
            config.get("secret_key") or
            _decrypt_embedded_key(_ENC_SEC)
        )
        self.user_agent = "HeadRushNAMStudio/1.2"

    def _load_config(self):
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def save_credentials(self, public_key=None, secret_key=None):
        if public_key:
            self.public_key = public_key
        if secret_key:
            self.secret_key = secret_key
            
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        conf = self._load_config()
        conf["public_key"] = self.public_key
        conf["secret_key"] = self.secret_key
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(conf, f, indent=2)
            return True
        except Exception:
            return False

    def is_configured(self):
        return bool(self.secret_key and self.secret_key.strip())

    def _request(self, endpoint, params=None):
        """Internal helper to make authenticated HTTP GET requests to TONE3000 API."""
        if not self.secret_key:
            raise Exception("Chave da API TONE3000 não configurada. Clique em '🔑 Chaves API' para salvar sua Secret Key com segurança.")
            
        url = f"{BASE_URL}{endpoint}"
        if params:
            query_str = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
            if query_str:
                url = f"{url}?{query_str}"
                
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "User-Agent": self.user_agent,
            "Accept": "application/json"
        }
        
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
            except Exception:
                pass
            raise Exception(f"TONE3000 API Error (HTTP {e.code}): {error_body or e.reason}")
        except urllib.error.URLError as e:
            raise Exception(f"Falha de conexão com TONE3000: {e.reason}")

    def get_trending(self, gear=None):
        """Fetch top trending tones on TONE3000 (optionally filtered by gear: amp, pedal, cab, etc.)."""
        params = {}
        if gear:
            params["gear"] = gear
        res = self._request("/tones/trending", params)
        return res.get("data", []) if isinstance(res, dict) else res

    def get_latest(self, gear=None):
        """Fetch latest uploaded tones on TONE3000."""
        params = {}
        if gear:
            params["gear"] = gear
        res = self._request("/tones/latest", params)
        return res.get("data", []) if isinstance(res, dict) else res

    def search_tones(self, query="", gear=None, format_type="nam", page=1, page_size=20):
        """Search tones by keyword, brand, or tag."""
        params = {
            "query": query,
            "page": page,
            "page_size": page_size
        }
        if gear:
            params["gear"] = gear
        if format_type:
            params["format"] = format_type
            
        res = self._request("/tones/search", params)
        if isinstance(res, dict):
            return {
                "tones": res.get("data", []),
                "page": res.get("page", 1),
                "page_size": res.get("page_size", page_size),
                "total": res.get("total", len(res.get("data", []))),
                "total_pages": res.get("total_pages", 1)
            }
        return {"tones": res, "page": 1, "page_size": len(res), "total": len(res), "total_pages": 1}

    def get_tone(self, tone_id):
        """Fetch full details for a single tone by ID."""
    def get_tone_models(self, tone_id):
        """
        Fetch all individual models/captures for a specific tone across all architectures
        (A2 Slim, NAM v1, Custom, and IRs).
        """
        models = []
        seen_ids = set()

        # Query A2 first (recommended for modern DSP units like MX5), then v1, then custom, then default
        for arch in ['2', '1', 'custom', None]:
            params = {"tone_id": tone_id}
            if arch is not None:
                params["architecture"] = arch
            try:
                res = self._request("/models", params)
                data = res.get("data", []) if isinstance(res, dict) else res
                for m in data:
                    mid = m.get("id")
                    if mid and mid not in seen_ids:
                        seen_ids.add(mid)
                        if not m.get("architecture_version") and arch:
                            m["architecture_version"] = arch
                        models.append(m)
            except Exception:
                continue

        return models

    def download_model(self, model_url, dest_path=None):
        """
        Downloads a .nam model file using its authenticated download URL.
        If dest_path is None, saves to a temporary file.
        """
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "User-Agent": self.user_agent
        }
        
        req = urllib.request.Request(model_url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
            
        if not dest_path:
            import tempfile
            fd, dest_path = tempfile.mkstemp(suffix=".nam")
            os.close(fd)
            
        with open(dest_path, "wb") as f:
            f.write(content)
            
        return dest_path

    def download_and_install_to_headrush(self, model_obj, slot=None, custom_name=None, tone=50, level=70):
        """
        Downloads a model from TONE3000 and installs it straight into the connected HeadRush MX5 USB drive,
        creating both V1 and V2 .block presets and applying smart LCD abbreviation.
        """
        model_url = model_obj.get("model_url")
        if not model_url:
            raise ValueError("O objeto do modelo não contém 'model_url'")
            
        raw_name = custom_name or model_obj.get("name") or "Cloud Tone"
        model_name = hm.smart_format_preset_name(raw_name, 24)
        
        # 1. Download to temporary file
        temp_file = self.download_model(model_url)
        try:
            # 2. Inspect downloaded file for validity
            info = hm.inspect_nam_file(temp_file)
            if not info.get("valid"):
                raise ValueError(f"O modelo baixado é inválido ou incompatível: {info.get('error')}")
                
            # 3. Install to HeadRush USB Drive
            res = hm.install_nam_to_headrush(
                src_nam_path=temp_file,
                custom_name=model_name,
                slot=slot,
                tone=tone,
                level=level
            )
            res["cloud_info"] = {
                "id": model_obj.get("id"),
                "architecture": info.get("architecture"),
                "sample_rate": info.get("sample_rate"),
                "author": info.get("author")
            }
            return res
        finally:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

# Singleton instance
_client = None

def get_tone3000_client():
    global _client
    if _client is None:
        _client = Tone3000Client()
    return _client
