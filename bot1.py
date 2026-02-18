"""
╔══════════════════════════════════════════════════════════════╗
║           MOLTY ROYALE - AI AGENT BOT                        ║
║  Powered by Claude AI / Gemini AI / Rule-Based Fallback      ║
║  Strategy: Aggressive Hunter                                 ║
╚══════════════════════════════════════════════════════════════╝

Run: python bot.py
Requires: pip install -r requirements.txt

AI Engine Priority:
  1. Claude AI  → jika CLAUDE_API_KEY diisi
  2. Gemini AI  → jika GEMINI_API_KEY diisi (dan Claude tidak ada)
  3. Rule-Based → otomatis jika tidak ada AI key sama sekali
"""

import time
import json
import requests
from datetime import datetime

# ── Import AI libraries secara opsional ──
try:
    import anthropic
    _HAS_ANTHROPIC = True
except ImportError:
    _HAS_ANTHROPIC = False

try:
    from google import genai
    from google.genai import types as genai_types
    _HAS_GEMINI = True
except ImportError:
    _HAS_GEMINI = False

# ══════════════════════════════════════════════════════════════
#                    ★ KONFIGURASI UTAMA ★
#         Isi semua nilai di bawah ini sebelum menjalankan bot
# ══════════════════════════════════════════════════════════════

# ── [WAJIB] API Key Molty Royale ───────────────────────────────
# Dapatkan di: https://www.moltyroyale.com
MOLTY_API_KEY = "mr_live_u3ZfNmr9iPGjeM1YxKavg3am7Q6tw-4b"

# ── [WAJIB] Nama agent kamu di dalam game ──────────────────────
AGENT_NAME = "ArangDul"

# ── [OPSIONAL] Jika agent sudah terdaftar sebelumnya ───────────
# Isi agentId jika bot pernah dijalankan di game yang sama
# Kosongkan ("") jika ini pertama kali jalankan bot
AGENT_ID = ""

# ──────────────────────────────────────────────────────────────
#   AI ENGINE — Isi SALAH SATU, sisanya biarkan kosong  ""
#
#   Prioritas otomatis:
#     1. Claude  → jika CLAUDE_API_KEY terisi
#     2. Gemini  → jika GEMINI_API_KEY terisi (Claude kosong)
#     3. Rule-Based → jika keduanya kosong (tanpa AI, gratis)
# ──────────────────────────────────────────────────────────────

# OPSI 1: Claude AI → https://console.anthropic.com/settings/keys
CLAUDE_API_KEY = ""

# OPSI 2: Gemini AI → https://aistudio.google.com/app/apikey
GEMINI_API_KEY = ""

# ── Model yang digunakan ───────────────────────────────────────
CLAUDE_MODEL = "claude-haiku-4-5-20251001"   # hemat & cepat
# CLAUDE_MODEL = "claude-sonnet-4-6"         # lebih pintar

GEMINI_MODEL = "gemini-2.0-flash"            # hemat & cepat
# GEMINI_MODEL = "gemini-2.0-pro"            # lebih pintar

# ══════════════════════════════════════════════════════════════
#              KONFIGURASI LANJUTAN (tidak perlu diubah)
# ══════════════════════════════════════════════════════════════
BASE_URL              = "https://mort-royal-production.up.railway.app/api"
POLL_INTERVAL_SECONDS = 62   # jangan dikurangi! cooldown aksi = 60 detik
STATE_POLL_SECONDS    = 5    # interval cek status game saat menunggu start

# ── Deteksi AI Engine otomatis ──
def detect_ai_engine() -> str:
    if CLAUDE_API_KEY and _HAS_ANTHROPIC:
        return "claude"
    if GEMINI_API_KEY and _HAS_GEMINI:
        return "gemini"
    return "rule_based"

AI_ENGINE = detect_ai_engine()

