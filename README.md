# Gökyolu Havacılık · Uçuş Kayıt ve Takip (Flask)

Pilot, koordinatör ve yönetici girişli uçuş kayıt sistemi. Tek dosya: `app.py`.
Yerelde SQLite ile, canlıda Supabase (Postgres) ile çalışır. Tüm şirket, uçak ve kişi adları uydurmadır.

## Canlıya alma: Supabase + Vercel
1. **Supabase**: yeni proje açın (bölge: Frankfurt, eu-central-1). Project Settings → Database → Connection string → **Transaction pooler** adresini kopyalayın
   (`postgresql://postgres.xxxx:ŞİFRE@aws-0-eu-central-1.pooler.supabase.com:6543/postgres`). Tablolar ilk açılışta kendiliğinden kurulur
   (isterseniz `supabase_schema.sql` dosyasını SQL Editor'de çalıştırabilirsiniz).
2. **Vercel**: Add New → Project → bu GitHub deposunu seçin. Framework otomatik "Flask" görünür; ayar değiştirmeyin.
3. **Environment Variables** (Production):
   - `DATABASE_URL` = Supabase transaction pooler adresi
   - `SECRET_KEY` = uzun rastgele bir metin (ör. `python -c "import secrets;print(secrets.token_hex(32))"`)
   - `SEED_DEMO` = `1` örnek veriyle başlar, `0` boş başlar (o zaman ilk yöneticiyi aşağıdaki gibi ekleyin)
4. Deploy. Açılan adreste `yonetici / Yonetici123!` ile girip **hemen şifreleri değiştirin**.

İlk yöneticiyi elle eklemek (SEED_DEMO=0 ise), yerelde:
```
DATABASE_URL=... python -c "import app; from werkzeug.security import generate_password_hash as h; import datetime;
c=app.connect(); app.run(c,'INSERT INTO users(username,password_hash,full_name,role,created_at) VALUES (?,?,?,?,?)',('yonetici',h('GüçlüŞifre!'),'Ad Soyad','yonetici',str(datetime.datetime.now())))"
```

## Yerelde çalıştırma
```
pip install -r requirements.txt
python app.py        # http://127.0.0.1:5000, veriler ucus.db dosyasında
```

## Örnek hesaplar
yonetici / Yonetici123! · koordinator / Koordinator123! · pilot.deniz, pilot.selin, pilot.mert / Pilot123!

## Roller
- **Pilot:** uçuş kaydı oluşturur (koordinatör onayına düşer), yalnızca kendi uçuşlarını görür.
- **Koordinatör:** onaylı uçuş planlar, pilot kayıtlarını onaylar/reddeder, iptal eder, bakım ve günlük kod (RON/RES/M) girer, CSV alır.
- **Yönetici:** + uçak ve kullanıcı yönetimi, şifre sıfırlama, işlem geçmişi.

## Uçuş masrafları
Menüde **Masraflar**. Her masraf bir uçuşa (ya da uçuşa bağlı olmayan aylık hangar gibi kalemlerde doğrudan uçağa) bağlanır.
Türler: yakıt, handling, iniş/yolcu ücreti, park/hangar, konaklama, ekip harcırahı, ulaşım, catering, FBO/VIP salon, navigasyon/overflight,
izin/slot, gümrük, buzlanma önleme, hat bakımı, temizlik, diğer. Her kayıtta tutar + para birimi (EUR, USD, TRY, GBP, CHF, AED), miktar/birim,
tedarikçi, yer, fatura no, ödeme yolu ve ödeme durumu (ödenecek / ödendi / müşteriye yansıtılacak) tutulur.
Toplamlar para birimine göre ayrı gösterilir (kur çevrimi yapılmaz). Uçuş detayında o uçuşun masraf tablosu ve toplamı görünür.
Pilot yalnızca kendi uçuşlarına masraf girer ve görür; koordinatör/yönetici hepsini görür, CSV alır.
Supabase'de tablo: `supabase_schema.sql` içindeki `expenses` (canlı projede kurulu).

## Anlık durum
Havada → Görevde · süren bakım → Bakımda · bugün inmemiş uçuş → Görevde · RON/RES/M → Konaklamada/Yedekte/Bakımda · aksi halde Müsait.

## Ortam değişkenleri
`DATABASE_URL`, `SECRET_KEY`, `SEED_DEMO`, `APP_TZ` (varsayılan Europe/Istanbul), `APP_COMPANY`, `APP_FAKE_NOW` (test için saati sabitler).
