import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import time

# --- KURUMSAL AYARLAR ---
st.set_page_config(
    page_title="Akyurt Kütüphane YS",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    h1 { font-size: 3rem !important; color: #4A90E2; font-weight: 700; }
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
    .big-table th { text-align: left; background-color: #333; color: #4A90E2; padding: 15px; font-size: 1.3rem; border-bottom: 2px solid #555; }
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
    st.markdown("## 🏛️ AKYURT KÜTÜPHANESİ")
    st.markdown("Yönetim Paneli v4.0")
    st.markdown("---")
    menu = st.radio("ANA MENÜ",
                    ["Operasyon Merkezi", "Ödünç ve İade", "📚 Kitap Yönetimi", "👥 Üye Yönetimi"],
                    label_visibility="collapsed")
    st.markdown("---")
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
# 2. MODÜL: ÖDÜNÇ VE İADE
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
                end_date = datetime.now() + timedelta(days=days)
                conn.execute(
                    "INSERT INTO transactions (book_id, member_id, issue_date, due_date) VALUES (?, ?, DATE('now'), ?)",
                    (books[sel_bk], members[sel_mem], end_date.strftime('%Y-%m-%d')))
                conn.execute("UPDATE books SET status = 'Ödünçte' WHERE id = ?", (books[sel_bk],))
                conn.commit()
                conn.close()
                st.success("İşlem tamamlandı.")
                time.sleep(1)
                st.rerun()

    with tab2:
        st.markdown("### İade Alma Ekranı")
        conn = get_db_connection()
        loans = pd.read_sql(
            "SELECT t.id, b.title, m.name FROM transactions t JOIN books b ON t.book_id=b.id JOIN members m ON t.member_id=m.id WHERE t.status='Aktif'",
            conn)
        conn.close()

        if loans.empty:
            st.info("İade bekleyen kitap yok.")
        else:
            loan_dict = {f"{row['title']} - {row['name']}": row['id'] for i, row in loans.iterrows()}
            sel_ret = st.selectbox("İade Edilen:", list(loan_dict.keys()))

            if st.button("İADEYİ ONAYLA"):
                tid = loan_dict[sel_ret]
                conn = get_db_connection()
                conn.execute("UPDATE transactions SET return_date=DATE('now'), status='Tamamlandı' WHERE id=?", (tid,))
                bid = conn.execute("SELECT book_id FROM transactions WHERE id=?", (tid,)).fetchone()[0]
                conn.execute("UPDATE books SET status='Müsait' WHERE id=?", (bid,))
                conn.commit()
                conn.close()
                st.success("İade alındı.")
                time.sleep(1)
                st.rerun()

# ========================================================
# 3. MODÜL: KİTAP YÖNETİMİ (YENİ CRUD SİSTEMİ)
# ========================================================
elif menu == "📚 Kitap Yönetimi":
    st.title("Kitap Envanter Yönetimi")

    tab_list, tab_add, tab_edit = st.tabs(["📋 Kitap Listesi", "➕ Yeni Kitap Ekle", "✏️ Düzenle / Sil"])

    # --- LİSTELEME ---
    with tab_list:
        search = st.text_input("Kitap Ara:", placeholder="Kitap adı, yazar...")
        conn = get_db_connection()
        q = "SELECT title as 'Eser', author as 'Yazar', location as 'Raf', status as 'Durum', isbn as 'ISBN' FROM books"
        if search: q += f" WHERE title LIKE '%{search}%' OR author LIKE '%{search}%'"
        df = pd.read_sql(q, conn)
        st.markdown(create_custom_table(df), unsafe_allow_html=True)
        conn.close()

    # --- EKLEME ---
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
                        st.error("Kitap adı ve Yazar zorunludur.")

    # --- DÜZENLEME / SİLME ---
    with tab_edit:
        st.markdown("### Kitap Düzenle veya Sil")

        # Tüm kitapları (ID'leri ile) çekelim
        all_books = get_books_dict()  # Tüm kitaplar (müsait/ödünçte farketmez)

        if not all_books:
            st.warning("Düzenlenecek kitap yok.")
        else:
            selected_book_key = st.selectbox("İşlem Yapılacak Kitabı Seç:", list(all_books.keys()))
            selected_book_id = all_books[selected_book_key]

            conn = get_db_connection()
            # Seçilen kitabın mevcut bilgilerini getir
            curr_book = conn.execute("SELECT * FROM books WHERE id=?", (selected_book_id,)).fetchone()
            conn.close()

            # Form içinde göster (Index 1=title, 2=author, 3=isbn, 4=location)
            with st.form("edit_book_form"):
                st.info(f"Seçilen Kitap ID: {selected_book_id}")
                new_title = st.text_input("Kitap Adı", value=curr_book[1])
                new_author = st.text_input("Yazar", value=curr_book[2])
                new_loc = st.text_input("Raf Yeri", value=curr_book[4])

                c1, c2 = st.columns(2)
                update_btn = c1.form_submit_button("💾 BİLGİLERİ GÜNCELLE")
                delete_btn = c2.form_submit_button("🗑️ KİTABI SİL (DİKKAT)")

                if update_btn:
                    conn = get_db_connection()
                    conn.execute("UPDATE books SET title=?, author=?, location=? WHERE id=?",
                                 (new_title, new_author, new_loc, selected_book_id))
                    conn.commit()
                    conn.close()
                    st.success("Bilgiler güncellendi!")
                    time.sleep(1)
                    st.rerun()

                if delete_btn:
                    conn = get_db_connection()
                    # Önce kontrol: Kitap ödünçte mi?
                    status = conn.execute("SELECT status FROM books WHERE id=?", (selected_book_id,)).fetchone()[0]
                    if status == 'Ödünçte':
                        st.error("HATA: Bu kitap şu an ödünçte olduğu için silinemez! Önce iade alın.")
                    else:
                        conn.execute("DELETE FROM books WHERE id=?", (selected_book_id,))
                        conn.commit()
                        st.success("Kitap silindi.")
                        time.sleep(1)
                        st.rerun()
                    conn.close()

# ========================================================
# 4. MODÜL: ÜYE YÖNETİMİ (YENİ CRUD SİSTEMİ)
# ========================================================
elif menu == "👥 Üye Yönetimi":
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