# ══════════════════════════════════════════
#              LOGGING HELPER
# ══════════════════════════════════════════
def log(tag: str, msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    colors = {
        "INFO":  "\033[96m",   # cyan
        "ACT":   "\033[92m",   # green
        "WARN":  "\033[93m",   # yellow
        "ERR":   "\033[91m",   # red
        "BRAIN": "\033[95m",   # magenta
        "ZONE":  "\033[91m",   # red bold
        "KILL":  "\033[92m",   # green bold
    }
    reset = "\033[0m"
    color = colors.get(tag, "")
    print(f"[{ts}] {color}[{tag}]{reset} {msg}")


# ══════════════════════════════════════════
#              MOLTY API CLIENT
# ══════════════════════════════════════════

# Timeout config: (connect_timeout, read_timeout) dalam detik
REQUEST_TIMEOUT   = (10, 45)   # beri server 45 detik untuk baca response
MAX_RETRIES       = 4          # maksimal percobaan ulang
RETRY_BACKOFF     = [5, 10, 20, 30]  # detik tunggu antar retry

class MoltyClient:
    def __init__(self):
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": MOLTY_API_KEY,
        }

    def _request(self, method: str, path: str, body: dict = None, auth: bool = False) -> dict:
        """Helper request dengan retry + exponential backoff."""
        h = self.headers if auth else {"Content-Type": "application/json"}
        url = f"{BASE_URL}{path}"
        last_err = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if method == "GET":
                    r = requests.get(url, headers=h, timeout=REQUEST_TIMEOUT)
                else:
                    r = requests.post(url, json=body or {}, headers=h, timeout=REQUEST_TIMEOUT)

                # Response kosong
                if not r.text.strip():
                    log("WARN", f"{method} {path} → response kosong (HTTP {r.status_code}), "
                                f"percobaan {attempt}/{MAX_RETRIES}…")
                    last_err = "EMPTY_RESPONSE"
                    raise ValueError("empty response")

                # Coba parse JSON
                try:
                    return r.json()
                except (ValueError, requests.exceptions.JSONDecodeError):
                    log("ERR", f"{method} {path} → bukan JSON (HTTP {r.status_code}) | "
                               f"Body: {r.text[:150]}")
                    return {"success": False, "error": {"code": "INVALID_RESPONSE"}}

            except (
                requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectTimeout,
                requests.exceptions.Timeout,
            ) as e:
                last_err = "TIMEOUT"
                wait = RETRY_BACKOFF[min(attempt - 1, len(RETRY_BACKOFF) - 1)]
                log("WARN", f"{method} {path} → timeout (percobaan {attempt}/{MAX_RETRIES}), "
                            f"tunggu {wait}s…")
                if attempt < MAX_RETRIES:
                    time.sleep(wait)
                continue

            except requests.exceptions.ConnectionError as e:
                last_err = "CONNECTION_ERROR"
                wait = RETRY_BACKOFF[min(attempt - 1, len(RETRY_BACKOFF) - 1)]
                log("WARN", f"{method} {path} → koneksi gagal (percobaan {attempt}/{MAX_RETRIES}), "
                            f"tunggu {wait}s…")
                if attempt < MAX_RETRIES:
                    time.sleep(wait)
                continue

            except ValueError:
                # empty response — sudah di-log, retry
                wait = RETRY_BACKOFF[min(attempt - 1, len(RETRY_BACKOFF) - 1)]
                if attempt < MAX_RETRIES:
                    time.sleep(wait)
                continue

            except Exception as e:
                log("ERR", f"{method} {path} → error tak terduga: {e}")
                return {"success": False, "error": {"code": "UNKNOWN_ERROR", "message": str(e)}}

        log("ERR", f"{method} {path} → gagal setelah {MAX_RETRIES} percobaan (terakhir: {last_err})")
        return {"success": False, "error": {"code": last_err or "FAILED_AFTER_RETRIES"}}

    def _get(self, path: str, auth: bool = False) -> dict:
        return self._request("GET", path, auth=auth)

    def _post(self, path: str, body: dict, auth: bool = False) -> dict:
        return self._request("POST", path, body=body, auth=auth)

    # ── Game ──
    def _print_room_info(self, game: dict):
        """Tampilkan info room di terminal."""
        gid        = game.get("id", "?")
        name       = game.get("name", "?")
        count      = game.get("agentCount", "?")
        max_agents = game.get("maxAgents", "?")
        status     = game.get("status", "?")
        map_size   = game.get("mapSize", "?")

        # Bar visual isi room
        if isinstance(count, int) and isinstance(max_agents, int) and max_agents > 0:
            filled  = int((count / max_agents) * 20)
            bar     = "█" * filled + "░" * (20 - filled)
            pct     = int(count / max_agents * 100)
            bar_str = f"[{bar}] {count}/{max_agents} ({pct}%)"
        else:
            bar_str = f"{count}/{max_agents}"

        log("INFO", f"┌─ ROOM INFO ───────────────────────────")
        log("INFO", f"│  Nama    : {name}")
        log("INFO", f"│  ID      : {gid}")
        log("INFO", f"│  Pemain  : {bar_str}")
        log("INFO", f"│  Map     : {map_size} | Status: {status}")
        log("INFO", f"└───────────────────────────────────────")

    def _is_room_full(self, game: dict) -> bool:
        """Cek apakah room sudah penuh."""
        count      = game.get("agentCount", 0)
        max_agents = game.get("maxAgents", 100)
        if not isinstance(count, int) or not isinstance(max_agents, int):
            return False
        return count >= max_agents

    def find_or_create_game(self) -> str:
        """Cari room yang tersedia. Skip room penuh, buat baru jika perlu."""
        res = self._get("/games?status=waiting")

        if not res.get("success", True) or "data" not in res:
            log("WARN", f"Gagal ambil daftar game: {res.get('error', {})} — coba buat game baru…")
            return self._create_new_game()

        games = res.get("data", [])

        if not games:
            log("INFO", "Tidak ada room waiting, membuat room baru…")
            return self._create_new_game()

        # ── Tampilkan semua room yang tersedia ──
        log("INFO", f"Ditemukan {len(games)} room waiting:")
        available = []
        for i, g in enumerate(games, 1):
            count      = g.get("agentCount", "?")
            max_agents = g.get("maxAgents", "?")
            name       = g.get("name", "?")
            is_full    = self._is_room_full(g)
            status_tag = "❌ PENUH" if is_full else "✅ BISA JOIN"
            log("INFO", f"  {i}. {name} | {count}/{max_agents} | {status_tag}")
            if not is_full:
                available.append(g)

        if not available:
            log("WARN", "Semua room penuh! Membuat room baru…")
            return self._create_new_game()

        # ── Pilih room dengan pemain paling banyak (tapi belum penuh) ──
        chosen = max(available, key=lambda g: g.get("agentCount", 0))
        self._print_room_info(chosen)
        log("INFO", f"✅ Bergabung ke room: {chosen.get('name')}")
        return chosen["id"]

    def _create_new_game(self) -> str:
        """Buat room baru."""
        res = self._post("/games", {"hostName": f"{AGENT_NAME}_room"})
        if not res.get("success"):
            code = res.get("error", {}).get("code", "")
            if code == "WAITING_GAME_EXISTS":
                log("WARN", "Waiting room sudah ada, retry find…")
                time.sleep(5)
                return self.find_or_create_game()
            raise RuntimeError(f"Gagal buat game: {res}")
        game = res.get("data", {})
        self._print_room_info(game)
        log("INFO", f"🆕 Room baru dibuat: {game.get('name')}")
        return game["id"]

    def get_game_status(self, game_id: str) -> str:
        res = self._get(f"/games/{game_id}")
        data = res.get("data", {})
        count      = data.get("agentCount")
        max_agents = data.get("maxAgents")
        status     = data.get("status", "unknown")
        if count is not None and max_agents is not None:
            log("INFO", f"  Room: {count}/{max_agents} pemain | status: {status}")
        return status

    # ── Agent ──
    def register_agent(self, game_id: str) -> str:
        res = self._post(
            f"/games/{game_id}/agents/register",
            {"name": AGENT_NAME},
            auth=True,
        )
        if not res.get("success"):
            code = res.get("error", {}).get("code", "")
            if code == "ONE_AGENT_PER_API_KEY":
                log("WARN", "Agent sudah terdaftar. Cari agentId dari state…")
                return None  # akan di-handle di luar
            raise RuntimeError(f"Register gagal: {res}")
        agent_id = res["data"]["id"]
        log("INFO", f"Agent terdaftar: {agent_id}")
        return agent_id

    def get_state(self, game_id: str, agent_id: str) -> dict:
        res = self._get(f"/games/{game_id}/agents/{agent_id}/state")
        return res.get("data", {})

    def execute_action(self, game_id: str, agent_id: str, action: dict, thought: dict = None) -> dict:
        body = {"action": action}
        if thought:
            body["thought"] = thought
        res = self._post(f"/games/{game_id}/agents/{agent_id}/action", body)
        return res


