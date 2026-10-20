"""TR / EN dil desteği.

Sayfalar Türkçe yazılır. Dil EN seçiliyse:
  * şablonlardaki sabit metinler yükleme sırasında T("...") çağrısına çevrilir (translate_template)
  * Python'dan gelen değişken metinler (anlık durum, uyarılar, süreler) T() içindeki kurallarla çevrilir
Excel/CSV çıktıları ve kullanıcının girdiği veriler (meydan, ekip, not) olduğu gibi kalır.
"""
import re

EN = {
    # menü ve genel
    "Genel Bakış": "Overview", "Uçuşlar": "Flights", "Uçuşlarım": "My flights", "Uçuş kaydı": "Flight log",
    "Onaylar": "Approvals", "Filo": "Fleet", "Bakım": "Maintenance", "Kullanıcılar": "Users", "Geçmiş": "History",
    "Çıkış": "Sign out", "Private Aviation": "Private Aviation", "Uçuş Kayıt ve Takip": "Flight Log & Tracking", "Sivil Havacılık": "Civil Aviation", "Giriş": "Sign in",
    "Pilot": "Pilot", "Koordinatör": "Coordinator", "Yönetici": "Administrator",
    # giriş
    "Gökyüzünde": "A", "zamansız": "timeless", "bir ayrıcalık.": "privilege in the skies.",
    "Filo, uçuş programı ve bakım takibi tek ekranda. Ekibinizin her uçuşu, kalkıştan inişe kadar kayıt altında.":
        "Fleet, flight schedule and maintenance tracking on one screen. Every flight your crew flies is on record, from take-off to landing.",
    "İstanbul": "Istanbul", "Cenevre": "Geneva", "Paris": "Paris", "Londra": "London",
    "Ekip girişi": "Crew sign-in", "Hoş geldiniz": "Welcome", "Uçuş Kayıt ve Takip Sistemi": "Flight Log & Tracking System",
    "Kullanıcı adı": "Username", "Şifre": "Password", "Giriş yap": "Sign in", "Deneme hesapları": "Demo accounts",
    "Kullanıcı adı ya da şifre hatalı.": "Incorrect username or password.",
    # genel bakış
    "Durum anlık hesaplanır, sayfa her dakika yenilenir.": "Status is calculated live; the page refreshes every minute.",
    "Bugünün sütunu anlık durumu gösterir; müsait uçakta boştur.": "Today's column shows the live status; it is empty for available aircraft.",
    "Bu yıl tamamlanan": "Completed this year", "Planlı uçuş": "Scheduled flights", "Onay bekleyen": "Awaiting approval",
    "Program": "Schedule", "Sıradaki uçuşlar": "Upcoming flights", "Sıradaki uçuşlarım": "My upcoming flights",
    "+ Uçuş kaydı oluştur": "+ New flight log", "Yaklaşan uçuş yok.": "No upcoming flights.",
    "Uçuş": "Flight", "Eğitim": "Training", "Ferry": "Ferry", "Konaklama": "Overnight", "Yedek": "Standby", "AOG": "AOG",
    # durumlar
    "Müsait": "Available", "Görevde": "On duty", "Bakımda": "In maintenance", "Parça bekliyor": "Awaiting parts",
    "AOG (yerde arızalı)": "AOG (grounded)", "Gayrifaal": "Unserviceable", "Konaklamada": "Overnight", "Yedekte": "On standby",
    "Filo dışı": "Out of fleet", "Pasif kayıt": "Inactive record",
    "Planlı": "Scheduled", "Uçuşta": "Airborne", "Tamamlandı": "Completed", "Onay bekliyor": "Pending approval",
    "Reddedildi": "Rejected", "İptal": "Cancelled", "Sürüyor": "Ongoing", "Başlamadı": "Not started", "Bitti": "Finished",
    "Bugün kayıt yok": "No records today", "Günlük kodu bakım": "Day code: maintenance",
    "Dış meydanda konaklama": "Overnight away from base", "Yedek uçak": "Standby aircraft", "Kayıt yok": "No record",
    "bitiş tarihi girilmemiş": "no end date", "uçuş sonrası bakım": "maintenance after the flight",
    # uçuşlar
    "Excel'e aktar (CSV)": "Export to Excel (CSV)", "Başlangıç": "Start", "Bitiş": "End", "Uçak": "Aircraft", "Durum": "Status",
    "Tümü": "All", "Filtrele": "Filter", "Temizle": "Clear", "Kod": "Code", "Tarih / saat": "Date / time", "Rota": "Route",
    "Görev": "Mission", "Yolcu": "Pax", "Kayıt yok.": "No records.", "Tarih": "Date",
    "Personel Nakli": "Staff transport", "VIP Transfer": "VIP transfer", "Kurumsal Seyahat": "Corporate travel",
    "Test Uçuşu": "Test flight", "Ambulans": "Air ambulance",
    # form
    "Yeni uçuş kaydı": "New flight log", "Uçuş kaydını düzenle": "Edit flight log",
    "Kaydınız koordinatör onayına gider; onaylanınca programa ve uçak durumuna yansır.":
        "Your log goes to the coordinator for approval; once approved it appears in the schedule and aircraft status.",
    "Koordinatör ve yönetici kayıtları doğrudan onaylı olarak programa girer.":
        "Coordinator and administrator entries go straight into the schedule as approved.",
    "Saatler yerel saattir; iniş kalkıştan önceyse ertesi gün sayılır. Aynı uçak ya da pilotla çakışan uçuş ve bakımdaki uçak kabul edilmez.":
        "Times are local; if landing is earlier than take-off it counts as the next day. Flights that clash with the same aircraft or pilot, and aircraft in maintenance, are rejected.",
    "Seçin": "Select", "Kaptan pilot": "Pilot in command", "Ekip (diğer)": "Other crew", "F/O, kabin ekibi": "F/O, cabin crew",
    "Kalkış meydanı": "Departure airport", "Kalkış saati (yerel)": "Departure time (local)", "İniş meydanı": "Arrival airport",
    "İniş saati (yerel)": "Arrival time (local)", "Yolcu sayısı": "Passengers", "Uçuş kodu (boşsa otomatik)": "Flight code (auto if blank)",
    "Not": "Note", "sa": "h", "dk": "min", "Kaydı oluştur": "Create log", "Kaydet": "Save", "Vazgeç": "Cancel", "koltuk": "seats",
    # detay
    "Uçuş #": "Flight #", "(yerel)": "(local)", "Ekip": "Crew", "Kalkış": "Departure", "İniş": "Arrival", "Oluşturan": "Created by",
    "Karar": "Decision", "Düzenle": "Edit", "Listeye dön": "Back to list", "Koordinatör işlemi": "Coordinator action",
    "Açıklama (isteğe bağlı)": "Comment (optional)", "Onayla": "Approve", "Reddet": "Reject", "Uçuşu iptal et": "Cancel flight",
    # onaylar
    "Koordinasyon": "Coordination", "Onay bekleyen kayıtlar": "Logs awaiting approval",
    "Pilotların oluşturduğu kayıtlar. Onaylanan kayıt programa ve uçak durumuna yansır; onay anında çakışma ve bakım tekrar kontrol edilir.":
        "Logs created by pilots. An approved log appears in the schedule and aircraft status; clashes and maintenance are re-checked at approval.",
    "Onay bekleyen kayıt yok.": "No logs awaiting approval.", "yolcu": "pax",
    # bakım
    "Teknik": "Technical", "Bakım ve uçak durumu": "Maintenance & aircraft status",
    "Başlamış ve bitişi gelmemiş kayıt uçağı o andan itibaren \"Bakımda\" gösterir; bitiş boşsa bakım sürüyor sayılır. Bitiş saati gelince uçak kendiliğinden müsait olur.":
        "A record that has started and not yet ended shows the aircraft as \"In maintenance\" from that moment; with no end date it is treated as ongoing. When the end time passes the aircraft becomes available on its own.",
    "Yeni kayıt": "New record", "Bakım tipi": "Maintenance type", "200 Saatlik, 24 Aylık": "200-Hour, 24-Month", "Bakım yeri": "Location",
    "Bitiş (tahmini, boş bırakılabilir)": "End (estimated, optional)", "Açıklama": "Description", "Kayıtlar": "Records",
    "Tip / yer": "Type / location", "Girilmemiş": "Not set", "Şimdi bitir": "End now", "Sil": "Delete",
    "Günlük kodlar": "Day codes",
    "Uçuş ve bakım kaydı dışındaki gün bilgileri: RON (dış meydanda konaklama), RES (yedek), M (saatsiz bakım günü).":
        "Day information other than flights and maintenance: RON (overnight away), RES (standby), M (maintenance day without times).",
    "Gün": "Day", "Kodu sil": "Remove code",
    # filo
    "Uçaklarımız": "Our aircraft", "Durum anlık hesaplanır: uçuş saatleri, bakım kayıtları ve günlük kodlar birlikte değerlendirilir.":
        "Status is calculated live from flight times, maintenance records and day codes.",
    "Filo kaydındaki durum": "Fleet record status", "Konum": "Location", "Koltuk": "Seats", "Tamamlanan": "Completed",
    "Son uçuş": "Last flight", "Sıradaki uçuş": "Next flight", "Planlı uçuş yok": "No scheduled flights",
    "Bu uçakla kayıt oluştur": "Log a flight on this aircraft", "Uçuşları": "Flights", "Uçak bilgilerini düzenle": "Edit aircraft details",
    "Tescil": "Registration", "Tip": "Type", "Kategori": "Category", "Üs": "Base", "Filoda aktif": "Active in fleet",
    "Yeni uçak": "New aircraft", "Ekle": "Add", "Jet": "Jet", "Turboprop": "Turboprop", "Helikopter": "Helicopter", "uçuş": "flights",
    # kullanıcılar
    "Yönetim": "Administration", "Ad soyad": "Full name", "Rol": "Role", "Aktif": "Active", "Pasif": "Inactive",
    "Şifre sıfırla": "Reset password", "Pasifleştir": "Deactivate", "Aktifleştir": "Activate", "Yeni kullanıcı": "New user",
    "Unvan": "Title", "Kaptan Pilot": "Captain", "İkinci Pilot": "First Officer", "Uçuş Koordinatörü": "Flight Coordinator",
    "Operasyon Müdürü": "Operations Manager", "Geçici şifre (en az 8)": "Temporary password (min. 8)",
    "İşlem geçmişi": "Activity log", "Zaman": "Time", "Kullanıcı": "User", "İşlem": "Action", "Ayrıntı": "Detail",
    "giriş": "signed in", "uçuş kaydı oluşturdu": "created flight log", "uçuş kaydını düzenledi": "edited flight log",
    "uçuşu onayladı": "approved flight", "uçuşu reddetti": "rejected flight", "uçuşu iptal etti": "cancelled flight",
    "bakım kaydı ekledi": "added maintenance", "bakımı kapattı": "closed maintenance", "günlük kod": "day code",
    "uçak kaydı": "aircraft record", "kullanıcı ekledi": "added user", "kullanıcı durumu": "user status",
    "rol değiştirdi": "changed role", "şifre sıfırladı": "reset password", "şifre değiştirdi": "changed password",
    # şifre
    "Şifre değiştir": "Change password", "Mevcut şifre": "Current password", "Yeni şifre (en az 8 karakter)": "New password (min. 8 characters)",
    "Mevcut şifre hatalı.": "Current password is incorrect.", "Yeni şifre en az 8 karakter olmalı.": "New password must be at least 8 characters.",
    "Şifreniz değiştirildi.": "Your password has been changed.",
    # uyarılar
    "Uçuş kaydı oluşturuldu.": "Flight log created.", "Uçuş kaydınız koordinatör onayına gönderildi.": "Your flight log was sent for coordinator approval.",
    "Kayıt güncellendi.": "Record updated.", "Uçuş onaylandı.": "Flight approved.", "Uçuş reddedildi.": "Flight rejected.",
    "Uçuş iptal edildi.": "Flight cancelled.", "Başlangıç tarih-saatini girin.": "Enter the start date and time.",
    "Uçak ve durum seçin.": "Select aircraft and status.", "Bitiş, başlangıçtan sonra olmalı.": "End must be after start.",
    "Bakım kaydı eklendi.": "Maintenance record added.", "Başlamamış bakım kaydı silindi.": "Maintenance record that had not started was deleted.",
    "Bakım şu an itibarıyla bitirildi; uçak tekrar müsait sayılır.": "Maintenance ended as of now; the aircraft counts as available again.",
    "Tarih seçin.": "Select a date.", "Günlük kod kaydedildi.": "Day code saved.", "Tescil, tip ve kategori zorunlu.": "Registration, type and category are required.",
    "Uçak kaydedildi.": "Aircraft saved.", "Bu tescil zaten kayıtlı.": "This registration already exists.",
    "Kullanıcı adı, ad soyad, rol ve en az 8 karakterli şifre zorunlu.": "Username, full name, role and a password of at least 8 characters are required.",
    "Bu kullanıcı adı alınmış.": "This username is taken.", "Kendi hesabınızın rolünü ya da durumunu değiştiremezsiniz.": "You cannot change the role or status of your own account.",
    "Tarih ve saatleri doğru girin (saat SS:DD).": "Enter valid dates and times (HH:MM).", "Uçak seçin.": "Select an aircraft.",
    "Kalkış ve iniş meydanını yazın.": "Enter departure and arrival airports.", "Görev türü seçin.": "Select a mission type.",
    "Kaptan pilot seçin.": "Select the pilot in command.", "Uçuş süresi 16 saati geçemez; saatleri kontrol edin.": "Flight time cannot exceed 16 hours; check the times.",
    "Bu sayfa için yetkiniz yok.": "You do not have permission for this page.", "Kayıt bulunamadı.": "Record not found.",
    "Geçersiz istek.": "Invalid request.", "Genel bakışa dön": "Back to overview",
    "Oturum süresi doldu ya da form geçersiz. Sayfayı yenileyip tekrar deneyin.": "Your session expired or the form is invalid. Refresh the page and try again.",
    # masraflar
    "Masraflar": "Expenses", "Maliyet": "Costs", "Uçuş masrafları": "Flight expenses", "+ Masraf ekle": "+ Add expense",
    "Yakıt, konaklama, park, handling ve diğer özel jet uçuş maliyetleri. Toplamlar para birimine göre ayrı tutulur.":
        "Fuel, accommodation, parking, handling and other private jet flight costs. Totals are kept separately per currency.",
    "Masraf türü": "Expense type", "Tür": "Type", "Bu uçuşa masraf giremezsiniz; listeden bir uçuş seçin.": "You cannot add expenses to this flight; pick a flight from the list.", "Ödeme durumu": "Payment status", "Para birimi": "Currency", "Toplam": "Total",
    "Ödenecek": "To be paid", "Ödendi": "Paid", "Müşteriye yansıtılacak": "Rebill to client", "Yansıtılacak": "To rebill",
    "Masraf türüne göre": "By expense type", "Uçağa göre": "By aircraft", "En maliyetli uçuşlar": "Most expensive flights",
    "Tedarikçi / yer": "Supplier / location", "Miktar": "Quantity", "Tutar": "Amount", "Uçuşa bağlı değil": "Not linked to a flight",
    "Bu filtrelere uyan masraf kaydı yok.": "No expenses match these filters.", "Bu uçuş için masraf girilmemiş.": "No expenses recorded for this flight.",
    "Yeni masraf": "New expense", "Masrafı düzenle": "Edit expense", "Uçak (uçuş yoksa)": "Aircraft (if no flight)", "Birim": "Unit",
    "Tedarikçi": "Supplier", "Yer / meydan": "Location / airport", "Fatura / fiş no": "Invoice / receipt no", "Ödeme yolu": "Payment method",
    "Kaydet ve yeni ekle": "Save and add another", "Masrafı sil": "Delete expense",
    "Masrafı bir uçuşa bağlayın; uçak uçuştan otomatik alınır. Uçuşa bağlı olmayan masraflar (aylık hangar gibi) için uçuşu boş bırakıp uçağı seçin. Tutarda virgül ya da nokta kullanabilirsiniz.":
        "Link the expense to a flight; the aircraft is taken from the flight. For costs not tied to a flight (such as a monthly hangar), leave the flight empty and pick the aircraft. You can use a comma or a dot in amounts.",
    "Jet A-1 ikmali, 2 oda 1 gece": "Jet A-1 uplift, 2 rooms 1 night", "FBO, otel, yakıt şirketi": "FBO, hotel, fuel supplier",
    "Yakıt": "Fuel", "Yer hizmetleri (handling)": "Ground handling", "İniş / yolcu ücreti": "Landing / passenger fees", "Park / hangar": "Parking / hangar",
    "Ekip harcırahı": "Crew per diem", "Ulaşım / transfer": "Ground transport", "Catering": "Catering", "FBO / VIP salon": "FBO / VIP lounge",
    "Navigasyon / overflight": "Navigation / overflight", "İzin / slot": "Permits / slots", "Gümrük / pasaport": "Customs / immigration",
    "Buzlanma önleme": "De-icing", "Hat bakımı": "Line maintenance", "Temizlik": "Cleaning", "Diğer": "Other",
    "gece": "nights", "gün": "days", "saat": "hours", "adet": "pcs",
    "Şirket kartı": "Company card", "Havale / EFT": "Bank transfer", "Nakit": "Cash", "Ekip ödedi (iade edilecek)": "Paid by crew (to reimburse)", "Cari hesap": "On account",
    "Masraf kaydedildi.": "Expense saved.", "Masraf güncellendi.": "Expense updated.", "Masraf silindi.": "Expense deleted.", "Uçuş seçin.": "Select a flight.",
    "Uçuş ya da uçak seçin.": "Select a flight or an aircraft.", "Pilotlar masrafı kendi uçuşlarından birine bağlamalıdır.": "Pilots must link an expense to one of their own flights.",
    "Masraf türü seçin.": "Select an expense type.", "Tutarı doğru girin.": "Enter a valid amount.", "Para birimi seçin.": "Select a currency.",
    "Miktarı doğru girin.": "Enter a valid quantity.", "masraf ekledi": "added expense", "masrafı düzenledi": "edited expense", "masrafı sildi": "deleted expense",
    # aylar / günler
    "Ocak": "January", "Şubat": "February", "Mart": "March", "Nisan": "April", "Mayıs": "May", "Haziran": "June", "Temmuz": "July",
    "Ağustos": "August", "Eylül": "September", "Ekim": "October", "Kasım": "November", "Aralık": "December",
    "Pzt": "Mon", "Sal": "Tue", "Çar": "Wed", "Per": "Thu", "Cum": "Fri", "Cmt": "Sat", "Paz": "Sun",
}
MON = {"Oca": "Jan", "Şub": "Feb", "Mar": "Mar", "Nis": "Apr", "May": "May", "Haz": "Jun", "Tem": "Jul", "Ağu": "Aug",
       "Eyl": "Sep", "Eki": "Oct", "Kas": "Nov", "Ara": "Dec"}
