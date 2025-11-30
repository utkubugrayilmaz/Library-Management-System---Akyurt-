import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import time
import base64
import os

# --- KURUMSAL AYARLAR (AKYURT BELEDİYESİ) ---
st.set_page_config(
    page_title="Akyurt Belediyesi | Kütüphane Bilgi Sistemi",
    page_icon="https://www.akyurt.bel.tr/wp-content/uploads/2019/07/logo-1.png", # Belediye Favicon
    layout="wide",
    initial_sidebar_state="expanded"
)
# --- RESMİ KODA ÇEVİREN FONKSİYON ---
def get_img_as_base64(file_path):
    if not os.path.exists(file_path):
        return ""
    with open(file_path, "rb") as f:
        data = f.read()
    return f"data:image/png;base64,{base64.b64encode(data).decode()}"

# --- CSS: MAKSİMUM OKUNABİLİRLİK VE DEVASA KARTLAR ---
st.markdown("""
<style>
    /* 1. GENEL YAZI BOYUTU */
    html, body, p, div, span, label {
        font-family: 'Segoe UI', sans-serif;
        font-size: 20px !important; 
        line-height: 1.6;
    }

    /* 2. BAŞLIKLAR */
    h1 { font-size: 3rem !important; color: #0056b3; font-weight: 700; }
    h2 { font-size: 2.4rem !important; border-bottom: 2px solid #444; margin-bottom: 20px; }
    h3 { font-size: 1.8rem !important; color: #ddd; }

    /* 3. KPI KARTLARI (SAYILARIN OLDUĞU KUTULAR) */
    div[data-testid="stMetric"] {
        background-color: #222;       
        border: 2px solid #555;       
        padding: 10px;                
        border-radius: 12px;          
        box-shadow: 2px 2px 10px rgba(0,0,0,0.5); 
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        min-height: 150px; 
    }

    /* Kartın Başlığı */
    div[data-testid="stMetricLabel"] {
        font-size: 1.5rem !important; 
        color: #bbb;
        width: 100%;
        text-align: center !important;
    }

    /* Kartın Değeri (Sayılar) */
    div[data-testid="stMetricValue"], 
    div[data-testid="stMetricValue"] > div {
        font-size: 70px !important; 
        font-weight: 900 !important;
        color: white;
        text-align: center !important;
        line-height: 1.1;
    }

    /* 4. INPUT VE BUTONLAR */
    .stSelectbox div[data-baseweb="select"] > div { height: 3.5rem; }
    .stSelectbox div[data-baseweb="select"] span { font-size: 1.2rem !important; }
    .stTextInput input { font-size: 1.2rem !important; height: 3.5rem; }
    .stButton button { font-size: 1.4rem !important; height: 4rem !important; font-weight: bold; }

    /* 5. MENÜ VE TABLO */
    section[data-testid="stSidebar"] .stRadio label { font-size: 1.4rem !important; padding: 15px 5px; }

    .big-table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 1.2rem; }
    .big-table th { text-align: left; background-color: #333; color: #0056b3; padding: 15px; font-size: 1.3rem; border-bottom: 2px solid #555; }
    .big-table td { padding: 15px; border-bottom: 1px solid #444; color: #eee; }
    .big-table tr:hover { background-color: #222; }
    .alert-row { color: #ff6b6b !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


# --- YARDIMCI: HTML TABLO ---
def create_custom_table(df, alert_col=None):
    if df.empty: return "<div style='padding:20px; font-size:1.2rem;'>Kayıt bulunamadı.</div>"
    html = '<table class="big-table"><thead><tr>'
    for col in df.columns: html += f'<th>{col}</th>'
    html += '</tr></thead><tbody>'
    for index, row in df.iterrows():
        html += '<tr>'
        for col in df.columns:
            val = row[col]
            style = "class='alert-row'" if alert_col and col == alert_col else ""
            html += f'<td {style}>{val}</td>'
        html += '</tr>'
    html += '</tbody></table>'
    return html


# --- VERİTABANI BAĞLANTISI ---
def get_db_connection():
    conn = sqlite3.connect('library.db', check_same_thread=False)
    # Rezervasyon tablosunu kontrol et
    conn.execute('''
            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER,
                member_id INTEGER,
                request_date DATE,
                status TEXT DEFAULT 'Bekliyor',
                FOREIGN KEY (book_id) REFERENCES books (id),
                FOREIGN KEY (member_id) REFERENCES members (id)
            )
        ''')
    conn.commit()
    return conn


def get_books_dict(only_available=False):
    conn = get_db_connection()
    query = "SELECT id, title, author, location FROM books"
    if only_available: query += " WHERE status='Müsait'"
    df = pd.read_sql(query, conn)
    conn.close()
    if df.empty: return {}
    return {f"{row['title']} | {row['author']} (Raf: {row['location']})": row['id'] for i, row in df.iterrows()}


def get_members_dict():
    conn = get_db_connection()
    df = pd.read_sql("SELECT id, name, phone FROM members", conn)
    conn.close()
    if df.empty: return {}
    return {f"{row['name']} ({row['phone']})": row['id'] for i, row in df.iterrows()}


# --- UYGULAMA BAŞLANGICI ---

with st.sidebar:
    # --- YEREL LOGOYU GÖSTERME KODU ---
    logo_path = "akyurt_logo.png"
    img_base64 = get_img_as_base64(logo_path)

    # Resim varsa onu göster, yoksa sadece yazı yaz
    if img_base64:
        st.markdown(
            f"""
            <div style="text-align: center; padding-top: 10px;">
                <img src="{img_base64}" width="130">
                <br><br>
                <h3 style="color: #ffffff; margin:0; font-weight: 800; font-size: 22px;">AKYURT BELEDİYESİ</h3>
                <p style="color: #a3a3a3; font-size: 15px; margin-top: 5px;">Millet Kıraathanesi<br>Yönetim Sistemi v5.3</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown("## AKYURT KÜTÜPHANESİ")
        st.warning("Logo bulunamadı! (akyurt_logo.png)")

    st.markdown("---")
    # (Buradan sonra menu = st.radio... diye devam ediyor, oraya dokunma)

    # --- MENÜ ---
    # Not: Buradaki isimler aşağıdaki if/elif bloklarıyla birebir aynı olmalı!
    menu = st.radio("ANA MENÜ",
                    ["Operasyon Merkezi", "Ödünç ve İade", "Rezervasyon", "Kitap Yönetimi", "Üye Yönetimi"],
                    label_visibility="collapsed")

    st.markdown("---")

    # --- TARİH BİLGİSİ ---
    st.info(f"📅 Tarih: {datetime.now().strftime('%d.%m.%Y')}")

# ========================================================
# 1. MODÜL: OPERASYON MERKEZİ (DASHBOARD)
# ========================================================
if menu == "Operasyon Merkezi":
    st.title("Operasyon Merkezi")

    conn = get_db_connection()

    total_books = pd.read_sql("SELECT COUNT(*) FROM books", conn).iloc[0, 0]
    total_members = pd.read_sql("SELECT COUNT(*) FROM members", conn).iloc[0, 0]

    df_trans = pd.read_sql("""
        SELECT t.id, m.name as 'Üye', b.title as 'Eser', 
        t.due_date as 'Teslim Tarihi', m.phone as 'Telefon',
        (julianday('now') - julianday(t.due_date)) as gecikme
        FROM transactions t
        JOIN members m ON t.member_id = m.id
        JOIN books b ON t.book_id = b.id
        WHERE t.status = 'Aktif'
    """, conn)

    active_loans = len(df_trans)
    overdue_df = df_trans[df_trans['gecikme'] > 0].copy()

    # KPI KARTLARI (DEVASA PUNTOLU)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Kitap", total_books)
    c2.metric("Toplam Üye", total_members)
    c3.metric("Ödünç Verilen", active_loans)
    c4.metric("Geciken İade", len(overdue_df))

    st.markdown("---")

    if not overdue_df.empty:
        st.subheader("⚠️ DİKKAT: Teslim Tarihi Geçenler")
        display_df = overdue_df[['Üye', 'Eser', 'Teslim Tarihi', 'Telefon']].copy()
        display_df['Gecikme Süresi'] = overdue_df['gecikme'].astype(int).astype(str) + " GÜN"

        st.markdown(create_custom_table(display_df, alert_col="Gecikme Süresi"), unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("### 🔔 SMS Paneli")
            c_sel, c_btn = st.columns([3, 1])
            selected_person = c_sel.selectbox("Kişi Seç:", overdue_df['Üye'] + " - " + overdue_df['Eser'])
            if c_btn.button("SMS GÖNDER"):
                st.success(f"✅ SMS İletildi: {selected_person}")
    else:
        st.success("Gecikmiş iade bulunmuyor.")

# ========================================================
# 2. MODÜL: ÖDÜNÇ VE İADE (BUG FIX YAPILDI ✅)
# ========================================================
elif menu == "Ödünç ve İade":
    st.title("Ödünç ve İade İşlemleri")

    tab1, tab2 = st.tabs(["📤 KİTAP VER (ÖDÜNÇ)", "📥 KİTAP AL (İADE)"])

    with tab1:
        st.markdown("### Ödünç Verme Ekranı")
        books = get_books_dict(only_available=True)
        members = get_members_dict()

        if not books:
            st.error("Stokta kitap kalmadı.")
        else:
            sel_mem = st.selectbox("Üye Seç:", list(members.keys()))
            sel_bk = st.selectbox("Kitap Seç:", list(books.keys()))
            days = st.slider("Süre (Gün):", 1, 14, 14)

            if st.button("ÖDÜNÇ VER", type="primary"):
                conn = get_db_connection()

                # --- REZERVASYON KONTROLÜ ---
                bk_id = books[sel_bk]
                res_check = conn.execute(
                    "SELECT m.name FROM reservations r JOIN members m ON r.member_id = m.id WHERE r.book_id=? AND r.status='Bekliyor'",
                    (bk_id,)).fetchone()

                allow = True
                if res_check:
                    res_owner = res_check[0]
                    if sel_mem.split(" (")[0] != res_owner:
                        st.error(f"⛔ DUR! Bu kitap **{res_owner}** adına rezerve edilmiş.")
                        allow = False
                    else:
                        conn.execute(
                            "UPDATE reservations SET status='Tamamlandı' WHERE book_id=? AND status='Bekliyor'",
                            (bk_id,))

                if allow:
                    end_date = datetime.now() + timedelta(days=days)
                    conn.execute(
                        "INSERT INTO transactions (book_id, member_id, issue_date, due_date) VALUES (?, ?, DATE('now'), ?)",
                        (books[sel_bk], members[sel_mem], end_date.strftime('%Y-%m-%d')))
                    conn.execute("UPDATE books SET status = 'Ödünçte' WHERE id = ?", (books[sel_bk],))
                    conn.commit()
                    st.success("İşlem tamamlandı.")
                    time.sleep(1)
                    st.rerun()

                conn.close()

    with tab2:
        st.markdown("### İade Alma Ekranı")
        conn = get_db_connection()
        loans = pd.read_sql(
            "SELECT t.id, b.title, m.name, b.id as book_id FROM transactions t JOIN books b ON t.book_id=b.id JOIN members m ON t.member_id=m.id WHERE t.status='Aktif'",
            conn)

        if loans.empty:
            st.info("İade bekleyen kitap yok.")
            conn.close()
        else:
            loan_dict = {f"{row['title']} - {row['name']}": (row['id'], row['book_id']) for i, row in loans.iterrows()}
            sel_ret = st.selectbox("İade Edilen:", list(loan_dict.keys()))

            if st.button("İADEYİ ONAYLA"):
                trans_id, book_id = loan_dict[sel_ret]

                # 1. İadeyi Yap
                conn.execute("UPDATE transactions SET return_date=DATE('now'), status='Tamamlandı' WHERE id=?",
                             (trans_id,))
                conn.execute("UPDATE books SET status='Müsait' WHERE id=?", (book_id,))

                # 2. Rezervasyon Kontrolü (Bağlantı hala açık!)
                res_check = conn.execute("""
                    SELECT m.name, m.phone FROM reservations r 
                    JOIN members m ON r.member_id = m.id 
                    WHERE r.book_id=? AND r.status='Bekliyor' 
                    ORDER BY r.request_date ASC LIMIT 1
                """, (book_id,)).fetchone()

                conn.commit()  # Değişiklikleri kaydet

                st.success("Kitap iade alındı.")

                # 3. Uyarı varsa göster
                if res_check:
                    st.warning(f"DİKKAT! Bu kitap için sırada bekleyen var: **{res_check[0]}**")
                    st.info(f"İletişim: {res_check[1]}")
                    time.sleep(5)  # Okuması için bekle
                else:
                    time.sleep(1)

                conn.close()  # <--- ARTIK KAPATABİLİRİZ
                st.rerun()

# ========================================================
# YENİ MODÜL: REZERVASYON
# ========================================================
elif menu == "Rezervasyon":
    st.title("Kitap Rezervasyon Sistemi")

    col1, col2 = st.columns([1, 1])

    # SOL: Talep Oluştur
    with col1:
        st.markdown("### ➕ Sıraya Gir (Talep)")
        with st.container(border=True):
            # Sadece ÖDÜNÇTE olan kitaplar listelenir
            conn = get_db_connection()
            # Ödünçteki kitapları bul
            borrowed_df = pd.read_sql("SELECT id, title, author FROM books WHERE status='Ödünçte'", conn)
            books_borrowed = {f"{row['title']} | {row['author']}": row['id'] for i, row in borrowed_df.iterrows()}
            conn.close()

            members = get_members_dict()

            if not books_borrowed:
                st.success("Tüm kitaplar rafta! Rezervasyona gerek yok, direkt ödünç verebilirsiniz.")
            else:
                r_mem = st.selectbox("Talep Eden Üye:", list(members.keys()))
                r_bk = st.selectbox("İstenen Kitap (Sadece Ödünçtekiler):", list(books_borrowed.keys()))

                if st.button("REZERVASYON OLUŞTUR"):
                    conn = get_db_connection()
                    bk_id = books_borrowed[r_bk]
                    mem_id = members[r_mem]

                    # Zaten sırada mı?
                    check = conn.execute(
                        "SELECT * FROM reservations WHERE book_id=? AND member_id=? AND status='Bekliyor'",
                        (bk_id, mem_id)).fetchone()
                    if check:
                        st.error("Bu üye zaten bu kitap için sırada bekliyor.")
                    else:
                        conn.execute(
                            "INSERT INTO reservations (book_id, member_id, request_date) VALUES (?, ?, DATE('now'))",
                            (bk_id, mem_id))
                        conn.commit()
                        st.success(f"Rezervasyon başarıyla alındı.")
                    conn.close()

    # SAĞ: Bekleyenler Listesi
    with col2:
        st.markdown("### Bekleyen Talepler")
        conn = get_db_connection()
        res_df = pd.read_sql("""
            SELECT r.id, b.title as 'Kitap', m.name as 'Üye', r.request_date as 'Tarih'
            FROM reservations r
            JOIN books b ON r.book_id = b.id
            JOIN members m ON r.member_id = m.id
            WHERE r.status = 'Bekliyor'
            ORDER BY r.request_date ASC
        """, conn)
        conn.close()

        if res_df.empty:
            st.info("Sırada bekleyen kimse yok.")
        else:
            # HTML Tablo ile göster
            st.markdown(create_custom_table(res_df), unsafe_allow_html=True)

            # İptal Etme Alanı
            st.markdown("---")
            cancel_id = st.selectbox("İptal Edilecek Talep ID:", res_df['id'])
            if st.button("TALEBİ İPTAL ET"):
                conn = get_db_connection()
                conn.execute("UPDATE reservations SET status='İptal' WHERE id=?", (cancel_id,))
                conn.commit()
                conn.close()
                st.success("Talep silindi.")
                time.sleep(1)
                st.rerun()

# ========================================================
# 4. MODÜL: KİTAP YÖNETİMİ (GELİŞMİŞ FİLTRELEME)
# ========================================================
elif menu == "Kitap Yönetimi":
    st.title("Kitap Envanter Yönetimi")

    # Yeni Tab Yapısı: Tümü | Ödünçtekiler | Ekle | Düzenle
    tab_list, tab_loaned, tab_add, tab_edit = st.tabs(
        ["Tüm Envanter", "Ödünçtekiler & Sıra", "Yeni Ekle", "Düzenle / Sil"])

    # --- 1. TÜM ENVANTER ---
    with tab_list:
        search = st.text_input("Kitap Ara:", placeholder="Kitap adı, yazar...")
        conn = get_db_connection()
        q = "SELECT title as 'Eser', author as 'Yazar', location as 'Raf', status as 'Durum' FROM books"
        if search: q += f" WHERE title LIKE '%{search}%' OR author LIKE '%{search}%'"
        df = pd.read_sql(q, conn)
        st.markdown(create_custom_table(df), unsafe_allow_html=True)
        conn.close()

    # --- 2. ÖDÜNÇTEKİLER VE SIRA DURUMU (YENİ ÖZELLİK) ---
    with tab_loaned:
        st.markdown("### Şu An Dışarıda Olan Kitaplar")
        conn = get_db_connection()
        # Bu sorgu biraz karmaşık: Kitabı alanı, tarihi ve O KİTAP İÇİN BEKLEYEN REZERVASYON SAYISINI getirir.
        q_loaned = """
        SELECT b.title as 'Eser', m.name as 'Alan Üye', t.due_date as 'Dönüş Tarihi',
        (SELECT COUNT(*) FROM reservations r WHERE r.book_id = b.id AND r.status='Bekliyor') as 'Sırada Bekleyen'
        FROM transactions t
        JOIN books b ON t.book_id = b.id
        JOIN members m ON t.member_id = m.id
        WHERE t.status = 'Aktif'
        """
        df_loaned = pd.read_sql(q_loaned, conn)

        if df_loaned.empty:
            st.info("Şu an dışarıda hiç kitap yok.")
        else:
            # Bekleyen varsa o sütunu kırmızı gösterelim
            df_loaned['Sırada Bekleyen'] = df_loaned['Sırada Bekleyen'].apply(lambda x: f"{x} KİŞİ" if x > 0 else "-")
            st.markdown(create_custom_table(df_loaned, alert_col="Sırada Bekleyen"), unsafe_allow_html=True)
        conn.close()

    # --- 3. EKLEME ---
    with tab_add:
        st.markdown("### Yeni Eser Girişi")
        with st.container(border=True):
            with st.form("add_book_form"):
                col1, col2 = st.columns(2)
                t = col1.text_input("Kitap Adı")
                a = col2.text_input("Yazar")
                l = col1.text_input("Raf Numarası")
                i = col2.text_input("ISBN (Opsiyonel)")

                if st.form_submit_button("KİTABI KAYDET"):
                    if t and a:
                        conn = get_db_connection()
                        conn.execute("INSERT INTO books (title, author, location, isbn) VALUES (?, ?, ?, ?)",
                                     (t, a, l, i))
                        conn.commit()
                        conn.close()
                        st.success(f"'{t}' envantere eklendi.")
                    else:
                        st.error("Eksik bilgi.")

    # --- 4. DÜZENLEME / SİLME ---
    with tab_edit:
        st.markdown("### Kitap Düzenle veya Sil")
        all_books = get_books_dict()

        if not all_books:
            st.warning("Kitap yok.")
        else:
            selected_book_key = st.selectbox("İşlem Yapılacak Kitap:", list(all_books.keys()))
            selected_book_id = all_books[selected_book_key]

            conn = get_db_connection()
            curr_book = conn.execute("SELECT * FROM books WHERE id=?", (selected_book_id,)).fetchone()
            conn.close()

            with st.form("edit_book_form"):
                new_title = st.text_input("Kitap Adı", value=curr_book[1])
                new_author = st.text_input("Yazar", value=curr_book[2])
                new_loc = st.text_input("Raf Yeri", value=curr_book[4])

                c1, c2 = st.columns(2)
                if c1.form_submit_button("💾 GÜNCELLE"):
                    conn = get_db_connection()
                    conn.execute("UPDATE books SET title=?, author=?, location=? WHERE id=?",
                                 (new_title, new_author, new_loc, selected_book_id))
                    conn.commit();
                    conn.close()
                    st.success("Güncellendi!")
                    time.sleep(1);
                    st.rerun()

                if c2.form_submit_button("🗑️ SİL"):
                    conn = get_db_connection()
                    status = conn.execute("SELECT status FROM books WHERE id=?", (selected_book_id,)).fetchone()[0]
                    if status == 'Ödünçte':
                        st.error("Bu kitap ödünçte, silinemez!")
                    else:
                        conn.execute("DELETE FROM books WHERE id=?", (selected_book_id,))
                        conn.commit()
                        st.success("Silindi.")
                        time.sleep(1);
                        st.rerun()
                    conn.close()

# ========================================================
# 4. MODÜL: ÜYE YÖNETİMİ (YENİ CRUD SİSTEMİ)
# ========================================================
elif menu == "Üye Yönetimi":
    st.title("Üye Veritabanı Yönetimi")

    tab_list, tab_add, tab_edit = st.tabs(["📋 Üye Listesi", "➕ Yeni Üye Ekle", "✏️ Düzenle / Sil"])

    with tab_list:
        conn = get_db_connection()
        df = pd.read_sql(
            "SELECT name as 'Ad Soyad', phone as 'Telefon', email as 'E-Posta', join_date as 'Kayıt Tarihi' FROM members",
            conn)
        st.markdown(create_custom_table(df), unsafe_allow_html=True)
        conn.close()

    with tab_add:
        st.markdown("### Yeni Üye Kaydı")
        with st.container(border=True):
            with st.form("add_member_form"):
                nm = st.text_input("Ad Soyad")
                ph = st.text_input("Telefon")
                em = st.text_input("E-Posta")

                if st.form_submit_button("ÜYEYİ KAYDET"):
                    if nm and ph:
                        conn = get_db_connection()
                        conn.execute(
                            "INSERT INTO members (name, phone, email, join_date) VALUES (?, ?, ?, DATE('now'))",
                            (nm, ph, em))
                        conn.commit()
                        conn.close()
                        st.success(f"{nm} sisteme eklendi.")
                    else:
                        st.error("Ad ve Telefon zorunludur.")

    with tab_edit:
        st.markdown("### Üye Bilgilerini Düzenle")
        all_members = get_members_dict()

        if not all_members:
            st.warning("Kayıtlı üye yok.")
        else:
            sel_mem_key = st.selectbox("İşlem Yapılacak Üyeyi Seç:", list(all_members.keys()))
            sel_mem_id = all_members[sel_mem_key]

            conn = get_db_connection()
            curr_mem = conn.execute("SELECT * FROM members WHERE id=?", (sel_mem_id,)).fetchone()
            conn.close()

            with st.form("edit_mem_form"):
                new_name = st.text_input("Ad Soyad", value=curr_mem[1])
                new_phone = st.text_input("Telefon", value=curr_mem[2])
                new_email = st.text_input("E-Posta", value=curr_mem[3])

                c1, c2 = st.columns(2)
                upd_btn = c1.form_submit_button("💾 GÜNCELLE")
                del_btn = c2.form_submit_button("🗑️ ÜYEYİ SİL")

                if upd_btn:
                    conn = get_db_connection()
                    conn.execute("UPDATE members SET name=?, phone=?, email=? WHERE id=?",
                                 (new_name, new_phone, new_email, sel_mem_id))
                    conn.commit()
                    conn.close()
                    st.success("Üye bilgileri güncellendi.")
                    time.sleep(1)
                    st.rerun()

                if del_btn:
                    conn = get_db_connection()
                    # Kontrol: Üyenin üstünde kitap var mı?
                    active_loan = conn.execute("SELECT COUNT(*) FROM transactions WHERE member_id=? AND status='Aktif'",
                                               (sel_mem_id,)).fetchone()[0]

                    if active_loan > 0:
                        st.error(f"HATA: Bu üyenin elinde {active_loan} adet iade edilmemiş kitap var. Silinemez!")
                    else:
                        conn.execute("DELETE FROM members WHERE id=?", (sel_mem_id,))
                        conn.commit()
                        st.success("Üye silindi.")
                        time.sleep(1)
                        st.rerun()
                    conn.close()

# --- FOOTER (ORTALI VE SABİT) ---
st.markdown("""
<style>
.footer {
    position: fixed; 
    left: 0; 
    bottom: 0; 
    width: 100%; 
    background-color: #111; 
    color: grey;
    text-align: center; 
    font-size: 12px; 
    padding: 10px 0; 
    z-index: 999;
    display: flex; 
    justify-content: center; 
    align-items: center; 
    border-top: 1px solid #333;
}
</style>
<div class="footer">
    T.C. Akyurt Belediyesi Bilgi İşlem Müdürlüğü © 2025 | Millet Kıraathanesi Yönetim Sistemi v5.3 | Utku Buğra YILMAZ | KVKK Aydınlatma Metni
</div>
""", unsafe_allow_html=True)