# ══════════════════════════════════════════
#              REGION MEMORY
# ══════════════════════════════════════════
class RegionMemory:
    def __init__(self):
        self.scores: dict[str, float] = {}
        self.explore_fails: dict[str, int] = {}

    def get_score(self, region_id: str) -> float:
        return self.scores.get(region_id, 1.0)

    def update(self, region_id: str, delta: float):
        current = self.scores.get(region_id, 1.0)
        self.scores[region_id] = max(0.0, current + delta)

    def mark_explore_fail(self, region_id: str):
        self.explore_fails[region_id] = self.explore_fails.get(region_id, 0) + 1
        if self.explore_fails[region_id] >= 2:
            self.update(region_id, -0.3)
            log("INFO", f"Region {region_id} ditandai LOW VALUE (2x explore gagal)")

    def mark_death_zone_prone(self, region_id: str):
        self.update(region_id, -0.5)

    def mark_ambush(self, region_id: str):
        self.update(region_id, -0.2)

    def mark_kill(self, region_id: str):
        self.update(region_id, +0.2)

    def mark_weapon_found(self, region_id: str):
        self.update(region_id, +0.3)

    def is_low_value(self, region_id: str) -> bool:
        return self.get_score(region_id) < 0.5


# ══════════════════════════════════════════
#       STRATEGY BRAIN (CLAUDE / GEMINI)
# ══════════════════════════════════════════
WEAPON_ATK_BONUS = {
    "Fist": 0, "Knife": 5, "Sword": 8, "Katana": 21,
    "Bow": 3, "Pistol": 6, "Sniper": 17,
}

