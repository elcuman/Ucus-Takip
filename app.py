"""
Cevheri Sivil Havacılık - Uçuş Kayıt ve Takip Sistemi
================================================
Tek dosyalık Flask + SQLite uygulaması.

Roller
  pilot        : kendi uçuş kaydını oluşturur (koordinatör onayına düşer), kendi kayıtlarını görür/düzenler
  koordinator  : uçuş planlar (doğrudan onaylı), pilot kayıtlarını onaylar/reddeder, bakım ve günlük kod girer
  yonetici     : koordinatörün yaptığı her şey + uçak ve kullanıcı yönetimi, işlem geçmişi

Uçağın anlık durumu (Genel Bakış, Filo):
  1. Şu an havada        -> Görevde
  2. Süren bakım kaydı   -> Bakımda (AOG / AWP / U/S kendi adıyla)
  3. Bugün inmemiş uçuşu -> Görevde (sıradaki kalkış)
  4. Günlük kod RON/RES/M -> Konaklamada / Yedekte / Bakımda
  5. Hiçbiri değilse      -> Müsait  (ör. 22:00'de inen uçak 22:00'den sonra müsait)

Çalıştırma:
  pip install -r requirements.txt
  python app.py                -> http://127.0.0.1:5000
Örnek kullanıcılar (ilk açılışta oluşturulur, şifreleri değiştirin):
  yonetici / Yonetici123!   koordinator / Koordinator123!   pilot.deniz / Pilot123!   pilot.selin / Pilot123!

Örnek verideki uçak, tescil ve kişi adları uydurmadır.
"""
import csv
import io
import os
import secrets
import sqlite3
from datetime import datetime, date, timedelta, time
from functools import wraps
from zoneinfo import ZoneInfo

from flask import (Flask, Response, abort, flash, g, redirect, render_template, request,
                   session, url_for)
from jinja2 import DictLoader

import i18n
from werkzeug.security import check_password_hash, generate_password_hash

# ---------------------------------------------------------------- ayarlar
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "ucus.db"))
TZ = ZoneInfo(os.environ.get("APP_TZ", "Europe/Istanbul"))
COMPANY = os.environ.get("APP_COMPANY", "Cevheri Sivil Havacılık")
LOGO_URI = 'data:image/png;base64,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'

app = Flask(__name__)
# Veritabanı: DATABASE_URL (Supabase / Postgres) verilmişse oraya, yoksa yerel SQLite dosyasına bağlanır
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or ""
PG = DATABASE_URL.startswith(("postgres://", "postgresql://"))
if PG:
    import psycopg
    from psycopg.rows import dict_row
    IntegrityError = psycopg.IntegrityError
else:
    IntegrityError = sqlite3.IntegrityError
ON_VERCEL = any(os.environ.get(k) for k in ("VERCEL", "VERCEL_ENV", "VERCEL_URL", "AWS_LAMBDA_FUNCTION_NAME"))
if ON_VERCEL and not (os.environ.get("SECRET_KEY") and PG):
    raise RuntimeError("Vercel'de SECRET_KEY ve DATABASE_URL (Supabase bağlantı adresi) ortam değişkenleri zorunludur.")

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["SESSION_COOKIE_SECURE"] = ON_VERCEL
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=12)

ROLES = {"pilot": "Pilot", "koordinator": "Koordinatör", "yonetici": "Yönetici"}
MISSIONS = ["Personel Nakli", "VIP Transfer", "Kurumsal Seyahat", "Ferry", "Eğitim", "Test Uçuşu", "Ambulans"]
MX_CODES = {"M": "Bakımda", "AWP": "Parça bekliyor", "AOG": "AOG (yerde arızalı)", "U/S": "Gayrifaal"}
DAY_CODES = {"RON": "Konaklama", "RES": "Yedek", "M": "Bakım"}
CODE_COLORS = {"FLT": "#D8E3FD", "T": "#8DC4F4", "F": "#B9A9D9", "M": "#F0B46A", "AWP": "#C8A2E0",
               "AOG": "#EF7E72", "U/S": "#66769A", "RON": "#9AA8C8", "RES": "#D9CF9C", "PEND": "#2E4170"}
CATEGORIES = {"jet": "Jet", "turboprop": "Turboprop", "helicopter": "Helikopter"}
AIRPORTS = ["İstanbul Havalimanı (LTFM)", "Sabiha Gökçen (LTFJ)", "Atatürk (LTBA)", "Hezarfen (LTBW)",
            "Ankara Esenboğa (LTAC)", "İzmir Adnan Menderes (LTBJ)", "Antalya (LTAI)", "Dalaman (LTBS)",
            "Bodrum Milas (LTFE)", "Trabzon (LTCG)", "Rize-Artvin (LTFO)", "Gaziantep (LTAJ)",
            "Roma Ciampino (LIRA)", "Paris Le Bourget (LFPB)", "Cenevre (LSGG)", "Londra Farnborough (EGLF)"]


def now_local():
    """Yerel saat (naive). Test için APP_FAKE_NOW='2026-10-19T22:12' verilebilir."""
    fake = os.environ.get("APP_FAKE_NOW")
    if fake:
        return datetime.fromisoformat(fake)
    return datetime.now(TZ).replace(tzinfo=None, second=0, microsecond=0)


