import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import altair as alt  # Grafikler için

# Sayfa Ayarları
st.set_page_config(page_title="Akyurt Kütüphane YS", page_icon="📚", layout="wide")


# Veritabanı Bağlantısı
def get_db_connection():
    conn = sqlite3.connect('library.db', check_same_thread=False)
    return conn


# Yardımcı Fonksiyon: Müsait Kitapları Getir
def get_available_books():
    conn = get_db_connection()
    df = pd.read_sql("SELECT id, title, author, location FROM books WHERE status='Müsait'", conn)
    conn.close()
    return df


# Yardımcı Fonksiyon: Üyeleri Getir
def get_members():
    conn = get_db_connection()
    df = pd.read_sql("SELECT id, name FROM members", conn)
    conn.close()
    return df


# Yardımcı Fonksiyon: İade Edilecekleri Getir
def get_active_transactions():
    conn = get_db_connection()
    query = """
    SELECT t.id, m.name, b.title, t.due_date 
    FROM transactions t
    JOIN books b ON t.book_id = b.id
    JOIN members m ON t.member_id = m.id
    WHERE t.status = 'Aktif'
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


# --- SIDEBAR MENÜ ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2232/2232688.png", width=80)
    st.title("Akyurt Kütüphanesi")
    st.markdown("---")
    menu = st.radio("Menü", [
        "🏠 Gösterge Paneli",
        "🔄 Ödünç / İade İşlemleri",
        "🔍 Kitap Sorgula & Konum",
        "👥 Üye Yönetimi",
        "📈 Analitik Raporlar"
    ])
    st.markdown("---")
    st.info("v1.2 - Developer: Utku Buğra")

# --- 1. GÖSTERGE PANELİ (DASHBOARD) ---
if menu == "🏠 Gösterge Paneli":
    st.subheader("📊 Kütüphane Operasyon Merkezi")

    conn = get_db_connection()
    query = """
    SELECT t.id, m.name, m.phone, b.title, t.due_date, 
    (julianday('now') - julianday(t.due_date)) as Gecikme_Gunu
    FROM transactions t
    JOIN members m ON t.member_id = m.id
    JOIN books b ON t.book_id = b.id
    WHERE t.status = 'Aktif'
    """
    df = pd.read_sql(query, conn)

    # Metrikler
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Kitap", pd.read_sql("SELECT COUNT(*) FROM books", conn).iloc[0, 0])
    c2.metric("Toplam Üye", pd.read_sql("SELECT COUNT(*) FROM members", conn).iloc[0, 0])
    c3.metric("Ödünçteki Eser", len(df))
    geciken = len(df[df['Gecikme_Gunu'] > 0])
    c4.metric("⚠️ GECİKENLER", geciken, delta_color="inverse")

    # Gecikenler Listesi ve SMS
    if geciken > 0:
        st.error(f"Dikkat! {geciken} adet iadesi gecikmiş kitap var.")
        geciken_df = df[df['Gecikme_Gunu'] > 0]

        for i, row in geciken_df.iterrows():
            with st.expander(f"🚨 {row['name']} - {row['title']} ({int(row['Gecikme_Gunu'])} gün gecikmiş)"):
                st.write(f"**Telefon:** {row['phone']}")
                if st.button(f"🔔 SMS Gönder ({row['name']})", key=row['id']):
                    st.toast(f"✅ SMS Gönderildi: '{row['title']}' kitabı için hatırlatma yapıldı.")

# --- 2. ÖDÜNÇ VE İADE İŞLEMLERİ ---
elif menu == "🔄 Ödünç / İade İşlemleri":
    tab1, tab2 = st.tabs(["📖 Kitap Ödünç Ver", "🔙 İade Al"])

    # TAB 1: ÖDÜNÇ VERME
    with tab1:
        st.subheader("Yeni Ödünç Kaydı")

        col1, col2 = st.columns(2)
        members = get_members()
        books = get_available_books()

        if books.empty:
            st.warning("Kütüphanede şu an ödünç verilebilir kitap kalmadı!")
        else:
            with col1:
                member_choice = st.selectbox("Üye Seçiniz", members['name'].tolist())
                # Seçilen ismin ID'sini bul
                member_id = members[members['name'] == member_choice]['id'].values[0]

            with col2:
                # Kitapları "Adı - Yazarı (Raf)" formatında gösterelim
                book_display_list = [f"{row['title']} - {row['author']} ({row['location']})" for i, row in
                                     books.iterrows()]
                book_choice_str = st.selectbox("Kitap Seçiniz", book_display_list)
                # Seçilen kitabın ID'sini bul (Basit parsing)
                selected_book_title = book_choice_str.split(" - ")[0]
                book_id = books[books['title'] == selected_book_title]['id'].values[0]

            days = st.slider("Ödünç Süresi (Gün)", 7, 30, 15)

            if st.button("Ödünç Veriyi Kaydet", type="primary"):
                conn = get_db_connection()
                cursor = conn.cursor()

                issue_date = datetime.now()
                due_date = issue_date + timedelta(days=days)

                # Transaction ekle
                cursor.execute(
                    "INSERT INTO transactions (book_id, member_id, issue_date, due_date) VALUES (?, ?, ?, ?)",
                    (int(book_id), int(member_id), issue_date.strftime('%Y-%m-%d'), due_date.strftime('%Y-%m-%d')))

                # Kitap durumunu güncelle
                cursor.execute("UPDATE books SET status = 'Ödünçte' WHERE id = ?", (int(book_id),))

                conn.commit()
                conn.close()
                st.success(f"✅ İşlem Başarılı! '{selected_book_title}' kitabı {member_choice} adına kaydedildi.")
                st.rerun()

    # TAB 2: İADE ALMA
    with tab2:
        st.subheader("Kitap İadesi")
        active_trans = get_active_transactions()

        if active_trans.empty:
            st.info("Şu an dışarıda (ödünçte) kitap yok.")
        else:
            # Dropdown için okunabilir format
            trans_list = [f"{row['title']} -> {row['name']} (Son Tarih: {row['due_date']})" for i, row in
                          active_trans.iterrows()]
            selected_trans_str = st.selectbox("İade Edilecek İşlemi Seçin", trans_list)

            # Seçileni bul
            selected_title = selected_trans_str.split(" -> ")[0]
            trans_id = active_trans[active_trans['title'] == selected_title]['id'].values[0]

            if st.button("İadeyi Onayla"):
                conn = get_db_connection()
                cursor = conn.cursor()

                # Transaction kapat
                cursor.execute("UPDATE transactions SET return_date = ?, status = 'Tamamlandı' WHERE id = ?",
                               (datetime.now().strftime('%Y-%m-%d'), int(trans_id)))

                # Kitap ID'sini bulup müsait yap
                # (SQL join ile biraz kompleks ama basitçe şimdilik transaction tablosundan book_id çekebilirdik,
                # pratik olsun diye transaction kapatılırken book tablosunu da güncelliyoruz)
                book_id_query = \
                cursor.execute("SELECT book_id FROM transactions WHERE id = ?", (int(trans_id),)).fetchone()[0]
                cursor.execute("UPDATE books SET status = 'Müsait' WHERE id = ?", (book_id_query,))

                conn.commit()
                conn.close()
                st.success("✅ Kitap başarıyla iade alındı ve rafa eklendi.")
                st.rerun()

# --- 3. KİTAP SORGULA & KONUM ---
elif menu == "🔍 Kitap Sorgula & Konum":
    st.subheader("Kütüphane Arşivi ve Yerleşim")

    search_term = st.text_input("Kitap Adı, Yazar veya ISBN:", placeholder="Örn: Nutuk")

    conn = get_db_connection()
    if search_term:
        query = """
        SELECT title as 'Eser', author as 'Yazar', isbn as 'ISBN', 
               location as 'Raf/Konum', status as 'Durum'
        FROM books 
        WHERE title LIKE ? OR author LIKE ?
        """
        results = pd.read_sql(query, conn, params=(f'%{search_term}%', f'%{search_term}%'))

        if not results.empty:
            st.write(f"{len(results)} kayıt bulundu.")
            st.dataframe(results, use_container_width=True)

            # Raf görselleştirmesi (Basit Metin Bazlı)
            st.markdown("### 📍 Raf Bilgisi")
            first_loc = results.iloc[0]['Raf/Konum']
            st.info(f"Aradığınız eser kütüphanenin **{first_loc}** bölümündedir.")
            # Buraya ileride harita görseli eklenebilir
        else:
            st.warning("Kayıt bulunamadı.")
    else:
        # Tüm kitapları göster
        df_all = pd.read_sql("SELECT title, author, location, status FROM books", conn)
        st.dataframe(df_all, use_container_width=True)
    conn.close()

# --- 4. ÜYE YÖNETİMİ ---
elif menu == "👥 Üye Yönetimi":
    tab1, tab2 = st.tabs(["➕ Yeni Üye Ekle", "📋 Üye Listesi & Düzenle"])

    with tab1:
        with st.form("new_member_form"):
            st.write("Yeni Üye Kaydı")
            name = st.text_input("Ad Soyad")
            phone = st.text_input("Telefon")
            email = st.text_input("E-Posta")
            submitted = st.form_submit_button("Üyeyi Kaydet")

            if submitted:
                if name and phone:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO members (name, phone, email, join_date) VALUES (?, ?, ?, ?)",
                                   (name, phone, email, datetime.now().strftime('%Y-%m-%d')))
                    conn.commit()
                    conn.close()
                    st.success(f"{name} sisteme eklendi!")
                else:
                    st.error("İsim ve Telefon zorunludur.")

    with tab2:
        conn = get_db_connection()
        members_df = pd.read_sql("SELECT * FROM members", conn)
        st.dataframe(members_df, use_container_width=True)
        conn.close()

# --- 5. ANALİTİK RAPORLAR (YENİ WOW ÖZELLİĞİ) ---
elif menu == "📈 Analitik Raporlar":
    st.subheader("📈 Kütüphane Veri Analizi")

    conn = get_db_connection()

    # Veri 1: En Çok Okunan Yazarlar
    query_authors = """
    SELECT b.author, COUNT(*) as okunma_sayisi
    FROM transactions t
    JOIN books b ON t.book_id = b.id
    GROUP BY b.author
    ORDER BY okunma_sayisi DESC
    LIMIT 7
    """
    df_authors = pd.read_sql(query_authors, conn)

    # Grafik 1
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🏆 En Popüler Yazarlar")
        chart = alt.Chart(df_authors).mark_bar().encode(
            x=alt.X('okunma_sayisi', title='Ödünç Sayısı'),
            y=alt.Y('author', sort='-x', title='Yazar'),
            color=alt.Color('okunma_sayisi', legend=None)
        )
        st.altair_chart(chart, use_container_width=True)

    with c2:
        st.markdown("#### 🍩 Kitap Durum Dağılımı")
        df_status = pd.read_sql("SELECT status, COUNT(*) as sayi FROM books GROUP BY status", conn)

        # Pasta Grafik (Donut)
        pie = alt.Chart(df_status).mark_arc(innerRadius=50).encode(
            theta=alt.Theta(field="sayi", type="quantitative"),
            color=alt.Color(field="status", type="nominal"),
            tooltip=["status", "sayi"]
        )
        st.altair_chart(pie, use_container_width=True)

    st.info("💡 İpucu: Bu veriler, gelecek dönem kitap alımlarında karar destek mekanizması olarak kullanılabilir.")
    conn.close()