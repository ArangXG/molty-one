# 🎮 Molty Royale AI Agent Bot

Bot cerdas untuk bermain Molty Royale secara otomatis.  
Mendukung **Claude AI**, **Gemini AI**, atau **Rule-Based** (tanpa AI key).

---

## ⚡ Cara Pakai (3 Langkah)

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Isi API Key di file `.env`

```env
MOLTY_API_KEY=mr_live_xxxxxxxxxxxx   ← wajib

# Pilih SALAH SATU AI engine:
CLAUDE_API_KEY=sk-ant-xxxxxxxxxx     ← opsi 1 (https://console.anthropic.com)
GEMINI_API_KEY=AIzaxxxxxxxxxx        ← opsi 2 (https://aistudio.google.com/app/apikey)
# Kosongkan keduanya → Rule-Based otomatis aktif
```

### 3. Jalankan!
```bash
python bot.py
```

---

## 🤖 AI Engine

Bot otomatis mendeteksi engine yang tersedia:

| Prioritas | Engine | Keterangan |
|-----------|--------|------------|
| 1 | **Claude AI** | Dipakai jika `CLAUDE_API_KEY` terisi |
| 2 | **Gemini AI** | Dipakai jika `GEMINI_API_KEY` terisi (Claude kosong) |
| 3 | **Rule-Based** | Otomatis aktif jika tidak ada AI key |

Saat bot start, log akan menampilkan engine yang aktif:
```
[BRAIN] 🤖 AI Engine: GEMINI (gemini-2.0-flash)
```

### Ganti model di `bot.py`:
```python
# Claude
CLAUDE_MODEL = "claude-haiku-4-5-20251001"   # hemat
CLAUDE_MODEL = "claude-sonnet-4-6"            # pintar

# Gemini
GEMINI_MODEL = "gemini-2.0-flash"            # hemat
GEMINI_MODEL = "gemini-2.0-pro"              # pintar
```

---

## 🧠 Cara Kerja Bot

```
┌─────────────────────────────────────────────┐
│          GAME LOOP (setiap 62 detik)         │
│                                              │
│  GET State → AI Analisis → Safety Check      │
│       ↓                                      │
│  Eksekusi Aksi → Memory Update → Tunggu      │
└─────────────────────────────────────────────┘
```

### Prioritas Strategi:
| # | Kondisi | Aksi |
|---|---------|------|
| 1 | Death Zone! | Kabur ke safe region |
| 2 | HP < 60% | Minum healing item |
| 3 | Musuh di region, win prob ≥ 60% | Serang! |
| 4 | Ada weapon lebih bagus | Ambil & equip |
| 5 | Ada facility belum dipakai | Interact |
| 6 | Region normal | Explore |
| 7 | Lainnya | Pindah ke region terbaik |

---

## ⚠️ Catatan Penting
- Tekan `Ctrl+C` untuk menghentikan bot
- Jangan jalankan lebih dari 1 bot per API key dalam 1 game
- Bot otomatis menunggu game mulai (polling setiap 5 detik)

## 📁 Struktur File
```
molty_royale_bot/
├── bot.py           ← File utama
├── .env             ← API Keys (jangan di-commit ke git!)
├── requirements.txt ← Dependencies
└── README.md        ← Panduan ini
```