WEAPON_TIER = {
    "Fist": 1, "Knife": 2, "Sword": 3, "Bow": 2,
    "Pistol": 3, "Sniper": 4, "Katana": 5,
}

def weapon_score(name: str) -> float:
    """Hitung weapon score sederhana berdasarkan ATK bonus × tier."""
    atk  = WEAPON_ATK_BONUS.get(name, 0)
    tier = WEAPON_TIER.get(name, 1)
    return atk * tier

def calc_win_prob(me: dict, enemy: dict) -> float:
    """Hitung probabilitas menang vs musuh."""
    my_dps   = (me.get("atk", 10) + (me.get("equippedWeapon") or {}).get("atkBonus", 0))
    my_hp    = me.get("hp", 100)
    en_dps   = (enemy.get("atk", 10) + (enemy.get("equippedWeapon") or {}).get("atkBonus", 0))
    en_hp    = enemy.get("hp", 100)
    my_def   = me.get("def", 5)
    en_def   = enemy.get("def", 0)

    my_effective_dps = max(1, my_dps - en_def * 0.5)
    en_effective_dps = max(1, en_dps - my_def * 0.5)

    # Perkiraan jumlah hit untuk membunuh
    hits_to_kill_enemy = en_hp / my_effective_dps
    hits_to_die        = my_hp / en_effective_dps

    if hits_to_die == 0:
        return 0.0
    ratio = hits_to_kill_enemy / hits_to_die
    # Prob menang = lebih besar jika kita butuh lebih sedikit hit
    prob = 1.0 / (1.0 + ratio)
    return round(prob, 2)