WORD = {"müsait": "available", "görevde": "on duty", "bakımda": "in maintenance", "arızalı": "grounded", "diğer": "other",
        "konaklamada": "overnight", "yedekte": "on standby", "parça bekliyor": "awaiting parts", "uçak": "aircraft", "pilot": "pilot"}


def _when(s):
    s = re.sub(r"\bbugün\b", "today", s)
    return re.sub(r"\b(" + "|".join(MON) + r")\b", lambda m: MON[m.group(1)], s)


RULES = [
    (r"^Bugünkü (\d+) uçuş tamamlandı, son iniş (\d\d:\d\d)$", lambda m: f"Today's {m[1]} flight(s) completed, last landing {m[2]}"),
    (r"^(\d+) Aylık$", lambda m: f"{m[1]}-Month"), (r"^(\d+) Saatlik$", lambda m: f"{m[1]}-Hour"),
    (r"^başlangıç (.+)$", lambda m: "start " + _when(m[1])), (r"^bitiş (.+)$", lambda m: "end " + _when(m[1])),
    (r"^Uçuşta: (.+), tahmini iniş (\d\d:\d\d)$", lambda m: f"Airborne: {m[1]}, est. landing {m[2]}"),
    (r"^Sıradaki kalkış (\d\d:\d\d), (.+)$", lambda m: f"Next departure {m[1]}, {m[2]}"),
    (r"^bakım (\d\d:\d\d) itibarıyla başlıyor$", lambda m: f"maintenance starts at {m[1]}"),
    (r"^Faal \(şu an (.+)\)$", lambda m: f"Active (currently {WORD.get(m[1], m[1])})"),
    (r"^(\d+) uçak (.+)$", lambda m: f"{m[1]} aircraft {WORD.get(m[2], m[2])}"),
    (r"^(\d+) (müsait|görevde|bakımda|arızalı|diğer)$", lambda m: f"{m[1]} {WORD[m[2]]}"),
    (r"^(\d+) sa (\d+) dk$", lambda m: f"{m[1]} h {m[2]} min"),
    (r"^Şu an (.+?) · (.*)$", lambda m: f"Now {T_en(m[1])} · {T_en(m[2])}"),
    (r"^(\d+) uçuş: (.+)$", lambda m: f"{m[1]} flight(s): {m[2]}"),
    (r"^(\d+) uçuş kaydı onay bekliyor$", lambda m: f"{m[1]} flight log(s) awaiting approval"),
    (r"^Çakışma: (.+) uçuşu ile aynı (uçak|pilot)\.$", lambda m: f"Conflict: same {WORD[m[2]]} as flight {m[1]}."),
    (r"^(\S+) bu saatlerde (.+) \((.+)\)\.$", lambda m: f"{m[1]} is {T_en(m[2][:1].upper() + m[2][1:]).lower()} at these times ({T_en(m[3])})."),
    (r"^Yolcu sayısı 0 ile (\d+) arasında olmalı\.$", lambda m: f"Passengers must be between 0 and {m[1]}."),
    (r"^Bakım kaydı eklendi\. Dikkat: bu aralıkta (\d+) uçuş kaydı var\.$", lambda m: f"Maintenance record added. Note: there are {m[1]} flight log(s) in this period."),
    (r"^Yeni geçici şifre: (\S+) .*$", lambda m: f"New temporary password: {m[1]}  (share it with the user; they should change it at first sign-in)"),
    (r"^(.+) eklendi\.$", lambda m: f"{m[1]} added."),
    (r"^(\d+) uçuş · (\d+) sa (\d+) dk$", lambda m: f"{m[1]} flights · {m[2]} h {m[3]} min"),
]
RULES = [(re.compile(p), f) for p, f in RULES]