# ---------------------------------------------------------------- veritabanı
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
  full_name TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('pilot','koordinator','yonetici')),
  title TEXT DEFAULT '', active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS aircraft (
  id INTEGER PRIMARY KEY, reg TEXT UNIQUE NOT NULL, type TEXT NOT NULL, category TEXT NOT NULL,
  seats INTEGER NOT NULL DEFAULT 0, base TEXT DEFAULT '', active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS flights (
  id INTEGER PRIMARY KEY, code TEXT, flight_date TEXT NOT NULL, aircraft_id INTEGER NOT NULL REFERENCES aircraft(id),
  pic_id INTEGER REFERENCES users(id), crew TEXT DEFAULT '', dep TEXT NOT NULL, arr TEXT NOT NULL,
  dep_time TEXT NOT NULL, arr_time TEXT NOT NULL, mission TEXT NOT NULL, pax INTEGER DEFAULT 0,
  approval TEXT NOT NULL DEFAULT 'pending' CHECK(approval IN ('pending','approved','rejected')),
  cancelled INTEGER NOT NULL DEFAULT 0, note TEXT DEFAULT '', decision_note TEXT DEFAULT '',
  created_by INTEGER REFERENCES users(id), created_at TEXT NOT NULL,
  decided_by INTEGER REFERENCES users(id), decided_at TEXT);
CREATE TABLE IF NOT EXISTS maintenance (
  id INTEGER PRIMARY KEY, aircraft_id INTEGER NOT NULL REFERENCES aircraft(id), code TEXT NOT NULL,
  kind TEXT DEFAULT '', place TEXT DEFAULT '', start_at TEXT NOT NULL, end_at TEXT, note TEXT DEFAULT '',
  created_by INTEGER REFERENCES users(id), created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS day_codes (
  aircraft_id INTEGER NOT NULL REFERENCES aircraft(id), day TEXT NOT NULL, code TEXT NOT NULL,
  PRIMARY KEY (aircraft_id, day));
CREATE TABLE IF NOT EXISTS audit (
  id INTEGER PRIMARY KEY, user_id INTEGER, action TEXT NOT NULL, detail TEXT DEFAULT '', at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS expenses (
  id INTEGER PRIMARY KEY, flight_id INTEGER REFERENCES flights(id), aircraft_id INTEGER NOT NULL REFERENCES aircraft(id),
  category TEXT NOT NULL, expense_date TEXT NOT NULL, description TEXT DEFAULT '', vendor TEXT DEFAULT '', location TEXT DEFAULT '',
  quantity NUMERIC(14,2), unit TEXT DEFAULT '', amount NUMERIC(14,2) NOT NULL, currency TEXT NOT NULL DEFAULT 'EUR',
  payment_method TEXT DEFAULT '', payment_status TEXT NOT NULL DEFAULT 'odenecek', invoice_no TEXT DEFAULT '', note TEXT DEFAULT '',
  created_by INTEGER REFERENCES users(id), created_at TEXT NOT NULL);
"""


def connect():
    if PG:
        # prepare_threshold=None: Supabase havuzlayıcısı (port 6543, transaction modu) hazır sorguları desteklemez
        global DATABASE_URL
        try:
            return psycopg.connect(DATABASE_URL, row_factory=dict_row, prepare_threshold=None, connect_timeout=10)
        except psycopg.OperationalError as e:
            # Supabase havuzlayıcısı projeye göre aws-0 ya da aws-1 kümesindedir; yanlışsa "Tenant or user not found" döner
            alt = DATABASE_URL.replace("aws-1-", "aws-0-") if "aws-1-" in DATABASE_URL else DATABASE_URL.replace("aws-0-", "aws-1-")
            if "tenant" not in str(e).lower() or alt == DATABASE_URL:
                raise
            conn = psycopg.connect(alt, row_factory=dict_row, prepare_threshold=None, connect_timeout=10)
            DATABASE_URL = alt
            return conn
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def sql_of(text):
    return text.replace("?", "%s") if PG else text


def db():
    if "db" not in g:
        g.db = connect()
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def run(conn, text, args=()):
    """Sorguyu çalıştırır; INSERT ise yeni kaydın id'sini döner. Hata olursa işlem geri alınır."""
    text = sql_of(text)
    returning = PG and text.lstrip().upper().startswith("INSERT") and "day_codes" not in text
    try:
        cur = conn.execute(text + (" RETURNING id" if returning else ""), args)
        new_id = cur.fetchone()["id"] if returning else getattr(cur, "lastrowid", None)
        conn.commit()
        return new_id
    except Exception:
        conn.rollback()
        raise


def fetch(conn, text, args=()):
    return conn.execute(sql_of(text), args).fetchall()


def q(text, args=(), one=False):
    rows = fetch(db(), text, args)
    return (rows[0] if rows else None) if one else rows


def ex(text, args=()):
    return run(db(), text, args)


def log(action, detail=""):
    uid = g.user["id"] if g.get("user") else None
    ex("INSERT INTO audit(user_id, action, detail, at) VALUES (?,?,?,?)", (uid, action, detail, now_local().isoformat(" ", "minutes")))


def init_db():
    conn = connect()
    try:
        # Tablolar varsa kurulum atlanır (canlıda uygulama, tablo oluşturma yetkisi olmayan kısıtlı bir kullanıcıyla bağlanır)
        exists = fetch(conn, "SELECT to_regclass('users') AS t")[0]["t"] if PG else None
        if not exists:
            schema = SCHEMA.replace("INTEGER PRIMARY KEY", "SERIAL PRIMARY KEY") if PG else SCHEMA
            for stmt in [x.strip() for x in schema.split(";") if x.strip()]:
                conn.execute(stmt)
            conn.commit()
        if fetch(conn, "SELECT COUNT(*) AS n FROM users")[0]["n"] == 0 and os.environ.get("SEED_DEMO", "1") == "1":
            try:
                seed(conn)
            except IntegrityError:   # aynı anda açılan iki sunucu örneği: diğeri zaten doldurdu
                conn.rollback()
    finally:
        conn.close()


def seed(conn):
    """Uydurma örnek veri: tarihler bugüne göre üretilir."""
    stamp = now_local().isoformat(" ", "minutes")
    users = [("yonetici", "Yonetici123!", "Aylin Demirtaş", "yonetici", "Operasyon Müdürü"),
             ("koordinator", "Koordinator123!", "Burak Ersoy", "koordinator", "Uçuş Koordinatörü"),
             ("pilot.deniz", "Pilot123!", "Deniz Arslan", "pilot", "Kaptan Pilot"),
             ("pilot.selin", "Pilot123!", "Selin Koç", "pilot", "Kaptan Pilot"),
             ("pilot.mert", "Pilot123!", "Mert Uysal", "pilot", "İkinci Pilot")]
    for u, p, n, r, t in users:
        run(conn, "INSERT INTO users(username,password_hash,full_name,role,title,created_at) VALUES (?,?,?,?,?,?)",
                     (u, generate_password_hash(p), n, r, t, stamp))
    fleet = [("TC-GKA", "Stratos 6500", "jet", 14, "İstanbul Havalimanı (LTFM)"),
             ("TC-GKB", "Stratos 650", "jet", 12, "Sabiha Gökçen (LTFJ)"),
             ("TC-GKP", "Vega P2", "turboprop", 8, "Atatürk (LTBA)"),
             ("TC-GKE", "Vega P2 EVO", "turboprop", 8, "Atatürk (LTBA)"),
             ("TC-GKH", "Helix 139", "helicopter", 12, "Hezarfen (LTBW)")]
    for f in fleet:
        run(conn, "INSERT INTO aircraft(reg,type,category,seats,base) VALUES (?,?,?,?,?)", f)
    ac = {r["reg"]: r["id"] for r in fetch(conn, "SELECT id, reg FROM aircraft")}
    us = {r["username"]: r["id"] for r in fetch(conn, "SELECT id, username FROM users")}
    today = now_local().date()
    d = lambda n: (today + timedelta(days=n)).isoformat()
    flights = [  # gün, uçak, pilot, kalkış, varış, saat, saat, görev, yolcu, onay
        (-6, "TC-GKA", "pilot.deniz", "İstanbul Havalimanı (LTFM)", "Paris Le Bourget (LFPB)", "08:30", "11:55", "Kurumsal Seyahat", 6, "approved"),
        (-5, "TC-GKA", "pilot.deniz", "Paris Le Bourget (LFPB)", "İstanbul Havalimanı (LTFM)", "15:00", "18:20", "Kurumsal Seyahat", 6, "approved"),
        (-3, "TC-GKH", "pilot.selin", "Hezarfen (LTBW)", "Ankara Esenboğa (LTAC)", "09:00", "10:40", "Personel Nakli", 5, "approved"),
        (-2, "TC-GKB", "pilot.mert", "Sabiha Gökçen (LTFJ)", "Antalya (LTAI)", "07:45", "09:00", "VIP Transfer", 3, "approved"),
        (0, "TC-GKA", "pilot.deniz", "İstanbul Havalimanı (LTFM)", "Ankara Esenboğa (LTAC)", "07:30", "08:35", "Personel Nakli", 4, "approved"),
        (0, "TC-GKA", "pilot.deniz", "Ankara Esenboğa (LTAC)", "İstanbul Havalimanı (LTFM)", "18:00", "19:05", "Personel Nakli", 4, "approved"),
        (0, "TC-GKH", "pilot.selin", "Hezarfen (LTBW)", "Bodrum Milas (LTFE)", "21:00", "23:30", "Ambulans", 2, "approved"),
        (0, "TC-GKE", "pilot.mert", "Atatürk (LTBA)", "Roma Ciampino (LIRA)", "06:00", "09:10", "Ferry", 0, "approved"),
        (1, "TC-GKB", "pilot.mert", "Sabiha Gökçen (LTFJ)", "İzmir Adnan Menderes (LTBJ)", "10:00", "11:05", "Kurumsal Seyahat", 5, "approved"),
        (2, "TC-GKA", "pilot.deniz", "İstanbul Havalimanı (LTFM)", "Cenevre (LSGG)", "09:15", "12:40", "VIP Transfer", 8, "approved"),
        (3, "TC-GKH", "pilot.selin", "Hezarfen (LTBW)", "Trabzon (LTCG)", "08:00", "11:30", "Eğitim", 0, "pending"),
        (5, "TC-GKB", "pilot.deniz", "Sabiha Gökçen (LTFJ)", "Dalaman (LTBS)", "13:00", "14:15", "Personel Nakli", 7, "pending"),
    ]
    for i, (n, reg, pil, dep, arr, t1, t2, mis, pax, appr) in enumerate(flights, 1):
        run(conn, """INSERT INTO flights(code,flight_date,aircraft_id,pic_id,crew,dep,arr,dep_time,arr_time,mission,pax,approval,
                        created_by,created_at,decided_by,decided_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (f"GKY{100 + i}", d(n), ac[reg], us[pil], "", dep, arr, t1, t2, mis, pax, appr,
                      us[pil] if appr == "pending" else us["koordinator"], stamp,
                      us["koordinator"] if appr == "approved" else None, stamp if appr == "approved" else None))
    run(conn, "INSERT INTO maintenance(aircraft_id,code,kind,place,start_at,end_at,note,created_by,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                 (ac["TC-GKP"], "M", "24 Aylık", "Roma / İtalya", f"{d(-10)}T08:00", None, "", us["koordinator"], stamp))
    run(conn, "INSERT INTO maintenance(aircraft_id,code,kind,place,start_at,end_at,note,created_by,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                 (ac["TC-GKE"], "M", "200 Saatlik", "Roma / İtalya", f"{d(0)}T10:00", f"{d(4)}T18:00", "Ferry sonrası", us["koordinator"], stamp))
    run(conn, "INSERT INTO day_codes(aircraft_id, day, code) VALUES (?,?,?)", (ac["TC-GKB"], d(-2), "RON"))
    fl = {r["code"]: r for r in fetch(conn, "SELECT id, code, aircraft_id, flight_date FROM flights")}
    sample = [  # uçuş kodu, kategori, açıklama, tedarikçi, yer, miktar, birim, tutar, para, ödeme yolu, durum
        ("GKY101", "fuel", "Jet A-1 ikmali", "Air BP", "LFPB", 4200, "L", 4830.00, "EUR", "card", "odendi"),
        ("GKY101", "handling", "Yer hizmetleri ve FBO", "Dassault Falcon Service", "LFPB", None, "", 1650.00, "EUR", "transfer", "odenecek"),
        ("GKY101", "parking", "Apron park, 1 gece", "Paris Le Bourget", "LFPB", 1, "night", 420.00, "EUR", "transfer", "odenecek"),
        ("GKY101", "hotel", "Ekip konaklaması, 2 oda", "Hôtel Le Bourget", "Paris", 2, "night", 560.00, "EUR", "card", "odendi"),
        ("GKY101", "landing", "İniş ve yolcu servis ücreti", "ADP", "LFPB", None, "", 980.00, "EUR", "transfer", "yansitilacak"),
        ("GKY102", "fuel", "Jet A-1 ikmali", "Shell Aviation", "LTFM", 3900, "L", 112500.00, "TRY", "card", "odendi"),
        ("GKY102", "nav", "Eurocontrol rota ücreti", "Eurocontrol", "", None, "", 1240.00, "EUR", "transfer", "odenecek"),
        ("GKY103", "fuel", "Jet A-1 ikmali", "Opet Havacılık", "LTBW", 620, "L", 17800.00, "TRY", "card", "odendi"),
        ("GKY103", "crew", "Ekip harcırahı", "", "Ankara", 2, "day", 3000.00, "TRY", "cash", "odendi"),
        ("GKY104", "catering", "VIP catering", "Do & Co", "LTFJ", 3, "each", 9600.00, "TRY", "card", "yansitilacak"),
    ]
    for code, cat, desc, vendor, loc, qty, unit, amt, cur, pm, st in sample:
        f = fl.get(code)
        if f:
            run(conn, """INSERT INTO expenses(flight_id,aircraft_id,category,expense_date,description,vendor,location,quantity,unit,amount,currency,
                         payment_method,payment_status,invoice_no,note,created_by,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (f["id"], f["aircraft_id"], cat, f["flight_date"], desc, vendor, loc, qty, unit, amt, cur, pm, st, "", "", us["koordinator"], stamp))


# ---------------------------------------------------------------- zaman / durum hesapları
def parse_dt(s):
    return datetime.fromisoformat(s) if s else None


def flight_window(f):
    day = date.fromisoformat(f["flight_date"])
    dep = datetime.combine(day, time.fromisoformat(f["dep_time"]))
    arr = datetime.combine(day, time.fromisoformat(f["arr_time"]))
    if arr <= dep:  # gece yarısını geçen uçuş
        arr += timedelta(days=1)
    return dep, arr


def flight_status(f, now=None):
    now = now or now_local()
    if f["cancelled"]:
        return "İptal"
    if f["approval"] == "pending":
        return "Onay bekliyor"
    if f["approval"] == "rejected":
        return "Reddedildi"
    dep, arr = flight_window(f)
    if now >= arr:
        return "Tamamlandı"
    if now >= dep:
        return "Uçuşta"
    return "Planlı"


def flight_code(mission):
    return "T" if mission == "Eğitim" else "F" if mission == "Ferry" else "FLT"


def duration_text(f):
    dep, arr = flight_window(f)
    m = int((arr - dep).total_seconds() // 60)
    return f"{m // 60} sa {m % 60:02d} dk"


def short_ap(ap):
    return ap[ap.rfind("(") + 1:ap.rfind(")")] if "(" in ap else ap[:12]


def when_text(dt, now):
    if dt is None:
        return ""
    if dt.date() == now.date():
        return f"bugün {dt:%H:%M}"
    return f"{dt.day} {MONTHS[dt.month - 1][:3]}{' ' + str(dt.year) if dt.year != now.year else ''} {dt:%H:%M}"


MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
DAYS = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]


def active_flights(aircraft_id, day):
    return q("""SELECT * FROM flights WHERE aircraft_id=? AND flight_date=? AND approval='approved' AND cancelled=0
                ORDER BY dep_time""", (aircraft_id, day))


def mx_on(aircraft_id, start, end):
    """[start, end) aralığına değen bakım kayıtları."""
    rows = q("SELECT * FROM maintenance WHERE aircraft_id=? ORDER BY start_at", (aircraft_id,))
    return [m for m in rows if parse_dt(m["start_at"]) < end and (m["end_at"] is None or parse_dt(m["end_at"]) > start)]


def live_state(ac, now=None):
    """Uçağın şu anki durumu: (ton, etiket, çizelge kodu, açıklama)."""
    now = now or now_local()
    today = now.date().isoformat()
    flights = [(f, *flight_window(f)) for f in active_flights(ac["id"], today)]
    # dünden sarkan (gece yarısını geçen) uçuş
    for f in active_flights(ac["id"], (now.date() - timedelta(days=1)).isoformat()):
        dep, arr = flight_window(f)
        if arr > now:
            flights.insert(0, (f, dep, arr))
    route = lambda f: f"{short_ap(f['dep'])}–{short_ap(f['arr'])}"
    code_today = q("SELECT code FROM day_codes WHERE aircraft_id=? AND day=?", (ac["id"], today), one=True)
    code_today = code_today["code"] if code_today else ""

    air = next(((f, d, a) for f, d, a in flights if d <= now < a), None)
    if air:
        f, d, a = air
        return dict(tone="busy", label="Görevde", cell=flight_code(f["mission"]),
                    detail=f"Uçuşta: {route(f)}, tahmini iniş {a:%H:%M}",
                    air=dict(dep=short_ap(f["dep"]), arr=short_ap(f["arr"]), reg=ac["reg"], eta=f"{a:%H:%M}",
                             p=round(max(0.02, min(0.98, (now - d) / (a - d))), 3)))
    mx = [m for m in mx_on(ac["id"], now, now + timedelta(minutes=1))]
    if mx:
        m = mx[0]
        parts = [m["kind"], m["place"], f"başlangıç {when_text(parse_dt(m['start_at']), now)}",
                 f"bitiş {when_text(parse_dt(m['end_at']), now)}" if m["end_at"] else "bitiş tarihi girilmemiş"]
        return dict(tone="bad" if m["code"] in ("AOG", "U/S") else "warn", label=MX_CODES[m["code"]],
                    cell=m["code"], detail=" · ".join(p for p in parts if p))
    pending = [(f, d, a) for f, d, a in flights if a > now]
    done = [(f, d, a) for f, d, a in flights if a <= now]
    done_txt = f"Bugünkü {len(done)} uçuş tamamlandı, son iniş {done[-1][2]:%H:%M}" if done else ""
    later_mx = [m for m in mx_on(ac["id"], now, datetime.combine(now.date(), time.max))]
    later_txt = f"bakım {parse_dt(later_mx[0]['start_at']):%H:%M} itibarıyla başlıyor" if later_mx else ""
    if pending:
        f, d, a = pending[0]
        return dict(tone="busy", label="Görevde", cell=flight_code(f["mission"]),
                    detail=" · ".join(x for x in [f"Sıradaki kalkış {d:%H:%M}, {route(f)}", later_txt] if x))
    if code_today == "M":
        return dict(tone="warn", label="Bakımda", cell="M", detail=done_txt or "Günlük kodu bakım")
    if code_today == "RON":
        return dict(tone="", label="Konaklamada", cell="RON", detail=done_txt or "Dış meydanda konaklama")
    if code_today == "RES":
        return dict(tone="", label="Yedekte", cell="RES", detail=done_txt or "Yedek uçak")
    return dict(tone="ok", label="Müsait", cell="", detail=" · ".join(x for x in [done_txt, later_txt] if x) or "Bugün kayıt yok")


def day_cell(ac, day, now):
    """Çizelgede bir günün kodu. Bugün anlık durumdan gelir (müsaitse boş)."""
    if day == now.date():
        s = live_state(ac, now)
        return s["cell"], f"Şu an {s['label']} · {s['detail']}"
    start = datetime.combine(day, time.min)
    mx = mx_on(ac["id"], start, start + timedelta(days=1))
    fl = active_flights(ac["id"], day.isoformat())
    pend = q("SELECT COUNT(*) c FROM flights WHERE aircraft_id=? AND flight_date=? AND approval='pending' AND cancelled=0",
             (ac["id"], day.isoformat()), one=True)["c"]
    if fl:
        codes = [flight_code(f["mission"]) for f in fl]
        c = "T" if "T" in codes else "F" if set(codes) == {"F"} else "FLT"
        return c, f"{len(fl)} uçuş: " + ", ".join(f"{f['dep_time']} {short_ap(f['dep'])}–{short_ap(f['arr'])}" for f in fl)
    if mx:
        m = mx[0]
        return m["code"], f"{MX_CODES[m['code']]} · {m['kind']}"
    dc = q("SELECT code FROM day_codes WHERE aircraft_id=? AND day=?", (ac["id"], day.isoformat()), one=True)
    if dc:
        return dc["code"], DAY_CODES.get(dc["code"], dc["code"])
    if pend:
        return "PEND", f"{pend} uçuş kaydı onay bekliyor"
    return "", "Kayıt yok"


# ---------------------------------------------------------------- oturum, yetki, CSRF
@app.before_request
def load_user():
    g.user = None
    uid = session.get("uid")
    if uid:
        u = q("SELECT * FROM users WHERE id=? AND active=1", (uid,), one=True)
        if u:
            g.user = u
        else:
            session.clear()
    if request.method == "POST":
        token = session.get("csrf")
        if not token or request.form.get("csrf") != token:
            abort(400, "Oturum süresi doldu ya da form geçersiz. Sayfayı yenileyip tekrar deneyin.")


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


app.jinja_env.globals.update(LOGO=LOGO_URI, csrf_token=csrf_token, ROLES=ROLES, COMPANY=COMPANY, CODE_COLORS=CODE_COLORS,
                             MX_CODES=MX_CODES, MISSIONS=MISSIONS, AIRPORTS=AIRPORTS, CATEGORIES=CATEGORIES,
                             DAY_CODES=DAY_CODES, short_ap=short_ap)


def login_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if not g.user:
                return redirect(url_for("login", next=request.path))
            if roles and g.user["role"] not in roles:
                abort(403)
            return fn(*a, **kw)
        return wrapper
    return deco


STAFF = ("koordinator", "yonetici")


def is_staff():
    return g.user and g.user["role"] in STAFF


# ---------------------------------------------------------------- sayfalar: giriş
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = q("SELECT * FROM users WHERE username=?", (request.form.get("username", "").strip().lower(),), one=True)
        if u and u["active"] and check_password_hash(u["password_hash"], request.form.get("password", "")):
            lang = session.get("lang")
            session.clear()
            session.permanent = True
            if lang:
                session["lang"] = lang
            session["uid"] = u["id"]
            g.user = u
            log("giriş")
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("dashboard"))
        flash("Kullanıcı adı ya da şifre hatalı.", "error")
    # Örnek şifreler giriş sayfasında yalnızca DEMO_HINT=1 ise gösterilir (yerelde varsayılan açık, canlıda kapalı)
    return render_template("login.html", demo_hint=os.environ.get("DEMO_HINT", "0" if ON_VERCEL else "1") == "1")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/password", methods=["GET", "POST"])
@login_required()
def password():
    if request.method == "POST":
        old, new = request.form.get("old", ""), request.form.get("new", "")
        if not check_password_hash(g.user["password_hash"], old):
            flash("Mevcut şifre hatalı.", "error")
        elif len(new) < 8:
            flash("Yeni şifre en az 8 karakter olmalı.", "error")
        else:
            ex("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(new), g.user["id"]))
            log("şifre değiştirdi")
            flash("Şifreniz değiştirildi.", "ok")
            return redirect(url_for("dashboard"))
    return render_template("password.html")


# ---------------------------------------------------------------- genel bakış
@app.route("/")
@login_required()
def dashboard():
    now = now_local()
    fleet = q("SELECT * FROM aircraft WHERE active=1 ORDER BY id")
    states = [(a, live_state(a, now)) for a in fleet]
    counts = {}
    for _, s in states:
        key = {"ok": "müsait", "busy": "görevde", "warn": "bakımda", "bad": "arızalı"}.get(s["tone"], "diğer")
        counts[key] = counts.get(key, 0) + 1
    order = ["müsait", "görevde", "bakımda", "arızalı", "diğer"]
    lede = ", ".join(f"{counts[k]}{' uçak' if i == 0 else ''} {k}" for i, k in enumerate(k for k in order if k in counts))
    days = [now.date() + timedelta(days=i) for i in range(14)]
    grid = [(a, [day_cell(a, d, now) for d in days]) for a in fleet]
    where, args = "", []
    if g.user["role"] == "pilot":
        where, args = " AND (f.pic_id=? OR f.created_by=?)", [g.user["id"], g.user["id"]]
    upcoming = q(f"""SELECT f.*, a.reg, a.type, u.full_name pilot FROM flights f JOIN aircraft a ON a.id=f.aircraft_id
                     LEFT JOIN users u ON u.id=f.pic_id WHERE f.flight_date>=? AND f.cancelled=0 AND f.approval!='rejected' {where}
                     ORDER BY f.flight_date, f.dep_time LIMIT 8""", [now.date().isoformat()] + args)
    upcoming = [f for f in upcoming if flight_status(f, now) != "Tamamlandı"][:6]
    pending = q("SELECT COUNT(*) c FROM flights WHERE approval='pending' AND cancelled=0", one=True)["c"]
    year = q("SELECT * FROM flights WHERE approval='approved' AND cancelled=0 AND substr(flight_date,1,4)=?", (str(now.year),))
    done_year = sum(1 for f in year if flight_status(f, now) == "Tamamlandı")
    planned = sum(1 for f in year if flight_status(f, now) in ("Planlı", "Uçuşta"))
    track = next((dict(s["air"], live=True) for _, s in states if s.get("air")), None)
    if not track and upcoming:
        f = upcoming[0]
        track = dict(dep=short_ap(f["dep"]), arr=short_ap(f["arr"]), reg=f["reg"], p=0, live=False,
                     eta=f"{f['flight_date'][8:10]}.{f['flight_date'][5:7]} {f['dep_time']}")
    return render_template("dashboard.html", now=now, states=states, track=track, lede=lede, days=days, grid=grid, DAYS=DAYS,
                           MONTHS=MONTHS, upcoming=upcoming, flight_status=flight_status, pending=pending,
                           done_year=done_year, planned=planned)


# ---------------------------------------------------------------- uçuşlar
def flight_query(extra="", args=()):
    return q(f"""SELECT f.*, a.reg, a.type, u.full_name pilot, c.full_name creator FROM flights f
                 JOIN aircraft a ON a.id=f.aircraft_id LEFT JOIN users u ON u.id=f.pic_id
                 LEFT JOIN users c ON c.id=f.created_by WHERE 1=1 {extra}""", args)


@app.route("/flights")
@login_required()
def flights():
    extra, args = "", []
    if g.user["role"] == "pilot":
        extra += " AND (f.pic_id=? OR f.created_by=?)"
        args += [g.user["id"], g.user["id"]]
    f_from, f_to, f_ac = request.args.get("from", ""), request.args.get("to", ""), request.args.get("ac", "")
    f_status = request.args.get("status", "")
    if f_from:
        extra += " AND f.flight_date>=?"; args.append(f_from)
    if f_to:
        extra += " AND f.flight_date<=?"; args.append(f_to)
    if f_ac:
        extra += " AND a.id=?"; args.append(f_ac)
    rows = flight_query(extra + " ORDER BY f.flight_date DESC, f.dep_time DESC", args)
    now = now_local()
    rows = [(f, flight_status(f, now)) for f in rows]
    if f_status:
        rows = [(f, s) for f, s in rows if s == f_status]
    return render_template("flights.html", rows=rows, fleet=q("SELECT * FROM aircraft ORDER BY reg"),
                           filters=request.args, duration_text=duration_text)


def validate_flight(form, flight_id=None):
    errors = []
    try:
        fdate = date.fromisoformat(form.get("flight_date", ""))
        t1 = time.fromisoformat(form.get("dep_time", ""))
        t2 = time.fromisoformat(form.get("arr_time", ""))
    except ValueError:
        return None, ["Tarih ve saatleri doğru girin (saat SS:DD)."]
    ac = q("SELECT * FROM aircraft WHERE id=? AND active=1", (form.get("aircraft_id"),), one=True)
    if not ac:
        errors.append("Uçak seçin.")
    dep, arr = form.get("dep", "").strip(), form.get("arr", "").strip()
    if not dep or not arr:
        errors.append("Kalkış ve iniş meydanını yazın.")
    mission = form.get("mission")
    if mission not in MISSIONS:
        errors.append("Görev türü seçin.")
    try:
        pax = int(form.get("pax") or 0)
    except ValueError:
        pax = -1
    if ac and not (0 <= pax <= ac["seats"]):
        errors.append(f"Yolcu sayısı 0 ile {ac['seats']} arasında olmalı.")
    if g.user["role"] == "pilot":
        pic_id = g.user["id"]
    else:
        pic = q("SELECT * FROM users WHERE id=? AND role='pilot' AND active=1", (form.get("pic_id"),), one=True)
        pic_id = pic["id"] if pic else None
        if not pic:
            errors.append("Kaptan pilot seçin.")
    data = dict(flight_date=fdate.isoformat(), aircraft_id=ac["id"] if ac else None, pic_id=pic_id,
                crew=form.get("crew", "").strip(), dep=dep, arr=arr, dep_time=t1.strftime("%H:%M"),
                arr_time=t2.strftime("%H:%M"), mission=mission, pax=max(pax, 0), code=form.get("code", "").strip(),
                note=form.get("note", "").strip())
    if ac and not errors:
        d1, d2 = flight_window(dict(data, cancelled=0))
        if (d2 - d1) > timedelta(hours=16):
            errors.append("Uçuş süresi 16 saati geçemez; saatleri kontrol edin.")
        # aynı uçakta ya da aynı pilotta çakışma
        near = q("""SELECT f.*, a.reg FROM flights f JOIN aircraft a ON a.id=f.aircraft_id WHERE f.cancelled=0 AND f.approval!='rejected'
                    AND f.flight_date BETWEEN ? AND ? AND (f.aircraft_id=? OR f.pic_id=?) AND f.id!=?""",
                 ((fdate - timedelta(days=1)).isoformat(), (fdate + timedelta(days=1)).isoformat(), ac["id"], pic_id, flight_id or 0))
        for o in near:
            o1, o2 = flight_window(o)
            if o1 < d2 and d1 < o2:
                who = "uçak" if o["aircraft_id"] == ac["id"] else "pilot"
                errors.append(f"Çakışma: {o['reg']} {o['flight_date']} {o['dep_time']}–{o['arr_time']} uçuşu ile aynı {who}.")
        for m in mx_on(ac["id"], d1, d2):
            errors.append(f"{ac['reg']} bu saatlerde {MX_CODES[m['code']].lower()} ({m['kind'] or m['code']}).")
    return data, errors


def flight_form_context(f=None):
    return dict(fleet=q("SELECT * FROM aircraft WHERE active=1 ORDER BY reg"),
                pilots=q("SELECT * FROM users WHERE role='pilot' AND active=1 ORDER BY full_name"), f=f)


@app.route("/flights/new", methods=["GET", "POST"])
@login_required()
def flight_new():
    if request.method == "POST":
        data, errors = validate_flight(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("flight_form.html", **flight_form_context(request.form), mode="new")
        approved = is_staff()
        stamp = now_local().isoformat(" ", "minutes")
        fid = ex("""INSERT INTO flights(code,flight_date,aircraft_id,pic_id,crew,dep,arr,dep_time,arr_time,mission,pax,note,approval,
                    created_by,created_at,decided_by,decided_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                 (data["code"], data["flight_date"], data["aircraft_id"], data["pic_id"], data["crew"], data["dep"], data["arr"],
                  data["dep_time"], data["arr_time"], data["mission"], data["pax"], data["note"],
                  "approved" if approved else "pending", g.user["id"], stamp,
                  g.user["id"] if approved else None, stamp if approved else None))
        if not data["code"]:
            ex("UPDATE flights SET code=? WHERE id=?", (f"GKY{100 + fid}", fid))
        log("uçuş kaydı oluşturdu", f"#{fid}")
        flash("Uçuş kaydı oluşturuldu." if approved else "Uçuş kaydınız koordinatör onayına gönderildi.", "ok")
        return redirect(url_for("flight_detail", fid=fid))
    pre = {"flight_date": request.args.get("date", now_local().date().isoformat()), "aircraft_id": request.args.get("ac", "")}
    return render_template("flight_form.html", **flight_form_context(pre), mode="new")


def get_flight_or_404(fid):
    f = flight_query(" AND f.id=?", (fid,))
    if not f:
        abort(404)
    f = f[0]
    if g.user["role"] == "pilot" and g.user["id"] not in (f["pic_id"], f["created_by"]):
        abort(403)
    return f


def can_edit(f):
    if f["cancelled"]:
        return False
    if is_staff():
        return True
    return f["approval"] == "pending" and f["created_by"] == g.user["id"]


@app.route("/flights/<int:fid>")
@login_required()
def flight_detail(fid):
    f = get_flight_or_404(fid)
    decider = q("SELECT full_name FROM users WHERE id=?", (f["decided_by"],), one=True) if f["decided_by"] else None
    ps, pa = pilot_scope()
    exps = expense_query(" AND e.flight_id=?" + ps + " ORDER BY e.expense_date, e.id", [fid] + pa)
    by_cat, exp_tot = totals_by(exps, lambda r: r["category"])
    return render_template("flight_detail.html", f=f, status=flight_status(f), duration=duration_text(f),
                           can_edit=can_edit(f), decider=decider, exps=exps, exp_tot=exp_tot)


@app.route("/flights/<int:fid>/edit", methods=["GET", "POST"])
@login_required()
def flight_edit(fid):
    f = get_flight_or_404(fid)
    if not can_edit(f):
        abort(403)
    if request.method == "POST":
        data, errors = validate_flight(request.form, fid)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("flight_form.html", **flight_form_context(dict(request.form, id=fid)), mode="edit")
        ex("""UPDATE flights SET code=?,flight_date=?,aircraft_id=?,pic_id=?,crew=?,dep=?,arr=?,dep_time=?,arr_time=?,mission=?,pax=?,note=?
              WHERE id=?""", (data["code"] or f["code"], data["flight_date"], data["aircraft_id"], data["pic_id"], data["crew"], data["dep"],
                              data["arr"], data["dep_time"], data["arr_time"], data["mission"], data["pax"], data["note"], fid))
        log("uçuş kaydını düzenledi", f"#{fid}")
        flash("Kayıt güncellendi.", "ok")
        return redirect(url_for("flight_detail", fid=fid))
    return render_template("flight_form.html", **flight_form_context(f), mode="edit")


@app.route("/flights/<int:fid>/decide", methods=["POST"])
@login_required(*STAFF)
def flight_decide(fid):
    f = get_flight_or_404(fid)
    action = request.form.get("action")
    note = request.form.get("decision_note", "").strip()
    stamp = now_local().isoformat(" ", "minutes")
    if action == "approve" and f["approval"] == "pending":
        _, errors = validate_flight(dict(f, aircraft_id=f["aircraft_id"], pic_id=f["pic_id"]), fid)
        if errors:
            for e in errors:
                flash(e, "error")
            return redirect(url_for("flight_detail", fid=fid))
        ex("UPDATE flights SET approval='approved', decided_by=?, decided_at=?, decision_note=? WHERE id=?", (g.user["id"], stamp, note, fid))
        log("uçuşu onayladı", f"#{fid}")
        flash("Uçuş onaylandı.", "ok")
    elif action == "reject" and f["approval"] == "pending":
        ex("UPDATE flights SET approval='rejected', decided_by=?, decided_at=?, decision_note=? WHERE id=?", (g.user["id"], stamp, note, fid))
        log("uçuşu reddetti", f"#{fid}")
        flash("Uçuş reddedildi.", "ok")
    elif action == "cancel" and not f["cancelled"]:
        ex("UPDATE flights SET cancelled=1, decision_note=? WHERE id=?", (note or f["decision_note"], fid))
        log("uçuşu iptal etti", f"#{fid}")
        flash("Uçuş iptal edildi.", "ok")
    return redirect(request.form.get("back") or url_for("flight_detail", fid=fid))


@app.route("/approvals")
@login_required(*STAFF)
def approvals():
    rows = flight_query(" AND f.approval='pending' AND f.cancelled=0 ORDER BY f.flight_date, f.dep_time")
    return render_template("approvals.html", rows=rows, duration_text=duration_text)


@app.route("/flights.csv")
@login_required(*STAFF)
def flights_csv():
    now = now_local()
    out = io.StringIO()
    w = csv.writer(out, delimiter=";")
    w.writerow(["No", "Uçuş kodu", "Tarih", "Uçak", "Tip", "Kaptan", "Ekip", "Kalkış", "Kalkış saati", "İniş", "İniş saati",
                "Süre", "Görev", "Yolcu", "Durum", "Not"])
    for f in flight_query(" ORDER BY f.flight_date, f.dep_time"):
        w.writerow([f["id"], f["code"], f["flight_date"], f["reg"], f["type"], f["pilot"] or "", f["crew"], f["dep"], f["dep_time"],
                    f["arr"], f["arr_time"], duration_text(f), f["mission"], f["pax"], flight_status(f, now), f["note"]])
    return Response("﻿" + out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=ucuslar_{now:%Y_%m_%d}.csv"})


# ---------------------------------------------------------------- bakım ve günlük kodlar
@app.route("/maintenance", methods=["GET", "POST"])
@login_required()
def maintenance():
    now = now_local()
    if request.method == "POST":
        if not is_staff():
            abort(403)
        try:
            start = datetime.fromisoformat(request.form["start_at"])
            end = datetime.fromisoformat(request.form["end_at"]) if request.form.get("end_at") else None
        except (KeyError, ValueError):
            flash("Başlangıç tarih-saatini girin.", "error")
            return redirect(url_for("maintenance"))
        code = request.form.get("code")
        ac = q("SELECT * FROM aircraft WHERE id=?", (request.form.get("aircraft_id"),), one=True)
        if code not in MX_CODES or not ac:
            flash("Uçak ve durum seçin.", "error")
        elif end and end <= start:
            flash("Bitiş, başlangıçtan sonra olmalı.", "error")
        else:
            ex("INSERT INTO maintenance(aircraft_id,code,kind,place,start_at,end_at,note,created_by,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
               (ac["id"], code, request.form.get("kind", "").strip(), request.form.get("place", "").strip(),
                start.isoformat(timespec="minutes"), end.isoformat(timespec="minutes") if end else None,
                request.form.get("note", "").strip(), g.user["id"], now.isoformat(" ", "minutes")))
            log("bakım kaydı ekledi", f"{ac['reg']} {code}")
            clash = [f for f in flight_query(" AND a.id=? AND f.cancelled=0 AND f.approval!='rejected' AND f.flight_date>=?",
                                             (ac["id"], start.date().isoformat()))
                     if flight_window(f)[1] > start and (end is None or flight_window(f)[0] < end)]
            flash("Bakım kaydı eklendi." + (f" Dikkat: bu aralıkta {len(clash)} uçuş kaydı var." if clash else ""),
                  "error" if clash else "ok")
        return redirect(url_for("maintenance"))
    rows = q("""SELECT m.*, a.reg, a.type, u.full_name creator FROM maintenance m JOIN aircraft a ON a.id=m.aircraft_id
                LEFT JOIN users u ON u.id=m.created_by ORDER BY (m.end_at IS NULL) DESC, m.start_at DESC""")
    def state(m):
        s, e = parse_dt(m["start_at"]), parse_dt(m["end_at"])
        return "Sürüyor" if s <= now and (e is None or e > now) else "Başlamadı" if s > now else "Bitti"
    codes = q("""SELECT d.*, a.reg FROM day_codes d JOIN aircraft a ON a.id=d.aircraft_id WHERE d.day>=? ORDER BY d.day""",
              ((now.date() - timedelta(days=7)).isoformat(),))
    return render_template("maintenance.html", rows=[(m, state(m)) for m in rows], fleet=q("SELECT * FROM aircraft WHERE active=1 ORDER BY reg"),
                           now=now, codes=codes)


@app.route("/maintenance/<int:mid>/close", methods=["POST"])
@login_required(*STAFF)
def maintenance_close(mid):
    m = q("SELECT * FROM maintenance WHERE id=?", (mid,), one=True)
    if not m:
        abort(404)
    now = now_local()
    if parse_dt(m["start_at"]) > now:
        ex("DELETE FROM maintenance WHERE id=?", (mid,))
        flash("Başlamamış bakım kaydı silindi.", "ok")
    else:
        ex("UPDATE maintenance SET end_at=? WHERE id=?", (now.isoformat(timespec="minutes"), mid))
        flash("Bakım şu an itibarıyla bitirildi; uçak tekrar müsait sayılır.", "ok")
    log("bakımı kapattı", f"#{mid}")
    return redirect(url_for("maintenance"))


@app.route("/day-code", methods=["POST"])
@login_required(*STAFF)
def day_code():
    ac_id, day, code = request.form.get("aircraft_id"), request.form.get("day", ""), request.form.get("code", "")
    try:
        date.fromisoformat(day)
    except ValueError:
        flash("Tarih seçin.", "error")
        return redirect(url_for("maintenance"))
    if code:
        if code not in DAY_CODES:
            abort(400)
        ex("INSERT INTO day_codes(aircraft_id, day, code) VALUES (?,?,?) ON CONFLICT(aircraft_id, day) DO UPDATE SET code=excluded.code",
           (ac_id, day, code))
    else:
        ex("DELETE FROM day_codes WHERE aircraft_id=? AND day=?", (ac_id, day))
    log("günlük kod", f"{ac_id} {day} {code or 'silindi'}")
    flash("Günlük kod kaydedildi.", "ok")
    return redirect(url_for("maintenance"))


# ---------------------------------------------------------------- filo
@app.route("/fleet", methods=["GET", "POST"])
@login_required()
def fleet():
    if request.method == "POST":
        if g.user["role"] != "yonetici":
            abort(403)
        reg = request.form.get("reg", "").strip().upper()
        try:
            seats = int(request.form.get("seats") or 0)
        except ValueError:
            seats = 0
        cat = request.form.get("category")
        if not reg or not request.form.get("type") or cat not in CATEGORIES:
            flash("Tescil, tip ve kategori zorunlu.", "error")
        else:
            aid = request.form.get("id")
            try:
                if aid:
                    ex("UPDATE aircraft SET reg=?, type=?, category=?, seats=?, base=?, active=? WHERE id=?",
                       (reg, request.form["type"].strip(), cat, seats, request.form.get("base", "").strip(),
                        1 if request.form.get("active") else 0, aid))
                else:
                    ex("INSERT INTO aircraft(reg,type,category,seats,base) VALUES (?,?,?,?,?)",
                       (reg, request.form["type"].strip(), cat, seats, request.form.get("base", "").strip()))
                log("uçak kaydı", reg)
                flash("Uçak kaydedildi.", "ok")
            except IntegrityError:
                flash("Bu tescil zaten kayıtlı.", "error")
        return redirect(url_for("fleet"))
    now = now_local()
    cards = []
    for a in q("SELECT * FROM aircraft ORDER BY active DESC, id"):
        s = live_state(a, now) if a["active"] else dict(tone="", label="Filo dışı", cell="", detail="Pasif kayıt")
        flown = [f for f in flight_query(" AND a.id=? AND f.approval='approved' AND f.cancelled=0", (a["id"],))
                 if flight_status(f, now) == "Tamamlandı"]
        minutes = sum(int((flight_window(f)[1] - flight_window(f)[0]).total_seconds() // 60) for f in flown)
        last = max(flown, key=lambda f: (f["flight_date"], f["arr_time"]), default=None)
        nxt = [f for f in flight_query(" AND a.id=? AND f.approval='approved' AND f.cancelled=0 AND f.flight_date>=? ORDER BY f.flight_date, f.dep_time",
                                       (a["id"], now.date().isoformat())) if flight_status(f, now) == "Planlı"]
        fleet_state = s["label"] if s["tone"] in ("warn", "bad") or not a["active"] else f"Faal (şu an {s['label'].lower()})"
        cards.append(dict(a=a, s=s, fleet_state=fleet_state, sorties=len(flown), minutes=minutes,
                          location=last["arr"] if last else a["base"], last=last, next=nxt[0] if nxt else None))
    return render_template("fleet.html", cards=cards)


# ---------------------------------------------------------------- uçuş masrafları
EXPENSE_CATS = {"fuel": "Yakıt", "handling": "Yer hizmetleri (handling)", "landing": "İniş / yolcu ücreti", "parking": "Park / hangar",
                "hotel": "Konaklama", "crew": "Ekip harcırahı", "transport": "Ulaşım / transfer", "catering": "Catering",
                "fbo": "FBO / VIP salon", "nav": "Navigasyon / overflight", "permits": "İzin / slot", "customs": "Gümrük / pasaport",
                "deice": "Buzlanma önleme", "line_mx": "Hat bakımı", "cleaning": "Temizlik", "other": "Diğer"}
CURRENCIES = ["EUR", "USD", "TRY", "GBP", "CHF", "AED"]
UNITS = {"": "—", "L": "L", "USG": "USG", "kg": "kg", "night": "gece", "day": "gün", "hour": "saat", "each": "adet"}
PAY_METHODS = {"": "—", "card": "Şirket kartı", "transfer": "Havale / EFT", "cash": "Nakit", "crew": "Ekip ödedi (iade edilecek)", "account": "Cari hesap"}
PAY_STATUS = {"odenecek": "Ödenecek", "odendi": "Ödendi", "yansitilacak": "Müşteriye yansıtılacak"}
CAT_UNIT = {"fuel": "L", "hotel": "night", "parking": "night", "crew": "day", "catering": "each"}


def parse_amount(v):
    """'1.234,56' ya da '1234.56' gibi yazılmış tutarı sayıya çevirir; geçersizse None."""
    t = str(v or "").strip().replace(" ", "")
    if not t:
        return None
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".") if t.rfind(",") > t.rfind(".") else t.replace(",", "")
    elif "," in t:
        t = t.replace(",", ".")
    try:
        return round(float(t), 2)
    except ValueError:
        return None


def money(v, cur=""):
    """Dile göre biçimlenmiş tutar: TR 12.345,67 · EN 12,345.67"""
    txt = f"{float(v or 0):,.2f}"
    if current_lang() == "tr":
        txt = txt.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{txt} {cur}".strip()


def expense_flights():
    """Masraf formundaki uçuş listesi: son 120 gün ve önümüzdeki 30 gün, iptal edilmemiş; pilot yalnızca kendi uçuşlarını görür."""
    today = now_local().date()
    extra, args = " AND f.cancelled=0 AND f.approval!='rejected' AND f.flight_date BETWEEN ? AND ?", [(today - timedelta(days=120)).isoformat(), (today + timedelta(days=30)).isoformat()]
    if g.user["role"] == "pilot":
        extra += " AND (f.pic_id=? OR f.created_by=?)"; args += [g.user["id"], g.user["id"]]
    return flight_query(extra + " ORDER BY f.flight_date DESC, f.dep_time DESC", args)


def expense_query(extra="", args=()):
    return q(f"""SELECT e.*, a.reg, a.type, f.code AS flight_code, f.flight_date, f.dep, f.arr, f.pic_id, u.full_name AS creator
                 FROM expenses e JOIN aircraft a ON a.id=e.aircraft_id LEFT JOIN flights f ON f.id=e.flight_id
                 LEFT JOIN users u ON u.id=e.created_by WHERE 1=1 {extra}""", args)


def pilot_scope():
    if g.user["role"] != "pilot":
        return "", []
    return " AND (f.pic_id=? OR e.created_by=?)", [g.user["id"], g.user["id"]]


def can_edit_expense(e):
    return is_staff() or e["created_by"] == g.user["id"]


def totals_by(rows, key):
    """{anahtar: {para birimi: toplam}} ve para birimi toplamları."""
    out, cur_tot = {}, {}
    for r in rows:
        k = key(r)
        amt = float(r["amount"])
        out.setdefault(k, {}).setdefault(r["currency"], 0.0)
        out[k][r["currency"]] += amt
        cur_tot[r["currency"]] = cur_tot.get(r["currency"], 0.0) + amt
    return out, cur_tot


def expense_filters():
    a = request.args
    extra, args = "", []
    for col, key in [("e.expense_date>=?", "from"), ("e.expense_date<=?", "to"), ("e.aircraft_id=?", "ac"), ("e.category=?", "cat"),
                     ("e.flight_id=?", "flight"), ("e.payment_status=?", "status"), ("e.currency=?", "cur")]:
        if a.get(key):
            extra += " AND " + col; args.append(a.get(key))
    ps, pa = pilot_scope()
    return extra + ps, args + pa


@app.route("/expenses")
@login_required()
def expenses():
    extra, args = expense_filters()
    rows = expense_query(extra + " ORDER BY e.expense_date DESC, e.id DESC", args)
    by_cat, cur_tot = totals_by(rows, lambda r: r["category"])
    by_ac, _ = totals_by(rows, lambda r: r["reg"])
    by_flight, _ = totals_by([r for r in rows if r["flight_id"]], lambda r: (r["flight_id"], r["flight_code"], r["flight_date"], r["reg"], r["dep"], r["arr"]))
    unpaid, _ = totals_by([r for r in rows if r["payment_status"] == "odenecek"], lambda r: "x")
    rebill, _ = totals_by([r for r in rows if r["payment_status"] == "yansitilacak"], lambda r: "x")
    curs = sorted(cur_tot, key=lambda c: CURRENCIES.index(c) if c in CURRENCIES else 99)
    cat_rows = sorted(by_cat.items(), key=lambda kv: -max(kv[1].values()))
    maxv = {c: max([v.get(c, 0) for v in by_cat.values()] or [1]) or 1 for c in curs}
    top_flights = sorted(by_flight.items(), key=lambda kv: -sum(kv[1].values()))[:8]
    return render_template("expenses.html", rows=rows, curs=curs, cur_tot=cur_tot, cat_rows=cat_rows, maxv=maxv,
                           by_ac=sorted(by_ac.items()), top_flights=top_flights, unpaid=unpaid.get("x", {}), rebill=rebill.get("x", {}),
                           fleet=q("SELECT * FROM aircraft ORDER BY reg"), flights_list=expense_flights(), filters=request.args)


def validate_expense(form):
    errors = []
    flight = None
    if form.get("flight_id"):
        flight = next((f for f in expense_flights() if str(f["id"]) == str(form.get("flight_id"))), None)
        if not flight:
            flight = flight_query(" AND f.id=?", (form.get("flight_id"),))
            flight = flight[0] if flight and is_staff() else None
        if not flight:
            return None, ["Bu uçuşa masraf giremezsiniz; listeden bir uçuş seçin."]
    aircraft_id = flight["aircraft_id"] if flight else form.get("aircraft_id")
    if not flight and not q("SELECT id FROM aircraft WHERE id=?", (aircraft_id or 0,), one=True):
        errors.append("Uçuş ya da uçak seçin.")
    if g.user["role"] == "pilot" and not flight:
        errors.append("Pilotlar masrafı kendi uçuşlarından birine bağlamalıdır.")
    cat = form.get("category")
    if cat not in EXPENSE_CATS:
        errors.append("Masraf türü seçin.")
    amount = parse_amount(form.get("amount"))
    if amount is None or amount <= 0:
        errors.append("Tutarı doğru girin.")
    cur = form.get("currency")
    if cur not in CURRENCIES:
        errors.append("Para birimi seçin.")
    qty_raw = form.get("quantity", "").strip()
    qty = parse_amount(qty_raw) if qty_raw else None
    if qty_raw and (qty is None or qty < 0):
        errors.append("Miktarı doğru girin.")
    try:
        edate = date.fromisoformat(form.get("expense_date") or (flight["flight_date"] if flight else now_local().date().isoformat()))
    except ValueError:
        edate = None
        errors.append("Tarih seçin.")
    status = form.get("payment_status") if form.get("payment_status") in PAY_STATUS else "odenecek"
    data = dict(flight_id=flight["id"] if flight else None, aircraft_id=int(aircraft_id) if aircraft_id else None, category=cat,
                expense_date=edate.isoformat() if edate else "", description=form.get("description", "").strip(), vendor=form.get("vendor", "").strip(),
                location=form.get("location", "").strip(), quantity=qty, unit=form.get("unit") if form.get("unit") in UNITS else "",
                amount=amount, currency=cur, payment_method=form.get("payment_method") if form.get("payment_method") in PAY_METHODS else "",
                payment_status=status, invoice_no=form.get("invoice_no", "").strip(), note=form.get("note", "").strip())
    return data, errors


EXP_COLS = ["flight_id", "aircraft_id", "category", "expense_date", "description", "vendor", "location", "quantity", "unit", "amount",
            "currency", "payment_method", "payment_status", "invoice_no", "note"]


def expense_form(e, mode):
    return render_template("expense_form.html", e=e, mode=mode, flights_list=expense_flights(), fleet=q("SELECT * FROM aircraft WHERE active=1 ORDER BY reg"))


@app.route("/expenses/new", methods=["GET", "POST"])
@login_required()
def expense_new():
    if request.method == "POST":
        data, errors = validate_expense(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            return expense_form(request.form, "new")
        eid = ex(f"INSERT INTO expenses({','.join(EXP_COLS)},created_by,created_at) VALUES ({','.join('?' * (len(EXP_COLS) + 2))})",
                 [data[c] for c in EXP_COLS] + [g.user["id"], now_local().isoformat(" ", "minutes")])
        log("masraf ekledi", f"#{eid} {data['category']} {data['amount']} {data['currency']}")
        flash("Masraf kaydedildi.", "ok")
        if request.form.get("again"):
            return redirect(url_for("expense_new", flight=data["flight_id"] or ""))
        return redirect(url_for("flight_detail", fid=data["flight_id"]) if data["flight_id"] else url_for("expenses"))
    pre = {"flight_id": request.args.get("flight", ""), "currency": "EUR", "payment_status": "odenecek"}
    if pre["flight_id"]:
        f = next((x for x in expense_flights() if str(x["id"]) == pre["flight_id"]), None)
        if f:
            pre["expense_date"] = f["flight_date"]
            pre["currency"] = "TRY" if f["arr"].endswith(("(LTFM)", "(LTFJ)", "(LTBA)", "(LTBW)", "(LTAC)", "(LTBJ)", "(LTAI)", "(LTBS)", "(LTFE)", "(LTCG)", "(LTFO)", "(LTAJ)")) else "EUR"
    return expense_form(pre, "new")


def get_expense_or_404(eid):
    ps, pa = pilot_scope()
    rows = expense_query(" AND e.id=?" + ps, [eid] + pa)
    if not rows:
        abort(404)
    return rows[0]


@app.route("/expenses/<int:eid>/edit", methods=["GET", "POST"])
@login_required()
def expense_edit(eid):
    e = get_expense_or_404(eid)
    if not can_edit_expense(e):
        abort(403)
    if request.method == "POST":
        data, errors = validate_expense(request.form)
        if errors:
            for m in errors:
                flash(m, "error")
            return expense_form(dict(request.form, id=eid), "edit")
        ex(f"UPDATE expenses SET {', '.join(c + '=?' for c in EXP_COLS)} WHERE id=?", [data[c] for c in EXP_COLS] + [eid])
        log("masrafı düzenledi", f"#{eid}")
        flash("Masraf güncellendi.", "ok")
        return redirect(request.args.get("back") or url_for("expenses"))
    return expense_form(e, "edit")


@app.route("/expenses/<int:eid>/delete", methods=["POST"])
@login_required()
def expense_delete(eid):
    e = get_expense_or_404(eid)
    if not can_edit_expense(e):
        abort(403)
    ex("DELETE FROM expenses WHERE id=?", (eid,))
    log("masrafı sildi", f"#{eid}")
    flash("Masraf silindi.", "ok")
    back = request.form.get("back", "")
    return redirect(back if back.startswith("/") and not back.startswith("//") else url_for("expenses"))


@app.route("/expenses.csv")
@login_required(*STAFF)
def expenses_csv():
    extra, args = expense_filters()
    out = io.StringIO()
    w = csv.writer(out, delimiter=";")
    w.writerow(["No", "Tarih", "Uçuş kodu", "Uçuş tarihi", "Rota", "Uçak", "Tür", "Açıklama", "Tedarikçi", "Yer", "Miktar", "Birim",
                "Tutar", "Para birimi", "Ödeme yolu", "Ödeme durumu", "Fatura no", "Not", "Giren"])
    for e in expense_query(extra + " ORDER BY e.expense_date, e.id", args):
        w.writerow([e["id"], e["expense_date"], e["flight_code"] or "", e["flight_date"] or "",
                    f"{short_ap(e['dep'])}–{short_ap(e['arr'])}" if e["dep"] else "", e["reg"], EXPENSE_CATS.get(e["category"], e["category"]),
                    e["description"], e["vendor"], e["location"], "" if e["quantity"] is None else str(e["quantity"]).replace(".", ","),
                    UNITS.get(e["unit"], e["unit"]) if e["unit"] else "", f"{float(e['amount']):.2f}".replace(".", ","), e["currency"],
                    PAY_METHODS.get(e["payment_method"], ""), PAY_STATUS.get(e["payment_status"], ""), e["invoice_no"], e["note"], e["creator"] or ""])
    return Response("﻿" + out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=ucus_masraflari_{now_local():%Y_%m_%d}.csv"})


# ---------------------------------------------------------------- kullanıcılar (yönetici)
@app.route("/users", methods=["GET", "POST"])
@login_required("yonetici")
def users():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "create":
            un, name, role = request.form.get("username", "").strip().lower(), request.form.get("full_name", "").strip(), request.form.get("role")
            pw = request.form.get("password", "")
            if not un or not name or role not in ROLES or len(pw) < 8:
                flash("Kullanıcı adı, ad soyad, rol ve en az 8 karakterli şifre zorunlu.", "error")
            else:
                try:
                    ex("INSERT INTO users(username,password_hash,full_name,role,title,created_at) VALUES (?,?,?,?,?,?)",
                       (un, generate_password_hash(pw), name, role, request.form.get("title", "").strip(), now_local().isoformat(" ", "minutes")))
                    log("kullanıcı ekledi", un)
                    flash(f"{name} eklendi.", "ok")
                except IntegrityError:
                    flash("Bu kullanıcı adı alınmış.", "error")
        else:
            uid = int(request.form.get("id", 0))
            if uid == g.user["id"] and action in ("toggle", "role"):
                flash("Kendi hesabınızın rolünü ya da durumunu değiştiremezsiniz.", "error")
            elif action == "toggle":
                ex("UPDATE users SET active=1-active WHERE id=?", (uid,))
                log("kullanıcı durumu", str(uid))
            elif action == "role" and request.form.get("role") in ROLES:
                ex("UPDATE users SET role=? WHERE id=?", (request.form["role"], uid))
                log("rol değiştirdi", f"{uid} -> {request.form['role']}")
            elif action == "reset":
                pw = secrets.token_urlsafe(8)
                ex("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(pw), uid))
                log("şifre sıfırladı", str(uid))
                flash(f"Yeni geçici şifre: {pw}  (kullanıcıya iletin; ilk girişte değiştirsin)", "ok")
        return redirect(url_for("users"))
    return render_template("users.html", rows=q("SELECT * FROM users ORDER BY role, full_name"))


@app.route("/audit")
@login_required("yonetici")
def audit():
    rows = q("SELECT l.*, u.full_name FROM audit l LEFT JOIN users u ON u.id=l.user_id ORDER BY l.id DESC LIMIT 300")
    return render_template("audit.html", rows=rows)


@app.errorhandler(403)
def forbidden(_e):
    return render_template("error.html", code=403, msg="Bu sayfa için yetkiniz yok."), 403


@app.errorhandler(404)
def not_found(_e):
    return render_template("error.html", code=404, msg="Kayıt bulunamadı."), 404


@app.errorhandler(400)
def bad_request(e):
    return render_template("error.html", code=400, msg=getattr(e, "description", "Geçersiz istek.")), 400


# ---------------------------------------------------------------- şablonlar
TEMPLATES = {}

TEMPLATES["base.html"] = '<!doctype html>\n<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">\n<title>{% block title %}{{ COMPANY }}{% endblock %} · {{ COMPANY }}</title><link rel="icon" href="{{ LOGO }}">\n<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700&display=swap" rel="stylesheet">\n<style>\n:root{color-scheme:dark;--ink:#142143;--night:#101B39;--panel:#1A2A52;--panel2:#20325F;--line:rgba(141,196,244,.16);--line2:rgba(216,227,253,.08);--gold:#8DC4F4;--gold2:#FFFFFF;--ivory:#FFFFFF;--text:#D8E3FD;--muted:#8E9CBE;--accent:#1E73BE;--ok:#7FD3A6;--busy:#8DC4F4;--warn:#F0B46A;--bad:#EF7E72;--r:8px;--serif:"Montserrat","Helvetica Neue",Arial,sans-serif;--sans:"Montserrat","Helvetica Neue",Arial,sans-serif}\n*{box-sizing:border-box}html,body{overflow-x:hidden}\nbody{margin:0;font:15px/1.55 var(--sans);font-weight:400;background:var(--ink);color:var(--text);\nbackground-image:radial-gradient(1100px 620px at 50% -12%,rgba(30,115,190,.22),transparent 65%);background-attachment:fixed}\na{color:var(--gold2);text-decoration:none}a:hover{color:#fff}\nheader.top{position:sticky;top:0;z-index:20;background:rgba(16,27,57,.9);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);border-bottom:1px solid var(--line);padding:0 32px}\n.top-in{max-width:1216px;margin:0 auto;display:flex;align-items:center;gap:0 28px;padding:14px 0 0;flex-wrap:wrap}nav.main{margin-top:12px!important}\n.brand{display:flex;align-items:center;gap:12px;color:var(--ivory)}.brand .mark{height:34px;width:auto;flex:none}\n.brand b{display:block;font:600 15px/1 var(--serif);letter-spacing:.18em;text-transform:uppercase}.brand small{display:block;font-size:10px;letter-spacing:.32em;text-transform:uppercase;color:var(--gold);margin-top:4px}\nnav.main{order:3;flex:1 1 100%;display:flex;gap:0;flex-wrap:nowrap;min-width:0;overflow-x:auto;scrollbar-width:none;margin:0 -10px;padding:2px 0 4px;border-top:1px solid var(--line2)}nav.main::-webkit-scrollbar{display:none}\nnav.main a{position:relative;color:var(--muted);padding:10px 10px;font-size:12px;letter-spacing:.1em;text-transform:uppercase;white-space:nowrap}\nnav.main a:hover{color:var(--ivory)}nav.main a.on{color:var(--gold2)}\nnav.main a.on::after{content:"";position:absolute;left:10px;right:10px;bottom:2px;height:2px;background:#479FED}\nnav.main .badge{background:#1E73BE;color:#fff;border-radius:10px;padding:0 6px;font-size:11px;margin-left:5px;letter-spacing:0}\n.who{display:flex;align-items:center;gap:12px;font-size:13px;color:var(--muted);margin-left:auto;white-space:nowrap}.who a{color:var(--ivory)}.who form{margin:0}\n.who button{background:rgba(255,255,255,.05);border:1px solid var(--line);color:#fff;border-radius:6px;padding:6px 14px;cursor:pointer;font:inherit;letter-spacing:.06em}\n.who button:hover{border-color:var(--gold)}\nmain{max-width:1280px;margin:0 auto;padding:40px 32px 80px}\nh1{font:600 36px/1.15 var(--serif);color:var(--ivory);margin:0 0 8px;letter-spacing:.02em}h2{font:600 22px/1.25 var(--serif);color:var(--ivory);margin:36px 0 14px}\n.eyebrow{font-size:11px;letter-spacing:.32em;text-transform:uppercase;color:var(--gold)}\n.muted{color:var(--muted)}.sub{display:block;font-size:12px;color:var(--muted);font-weight:400}\n.sheet{background:rgba(255,255,255,.04);border:1px solid var(--line);border-radius:var(--r);padding:22px}\n.tbl{overflow-x:auto;background:rgba(255,255,255,.03);border:1px solid var(--line);border-radius:var(--r)}\ntable{width:100%;border-collapse:collapse}th,td{text-align:left;padding:14px 16px;border-bottom:1px solid var(--line2);vertical-align:top;font-size:14px}\nth{font-size:11px;text-transform:uppercase;letter-spacing:.16em;color:var(--muted);font-weight:600;background:rgba(255,255,255,.04)}\ntr:last-child td{border-bottom:0}tbody tr:hover td,table tr:hover td{background:rgba(255,255,255,.025)}\n.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;border:1px solid #1E73BE;background:#1E73BE;color:#fff;border-radius:6px;padding:11px 20px;font:600 12px/1.2 var(--sans);letter-spacing:.12em;text-transform:uppercase;cursor:pointer}\n.btn:hover{background:#2A86D6;border-color:#2A86D6;color:#fff}.btn.ghost{background:rgba(255,255,255,.05);border-color:rgba(255,255,255,.14);color:#fff}.btn.ghost:hover{background:rgba(255,255,255,.10)}\n.btn.danger{background:none;border-color:rgba(227,133,122,.6);color:var(--bad)}.btn.small{padding:6px 12px;font-size:11px}\n.st{font-weight:500;font-size:12px;letter-spacing:.06em;white-space:nowrap;display:inline-flex;align-items:center;gap:7px;text-transform:uppercase}\n.st::before{content:"";width:7px;height:7px;border-radius:50%;background:currentColor;box-shadow:0 0 10px currentColor}\n.st.ok,.st.Tamamlandı{color:var(--ok)}.st.busy,.st.Uçuşta,.st.Planlı{color:var(--busy)}.st.warn,.st.Onay{color:var(--warn)}.st.bad,.st.İptal,.st.Reddedildi{color:var(--bad)}\nform.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:18px}\nlabel{display:block;font-size:11px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--gold)}\ninput,select,textarea{width:100%;margin-top:8px;padding:12px 14px;border:1px solid var(--line);border-radius:6px;background:rgba(255,255,255,.04);color:var(--ivory);font:15px var(--sans);letter-spacing:0;text-transform:none}\nselect{background-color:#1A2A52}select option,select optgroup{background:#101B39;color:#D8E3FD}select option:checked{background:#1E73BE;color:#fff}\ninput:focus,select:focus,textarea:focus{outline:none;border-color:rgba(255,255,255,.5);box-shadow:0 0 0 3px rgba(255,255,255,.15)}\ninput[type=checkbox]{width:auto;accent-color:#1E73BE}input::-webkit-calendar-picker-indicator{filter:invert(.8)}\ntextarea{min-height:80px}.full{grid-column:1/-1}.row{display:flex;gap:12px;flex-wrap:wrap;align-items:center}\n.flash{padding:12px 16px;border-radius:12px;margin-bottom:12px;border:1px solid rgba(140,197,164,.35);background:rgba(140,197,164,.08);color:var(--ivory)}.flash.error{border-color:rgba(227,133,122,.4);background:rgba(227,133,122,.08)}\ndl.kv{display:grid;grid-template-columns:190px 1fr;gap:12px 20px;margin:0}dl.kv dt{color:var(--muted);font-size:12px;letter-spacing:.08em;text-transform:uppercase}dl.kv dd{margin:0;color:var(--ivory)}\n.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:18px}\ndetails summary{cursor:pointer}\n.page-head{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;margin-bottom:22px}\n@media (max-width:760px){header.top{padding:0 16px}.top-in{gap:8px;padding:12px 0 0;min-height:0;flex-wrap:wrap}.brand .mark{width:28px;height:28px}.brand b{font-size:12px;letter-spacing:.16em}.brand small{display:none}.top-in{flex-wrap:wrap}.who{gap:8px}.who button{padding:5px 10px}nav.main{order:3;flex-basis:100%;flex-wrap:nowrap;overflow-x:auto;padding-bottom:2px}\nnav.main a{white-space:nowrap;padding:8px 10px;font-size:12px}.who{margin-left:auto}.who>span{display:none}td{white-space:nowrap}\nmain{padding:24px 16px 64px}dl.kv{grid-template-columns:1fr}dl.kv dt{margin-top:8px}h1{font-size:30px}h2{font-size:22px}.hide-m{display:none}}\n</style>{% block head %}{% endblock %}</head><body>\n{% if g.user %}<header class="top"><div class="top-in">\n<a class="brand" href="{{ url_for(\'dashboard\') }}"><img class="mark" src="{{ LOGO }}" alt="Cevheri"><span><b>{{ COMPANY }}</b><small>Uçuş Kayıt ve Takip</small></span></a>\n<nav class="main">{% set ep = request.endpoint %}\n<a href="{{ url_for(\'dashboard\') }}" class="{{ \'on\' if ep==\'dashboard\' }}">Genel Bakış</a>\n<a href="{{ url_for(\'flights\') }}" class="{{ \'on\' if ep in (\'flights\',\'flight_detail\',\'flight_edit\') }}">{{ \'Uçuşlarım\' if g.user.role==\'pilot\' else \'Uçuşlar\' }}</a>\n<a href="{{ url_for(\'flight_new\') }}" class="{{ \'on\' if ep==\'flight_new\' }}">Uçuş kaydı</a>\n{% if g.user.role != \'pilot\' %}<a href="{{ url_for(\'approvals\') }}" class="{{ \'on\' if ep==\'approvals\' }}">Onaylar{% if pending_count() %}<span class="badge">{{ pending_count() }}</span>{% endif %}</a>{% endif %}\n<a href="{{ url_for(\'fleet\') }}" class="{{ \'on\' if ep==\'fleet\' }}">Filo</a>\n<a href="{{ url_for(\'maintenance\') }}" class="{{ \'on\' if ep==\'maintenance\' }}">Bakım</a>\n{% if g.user.role==\'yonetici\' %}<a href="{{ url_for(\'users\') }}" class="{{ \'on\' if ep==\'users\' }}">Kullanıcılar</a><a href="{{ url_for(\'audit\') }}" class="{{ \'on\' if ep==\'audit\' }}">Geçmiş</a>{% endif %}\n</nav>\n<div class="who"><span><a href="{{ url_for(\'password\') }}">{{ g.user.full_name }}</a> · {{ ROLES[g.user.role] }}</span>\n<form method="post" action="{{ url_for(\'logout\') }}"><input type="hidden" name="csrf" value="{{ csrf_token() }}"><button>Çıkış</button></form></div>\n</div></header>{% endif %}\n{% block full %}<main>{% for cat, m in get_flashed_messages(with_categories=true) %}<div class="flash {{ cat }}">{{ m }}</div>{% endfor %}\n{% block body %}{% endblock %}</main>{% endblock %}</body></html>'

TEMPLATES["login.html"] = r"""{% extends "base.html" %}{% block title %}{{ T("Giriş") }}{% endblock %}{% block head %}<style>
.auth{position:relative;min-height:100vh;overflow:hidden;background:#142143;color:#fff;isolation:isolate}
.auth::before{content:"";position:absolute;inset:0;z-index:-1;background:radial-gradient(900px 560px at 50% 45%,rgba(71,159,237,.18),transparent 70%)}
.paths{position:absolute;inset:0;z-index:0;pointer-events:none;color:#8DC4F4;
  -webkit-mask-image:linear-gradient(to bottom,transparent,#000 14%,#000 86%,transparent);mask-image:linear-gradient(to bottom,transparent,#000 14%,#000 86%,transparent)}
.paths canvas{width:100%;height:100%;display:block;opacity:0;transition:opacity .6s ease-out}
.auth-card{position:relative}.auth-card .lang{position:absolute;top:18px;right:18px}.auth-logo{display:block;height:64px;width:auto;margin:0 0 26px}
.auth-top{position:relative;z-index:2;display:flex;justify-content:space-between;align-items:center;padding:32px 56px}
.auth-main{position:relative;z-index:2;min-height:calc(100vh - 90px);display:grid;grid-template-columns:1.15fr minmax(340px,420px);gap:64px;align-items:center;max-width:1280px;margin:0 auto;padding:48px 56px 40px}
.auth-copy h2{font:600 56px/1.08 var(--serif);letter-spacing:-.01em;margin:16px 0 20px;max-width:620px}
.auth-copy h2 em{font-style:normal;font-weight:600;background:linear-gradient(90deg,#8DC4F4,#479FED);-webkit-background-clip:text;background-clip:text;color:transparent}
.auth-copy p{max-width:460px;color:rgba(255,255,255,.62);font-size:16px;margin:0}
.auth-card{background:rgba(16,27,57,.72);backdrop-filter:blur(18px) saturate(120%);-webkit-backdrop-filter:blur(18px) saturate(120%);
  border:1px solid rgba(255,255,255,.12);border-radius:14px;padding:36px 32px;box-shadow:0 30px 80px -20px rgba(0,0,0,.7),inset 0 1px 0 rgba(255,255,255,.06)}
.auth-card h1{font-size:30px;margin:10px 0 4px}.auth-card form{margin-top:26px;display:grid;gap:18px}
.auth-card .btn{width:100%;padding:14px;margin-top:4px}
.auth-card input{background:rgba(255,255,255,.04)}
.demo{margin-top:22px;padding:14px 16px;border:1px solid rgba(255,255,255,.1);background:rgba(255,255,255,.03);border-radius:10px;font-size:13px;color:var(--muted)}
.demo b{display:block;font-size:10px;letter-spacing:.28em;text-transform:uppercase;color:var(--gold);margin-bottom:6px;font-weight:600}
.demo table td{padding:3px 0;border:0;font-size:13px;background:none!important}.demo code{color:#fff;font-family:inherit}
.auth-foot{position:relative;z-index:2;display:flex;justify-content:space-between;gap:24px;padding:0 56px 32px;font-size:11px;letter-spacing:.24em;text-transform:uppercase;color:rgba(255,255,255,.45)}
.auth-foot span+span{margin-left:28px}
/* giriş animasyonu: içerik sırayla, yumuşak bir yükselişle gelir */
.rise{opacity:0;transform:translateY(14px);animation:rise .8s cubic-bezier(.22,1,.36,1) forwards;animation-delay:calc(var(--i,0) * 90ms + 250ms)}
@keyframes rise{to{opacity:1;transform:none}}
.flyby{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
.fb-plane{position:absolute;left:0;top:0;width:26px;height:22px;margin:-11px 0 0 -13px;opacity:0;pointer-events:none;will-change:transform,opacity;filter:drop-shadow(0 0 8px rgba(141,196,244,.9))}
.fb-plane svg{width:100%;height:100%;display:block}.fb-trail{position:absolute;height:1.5px;border-radius:2px;pointer-events:none;background:linear-gradient(90deg,rgba(141,196,244,0),rgba(216,227,253,.55));transform-origin:100% 50%}
@media (prefers-reduced-motion:reduce),(max-width:960px){.fb-plane,.fb-trail{display:none}}
@media (prefers-reduced-motion:reduce){.rise{animation:none;opacity:1;transform:none}.paths canvas{transition:none}}
@media (max-width:960px){.auth-main{grid-template-columns:1fr;gap:32px;padding:36px 20px 32px;min-height:0}.auth-top{padding:22px 20px}
  .auth-copy h2{font-size:36px}.auth-foot{padding:0 20px 24px;flex-direction:column;gap:8px}.auth-card{padding:28px 22px}}
</style>{% endblock %}
{% block full %}<div class="auth" id="auth">
<!-- Akan çizgiler: Kokonut UI "Background Paths" (MIT, kokonutui.com · 21st.dev) bileşeninin düz JavaScript uyarlaması -->
<div class="paths" aria-hidden="true"><canvas id="paths"></canvas></div>
<svg class="flyby" aria-hidden="true" viewBox="0 0 1000 600" preserveAspectRatio="none"><path id="fbp" d="M-60 190C150 170 380 110 640 95S960 50 1080 20" fill="none"/></svg>
<div class="fb-plane" aria-hidden="true"><svg viewBox="-12 -10 24 20"><path d="M11 0C11-1 10-1.4 8-1.4L3-1.4-3-9-5.5-9-2-1.4-7-1.4-9.5-4.5-11-4.5-9.5 0-11 4.5-9.5 4.5-7 1.4-2 1.4-5.5 9-3 9 3 1.4 8 1.4C10 1.4 11 1 11 0Z" fill="#fff"/></svg></div>
<main class="auth-main">
<section class="auth-copy"><img class="auth-logo rise" style="--i:0" src="{{ LOGO }}" alt="{{ COMPANY }}"><div class="eyebrow rise" style="--i:1">{{ COMPANY }}</div>
<h2 class="rise" style="--i:2">Gökyüzünde <em>zamansız</em> bir ayrıcalık.</h2>
<p class="rise" style="--i:3">Filo, uçuş programı ve bakım takibi tek ekranda. Ekibinizin her uçuşu, kalkıştan inişe kadar kayıt altında.</p></section>
<section class="auth-card rise" style="--i:3">
<a class="lang" href="{{ lang_url() }}" title="Türkçe / English">{{ "EN" if LANG == "tr" else "TR" }}</a>
{% for cat, m in get_flashed_messages(with_categories=true) %}<div class="flash {{ cat }}">{{ T(m) }}</div>{% endfor %}
<div class="eyebrow">Ekip girişi</div><h1>Hoş geldiniz</h1><p class="muted" style="margin:0">Uçuş Kayıt ve Takip Sistemi</p>
<form method="post"><input type="hidden" name="csrf" value="{{ csrf_token() }}">
<label>Kullanıcı adı<input name="username" autocomplete="username" required autofocus></label>
<label>Şifre<input type="password" name="password" autocomplete="current-password" required></label>
<button class="btn">Giriş yap</button></form>
{% if demo_hint %}<div class="demo"><b>Deneme hesapları</b><table>
<tr><td>Yönetici</td><td><code>yonetici</code></td><td><code>Yonetici123!</code></td></tr>
<tr><td>Koordinatör</td><td><code>koordinator</code></td><td><code>Koordinator123!</code></td></tr>
<tr><td>Pilot</td><td><code>pilot.deniz</code></td><td><code>Pilot123!</code></td></tr></table></div>{% endif %}
</section></main>
<footer class="auth-foot rise" style="--i:4"><div><span>İstanbul</span><span>Cenevre</span><span>Paris</span><span>Londra</span></div><div>© {{ COMPANY }}</div></footer>
</div>
<script>
/* Background Paths — Kokonut UI (@dorianbaffier), MIT License, https://kokonutui.com · düz JavaScript uyarlaması */
(function () {
  var root = document.getElementById('auth'), canvas = document.getElementById('paths'), ctx = canvas && canvas.getContext('2d');
  if (!ctx) return;
  var SAMPLES = 64, OVERSCAN = 0.06, DRAW_MS = 1600, STAGGER = 40, PART_R = 150, PART_PUSH = 56;
  var LAYERS = [{w: 1, o: .16, ph: .6, pace: .7, part: .45}, {w: 1.25, o: .26, ph: .3, pace: .85, part: .75}, {w: 1.5, o: .42, ph: 0, pace: 1, part: 1}];
  var COUNT = 42, SPREAD = 1, ANGLE = -8, SPEED = 0.8;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var shape = {slope: Math.tan(ANGLE * Math.PI / 180), interactive: !reduce};
  var per = Math.max(1, Math.round(COUNT / LAYERS.length));
  var f = {w: 0, h: 0, t: 40, drawn: new Array(per * LAYERS.length).fill(reduce ? 1 : 0), p: {x: 0, y: 0, a: 0, on: false}};
  var color = '#8DC4F4', start = 0, last = 0, raf = 0, visible = true;
  var xs = new Float32Array(SAMPLES + 1), ys = new Float32Array(SAMPLES + 1);
  function lineY(s, u, L, band) {
    var t = f.t * L.pace, x = u * f.w;
    var center = f.h * .5 + shape.slope * (x - f.w / 2) + band * .1 * Math.sin(Math.PI * 2 * (.75 * u + .1) + L.ph + t * .35);
    var turn = .22 + .09 * Math.sin(t * .21 + L.ph), breathe = .3 * Math.sin(t * .5 + s * 4 + L.ph);
    return center + s * SPREAD * band * Math.cos(Math.PI * (u - turn) + s * (.6 + breathe) + L.ph);
  }
  function part(x, y, k) {
    if (f.p.a < .001) return y;
    var dx = x - f.p.x, dy = y - f.p.y, fall = Math.exp(-(dx * dx + dy * dy) / (PART_R * PART_R));
    return y + dy / (Math.abs(dy) + 24) * fall * PART_PUSH * k * f.p.a;
  }
  function paint() {
    ctx.clearRect(0, 0, f.w, f.h); ctx.strokeStyle = color; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    var band = Math.min(f.h, f.w * 1.1);
    LAYERS.forEach(function (L, li) {
      ctx.lineWidth = L.w;
      for (var i = 0; i < per; i++) {
        var d = f.drawn[li * per + i]; if (d <= 0) continue;
        var s = per === 1 ? 0 : i / (per - 1) - .5, end = Math.max(1, Math.ceil(SAMPLES * d));
        for (var k = 0; k <= end; k++) { var u = -OVERSCAN + k / SAMPLES * (1 + OVERSCAN * 2), x = u * f.w, y = lineY(s, u, L, band); xs[k] = x; ys[k] = shape.interactive ? part(x, y, L.part) : y; }
        ctx.globalAlpha = L.o * (.45 + .55 * (1 - Math.abs(s) * 2));
        ctx.beginPath(); ctx.moveTo(xs[0], ys[0]);
        for (k = 1; k < end; k++) ctx.quadraticCurveTo(xs[k], ys[k], (xs[k] + xs[k + 1]) / 2, (ys[k] + ys[k + 1]) / 2);
        ctx.lineTo(xs[end], ys[end]); ctx.stroke();
      }
    });
    ctx.globalAlpha = 1;
  }
  function resize() {
    var r = canvas.getBoundingClientRect(), dpr = Math.min(window.devicePixelRatio || 1, 2);
    f.w = r.width; f.h = r.height; canvas.width = Math.round(r.width * dpr); canvas.height = Math.round(r.height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); paint();
  }
  var ease = function (t) { return 1 - Math.pow(1 - t, 3); };
  function loop(now) {
    raf = 0; if (!start) { start = now; last = now; }
    var dt = Math.min((now - last) / 1000, .05); last = now; f.t += dt * SPEED;
    var el = now - start;
    for (var i = 0; i < f.drawn.length; i++) if (f.drawn[i] < 1) f.drawn[i] = ease(Math.min(Math.max((el - (i % per) * STAGGER) / DRAW_MS, 0), 1));
    f.p.a += ((f.p.on ? 1 : 0) - f.p.a) * .08; paint();
    if (visible) raf = requestAnimationFrame(loop);
  }
  function play() { if (!raf && visible && !reduce) { last = performance.now(); raf = requestAnimationFrame(loop); } }
  resize(); canvas.style.opacity = '1';
  new ResizeObserver(resize).observe(canvas);
  document.addEventListener('visibilitychange', function () { visible = !document.hidden; if (visible) play(); });
  root.addEventListener('pointermove', function (e) { if (e.pointerType !== 'mouse' || !shape.interactive) return; var r = canvas.getBoundingClientRect(); f.p.x = e.clientX - r.left; f.p.y = e.clientY - r.top; f.p.on = true; play(); });
  root.addEventListener('pointerleave', function () { f.p.on = false; play(); });
  play();
})();

/* Süzülen jet: rotası boyunca ease-in-out uçar, iz bırakır, 7 sn ara verir */
(function () {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  var root = document.getElementById('auth'), path = document.getElementById('fbp'), pl = document.querySelector('.fb-plane');
  if (!root || !path || !pl) return;
  var svg = path.ownerSVGElement, L = path.getTotalLength(), TR = 18, trail = [];
  for (var i = 0; i < TR; i++) { var d = document.createElement('i'); d.className = 'fb-trail'; root.appendChild(d); trail.push({ el: d, x: 0, y: 0 }); }
  var hist = [], D = 9000, GAP = 7000, t0 = 0;
  function pt(f) { var p = path.getPointAtLength(f * L), r = svg.getBoundingClientRect(), a = root.getBoundingClientRect();
    return { x: r.left - a.left + p.x / 1000 * r.width, y: r.top - a.top + p.y / 600 * r.height }; }
  function ease(t) { return t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }
  function frame(ts) {
    if (!t0) t0 = ts;
    var k = (ts - t0) % (D + GAP), t = Math.min(1, k / D), f = ease(t);
    var a = pt(f), b = pt(Math.min(1, f + 0.002)); if (f >= 0.998) b = { x: a.x + (a.x - pt(f - 0.002).x), y: a.y + (a.y - pt(f - 0.002).y) };
    var ang = Math.atan2(b.y - a.y, b.x - a.x), vis = k < D ? Math.min(1, t * 8, (1 - t) * 8) : 0;
    pl.style.opacity = vis.toFixed(2);
    pl.style.transform = 'translate(' + a.x.toFixed(1) + 'px,' + a.y.toFixed(1) + 'px) rotate(' + (ang * 57.3).toFixed(1) + 'deg)';
    hist.unshift(a); if (hist.length > TR * 3 + 1) hist.pop();
    for (var i = 0; i < TR; i++) {
      var p = hist[i * 3], q = hist[i * 3 + 3], el = trail[i].el;
      if (!p || !q || !vis) { el.style.opacity = 0; continue; }
      var dx = p.x - q.x, dy = p.y - q.y, len = Math.hypot(dx, dy);
      el.style.width = len.toFixed(1) + 'px'; el.style.left = (p.x - len).toFixed(1) + 'px'; el.style.top = p.y.toFixed(1) + 'px';
      el.style.transform = 'rotate(' + (Math.atan2(dy, dx) * 57.3).toFixed(1) + 'deg)'; el.style.opacity = (vis * (1 - i / TR) * .9).toFixed(2);
    }
    requestAnimationFrame(frame);
  }
  setTimeout(function () { requestAnimationFrame(frame); }, 1200);
})();
</script>{% endblock %}
"""

TEMPLATES["password.html"] = r"""{% extends "base.html" %}{% block body %}<h1>Şifre değiştir</h1>
<form method="post" class="sheet" style="max-width:420px"><input type="hidden" name="csrf" value="{{ csrf_token() }}">
<label>Mevcut şifre<input type="password" name="old" required></label><br><label>Yeni şifre (en az 8 karakter)<input type="password" name="new" minlength="8" required></label><br>
<button class="btn">Kaydet</button></form>{% endblock %}"""

TEMPLATES["dashboard.html"] = '{% extends "base.html" %}{% block head %}<meta http-equiv="refresh" content="60">\n<style>.hero{position:relative;margin:-40px calc(50% - 50vw) 36px;padding:48px 32px 40px;border-bottom:1px solid var(--line);\nbackground:radial-gradient(760px 380px at 72% 18%,rgba(71,159,237,.22),transparent 70%),linear-gradient(180deg,#17264D,#142143)}\n.hero-in{max-width:1216px;margin:0 auto;position:relative}\n.track{position:absolute;right:-6px;top:-30px;width:400px;pointer-events:none}@media (max-width:1100px){.track{display:none}}.track svg{width:100%;display:block;overflow:visible}\n.track .rt{stroke:rgba(141,196,244,.35);stroke-width:1.2;stroke-dasharray:2 7;animation:flow 1.6s linear infinite}\n.track .trail{stroke:url(#trg);stroke-width:2;stroke-linecap:round;stroke-dasharray:0 9999}\n.track .ap circle{fill:#8DC4F4}.track .ap .pulse{fill:none;stroke:#8DC4F4;stroke-width:1;transform-box:fill-box;transform-origin:center;animation:ping 2.4s cubic-bezier(.22,1,.36,1) infinite}\n.track .dest .pulse{animation-delay:1.2s}.track text{font:600 11px var(--sans);letter-spacing:.2em;fill:#D8E3FD}\n.track #pl{filter:drop-shadow(0 0 6px rgba(141,196,244,.8))}\n.track .cap{position:absolute;right:28px;top:2px;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}.track .cap b{color:#fff;font-weight:600}\n.track.live .cap span:first-of-type{color:#8DC4F4}\n@keyframes flow{to{stroke-dashoffset:-18}}@keyframes ping{0%{transform:scale(.4);opacity:.9}100%{transform:scale(2.2);opacity:0}}\n@media (prefers-reduced-motion:reduce){.track .rt,.track .ap .pulse{animation:none}}\n.hero h1{font-size:44px;margin:12px 0 6px;max-width:780px;letter-spacing:.01em}.hero .muted{font-size:14px}\n.now{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px;margin:32px 0 30px}\n.now a{display:grid;grid-template-columns:auto 1fr;column-gap:12px;row-gap:4px;padding:16px 18px;border:1px solid var(--line);border-radius:var(--r);\nbackground:rgba(255,255,255,.05);backdrop-filter:blur(8px);color:var(--text);transition:border-color .2s}\n.now a:hover{border-color:rgba(255,255,255,.3);background:rgba(255,255,255,.08)}.dot{width:8px;height:8px;border-radius:50%;margin-top:9px;background:var(--muted);box-shadow:0 0 12px currentColor}\n.t-ok .dot{background:var(--ok);color:var(--ok)}.t-busy .dot{background:var(--busy);color:var(--busy)}.t-warn .dot{background:var(--warn);color:var(--warn)}.t-bad .dot{background:var(--bad);color:var(--bad)}\n.now .reg{font:600 17px/1.2 var(--serif);color:var(--ivory);letter-spacing:.1em}.now em{display:block;font-style:normal;font-size:11px;letter-spacing:.2em;text-transform:uppercase;margin-top:2px}\n.t-ok em{color:var(--ok)}.t-busy em{color:var(--busy)}.t-warn em{color:var(--warn)}.t-bad em{color:var(--bad)}.t-none em{color:var(--muted)}\n.now small{grid-column:2;color:var(--muted);font-size:12.5px;line-height:1.45}\n.tl{overflow-x:auto;border:1px solid var(--line);border-radius:var(--r);background:rgba(255,255,255,.03);padding:16px 18px}\n.tl table{min-width:820px;border-collapse:separate;border-spacing:3px}.tl th,.tl td{border:0;padding:0;text-align:center;background:none}\n.tl th{font-size:10px;font-weight:500;color:var(--muted);letter-spacing:.14em;padding-bottom:6px}.tl th b{display:block;font:600 14px/1.4 var(--serif);color:var(--ivory);letter-spacing:0}\n.tl th.today b{color:var(--gold2)}.tl th.today{color:var(--gold)}\n.tl td.lab{text-align:left;padding-right:16px;white-space:nowrap;font:600 13px/1.3 var(--serif);color:var(--ivory);letter-spacing:.1em}\n.tl td.lab span{display:block;font:400 11px var(--sans);color:var(--muted);letter-spacing:.04em}\n.tl td.c{vertical-align:middle;height:30px;min-width:34px;border-radius:4px;background:rgba(255,255,255,.05);font-size:10px;font-weight:600;letter-spacing:.06em;color:#0B0F19}\n.tl td.c.today{box-shadow:inset 0 0 0 1px rgba(255,255,255,.7)}\n.legend{display:flex;flex-wrap:wrap;gap:8px 20px;font-size:12px;color:var(--muted);margin-top:14px}.legend i{display:inline-block;width:14px;height:8px;border-radius:2px;margin-right:6px;vertical-align:1px}\n.figs{display:flex;gap:0;margin-top:28px;border-top:1px solid var(--line)}.figs div{padding:18px 40px 0 0;margin-right:40px;border-right:1px solid var(--line2)}.figs div:last-child{border:0}\n.figs b{display:block;font:600 38px/1.1 var(--serif);color:#fff}.figs span{font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:var(--muted)}\n@media (max-width:760px){.hero{margin:-24px calc(50% - 50vw) 24px;padding:28px 16px}.hero h1{font-size:32px}.track{display:none}\n.now{grid-template-columns:1fr;gap:8px;margin:20px 0}.figs div{padding-right:16px;margin-right:16px}.figs b{font-size:32px}}</style>{% endblock %}\n{% block body %}<div class="hero"><div class="hero-in">{% if track %}<div class="track{{ \' live\' if track.live }}" data-p="{{ track.p }}" aria-hidden="true"><svg viewBox="0 0 440 190" fill="none"><defs><linearGradient id="trg" x1="0" x2="1"><stop offset="0" stop-color="#8DC4F4" stop-opacity="0"/><stop offset="1" stop-color="#FFFFFF"/></linearGradient></defs><path id="rt" class="rt" d="M40 146Q220 4 400 128"/><path id="trail" class="trail" d="M40 146Q220 4 400 128"/><g class="ap"><circle class="pulse" cx="40" cy="146" r="9"/><circle cx="40" cy="146" r="3.5"/></g><g class="ap dest"><circle class="pulse" cx="400" cy="128" r="9"/><circle cx="400" cy="128" r="3.5"/></g><g id="pl"><path d="M11 0C11-1 10-1.4 8-1.4L3-1.4-3-9-5.5-9-2-1.4-7-1.4-9.5-4.5-11-4.5-9.5 0-11 4.5-9.5 4.5-7 1.4-2 1.4-5.5 9-3 9 3 1.4 8 1.4C10 1.4 11 1 11 0Z" fill="#FFFFFF"/></g><text x="40" y="174" text-anchor="middle">{{ track.dep }}</text><text x="400" y="156" text-anchor="middle">{{ track.arr }}</text></svg><div class="cap"><b>{{ track.reg }}</b> · {% if track.live %}<span>Canlı uçuş</span> · <span>Tahmini iniş</span> {{ track.eta }}{% else %}<span>Sıradaki kalkış</span> {{ track.eta }}{% endif %}</div></div>{% endif %}\n<div class="eyebrow">{{ now.day }} {{ MONTHS[now.month-1] }} {{ now.year }} · {{ DAYS[now.weekday()] }} · {{ now.strftime(\'%H:%M\') }}</div>\n<h1>{{ lede }}</h1><div class="muted">Durum anlık hesaplanır, sayfa her dakika yenilenir.</div>\n<div class="now">{% for a, s in states %}<a class="t-{{ s.tone or \'none\' }}" href="{{ url_for(\'fleet\') }}#ac{{ a.id }}"><i class="dot"></i>\n<span><span class="reg">{{ a.reg }}</span><em>{{ s.label }}</em></span><small>{{ s.detail }}</small></a>{% endfor %}</div>\n<div class="tl"><table><tr><th></th>{% for d in days %}<th class="{{ \'today\' if loop.first }}">{{ DAYS[d.weekday()] }}<b>{{ d.day }}</b></th>{% endfor %}</tr>\n{% for a, cells in grid %}<tr><td class="lab">{{ a.reg }}<span>{{ a.type }}</span></td>\n{% for code, tip in cells %}<td class="c{{ \' today\' if loop.first }}" title="{{ a.reg }} · {{ days[loop.index0].strftime(\'%d.%m\') }}: {{ tip }}"{% if code %} style="background:{{ CODE_COLORS.get(code, \'#8B92A3\') }}"{% endif %}>{{ \'\' if code==\'PEND\' else code }}</td>{% endfor %}</tr>{% endfor %}\n</table>\n<div class="legend">{% for c, l in [(\'FLT\',\'Uçuş\'),(\'T\',\'Eğitim\'),(\'F\',\'Ferry\'),(\'M\',\'Bakım\'),(\'AOG\',\'AOG\'),(\'RON\',\'Konaklama\'),(\'RES\',\'Yedek\'),(\'PEND\',\'Onay bekleyen\')] %}<span><i style="background:{{ CODE_COLORS[c] }}"></i>{{ l }}</span>{% endfor %}<span>Bugünün sütunu anlık durumu gösterir; müsait uçakta boştur.</span></div></div>\n<div class="figs"><div><b>{{ done_year }}</b><span>Bu yıl tamamlanan</span></div><div><b>{{ planned }}</b><span>Planlı uçuş</span></div>\n{% if g.user.role!=\'pilot\' %}<div><b>{{ pending }}</b><span>Onay bekleyen</span></div>{% endif %}</div>\n</div></div>\n<div class="page-head"><div><div class="eyebrow">Program</div><h2 style="margin:6px 0 0">{{ \'Sıradaki uçuşlarım\' if g.user.role==\'pilot\' else \'Sıradaki uçuşlar\' }}</h2></div><a class="btn" href="{{ url_for(\'flight_new\') }}">+ Uçuş kaydı oluştur</a></div>\n{% if upcoming %}<div class="tbl"><table><tr><th>Tarih</th><th>Uçak</th><th>Rota</th><th class="hide-m">Pilot</th><th class="hide-m">Görev</th><th>Durum</th></tr>\n{% for f in upcoming %}{% set st = flight_status(f, now) %}<tr><td><a href="{{ url_for(\'flight_detail\', fid=f.id) }}">{{ f.flight_date }}</a><span class="sub">{{ f.dep_time }} – {{ f.arr_time }}</span></td>\n<td><span style="font:600 13px var(--serif);color:var(--ivory);letter-spacing:.1em">{{ f.reg }}</span><span class="sub">{{ f.type }}</span></td><td>{{ short_ap(f.dep) }} <span style="color:var(--gold)">→</span> {{ short_ap(f.arr) }}</td><td class="hide-m">{{ f.pilot or \'—\' }}</td><td class="hide-m">{{ f.mission }}</td>\n<td><span class="st {{ st.split()[0] }}">{{ st }}</span></td></tr>{% endfor %}</table></div>\n{% else %}<p class="muted">Yaklaşan uçuş yok.</p>{% endif %}<script>(function(){var w=document.querySelector(".track");if(!w)return;var p=w.querySelector("#rt"),pl=w.querySelector("#pl"),tr=w.querySelector("#trail"),L=p.getTotalLength(),to=+w.dataset.p||0;function put(f){var a=p.getPointAtLength(f*L),b=p.getPointAtLength(Math.min(L,f*L+1)),c=f*L+1>L?p.getPointAtLength(L-1):a;if(f*L+1>L){b=a;a=c}pl.setAttribute("transform","translate("+b.x.toFixed(1)+","+b.y.toFixed(1)+") rotate("+(Math.atan2(b.y-a.y,b.x-a.x)*57.3).toFixed(1)+")");tr.style.strokeDasharray=(f*L).toFixed(1)+" 9999"}var nav=(performance.getEntriesByType&&performance.getEntriesByType("navigation")[0])||{};if(matchMedia("(prefers-reduced-motion: reduce)").matches||nav.type==="reload"||!to){put(to);return}var t0=0,D=2200,e=function(t){return t<.5?4*t*t*t:1-Math.pow(-2*t+2,3)/2};put(0);requestAnimationFrame(function st(ts){t0=t0||ts;var k=Math.min(1,(ts-t0)/D);put(to*e(k));if(k<1)requestAnimationFrame(st)})})();</script>{% endblock %}'

TEMPLATES["flights.html"] = r"""{% extends "base.html" %}{% block body %}
<div class="row" style="justify-content:space-between"><h1>{{ 'Uçuşlarım' if g.user.role=='pilot' else 'Uçuşlar' }}</h1>
<div class="row">{% if g.user.role!='pilot' %}<a class="btn ghost" href="{{ url_for('flights_csv') }}">Excel'e aktar (CSV)</a>{% endif %}<a class="btn" href="{{ url_for('flight_new') }}">+ Uçuş kaydı oluştur</a></div></div>
<form class="grid sheet" method="get" style="margin:14px 0">
<label>Başlangıç<input type="date" name="from" value="{{ filters.get('from','') }}"></label><label>Bitiş<input type="date" name="to" value="{{ filters.get('to','') }}"></label>
<label>Uçak<select name="ac"><option value="">Tümü</option>{% for a in fleet %}<option value="{{ a.id }}" {{ 'selected' if filters.get('ac')==a.id|string }}>{{ a.reg }} {{ a.type }}</option>{% endfor %}</select></label>
<label>Durum<select name="status"><option value="">Tümü</option>{% for s in ['Planlı','Uçuşta','Tamamlandı','Onay bekliyor','Reddedildi','İptal'] %}<option {{ 'selected' if filters.get('status')==s }}>{{ s }}</option>{% endfor %}</select></label>
<div style="align-self:end" class="row"><button class="btn">Filtrele</button><a href="{{ url_for('flights') }}">Temizle</a></div></form>
<div class="tbl"><table><tr><th>Kod</th><th>Tarih / saat</th><th>Uçak</th><th>Rota</th><th class="hide-m">Pilot</th><th class="hide-m">Görev</th><th class="hide-m">Yolcu</th><th>Durum</th></tr>
{% for f, st in rows %}<tr><td><a href="{{ url_for('flight_detail', fid=f.id) }}">{{ f.code or ('#'~f.id) }}</a></td>
<td>{{ f.flight_date }}<span class="sub">{{ f.dep_time }}–{{ f.arr_time }} · {{ duration_text(f) }}</span></td><td>{{ f.reg }}<span class="sub">{{ f.type }}</span></td>
<td>{{ short_ap(f.dep) }} → {{ short_ap(f.arr) }}</td><td class="hide-m">{{ f.pilot or '—' }}</td><td class="hide-m">{{ f.mission }}</td><td class="hide-m">{{ f.pax }}</td>
<td><span class="st {{ st.split()[0] }}">{{ st }}</span></td></tr>{% else %}<tr><td colspan="8" class="muted">Kayıt yok.</td></tr>{% endfor %}</table></div>{% endblock %}"""

TEMPLATES["flight_form.html"] = r"""{% extends "base.html" %}{% block body %}
<div class="eyebrow">Uçuş kaydı</div><h1>{{ 'Yeni uçuş kaydı' if mode=='new' else 'Uçuş kaydını düzenle' }}</h1>
<p class="muted">{% if g.user.role=='pilot' %}Kaydınız koordinatör onayına gider; onaylanınca programa ve uçak durumuna yansır.{% else %}Koordinatör ve yönetici kayıtları doğrudan onaylı olarak programa girer.{% endif %}
Saatler yerel saattir; iniş kalkıştan önceyse ertesi gün sayılır. Aynı uçak ya da pilotla çakışan uçuş ve bakımdaki uçak kabul edilmez.</p>
<form method="post" class="grid sheet"><input type="hidden" name="csrf" value="{{ csrf_token() }}">
<label>Tarih<input type="date" name="flight_date" value="{{ f.flight_date if f else '' }}" required></label>
<label>Uçak<select name="aircraft_id" required><option value="">Seçin</option>{% for a in fleet %}<option value="{{ a.id }}" {{ 'selected' if f and f.aircraft_id|string==a.id|string }}>{{ a.reg }} · {{ a.type }} ({{ a.seats }} koltuk)</option>{% endfor %}</select></label>
{% if g.user.role!='pilot' %}<label>Kaptan pilot<select name="pic_id" required><option value="">Seçin</option>{% for p in pilots %}<option value="{{ p.id }}" {{ 'selected' if f and f.pic_id|string==p.id|string }}>{{ p.full_name }} · {{ p.title }}</option>{% endfor %}</select></label>
{% else %}<label>Kaptan pilot<input value="{{ g.user.full_name }}" disabled></label>{% endif %}
<label>Ekip (diğer)<input name="crew" value="{{ f.crew if f else '' }}" placeholder="F/O, kabin ekibi"></label>
<label>Kalkış meydanı<input name="dep" list="aps" value="{{ f.dep if f else '' }}" required></label>
<label>Kalkış saati (yerel)<input type="time" name="dep_time" value="{{ f.dep_time if f else '' }}" required></label>
<label>İniş meydanı<input name="arr" list="aps" value="{{ f.arr if f else '' }}" required></label>
<label>İniş saati (yerel)<input type="time" name="arr_time" value="{{ f.arr_time if f else '' }}" required></label>
<label>Görev<select name="mission" required>{% for m in MISSIONS %}<option {{ 'selected' if f and f.mission==m }}>{{ m }}</option>{% endfor %}</select></label>
<label>Yolcu sayısı<input type="number" name="pax" min="0" value="{{ f.pax if f and f.pax is not none else 0 }}"></label>
<label>Uçuş kodu (boşsa otomatik)<input name="code" value="{{ f.code if f and f.code else '' }}"></label>
<label class="full">Not<textarea name="note">{{ f.note if f and f.note else '' }}</textarea></label>
<div class="full row"><button class="btn">{{ 'Kaydı oluştur' if mode=='new' else 'Kaydet' }}</button><a href="{{ url_for('flights') }}">Vazgeç</a></div>
<datalist id="aps">{% for ap in AIRPORTS %}<option value="{{ ap }}">{% endfor %}</datalist></form>{% endblock %}"""

TEMPLATES["flight_detail.html"] = r"""{% extends "base.html" %}{% block body %}
<div class="row" style="justify-content:space-between"><h1>{{ f.code or ('Uçuş #'~f.id) }} · {{ short_ap(f.dep) }} → {{ short_ap(f.arr) }}</h1><span class="st {{ status.split()[0] }}">{{ status }}</span></div>
<div class="sheet"><dl class="kv">
<dt>Tarih</dt><dd>{{ f.flight_date }}, {{ f.dep_time }} – {{ f.arr_time }} (yerel) · {{ duration }}</dd>
<dt>Uçak</dt><dd>{{ f.reg }} · {{ f.type }}</dd><dt>Kaptan pilot</dt><dd>{{ f.pilot or '—' }}</dd><dt>Ekip</dt><dd>{{ f.crew or '—' }}</dd>
<dt>Kalkış</dt><dd>{{ f.dep }}</dd><dt>İniş</dt><dd>{{ f.arr }}</dd><dt>Görev</dt><dd>{{ f.mission }}</dd><dt>Yolcu</dt><dd>{{ f.pax }}</dd>
<dt>Not</dt><dd>{{ f.note or '—' }}</dd><dt>Oluşturan</dt><dd>{{ f.creator }} · {{ f.created_at }}</dd>
{% if decider %}<dt>Karar</dt><dd>{{ decider.full_name }} · {{ f.decided_at }}{% if f.decision_note %}<span class="sub">{{ f.decision_note }}</span>{% endif %}</dd>{% endif %}
</dl></div>
<div class="row" style="margin-top:16px">{% if can_edit %}<a class="btn ghost" href="{{ url_for('flight_edit', fid=f.id) }}">Düzenle</a>{% endif %}<a href="{{ url_for('flights') }}">Listeye dön</a></div>
<div class="page-head" style="margin:36px 0 14px"><div><div class="eyebrow">Maliyet</div><h2 style="margin:6px 0 0">Uçuş masrafları</h2></div>
{% if not f.cancelled %}<a class="btn" href="{{ url_for('expense_new', flight=f.id) }}">+ Masraf ekle</a>{% endif %}</div>
{% if exps %}<div class="tbl"><table><tr><th>Tür</th><th>Açıklama</th><th class="hide-m">Tedarikçi / yer</th><th class="hide-m">Miktar</th><th style="text-align:right">Tutar</th><th class="hide-m">Durum</th><th></th></tr>
{% for e in exps %}<tr><td>{{ T(EXPENSE_CATS.get(e.category, e.category)) }}</td><td>{{ e.description or '—' }}{% if e.invoice_no %}<span class="sub">{{ e.invoice_no }}</span>{% endif %}</td>
<td class="hide-m">{{ e.vendor or '—' }}<span class="sub">{{ e.location }}</span></td><td class="hide-m">{{ qty_text(e) }}</td>
<td style="text-align:right;white-space:nowrap;color:#fff">{{ money(e.amount, e.currency) }}</td><td class="hide-m"><span class="st {{ PAY_TONE[e.payment_status] }}">{{ T(PAY_STATUS[e.payment_status]) }}</span></td>
<td>{% if can_edit_expense(e) %}<a href="{{ url_for('expense_edit', eid=e.id, back=request.path) }}">Düzenle</a>{% endif %}</td></tr>{% endfor %}
<tr><td colspan="4" style="color:var(--muted);text-transform:uppercase;letter-spacing:.14em;font-size:11px">Toplam</td><td style="text-align:right;color:#fff;font-weight:600">{% for c, v in exp_tot.items() %}<div>{{ money(v, c) }}</div>{% endfor %}</td><td colspan="2" class="hide-m"></td></tr>
</table></div>{% else %}<p class="muted">Bu uçuş için masraf girilmemiş.</p>{% endif %}
{% if g.user.role!='pilot' and not f.cancelled %}<h2>Koordinatör işlemi</h2><form method="post" action="{{ url_for('flight_decide', fid=f.id) }}" class="sheet">
<input type="hidden" name="csrf" value="{{ csrf_token() }}"><label>Açıklama (isteğe bağlı)<input name="decision_note"></label><br><div class="row">
{% if f.approval=='pending' %}<button class="btn" name="action" value="approve">Onayla</button><button class="btn danger" name="action" value="reject">Reddet</button>{% endif %}
{% if f.approval=='approved' and status=='Planlı' %}<button class="btn danger" name="action" value="cancel">Uçuşu iptal et</button>{% endif %}</div></form>{% endif %}{% endblock %}"""

TEMPLATES["approvals.html"] = r"""{% extends "base.html" %}{% block body %}<div class="eyebrow">Koordinasyon</div><h1>Onay bekleyen kayıtlar</h1>
<p class="muted">Pilotların oluşturduğu kayıtlar. Onaylanan kayıt programa ve uçak durumuna yansır; onay anında çakışma ve bakım tekrar kontrol edilir.</p>
<div class="tbl"><table><tr><th>Tarih / saat</th><th>Uçak</th><th>Rota</th><th>Pilot</th><th class="hide-m">Görev</th><th></th></tr>
{% for f in rows %}<tr><td><a href="{{ url_for('flight_detail', fid=f.id) }}">{{ f.flight_date }}</a><span class="sub">{{ f.dep_time }}–{{ f.arr_time }} · {{ duration_text(f) }}</span></td>
<td>{{ f.reg }}</td><td>{{ short_ap(f.dep) }} → {{ short_ap(f.arr) }}</td><td>{{ f.pilot }}</td><td class="hide-m">{{ f.mission }} · {{ f.pax }} yolcu</td>
<td><form method="post" action="{{ url_for('flight_decide', fid=f.id) }}" class="row"><input type="hidden" name="csrf" value="{{ csrf_token() }}"><input type="hidden" name="back" value="{{ url_for('approvals') }}">
<button class="btn small" name="action" value="approve">Onayla</button><button class="btn small danger" name="action" value="reject">Reddet</button></form></td></tr>
{% else %}<tr><td colspan="6" class="muted">Onay bekleyen kayıt yok.</td></tr>{% endfor %}</table></div>{% endblock %}"""

TEMPLATES["maintenance.html"] = r"""{% extends "base.html" %}{% block body %}<div class="eyebrow">Teknik</div><h1>Bakım ve uçak durumu</h1>
<p class="muted">Başlamış ve bitişi gelmemiş kayıt uçağı o andan itibaren "Bakımda" gösterir; bitiş boşsa bakım sürüyor sayılır. Bitiş saati gelince uçak kendiliğinden müsait olur.</p>
{% if g.user.role!='pilot' %}<h2>Yeni kayıt</h2><form method="post" class="grid sheet"><input type="hidden" name="csrf" value="{{ csrf_token() }}">
<label>Uçak<select name="aircraft_id" required>{% for a in fleet %}<option value="{{ a.id }}">{{ a.reg }} · {{ a.type }}</option>{% endfor %}</select></label>
<label>Durum<select name="code">{% for c, l in MX_CODES.items() %}<option value="{{ c }}">{{ c }} · {{ l }}</option>{% endfor %}</select></label>
<label>Bakım tipi<input name="kind" placeholder="200 Saatlik, 24 Aylık"></label><label>Bakım yeri<input name="place"></label>
<label>Başlangıç<input type="datetime-local" name="start_at" value="{{ now.strftime('%Y-%m-%dT%H:%M') }}" required></label>
<label>Bitiş (tahmini, boş bırakılabilir)<input type="datetime-local" name="end_at"></label><label class="full">Açıklama<input name="note"></label>
<div class="full"><button class="btn">Kaydet</button></div></form>{% endif %}
<h2>Kayıtlar</h2><div class="tbl"><table><tr><th>Uçak</th><th>Durum</th><th>Tip / yer</th><th>Başlangıç</th><th>Bitiş</th><th></th>{% if g.user.role!='pilot' %}<th></th>{% endif %}</tr>
{% for m, st in rows %}<tr><td>{{ m.reg }}<span class="sub">{{ m.type }}</span></td><td>{{ m.code }}<span class="sub">{{ MX_CODES[m.code] }}</span></td>
<td>{{ m.kind or '—' }}<span class="sub">{{ m.place }}{% if m.note %} · {{ m.note }}{% endif %}</span></td><td>{{ m.start_at.replace('T',' ') }}</td><td>{{ m.end_at.replace('T',' ') if m.end_at else 'Girilmemiş' }}</td>
<td><span class="st {{ 'warn' if st=='Sürüyor' else 'ok' if st=='Bitti' else 'busy' }}">{{ st }}</span></td>
{% if g.user.role!='pilot' %}<td>{% if st!='Bitti' %}<form method="post" action="{{ url_for('maintenance_close', mid=m.id) }}"><input type="hidden" name="csrf" value="{{ csrf_token() }}"><button class="btn small ghost">{{ 'Şimdi bitir' if st=='Sürüyor' else 'Sil' }}</button></form>{% endif %}</td>{% endif %}</tr>
{% else %}<tr><td colspan="7" class="muted">Kayıt yok.</td></tr>{% endfor %}</table></div>
<h2>Günlük kodlar</h2><p class="muted">Uçuş ve bakım kaydı dışındaki gün bilgileri: RON (dış meydanda konaklama), RES (yedek), M (saatsiz bakım günü).</p>
{% if g.user.role!='pilot' %}<form method="post" action="{{ url_for('day_code') }}" class="grid sheet"><input type="hidden" name="csrf" value="{{ csrf_token() }}">
<label>Uçak<select name="aircraft_id">{% for a in fleet %}<option value="{{ a.id }}">{{ a.reg }}</option>{% endfor %}</select></label>
<label>Gün<input type="date" name="day" value="{{ now.strftime('%Y-%m-%d') }}" required></label>
<label>Kod<select name="code"><option value="">Kodu sil</option>{% for c, l in DAY_CODES.items() %}<option value="{{ c }}">{{ c }} · {{ l }}</option>{% endfor %}</select></label>
<div style="align-self:end"><button class="btn">Kaydet</button></div></form>{% endif %}
{% if codes %}<div class="tbl" style="margin-top:12px"><table><tr><th>Gün</th><th>Uçak</th><th>Kod</th></tr>{% for c in codes %}<tr><td>{{ c.day }}</td><td>{{ c.reg }}</td><td>{{ c.code }} · {{ DAY_CODES.get(c.code) }}</td></tr>{% endfor %}</table></div>{% endif %}{% endblock %}"""

TEMPLATES["fleet.html"] = r"""{% extends "base.html" %}{% block body %}<div class="eyebrow">Filo</div><h1>Uçaklarımız</h1>
<p class="muted">Durum anlık hesaplanır: uçuş saatleri, bakım kayıtları ve günlük kodlar birlikte değerlendirilir.</p>
<div class="cards">{% for c in cards %}{% set a = c.a %}<div class="sheet" id="ac{{ a.id }}"><div class="row" style="justify-content:space-between">
<div><b style="font:600 20px/1.2 var(--serif);color:var(--ivory);letter-spacing:.1em">{{ a.reg }}</b><span class="sub">{{ a.type }} · {{ CATEGORIES.get(a.category) }}</span></div><span class="st {{ c.s.tone }}">{{ c.s.label }}</span></div>
<dl class="kv" style="grid-template-columns:130px 1fr;margin-top:14px">
<dt>Filo kaydındaki durum</dt><dd>{{ c.fleet_state }}<span class="sub">{{ c.s.detail }}</span></dd>
<dt>Konum</dt><dd>{{ c.location or '—' }}</dd><dt>Koltuk</dt><dd>{{ a.seats }}</dd>
<dt>Tamamlanan</dt><dd>{{ c.sorties }} uçuş · {{ c.minutes // 60 }} sa {{ '%02d' % (c.minutes % 60) }} dk</dd>
<dt>Son uçuş</dt><dd>{{ c.last.flight_date ~ ' ' ~ short_ap(c.last.dep) ~ '–' ~ short_ap(c.last.arr) if c.last else '—' }}</dd>
<dt>Sıradaki uçuş</dt><dd>{{ c.next.flight_date ~ ' ' ~ c.next.dep_time ~ ', ' ~ short_ap(c.next.dep) ~ '–' ~ short_ap(c.next.arr) if c.next else 'Planlı uçuş yok' }}</dd></dl>
<div class="row" style="margin-top:12px">{% if a.active %}<a class="btn small" href="{{ url_for('flight_new', ac=a.id) }}">Bu uçakla kayıt oluştur</a>{% endif %}<a class="btn small ghost" href="{{ url_for('flights', ac=a.id) }}">Uçuşları</a></div>
{% if g.user.role=='yonetici' %}<details style="margin-top:10px"><summary class="muted">Uçak bilgilerini düzenle</summary><form method="post" class="grid" style="margin-top:10px">
<input type="hidden" name="csrf" value="{{ csrf_token() }}"><input type="hidden" name="id" value="{{ a.id }}">
<label>Tescil<input name="reg" value="{{ a.reg }}"></label><label>Tip<input name="type" value="{{ a.type }}"></label>
<label>Kategori<select name="category">{% for k, v in CATEGORIES.items() %}<option value="{{ k }}" {{ 'selected' if a.category==k }}>{{ v }}</option>{% endfor %}</select></label>
<label>Koltuk<input type="number" name="seats" value="{{ a.seats }}"></label><label>Üs<input name="base" value="{{ a.base }}"></label>
<label><input type="checkbox" name="active" value="1" style="width:auto" {{ 'checked' if a.active }}> Filoda aktif</label><div class="full"><button class="btn small">Kaydet</button></div></form></details>{% endif %}
</div>{% endfor %}</div>
{% if g.user.role=='yonetici' %}<h2>Yeni uçak</h2><form method="post" class="grid sheet"><input type="hidden" name="csrf" value="{{ csrf_token() }}">
<label>Tescil<input name="reg" required></label><label>Tip<input name="type" required></label>
<label>Kategori<select name="category">{% for k, v in CATEGORIES.items() %}<option value="{{ k }}">{{ v }}</option>{% endfor %}</select></label>
<label>Koltuk<input type="number" name="seats" value="8"></label><label>Üs<input name="base" list="aps"></label><div style="align-self:end"><button class="btn">Ekle</button></div>
<datalist id="aps">{% for ap in AIRPORTS %}<option value="{{ ap }}">{% endfor %}</datalist></form>{% endif %}{% endblock %}"""

TEMPLATES["users.html"] = r"""{% extends "base.html" %}{% block body %}<div class="eyebrow">Yönetim</div><h1>Kullanıcılar</h1>
<div class="tbl"><table><tr><th>Ad soyad</th><th>Kullanıcı adı</th><th>Rol</th><th>Durum</th><th></th></tr>
{% for u in rows %}<tr><td>{{ u.full_name }}<span class="sub">{{ u.title }}</span></td><td>{{ u.username }}</td>
<td><form method="post" class="row"><input type="hidden" name="csrf" value="{{ csrf_token() }}"><input type="hidden" name="id" value="{{ u.id }}"><input type="hidden" name="action" value="role">
<select name="role" onchange="this.form.submit()" style="width:auto" {{ 'disabled' if u.id==g.user.id }}>{% for k, v in ROLES.items() %}<option value="{{ k }}" {{ 'selected' if u.role==k }}>{{ v }}</option>{% endfor %}</select></form></td>
<td><span class="st {{ 'ok' if u.active else 'bad' }}">{{ 'Aktif' if u.active else 'Pasif' }}</span></td>
<td class="row"><form method="post"><input type="hidden" name="csrf" value="{{ csrf_token() }}"><input type="hidden" name="id" value="{{ u.id }}"><button class="btn small ghost" name="action" value="reset">Şifre sıfırla</button></form>
{% if u.id!=g.user.id %}<form method="post"><input type="hidden" name="csrf" value="{{ csrf_token() }}"><input type="hidden" name="id" value="{{ u.id }}"><button class="btn small ghost" name="action" value="toggle">{{ 'Pasifleştir' if u.active else 'Aktifleştir' }}</button></form>{% endif %}</td></tr>{% endfor %}</table></div>
<h2>Yeni kullanıcı</h2><form method="post" class="grid sheet"><input type="hidden" name="csrf" value="{{ csrf_token() }}"><input type="hidden" name="action" value="create">
<label>Ad soyad<input name="full_name" required></label><label>Unvan<input name="title" placeholder="Kaptan Pilot"></label><label>Kullanıcı adı<input name="username" required></label>
<label>Rol<select name="role">{% for k, v in ROLES.items() %}<option value="{{ k }}">{{ v }}</option>{% endfor %}</select></label>
<label>Geçici şifre (en az 8)<input name="password" minlength="8" required></label><div style="align-self:end"><button class="btn">Ekle</button></div></form>{% endblock %}"""

TEMPLATES["audit.html"] = r"""{% extends "base.html" %}{% block body %}<h1>İşlem geçmişi</h1><div class="tbl"><table><tr><th>Zaman</th><th>Kullanıcı</th><th>İşlem</th><th>Ayrıntı</th></tr>
{% for r in rows %}<tr><td>{{ r.at }}</td><td>{{ r.full_name or '—' }}</td><td>{{ r.action }}</td><td>{{ r.detail }}</td></tr>{% endfor %}</table></div>{% endblock %}"""

TEMPLATES["expenses.html"] = r"""{% extends "base.html" %}{% block head %}<style>
.exp-figs{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:14px;margin:6px 0 26px}
.exp-figs .sheet{padding:18px 20px}.exp-figs b{display:block;font:600 26px/1.2 var(--serif);color:#fff;margin-top:6px;white-space:nowrap}
.exp-figs .sub{margin-top:4px}
.exp-grid{display:grid;grid-template-columns:1.3fr 1fr;gap:18px;margin-bottom:26px}
.bar{height:6px;border-radius:3px;background:rgba(255,255,255,.08);margin-top:6px;overflow:hidden}.bar i{display:block;height:100%;background:rgba(255,255,255,.75);border-radius:3px}
.num{text-align:right;white-space:nowrap;color:#fff;font-variant-numeric:tabular-nums}
@media (max-width:900px){.exp-grid{grid-template-columns:1fr}}
</style>{% endblock %}{% block body %}
<div class="page-head"><div><div class="eyebrow">Maliyet</div><h1>Uçuş masrafları</h1>
<p class="muted" style="margin:0">Yakıt, konaklama, park, handling ve diğer özel jet uçuş maliyetleri. Toplamlar para birimine göre ayrı tutulur.</p></div>
<div class="row">{% if g.user.role!='pilot' %}<a class="btn ghost" href="{{ url_for('expenses_csv', **filters) }}">Excel'e aktar (CSV)</a>{% endif %}<a class="btn" href="{{ url_for('expense_new') }}">+ Masraf ekle</a></div></div>
<form class="grid sheet" method="get" style="margin-bottom:22px">
<label>Başlangıç<input type="date" name="from" value="{{ filters.get('from','') }}"></label><label>Bitiş<input type="date" name="to" value="{{ filters.get('to','') }}"></label>
<label>Uçak<select name="ac"><option value="">Tümü</option>{% for a in fleet %}<option value="{{ a.id }}" {{ 'selected' if filters.get('ac')==a.id|string }}>{{ a.reg }}</option>{% endfor %}</select></label>
<label>Uçuş<select name="flight"><option value="">Tümü</option>{% for f in flights_list %}<option value="{{ f.id }}" {{ 'selected' if filters.get('flight')==f.id|string }}>{{ f.code }} · {{ f.flight_date }} · {{ short_ap(f.dep) }}–{{ short_ap(f.arr) }}</option>{% endfor %}</select></label>
<label>Masraf türü<select name="cat"><option value="">Tümü</option>{% for k, v in EXPENSE_CATS.items() %}<option value="{{ k }}" {{ 'selected' if filters.get('cat')==k }}>{{ T(v) }}</option>{% endfor %}</select></label>
<label>Ödeme durumu<select name="status"><option value="">Tümü</option>{% for k, v in PAY_STATUS.items() %}<option value="{{ k }}" {{ 'selected' if filters.get('status')==k }}>{{ T(v) }}</option>{% endfor %}</select></label>
<label>Para birimi<select name="cur"><option value="">Tümü</option>{% for c in CURRENCIES %}<option {{ 'selected' if filters.get('cur')==c }}>{{ c }}</option>{% endfor %}</select></label>
<div style="align-self:end" class="row"><button class="btn">Filtrele</button><a href="{{ url_for('expenses') }}">Temizle</a></div></form>
{% if rows %}
<div class="exp-figs">{% for c in curs %}<div class="sheet"><div class="eyebrow">Toplam · {{ c }}</div><b>{{ money(cur_tot[c], c) }}</b>
<span class="sub">{% if unpaid.get(c) %}Ödenecek {{ money(unpaid[c], c) }}{% endif %}{% if unpaid.get(c) and rebill.get(c) %} · {% endif %}{% if rebill.get(c) %}Yansıtılacak {{ money(rebill[c], c) }}{% endif %}</span></div>{% endfor %}</div>
<div class="exp-grid">
<div class="sheet"><div class="eyebrow">Masraf türüne göre</div><table style="margin-top:8px">{% for cat, vals in cat_rows %}<tr><td style="width:44%">{{ T(EXPENSE_CATS.get(cat, cat)) }}</td>
<td>{% for c in curs %}{% if vals.get(c) %}<div class="row" style="justify-content:space-between;gap:8px"><span class="sub" style="margin:0">{{ c }}</span><span class="num">{{ money(vals[c], c) }}</span></div><div class="bar"><i style="width:{{ (vals[c] / maxv[c] * 100)|round(1) }}%"></i></div>{% endif %}{% endfor %}</td></tr>{% endfor %}</table></div>
<div style="display:grid;gap:18px;align-content:start">
<div class="sheet"><div class="eyebrow">Uçağa göre</div><table style="margin-top:8px">{% for reg, vals in by_ac %}<tr><td>{{ reg }}</td><td class="num">{% for c, v in vals.items() %}<div>{{ money(v, c) }}</div>{% endfor %}</td></tr>{% endfor %}</table></div>
<div class="sheet"><div class="eyebrow">En maliyetli uçuşlar</div><table style="margin-top:8px">{% for key, vals in top_flights %}<tr><td><a href="{{ url_for('flight_detail', fid=key[0]) }}">{{ key[1] }}</a><span class="sub">{{ key[2] }} · {{ key[3] }} · {{ short_ap(key[4]) }}–{{ short_ap(key[5]) }}</span></td><td class="num">{% for c, v in vals.items() %}<div>{{ money(v, c) }}</div>{% endfor %}</td></tr>{% endfor %}</table></div>
</div></div>
<h2>Kayıtlar</h2><div class="tbl"><table><tr><th>Tarih</th><th>Uçuş</th><th>Tür</th><th class="hide-m">Açıklama</th><th class="hide-m">Tedarikçi / yer</th><th class="hide-m">Miktar</th><th style="text-align:right">Tutar</th><th class="hide-m">Durum</th><th></th></tr>
{% for e in rows %}<tr><td style="white-space:nowrap">{{ e.expense_date }}</td><td>{% if e.flight_id %}<a href="{{ url_for('flight_detail', fid=e.flight_id) }}">{{ e.flight_code }}</a><span class="sub">{{ e.reg }} · {{ short_ap(e.dep) }}–{{ short_ap(e.arr) }}</span>{% else %}{{ e.reg }}<span class="sub">Uçuşa bağlı değil</span>{% endif %}</td>
<td>{{ T(EXPENSE_CATS.get(e.category, e.category)) }}</td><td class="hide-m">{{ e.description or '—' }}{% if e.invoice_no %}<span class="sub">{{ e.invoice_no }}</span>{% endif %}</td>
<td class="hide-m">{{ e.vendor or '—' }}<span class="sub">{{ e.location }}</span></td><td class="hide-m">{{ qty_text(e) }}</td><td class="num">{{ money(e.amount, e.currency) }}</td>
<td class="hide-m"><span class="st {{ PAY_TONE[e.payment_status] }}">{{ T(PAY_STATUS[e.payment_status]) }}</span></td>
<td>{% if can_edit_expense(e) %}<a href="{{ url_for('expense_edit', eid=e.id) }}">Düzenle</a>{% endif %}</td></tr>{% endfor %}</table></div>
{% else %}<div class="sheet"><p class="muted" style="margin:0">Bu filtrelere uyan masraf kaydı yok.</p></div>{% endif %}{% endblock %}"""

TEMPLATES["expense_form.html"] = r"""{% extends "base.html" %}{% block body %}
<div class="eyebrow">Maliyet</div><h1>{{ 'Yeni masraf' if mode=='new' else 'Masrafı düzenle' }}</h1>
<p class="muted">Masrafı bir uçuşa bağlayın; uçak uçuştan otomatik alınır. Uçuşa bağlı olmayan masraflar (aylık hangar gibi) için uçuşu boş bırakıp uçağı seçin. Tutarda virgül ya da nokta kullanabilirsiniz.</p>
<form method="post" class="grid sheet"><input type="hidden" name="csrf" value="{{ csrf_token() }}">
<label class="full">Uçuş<select name="flight_id" id="flight_id"><option value="">Uçuşa bağlı değil</option>{% for f in flights_list %}<option value="{{ f.id }}" data-date="{{ f.flight_date }}" {{ 'selected' if e and e.flight_id|string==f.id|string }}>{{ f.code }} · {{ f.flight_date }} · {{ f.reg }} · {{ short_ap(f.dep) }} → {{ short_ap(f.arr) }}</option>{% endfor %}</select></label>
{% if g.user.role!='pilot' %}<label>Uçak (uçuş yoksa)<select name="aircraft_id"><option value="">Seçin</option>{% for a in fleet %}<option value="{{ a.id }}" {{ 'selected' if e and e.aircraft_id|string==a.id|string }}>{{ a.reg }} · {{ a.type }}</option>{% endfor %}</select></label>{% endif %}
<label>Masraf türü<select name="category" id="category" required>{% for k, v in EXPENSE_CATS.items() %}<option value="{{ k }}" {{ 'selected' if e and e.category==k }}>{{ T(v) }}</option>{% endfor %}</select></label>
<label>Tarih<input type="date" name="expense_date" id="expense_date" value="{{ e.expense_date if e and e.expense_date else '' }}"></label>
<label>Tutar<input name="amount" inputmode="decimal" placeholder="0,00" value="{{ e.amount if e and e.amount is not none else '' }}" required></label>
<label>Para birimi<select name="currency">{% for c in CURRENCIES %}<option {{ 'selected' if e and e.currency==c }}>{{ c }}</option>{% endfor %}</select></label>
<label>Miktar<input name="quantity" inputmode="decimal" value="{{ e.quantity if e and e.quantity is not none else '' }}"></label>
<label>Birim<select name="unit" id="unit">{% for k, v in UNITS.items() %}<option value="{{ k }}" {{ 'selected' if e and e.unit==k }}>{{ T(v) }}</option>{% endfor %}</select></label>
<label>Açıklama<input name="description" value="{{ e.description if e and e.description else '' }}" placeholder="Jet A-1 ikmali, 2 oda 1 gece"></label>
<label>Tedarikçi<input name="vendor" value="{{ e.vendor if e and e.vendor else '' }}" placeholder="FBO, otel, yakıt şirketi"></label>
<label>Yer / meydan<input name="location" list="aps" value="{{ e.location if e and e.location else '' }}"></label>
<label>Fatura / fiş no<input name="invoice_no" value="{{ e.invoice_no if e and e.invoice_no else '' }}"></label>
<label>Ödeme yolu<select name="payment_method">{% for k, v in PAY_METHODS.items() %}<option value="{{ k }}" {{ 'selected' if e and e.payment_method==k }}>{{ T(v) }}</option>{% endfor %}</select></label>
<label>Ödeme durumu<select name="payment_status">{% for k, v in PAY_STATUS.items() %}<option value="{{ k }}" {{ 'selected' if e and e.payment_status==k }}>{{ T(v) }}</option>{% endfor %}</select></label>
<label class="full">Not<textarea name="note">{{ e.note if e and e.note else '' }}</textarea></label>
<div class="full row"><button class="btn">Kaydet</button>{% if mode=='new' %}<button class="btn ghost" name="again" value="1">Kaydet ve yeni ekle</button>{% endif %}<a href="{{ request.args.get('back') or url_for('expenses') }}">Vazgeç</a></div>
<datalist id="aps">{% for ap in AIRPORTS %}<option value="{{ ap }}">{% endfor %}</datalist></form>
{% if mode=='edit' %}<form method="post" action="{{ url_for('expense_delete', eid=e.id) }}" style="margin-top:14px"><input type="hidden" name="csrf" value="{{ csrf_token() }}"><input type="hidden" name="back" value="{{ request.args.get('back','') }}"><button class="btn danger small">Masrafı sil</button></form>{% endif %}
<script>
(function(){ var CAT_UNIT = {{ CAT_UNIT|tojson }};
  var fl=document.getElementById('flight_id'), dt=document.getElementById('expense_date'), cat=document.getElementById('category'), un=document.getElementById('unit');
  fl.addEventListener('change',function(){ var o=fl.options[fl.selectedIndex]; if(o && o.dataset.date && !dt.value) dt.value=o.dataset.date; });
  if(!dt.value){ var o=fl.options[fl.selectedIndex]; if(o && o.dataset.date) dt.value=o.dataset.date; }
  cat.addEventListener('change',function(){ if(CAT_UNIT[cat.value]) un.value=CAT_UNIT[cat.value]; });
})();
</script>{% endblock %}"""

TEMPLATES["error.html"] = r"""{% extends "base.html" %}{% block body %}<div class="sheet" style="max-width:520px"><h1>{{ code }}</h1><p>{{ msg }}</p><a href="{{ url_for('dashboard') }}">Genel bakışa dön</a></div>{% endblock %}"""

# Değişken metinler (durum, uyarı, süre, ay/gün adları) çalışma anında T() ile çevrilir
_DYN = {
    "base.html": [('{{ m }}', '{{ T(m) }}'), ("class=\"{{ 'on' if ep=='maintenance' }}\">Bakım</a>", "class=\"{{ 'on' if ep=='maintenance' }}\">Bakım</a><a href=\"{{ url_for('expenses') }}\" class=\"{{ 'on' if ep in ('expenses','expense_new','expense_edit') }}\">Masraflar</a>"), ('{{ ROLES[g.user.role] }}', '{{ T(ROLES[g.user.role]) }}'), ('<html lang="tr">', '<html lang="{{ LANG }}">'),
                  ('<form method="post" action="{{ url_for(\'logout\') }}">', '<a class="lang" href="{{ lang_url() }}" title="Türkçe / English">{{ "EN" if LANG == "tr" else "TR" }}</a><form method="post" action="{{ url_for(\'logout\') }}">'),
                  ('.who button:hover{', '.lang{border:1px solid var(--line);border-radius:6px;padding:5px 10px;font-size:12px;letter-spacing:.12em;color:#fff;background:rgba(255,255,255,.05)}.lang:hover{background:rgba(255,255,255,.1);color:#fff}.who button:hover{')],
    "login.html": [],   # giriş şablonu T() çağrılarını kendisi içerir
    "dashboard.html": [('{{ MONTHS[now.month-1] }}', '{{ T(MONTHS[now.month-1]) }}'), ('{{ DAYS[now.weekday()] }}', '{{ T(DAYS[now.weekday()]) }}'),
                       ('{{ DAYS[d.weekday()] }}', '{{ T(DAYS[d.weekday()]) }}'), ('{{ lede }}', '{{ T(lede) }}'), ('{{ s.label }}', '{{ T(s.label) }}'),
                       ('{{ s.detail }}', '{{ T(s.detail) }}'), ('{{ tip }}', '{{ T(tip) }}'), ('{{ l }}', '{{ T(l) }}'), ('">{{ st }}<', '">{{ T(st) }}<'), ('{{ f.mission }}', '{{ T(f.mission) }}')],
    "flights.html": [("<option {{ 'selected' if filters.get('status')==s }}>{{ s }}</option>", "<option value=\"{{ s }}\" {{ 'selected' if filters.get('status')==s }}>{{ T(s) }}</option>"),
                     ('">{{ st }}<', '">{{ T(st) }}<'), ('{{ f.mission }}', '{{ T(f.mission) }}'), ('{{ duration_text(f) }}', '{{ T(duration_text(f)) }}')],
    "flight_form.html": [("<option {{ 'selected' if f and f.mission==m }}>{{ m }}</option>", "<option value=\"{{ m }}\" {{ 'selected' if f and f.mission==m }}>{{ T(m) }}</option>"), ('{{ p.title }}', '{{ T(p.title) }}')],
    "flight_detail.html": [('{{ status }}', '{{ T(status) }}'), ('{{ duration }}', '{{ T(duration) }}'), ('{{ f.mission }}', '{{ T(f.mission) }}')],
    "approvals.html": [('{{ f.mission }}', '{{ T(f.mission) }}'), ('{{ duration_text(f) }}', '{{ T(duration_text(f)) }}')],
    "maintenance.html": [('{{ l }}', '{{ T(l) }}'), ('{{ MX_CODES[m.code] }}', '{{ T(MX_CODES[m.code]) }}'), ('">{{ st }}<', '">{{ T(st) }}<'), ('{{ DAY_CODES.get(c.code) }}', '{{ T(DAY_CODES.get(c.code)) }}')],
    "fleet.html": [('{{ c.fleet_state }}', '{{ T(c.fleet_state) }}'), ('{{ c.s.detail }}', '{{ T(c.s.detail) }}'), ('{{ c.s.label }}', '{{ T(c.s.label) }}'),
                   ('{{ CATEGORIES.get(a.category) }}', '{{ T(CATEGORIES.get(a.category)) }}'), ('{{ v }}', '{{ T(v) }}')],
    "users.html": [('{{ u.title }}', '{{ T(u.title) }}'), ('{{ v }}', '{{ T(v) }}')],
    "audit.html": [('{{ r.action }}', '{{ T(r.action) }}')],
    "error.html": [('{{ msg }}', '{{ T(msg) }}')],
}
for _name, _pairs in _DYN.items():
    for _a, _b in _pairs:
        if _a not in TEMPLATES[_name]:
            raise RuntimeError(f"Çeviri eşleşmesi bulunamadı: {_name}: {_a}")
        TEMPLATES[_name] = TEMPLATES[_name].replace(_a, _b)


class TranslatingLoader(DictLoader):
    """Şablonları yüklerken sabit Türkçe metinleri T() çağrısına çevirir (dil seçimi çalışma anında yapılır)."""
    def get_source(self, environment, template):
        source, filename, uptodate = super().get_source(environment, template)
        return i18n.translate_template(source), filename, uptodate


app.jinja_loader = TranslatingLoader(TEMPLATES)


def current_lang():
    lang = session.get("lang") or request.cookies.get("lang") or "tr"
    return lang if lang in ("tr", "en") else "tr"


def T(text):
    return i18n.T_en(text) if current_lang() == "en" else ("" if text is None else text)


@app.route("/lang/<code>")
def set_lang(code):
    code = code if code in ("tr", "en") else "tr"
    session["lang"] = code
    nxt = request.args.get("next", "")
    resp = redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("dashboard"))
    resp.set_cookie("lang", code, max_age=365 * 86400, samesite="Lax", secure=ON_VERCEL)
    return resp


def lang_url():
    path = request.full_path.rstrip("?") if request.endpoint != "set_lang" else "/"
    return url_for("set_lang", code="en" if current_lang() == "tr" else "tr", next=path)


app.jinja_env.globals.update(T=T, lang_url=lang_url)


def qty_text(e):
    if e["quantity"] is None or e["quantity"] == "":
        return "—"
    v = float(e["quantity"])
    num = (f"{v:,.0f}" if v == int(v) else f"{v:,.2f}")
    if current_lang() == "tr":
        num = num.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{num} {T(UNITS.get(e['unit'], e['unit']))}".strip() if e["unit"] else num


app.jinja_env.globals.update(money=money, qty_text=qty_text, can_edit_expense=can_edit_expense, EXPENSE_CATS=EXPENSE_CATS,
                             CURRENCIES=CURRENCIES, UNITS=UNITS, PAY_METHODS=PAY_METHODS, PAY_STATUS=PAY_STATUS, CAT_UNIT=CAT_UNIT,
                             PAY_TONE={"odenecek": "warn", "odendi": "ok", "yansitilacak": "busy"})


@app.context_processor
def helpers():
    def pending_count():
        return q("SELECT COUNT(*) c FROM flights WHERE approval='pending' AND cancelled=0", one=True)["c"]
    return dict(pending_count=pending_count, LANG=current_lang())


init_db()

if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 5000)),
            debug=os.environ.get("FLASK_DEBUG") == "1")