def build_strategy_prompt(state: dict, memory: RegionMemory) -> str:
    """Buat prompt strategis untuk Claude berdasarkan state game."""
    me = state.get("self", {})
    region = state.get("currentRegion", {})
    connected = state.get("connectedRegions", [])
    visible_agents = state.get("visibleAgents", [])
    visible_monsters = state.get("visibleMonsters", [])
    visible_items = state.get("visibleItems", [])
    pending_zones = state.get("pendingDeathzones", [])
    inventory = me.get("inventory", [])
    equipped = me.get("equippedWeapon")

    # Hitung win prob untuk setiap target
    targets_info = []
    for agent in visible_agents:
        if agent.get("isAlive") and agent.get("regionId") == region.get("id"):
            prob = calc_win_prob(me, agent)
            targets_info.append({
                "id": agent["id"], "name": agent["name"],
                "hp": agent.get("hp"), "type": "agent", "win_prob": prob,
            })
    for monster in visible_monsters:
        if monster.get("regionId") == region.get("id"):
            prob = calc_win_prob(me, monster)
            targets_info.append({
                "id": monster["id"], "name": monster["name"],
                "hp": monster.get("hp"), "type": "monster", "win_prob": prob,
            })

    # Weapon terbaik yang terlihat
    best_visible_weapon = None
    best_score = weapon_score(equipped["name"] if equipped else "Fist")
    for vi in visible_items:
        item = vi.get("item", {})
        if item.get("category") == "weapon":
            sc = weapon_score(item.get("name", ""))
            if sc > best_score:
                best_score = sc
                best_visible_weapon = {
                    "id": item["id"], "name": item["name"],
                    "regionId": vi["regionId"],
                }

    # Region memory
    region_scores = {
        r["id"] if isinstance(r, dict) else r: memory.get_score(r["id"] if isinstance(r, dict) else r)
        for r in connected
    }

    # Death zone
    current_is_dz = region.get("isDeathZone", False)
    pending_zone_ids = [p["id"] for p in pending_zones]
    connected_region_ids = [r["id"] if isinstance(r, dict) else r for r in connected]
    safe_escape_regions = [
        r for r in connected if isinstance(r, dict)
        and not r.get("isDeathZone", False)
        and r["id"] not in pending_zone_ids
    ]

    prompt = f"""
You are a Molty Royale AI Agent. Analyze the game state and decide the BEST SINGLE ACTION.

=== MY STATS ===
HP: {me.get('hp')}/{me.get('maxHp')} | EP: {me.get('ep')}/{me.get('maxEp')}
ATK: {me.get('atk')} | DEF: {me.get('def')} | Vision: {me.get('vision')}
Kills: {me.get('kills', 0)}
Weapon: {equipped['name'] if equipped else 'Fist (no weapon)'}

=== CURRENT REGION ===
ID: {region.get('id')} | Name: {region.get('name')}
Terrain: {region.get('terrain')} | Weather: {region.get('weather')}
Vision Modifier: {region.get('visionModifier', 0)}
Is Death Zone: {current_is_dz}
Facilities: {json.dumps(region.get('interactables', []))}

=== INVENTORY ===
{json.dumps(inventory) if inventory else 'EMPTY'}

=== PENDING DEATH ZONES (avoid!) ===
{json.dumps(pending_zones) if pending_zones else 'None'}

=== TARGETS IN SAME REGION ===
{json.dumps(targets_info) if targets_info else 'No targets here'}

=== BEST WEAPON NEARBY ===
{json.dumps(best_visible_weapon) if best_visible_weapon else 'None visible'}

=== CONNECTED REGIONS (can move to) ===
{json.dumps([
    {
        'id': r['id'] if isinstance(r, dict) else r,
        'name': r.get('name', '?') if isinstance(r, dict) else '(unknown)',
        'terrain': r.get('terrain', '?') if isinstance(r, dict) else '?',
        'isDZ': r.get('isDeathZone', False) if isinstance(r, dict) else '?',
        'rvs': memory.get_score(r['id'] if isinstance(r, dict) else r),
    }
    for r in connected
])}

=== PRIORITY RULES ===
1. DEATH ZONE: If current region is Death Zone or HP < 60% near DZ → ESCAPE IMMEDIATELY
2. WEAPON: If better weapon visible and path is safe → get it
3. KILL: If target win_prob >= 0.60 and not in DZ → attack (EP cost 2)
4. HEAL: If HP < 60% and have healing item → use_item
5. FACILITY: If unused facility here → interact
6. EXPLORE: If no targets and region not low-value → explore
7. MOVE: Move to highest RVS safe region

=== DECISION CONSTRAINTS ===
- EP available: {me.get('ep')} (Attack costs 2 EP, most actions cost 1 EP)
- If EP < 2 and want to attack → Rest or use free actions first
- NEVER move to Death Zone region
- NEVER chase target if win_prob < 0.55
- MAX inventory 10 items (current: {len(inventory)})

=== RESPOND IN JSON (no extra text) ===
{{
  "reasoning": "brief strategic analysis",
  "action": {{... valid action object ...}},
  "thought": {{
    "reasoning": "strategic analysis for spectators",
    "plannedAction": "what I'm planning"
  }}
}}

Valid action examples:
- {{"type": "move", "regionId": "region_id"}}
- {{"type": "explore"}}
- {{"type": "attack", "targetId": "id", "targetType": "agent"}}
- {{"type": "attack", "targetId": "id", "targetType": "monster"}}
- {{"type": "pickup", "itemId": "item_id"}}
- {{"type": "equip", "itemId": "weapon_id"}}
- {{"type": "use_item", "itemId": "item_id"}}
- {{"type": "interact", "interactableId": "facility_id"}}
- {{"type": "rest"}}
"""
    return prompt.strip()