def T_en(s):
    if s is None:
        return ""
    s = str(s)
    if s in EN:
        return EN[s]
    if " · " in s:
        return " · ".join(T_en(p) for p in s.split(" · "))
    if ", " in s and re.match(r"^\d+ uçak ", s):
        return ", ".join(T_en(p) for p in s.split(", "))
    for rx, fn in RULES:
        m = rx.match(s)
        if m:
            return fn(m)
    return s


# --- şablon dönüştürücü: sabit Türkçe metinleri T("...") çağrısına çevirir
_PROTECT = re.compile(r"(<style.*?</style>|<svg.*?</svg>|<script.*?</script>)", re.S)
_JINJA = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})", re.S)
_TEXT = re.compile(r">([^<>]+)<")
_LIT = re.compile(r"(?<!T\()(?<![=!]=)(?<![=!]= )'([^'{}\\]+)'(?!\s*[=!]=)")
_ATTR = re.compile(r'\b(placeholder|title)="([^"{}]+)"')
_PUNCT = " \n\t·,:→–-()"


def _wrap_core(seg):
    core = seg.strip()
    if core not in EN:
        core = seg.strip(_PUNCT)
    if not core or core not in EN:
        return seg
    i = seg.index(core)
    return seg[:i] + "{{ T(" + repr(core) + ") }}" + seg[i + len(core):]


