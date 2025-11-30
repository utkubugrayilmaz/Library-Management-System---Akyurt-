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

# --- CSS: MAKSİMUM OKUNABİLİRLİK VE DEVASA KARTLAR (FINAL) ---
st.markdown("""
<style>
    /* 1. GENEL YAZI BOYUTU - HER ŞEY İÇİN */
    html, body, p, div, span {
        font-family: 'Segoe UI', sans-serif;
        font-size: 20px !important; /* Standart metin boyutu */
        line-height: 1.6;
    }

    /* 2. BAŞLIKLAR */
    h1 { font-size: 3rem !important; color: #4A90E2; font-weight: 700; }
    h2 { font-size: 2.4rem !important; border-bottom: 2px solid #444; margin-bottom: 20px; }
    h3 { font-size: 1.8rem !important; color: #ddd; }

    /* 3. KPI KARTLARI (SAYILARIN OLDUĞU KUTULAR) - DEVASA VE ORTALI */
    div[data-testid="stMetric"] {
        background-color: #222;       /* Kutu arka planı koyu gri */
        border: 2px solid #555;       /* Çerçeve */
        padding: 15px 0px;            /* Dikey boşluk */
        border-radius: 12px;          /* Köşeleri yuvarla */
        box-shadow: 2px 2px 5px rgba(0,0,0,0.5); /* Hafif gölge */

        /* MERKEZLEME AYARLARI */
        text-align: center !important; 
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 160px; /* Kutuların hepsi eşit boyda dursun */
    }

    /* Kartın Başlığı (Toplam Envanter vb.) */
    div[data-testid="stMetricLabel"] {
        font-size: 1.4rem !important; 
        color: #bbb;
        width: 100%;
        text-align: center !important;
        justify-content: center !important;
        display: flex;
    }
    div[data-testid="stMetricLabel"] p {
        font-size: 1.4rem !important;
    }

    /* Kartın Değeri (Sayılar: 50, 20 vs.) */
    div[data-testid="stMetricValue"] {
        font-size: 15rem !important; /* 80px DEV PUNTOLU SAYI */
        font-weight: 900 !important; /* Kapkalın */
        color: white;
        text-align: center !important;
        margin-top: 5px;
        line-height: 1.2;
    }

    /* 4. INPUT VE BUTONLAR - BÜYÜK BOY */
    .stSelectbox div[data-baseweb="select"] > div {
        height: 3.5rem; 
    }
    .stSelectbox div[data-baseweb="select"] span {
        font-size: 1.2rem !important;
    }
    .stTextInput input {
        font-size: 1.2rem !important;
        height: 3.5rem;
    }
    .stButton button {
        font-size: 1.4rem !important;
        height: 4rem !important;
        font-weight: bold;
    }

    /* 5. KENAR ÇUBUĞU MENÜSÜ */
    section[data-testid="stSidebar"] .stRadio label {
        font-size: 1.4rem !important;
        padding: 15px 5px;
    }

    /* 6. TABLO STİLİ (HTML TABLO İÇİN) */
    .big-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 20px;
        font-size: 1.2rem;
    }
    .big-table th {
        text-align: left;
        background-color: #333;
        color: #4A90E2;
        padding: 15px;
        font-size: 1.3rem;
        border-bottom: 2px solid #555;
    }
    .big-table td {
        padding: 15px;
        border-bottom: 1px solid #444;
        color: #eee;
    }
    .big-table tr:hover {
        background-color: #222;
    }
    .alert-row {
        color: #ff6b6b !important;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- YARDIMCI: ÖZEL BÜYÜK TABLO OLUŞTURUCU ---
def create_custom_table(df, alert_col=None):
    """
    Pandas DataFrame'ini alır ve okunabilirliği yüksek HTML tabloya çevirir.
    """
    if df.empty:
        return "<div style='padding:20px; font-size:1.2rem;'>Kayıt bulunamadı.</div>"

    html = '<table class="big-table">'

    # Başlıklar
    html += '<thead><tr>'
    for col in df.columns:
        html += f'<th>{col}</th>'
    html += '</tr></thead>'

    # Satırlar
    html += '<tbody>'
    for index, row in df.iterrows():
        html += '<tr>'
        for col in df.columns:
            val = row[col]
            # Eğer gecikme sütunuysa ve değer varsa kırmızı yap
            style = ""
            if alert_col and col == alert_col:
                style = "class='alert-row'"
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
    if only_available:
        query += " WHERE status='Müsait'"
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
    st.markdown("Yönetim Paneli v3.2")
    st.markdown("---")
    menu = st.radio("ANA MENÜ", ["Operasyon Merkezi", "Ödünç ve İade", "Arşiv Sorgulama", "Üye Veritabanı"],
                    label_visibility="collapsed")
    st.markdown("---")
    st.info(f"📅 Tarih: {datetime.now().strftime('%d.%m.%Y')}")

# 1. MODÜL: OPERASYON MERKEZİ
if menu == "Operasyon Merkezi":
    st.title("Operasyon Merkezi")

    conn = get_db_connection()

    # İstatistikler
    total_books = pd.read_sql("SELECT COUNT(*) FROM books", conn).iloc[0, 0]
    total_members = pd.read_sql("SELECT COUNT(*) FROM members", conn).iloc[0, 0]

    df_trans = pd.read_sql("""
        SELECT t.id, m.name as 'Üye Adı Soyadı', b.title as 'Kitap Adı', 
        t.due_date as 'Teslim Tarihi', m.phone as 'Telefon',
        (julianday('now') - julianday(t.due_date)) as gecikme
        FROM transactions t
        JOIN members m ON t.member_id = m.id
        JOIN books b ON t.book_id = b.id
        WHERE t.status = 'Aktif'
    """, conn)

    active_loans = len(df_trans)
    overdue_df = df_trans[df_trans['gecikme'] > 0].copy()

    # KPI Kartları
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Kitap", total_books)
    c2.metric("Toplam Üye", total_members)
    c3.metric("Ödünç Verilen", active_loans)
    c4.metric("Geciken İade", len(overdue_df))

    st.markdown("---")

    # KRİTİK LİSTE (Custom HTML Table kullanıyoruz)
    if not overdue_df.empty:
        st.subheader("⚠️ DİKKAT: Teslim Tarihi Geçenler Listesi")
        st.warning("Bu listedeki kişilerin teslim tarihi geçmiştir. Lütfen aşağıdaki panelden SMS gönderiniz.")

        # Tabloyu hazırlama (Gecikme gününü ekle)
        display_df = overdue_df[['Üye Adı Soyadı', 'Kitap Adı', 'Teslim Tarihi', 'Telefon']].copy()
        display_df['Gecikme Süresi'] = overdue_df['gecikme'].astype(int).astype(str) + " GÜN"

        # HTML Tabloyu Bas (Büyük Fontlu)
        st.markdown(create_custom_table(display_df, alert_col="Gecikme Süresi"), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Hızlı Aksiyon Paneli
        with st.container(border=True):
            st.markdown("### 🔔 SMS Gönderim Paneli")
            c_sel, c_btn = st.columns([3, 1])
            # Dropdown da büyük olacak (CSS ile ayarlandı)
            selected_person = c_sel.selectbox("Hatırlatma Yapılacak Kişiyi Seçiniz:",
                                              overdue_df['Üye Adı Soyadı'] + " - " + overdue_df['Kitap Adı'])
            if c_btn.button("SMS GÖNDER"):
                st.success(f"✅ SMS Başarıyla İletildi: {selected_person}")
    else:
        st.success("Harika! Gecikmiş iade bulunmuyor.")

# 2. MODÜL: ÖDÜNÇ VE İADE
elif menu == "Ödünç ve İade":
    st.title("Ödünç ve İade İşlemleri")

    tab1, tab2 = st.tabs(["📤 KİTAP VER (ÖDÜNÇ)", "📥 KİTAP AL (İADE)"])

    with tab1:
        st.markdown("### Yeni Ödünç Kaydı Oluştur")
        books = get_books_dict(only_available=True)
        members = get_members_dict()

        if not books:
            st.error("Stokta müsait kitap yok!")
        else:
            sel_mem = st.selectbox("Üye Seçiniz:", list(members.keys()))
            sel_bk = st.selectbox("Kitap Seçiniz:", list(books.keys()))
            days = st.slider("Ödünç Süresi (Gün):", 7, 45, 15)

            if st.button("KAYDET VE ÖDÜNÇ VER", type="primary"):
                conn = get_db_connection()
                end_date = datetime.now() + timedelta(days=days)
                conn.execute(
                    "INSERT INTO transactions (book_id, member_id, issue_date, due_date) VALUES (?, ?, DATE('now'), ?)",
                    (books[sel_bk], members[sel_mem], end_date.strftime('%Y-%m-%d')))
                conn.execute("UPDATE books SET status = 'Ödünçte' WHERE id = ?", (books[sel_bk],))
                conn.commit()
                conn.close()
                st.success("İşlem Başarılı! Kitap verildi.")
                time.sleep(1)
                st.rerun()

    with tab2:
        st.markdown("### İade İşlemi")
        conn = get_db_connection()
        loans = pd.read_sql(
            "SELECT t.id, b.title, m.name FROM transactions t JOIN books b ON t.book_id=b.id JOIN members m ON t.member_id=m.id WHERE t.status='Aktif'",
            conn)
        conn.close()

        if loans.empty:
            st.info("İade bekleyen kitap yok.")
        else:
            loan_dict = {f"{row['title']} - {row['name']}": row['id'] for i, row in loans.iterrows()}
            sel_ret = st.selectbox("İade Edilen Kitabı Seçin:", list(loan_dict.keys()))

            if st.button("İADEYİ ONAYLA"):
                tid = loan_dict[sel_ret]
                conn = get_db_connection()
                conn.execute("UPDATE transactions SET return_date=DATE('now'), status='Tamamlandı' WHERE id=?", (tid,))
                bid = conn.execute("SELECT book_id FROM transactions WHERE id=?", (tid,)).fetchone()[0]
                conn.execute("UPDATE books SET status='Müsait' WHERE id=?", (bid,))
                conn.commit()
                conn.close()
                st.success("Kitap iade alındı.")
                time.sleep(1)
                st.rerun()

# 3. MODÜL: ARŞİV SORGULAMA
elif menu == "Arşiv Sorgulama":
    st.title("Arşiv Sorgulama")
    search = st.text_input("Kitap Adı, Yazar veya Raf No Giriniz:", placeholder="Büyük harf küçük harf farketmez...")

    conn = get_db_connection()
    q = "SELECT title as 'Kitap', author as 'Yazar', location as 'Raf', status as 'Durum' FROM books"
    if search:
        q += f" WHERE title LIKE '%{search}%' OR author LIKE '%{search}%'"
    df = pd.read_sql(q, conn)
    conn.close()

    # Özel HTML tablo ile gösterim (Daha okunaklı)
    st.markdown(create_custom_table(df), unsafe_allow_html=True)

# 4. MODÜL: ÜYE VERİTABANI
elif menu == "Üye Veritabanı":
    st.title("Üye Yönetimi")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### ➕ Yeni Üye Ekle")
        with st.container(border=True):
            nm = st.text_input("Ad Soyad:")
            ph = st.text_input("Telefon:")
            em = st.text_input("E-Posta:")
            if st.button("ÜYEYİ KAYDET"):
                if nm and ph:
                    conn = get_db_connection()
                    conn.execute("INSERT INTO members (name, phone, email, join_date) VALUES (?, ?, ?, DATE('now'))",
                                 (nm, ph, em))
                    conn.commit()
                    conn.close()
                    st.success("Üye eklendi.")
                else:
                    st.error("Ad ve Telefon zorunludur.")

    with col2:
        st.markdown("### 📋 Üye Listesi")
        conn = get_db_connection()
        members = pd.read_sql(
            "SELECT name as 'Ad Soyad', phone as 'Telefon', email as 'E-Posta' FROM members ORDER BY id DESC", conn)
        conn.close()
        # Custom Table ile göster
        st.markdown(create_custom_table(members), unsafe_allow_html=True)