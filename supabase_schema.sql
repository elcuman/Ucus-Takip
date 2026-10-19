-- İsteğe bağlı: uygulama ilk açılışta bu tabloları kendisi de oluşturur.
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
  full_name TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('pilot','koordinator','yonetici')),
  title TEXT DEFAULT '', active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS aircraft (
  id SERIAL PRIMARY KEY, reg TEXT UNIQUE NOT NULL, type TEXT NOT NULL, category TEXT NOT NULL,
  seats INTEGER NOT NULL DEFAULT 0, base TEXT DEFAULT '', active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS flights (
  id SERIAL PRIMARY KEY, code TEXT, flight_date TEXT NOT NULL, aircraft_id INTEGER NOT NULL REFERENCES aircraft(id),
  pic_id INTEGER REFERENCES users(id), crew TEXT DEFAULT '', dep TEXT NOT NULL, arr TEXT NOT NULL,
  dep_time TEXT NOT NULL, arr_time TEXT NOT NULL, mission TEXT NOT NULL, pax INTEGER DEFAULT 0,
  approval TEXT NOT NULL DEFAULT 'pending' CHECK(approval IN ('pending','approved','rejected')),
  cancelled INTEGER NOT NULL DEFAULT 0, note TEXT DEFAULT '', decision_note TEXT DEFAULT '',
  created_by INTEGER REFERENCES users(id), created_at TEXT NOT NULL,
  decided_by INTEGER REFERENCES users(id), decided_at TEXT);
CREATE TABLE IF NOT EXISTS maintenance (
  id SERIAL PRIMARY KEY, aircraft_id INTEGER NOT NULL REFERENCES aircraft(id), code TEXT NOT NULL,
  kind TEXT DEFAULT '', place TEXT DEFAULT '', start_at TEXT NOT NULL, end_at TEXT, note TEXT DEFAULT '',
  created_by INTEGER REFERENCES users(id), created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS day_codes (
  aircraft_id INTEGER NOT NULL REFERENCES aircraft(id), day TEXT NOT NULL, code TEXT NOT NULL,
  PRIMARY KEY (aircraft_id, day));
CREATE TABLE IF NOT EXISTS audit (
  id SERIAL PRIMARY KEY, user_id INTEGER, action TEXT NOT NULL, detail TEXT DEFAULT '', at TEXT NOT NULL);
