import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# Sayfa Ayarları
st.set_page_config(page_title="Akyurt Kütüphane YS", page_icon="📚", layout="wide")


# Veritabanı Bağlantısı (Cache kullanarak hızlandırıyoruz)
def get_db_connection():
    conn = sqlite3.connect('library.db', check_same_thread=False)
    return conn


# SMS Gönderme Simülasyonu (Toast Mesajı)
def send_sms_simulation(uye_adi, kitap, tel):
    # Gerçek hayatta burada API isteği olur (Netgsm, Twilio vs.)
    mesaj = f"Sayın {uye_adi}, '{kitap}' kitabının iade tarihi geçmiştir. Lütfen kütüphaneye getiriniz."
    st.toast(f"✅ SMS GÖNDERİLDİ: {tel} numarasına iletildi!", icon="📩")
    st.toast(f"📝 İçerik: {mesaj}")


# --- ARAYÜZ BAŞLIYOR ---

# 1. SIDEBAR (Sol Menü)
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2232/2232688.png", width=100)
    st.title("Akyurt Kütüphanesi")
    st.divider()
    menu = st.radio("Menü", ["Gösterge Paneli", "Kitap Sorgula", "Üye İşlemleri"])
    st.info("Sistem Durumu: 🟢 Online")

# 2. ANA EKRAN (Dashboard)
if menu == "Gösterge Paneli":
    st.subheader("📊 Kütüphane Operasyon Paneli")

    conn = get_db_connection()

    # SQL ile verileri çekip Pandas DataFrame'e çeviriyoruz
    # Gecikmeyi hesaplamak için SQL'de julianday farkını alıyoruz
    query = """
    SELECT 
        t.id,
        m.name as 'Üye Adı',
        m.phone as 'Telefon',
        b.title as 'Kitap Adı',
        t.issue_date as 'Veriliş Tarihi',
        t.due_date as 'Teslim Tarihi',
        (julianday('now') - julianday(t.due_date)) as 'Gecikme_Gunu'
    FROM transactions t
    JOIN members m ON t.member_id = m.id
    JOIN books b ON t.book_id = b.id
    WHERE t.status = 'Aktif'
    ORDER BY t.due_date ASC
    """
    df = pd.read_sql(query, conn)

    # KPI KARTLARI (Üst Panel)
    col1, col2, col3, col4 = st.columns(4)

    toplam_kitap = pd.read_sql("SELECT COUNT(*) FROM books", conn).iloc[0, 0]
    oduncteki_kitap = len(df)
    geciken_kitap = len(df[df['Gecikme_Gunu'] > 0])

    col1.metric("Toplam Kitap", toplam_kitap)
    col2.metric("Ödünçteki Kitap", oduncteki_kitap)
    col3.metric("Zamanında İadeler", oduncteki_kitap - geciken_kitap)
    col4.metric("🚨 GECİKEN İADELER", geciken_kitap, delta_color="inverse")

    st.divider()

    # 3. GECİKMİŞ KİTAPLAR VE SMS AKSİYONU
    # Burası en can alıcı yer. Kırmızı alan.
    if geciken_kitap > 0:
        st.error(f"⚠️ DİKKAT: Teslim tarihi geçmiş {geciken_kitap} kayıt var!")

        # Sadece gecikenleri filtrele
        geciken_df = df[df['Gecikme_Gunu'] > 0].copy()

        # Her satır için bir kart ve buton oluşturalım (Streamlit tablo içi buton zor olduğu için liste yapıyoruz)
        for index, row in geciken_df.iterrows():
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
                c1.write(f"**{row['Üye Adı']}**")
                c2.write(f"📕 {row['Kitap Adı']}")
                c3.write(f"📅 Teslim: {row['Teslim Tarihi']} (**{int(row['Gecikme_Gunu'])} gün gecikmiş**)")

                # Benzersiz anahtar (key) vererek butonu oluşturuyoruz
                if c4.button("🔔 SMS Gönder", key=f"btn_{row['id']}"):
                    send_sms_simulation(row['Üye Adı'], row['Kitap Adı'], row['Telefon'])

    else:
        st.success("Harika! Gecikmiş iade bulunmuyor.")

    st.divider()

    # 4. TÜM LİSTE (Excel yerine geçecek tablo)
    st.subheader("📋 Ödünç Takip Listesi (Tümü)")


    # Görsellik katmak için fonksiyon
    def color_coding(val):
        if val > 0: return 'background-color: #ffcccc'  # Kırmızımsı
        return ''


    # Tabloyu göster (Gecikme gününe göre renklendirme)
    st.dataframe(
        df.style.map(color_coding, subset=['Gecikme_Gunu']),
        use_container_width=True,
        hide_index=True
    )

elif menu == "Kitap Sorgula":
    st.info("Burası geliştirme aşamasında... (Kitap arama motoru)")

conn.close()