def _parse_ai_response(text: str) -> tuple[dict, dict, str]:
    """Parse JSON response dari AI, kembalikan (action, thought, reasoning)."""
    # Hapus markdown code block jika ada
    text = text.strip()
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            if part.startswith("json"):
                text = part[4:].strip()
                break
            elif "{" in part:
                text = part.strip()
                break
    # Cari JSON object
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start != -1 and end > start:
        text = text[start:end]
    data    = json.loads(text)
    action  = data.get("action", {"type": "rest"})
    thought = data.get("thought", {})
    reason  = data.get("reasoning", "")
    return action, thought, reason


class StrategyBrain:
    def __init__(self):
        self.engine = AI_ENGINE
        self._claude_client = None
        self._gemini_model  = None

        if self.engine == "claude" and _HAS_ANTHROPIC:
            self._claude_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
            log("BRAIN", f"🤖 AI Engine: CLAUDE ({CLAUDE_MODEL})")

        elif self.engine == "gemini" and _HAS_GEMINI:
            self._gemini_client = genai.Client(api_key=GEMINI_API_KEY)
            self._gemini_config  = genai_types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=512,
            )
            log("BRAIN", f"🤖 AI Engine: GEMINI ({GEMINI_MODEL})")

        else:
            self.engine = "rule_based"
            log("BRAIN", "🤖 AI Engine: RULE-BASED (tidak ada AI API key)")

    # ─────────────────────────────────────────
    def decide(self, state: dict, memory: RegionMemory) -> tuple[dict, dict, str]:
        """Kembalikan (action, thought, reasoning)."""
        if self.engine == "claude":
            return self._decide_claude(state, memory)
        elif self.engine == "gemini":
            return self._decide_gemini(state, memory)
        else:
            return self._fallback(state, memory)

    # ── Claude ───────────────────────────────
    def _decide_claude(self, state: dict, memory: RegionMemory) -> tuple[dict, dict, str]:
        prompt = build_strategy_prompt(state, memory)
        log("BRAIN", "Mengirim state ke Claude…")
        try:
            response = self._claude_client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text
            action, thought, reason = _parse_ai_response(text)
            log("BRAIN", f"Claude → {action['type']} | {reason[:80]}")
            return action, thought, reason
        except Exception as e:
            log("ERR", f"Claude error: {e} → fallback rule-based")
            return self._fallback(state, memory)

    # ── Gemini ───────────────────────────────
    def _decide_gemini(self, state: dict, memory: RegionMemory) -> tuple[dict, dict, str]:
        prompt = build_strategy_prompt(state, memory)
        log("BRAIN", "Mengirim state ke Gemini…")
        try:
            response = self._gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=self._gemini_config,
            )
            text = response.text
            action, thought, reason = _parse_ai_response(text)
            log("BRAIN", f"Gemini → {action['type']} | {reason[:80]}")
            return action, thought, reason
        except Exception as e:
            log("ERR", f"Gemini error: {e} → fallback rule-based")
            return self._fallback(state, memory)

    def _fallback(self, state: dict, memory: RegionMemory) -> tuple[dict, dict, str]:
        """Rule-based fallback sederhana."""
        me       = state.get("self", {})
        region   = state.get("currentRegion", {})
        hp       = me.get("hp", 100)
        ep       = me.get("ep", 0)
        inventory = me.get("inventory", [])
        connected = state.get("connectedRegions", [])
        pending   = [p["id"] for p in state.get("pendingDeathzones", [])]
        monsters  = state.get("visibleMonsters", [])
        agents    = [a for a in state.get("visibleAgents", []) if a.get("isAlive")]

        # 1. Death zone escape
        if region.get("isDeathZone") and ep >= 1:
            safe = [r for r in connected if isinstance(r, dict) and not r.get("isDeathZone") and r["id"] not in pending]
            if safe:
                return {"type": "move", "regionId": safe[0]["id"]}, {}, "ESCAPE DEATH ZONE"

        # 2. Heal jika HP rendah
        if hp < 60:
            heals = [i for i in inventory if i.get("category") == "recovery"]
            if heals and ep >= 1:
                return {"type": "use_item", "itemId": heals[0]["id"]}, {}, "Heal HP rendah"

        # 3. Serang monster terlemah
        if ep >= 2 and monsters:
            in_region = [m for m in monsters if m.get("regionId") == region.get("id")]
            if in_region:
                target = min(in_region, key=lambda m: m.get("hp", 999))
                return {"type": "attack", "targetId": target["id"], "targetType": "monster"}, {}, f"Attack {target['name']}"

        # 4. Serang agent jika prob menang tinggi
        if ep >= 2 and agents:
            in_region = [a for a in agents if a.get("regionId") == region.get("id")]
            for a in in_region:
                if calc_win_prob(me, a) >= 0.60:
                    return {"type": "attack", "targetId": a["id"], "targetType": "agent"}, {}, f"Attack agent {a['name']}"

        # 5. Ambil item di region
        visible_items = state.get("visibleItems", [])
        for vi in visible_items:
            if vi.get("regionId") == region.get("id") and len(inventory) < 10:
                return {"type": "pickup", "itemId": vi["item"]["id"]}, {}, "Pickup item"

        # 6. Explore
        if ep >= 1 and not memory.is_low_value(region.get("id", "")):
            return {"type": "explore"}, {}, "Explore region"

        # 7. Pindah ke region terbaik
        if ep >= 1 and connected:
            safe_regions = [
                r for r in connected
                if isinstance(r, dict)
                and not r.get("isDeathZone")
                and r["id"] not in pending
            ]
            if safe_regions:
                best = max(safe_regions, key=lambda r: memory.get_score(r["id"]))
                return {"type": "move", "regionId": best["id"]}, {}, f"Move to {best.get('name','?')}"

        # 8. Rest
        return {"type": "rest"}, {}, "Rest (recover EP)"