def _text(match):
    inner = match.group(1)
    parts = _JINJA.split(inner)
    return ">" + "".join(p if _JINJA.fullmatch(p) else _wrap_core(p) for p in parts) + "<"


_STR = re.compile(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"")


def _expr(block):
    """{{ ... }} içindeki metin sabitlerini sırayla (tırnak eşleşmesini bozmadan) dolaşır; karşılaştırmada kullanılanlara dokunmaz."""
    if block.startswith("{%"):
        return block
    out, pos = [], 0
    for m in _STR.finditer(block):
        lit = m.group(0)[1:-1]
        before, after = block[:m.start()].rstrip(), block[m.end():].lstrip()
        compared = before.endswith(("==", "!=")) or after.startswith(("==", "!=")) or before.endswith("T(")
        out.append(block[pos:m.start()])
        out.append("T(" + repr(lit) + ")" if lit in EN and not compared else m.group(0))
        pos = m.end()
    out.append(block[pos:])
    return "".join(out)


def translate_template(src):
    pieces = _PROTECT.split(src)
    out = []
    for p in pieces:
        if _PROTECT.fullmatch(p):
            out.append(p)
            continue
        p = _TEXT.sub(_text, p)
        p = _JINJA.sub(lambda m: _expr(m.group(0)), p)
        p = _ATTR.sub(lambda m: f'{m.group(1)}="{{{{ T({m.group(2)!r}) }}}}"' if m.group(2) in EN else m.group(0), p)
        out.append(p)
    return "".join(out)