# ══════════════════════════════════════════
#              MAIN GAME LOOP
# ══════════════════════════════════════════
class MoltyRoyaleBot:
    def __init__(self):
        self.api    = MoltyClient()
        self.brain  = StrategyBrain()
        self.memory = RegionMemory()
        self.game_id  = None
        self.agent_id = None
        self.prev_kills = 0
        self.prev_inventory_ids: set = set()

    def setup(self):
        """Registrasi ke game dengan retry jika server timeout."""
        # ── Cari / buat game dengan retry ──
        while True:
            try:
                self.game_id = self.api.find_or_create_game()
                if self.game_id:
                    break
            except Exception as e:
                log("ERR", f"Gagal find/create game: {e}")
            log("WARN", "Retry find/create game dalam 15 detik…")
            time.sleep(15)

        # ── Register agent dengan retry ──
        while True:
            try:
                self.agent_id = self.api.register_agent(self.game_id)
                break
            except RuntimeError as e:
                log("ERR", f"Register gagal: {e}")
                log("WARN", "Retry register dalam 15 detik…")
                time.sleep(15)

        # Jika agent sudah terdaftar, pakai AGENT_ID dari konfigurasi
        if self.agent_id is None:
            if AGENT_ID:
                log("INFO", f"Menggunakan AGENT_ID dari konfigurasi: {AGENT_ID}")
                self.agent_id = AGENT_ID
            else:
                raise RuntimeError(
                    "Agent sudah terdaftar tapi AGENT_ID kosong!\n"
                    "Isi variabel AGENT_ID di bagian konfigurasi atas file bot.py"
                )

        # ── Tunggu game mulai ──
        log("INFO", "Menunggu game mulai… (update setiap 5 detik)")
        while True:
            try:
                status = self.api.get_game_status(self.game_id)
                if status == "running":
                    log("INFO", "🎮 Game DIMULAI!")
                    break
                if status == "finished":
                    log("WARN", "Game sudah selesai.")
                    return False
            except Exception as e:
                log("WARN", f"Gagal cek status game: {e}, retry…")
            time.sleep(STATE_POLL_SECONDS)
        return True

    def _post_action_checks(self, state: dict, action: dict):
        """Update memory setelah aksi dieksekusi."""
        me = state.get("self", {})
        region_id = state.get("currentRegion", {}).get("id", "")
        inventory = me.get("inventory", [])
        inv_ids = {i["id"] for i in inventory}

        # Cek kill baru
        kills = me.get("kills", 0)
        if kills > self.prev_kills:
            log("KILL", f"🎯 KILL! Total kills: {kills}")
            self.memory.mark_kill(region_id)
            self.prev_kills = kills

        # Cek item baru dari explore
        new_items = inv_ids - self.prev_inventory_ids
        if action.get("type") == "explore":
            if new_items:
                new_names = [i["name"] for i in inventory if i["id"] in new_items]
                # Cek apakah ada weapon baru
                new_weapons = [i for i in inventory if i["id"] in new_items and i.get("category") == "weapon"]
                if new_weapons:
                    self.memory.mark_weapon_found(region_id)
                    log("INFO", f"Weapon ditemukan: {[w['name'] for w in new_weapons]}")
            else:
                self.memory.mark_explore_fail(region_id)

        self.prev_inventory_ids = inv_ids

        # Tandai pending death zones di memory
        for pz in state.get("pendingDeathzones", []):
            self.memory.mark_death_zone_prone(pz["id"])

    def run(self):
        """Main game loop."""
        log("INFO", f"╔══ MOLTY ROYALE BOT STARTED ══╗")
        log("INFO", f"Agent: {AGENT_NAME} | Game: {self.game_id}")

        turn = 0
        while True:
            turn += 1
            log("INFO", f"══ TURN {turn} ══")

            # Ambil state
            try:
                state = self.api.get_state(self.game_id, self.agent_id)
            except Exception as e:
                log("ERR", f"Gagal ambil state: {e}")
                time.sleep(10)
                continue

            # Cek game selesai
            if state.get("gameStatus") == "finished":
                me = state.get("self", {})
                log("INFO", f"🏁 GAME SELESAI! Kills: {me.get('kills', 0)} | HP: {me.get('hp', 0)}")
                break

            me = state.get("self", {})
            if not me.get("isAlive", True):
                log("WARN", "💀 Agent mati. Game over.")
                break

            log("INFO", f"HP:{me.get('hp')}/{me.get('maxHp')} | EP:{me.get('ep')} | "
                        f"Kills:{me.get('kills',0)} | "
                        f"Region:{state.get('currentRegion',{}).get('name','?')}")

            # Cek EP
            if me.get("ep", 0) < 1:
                log("INFO", "EP habis, menunggu regenerasi…")
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            # Keputusan strategis
            action, thought, reason = self.brain.decide(state, self.memory)

            # Safety override: jangan pindah ke Death Zone
            if action.get("type") == "move":
                target_region = action.get("regionId")
                connected = state.get("connectedRegions", [])
                pending_ids = [p["id"] for p in state.get("pendingDeathzones", [])]
                for r in connected:
                    if isinstance(r, dict) and r["id"] == target_region:
                        if r.get("isDeathZone") or r["id"] in pending_ids:
                            log("ZONE", f"⚠️  OVERRIDE: Menghindari Death Zone {target_region}")
                            safe = [x for x in connected if isinstance(x, dict) 
                                    and not x.get("isDeathZone") and x["id"] not in pending_ids]
                            if safe:
                                action = {"type": "move", "regionId": safe[0]["id"]}
                            else:
                                action = {"type": "rest"}
                            break

            # Eksekusi aksi
            log("ACT", f"→ {json.dumps(action)}")
            try:
                result = self.api.execute_action(self.game_id, self.agent_id, action, thought)
                if not result.get("success"):
                    err_code = result.get("error", {}).get("code", "")
                    log("WARN", f"Aksi gagal: {err_code}")

                    # Handle specific errors
                    if err_code == "ALREADY_ACTED":
                        log("INFO", "Sudah beraksi di window ini, tunggu cooldown…")
                        time.sleep(POLL_INTERVAL_SECONDS)
                        continue
                    elif err_code == "INSUFFICIENT_EP":
                        log("INFO", "EP tidak cukup, tunggu regenerasi…")
                        time.sleep(POLL_INTERVAL_SECONDS)
                        continue
                else:
                    log("ACT", f"✓ Aksi berhasil: {action['type']}")
                    # Update memory
                    self._post_action_checks(state, action)

            except Exception as e:
                log("ERR", f"Error eksekusi aksi: {e}")

            # Tunggu cooldown group 1 (1 menit real time)
            log("INFO", f"Menunggu {POLL_INTERVAL_SECONDS}s (cooldown + EP regen)…")
            time.sleep(POLL_INTERVAL_SECONDS)

        log("INFO", f"╚══ BOT SELESAI ══╝")


# ══════════════════════════════════════════
#              ENTRY POINT
# ══════════════════════════════════════════
def main():
    bot = MoltyRoyaleBot()
    try:
        started = bot.setup()
        if started:
            bot.run()
    except KeyboardInterrupt:
        log("INFO", "Bot dihentikan oleh user.")
    except Exception as e:
        log("ERR", f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
