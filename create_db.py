import sqlite3
from faker import Faker
import random
from datetime import datetime, timedelta

# Türkçe sahte veri üretici
fake = Faker('tr_TR')


def create_connection():
    # Veritabanı dosyası oluşturuluyor
    conn = sqlite3.connect('library.db')
    return conn


def create_tables(conn):
    cursor = conn.cursor()

    # 1. Kitaplar Tablosu
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        isbn TEXT,
        location TEXT,
        status TEXT DEFAULT 'Müsait' -- Müsait, Ödünçte, Kayıp
    )
    ''')

    # 2. Üyeler Tablosu
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        join_date DATE
    )
    ''')

    # 3. Hareketler (İşlemler) Tablosu
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER,
        member_id INTEGER,
        issue_date DATE,
        due_date DATE,
        return_date DATE,
        status TEXT DEFAULT 'Aktif', -- Aktif, Tamamlandı
        FOREIGN KEY (book_id) REFERENCES books (id),
        FOREIGN KEY (member_id) REFERENCES members (id)
    )
    ''')
    conn.commit()


def generate_mock_data(conn):
    cursor = conn.cursor()
    print("📚 Sahte veriler üretiliyor... (Biraz bekleyin)")

    # A. RASTGELE KİTAPLAR EKLE
    book_titles = [
        "Suç ve Ceza", "Sefiller", "Nutuk", "Kürk Mantolu Madonna",
        "Saatleri Ayarlama Enstitüsü", "Simyacı", "Hayvan Çiftliği",
        "1984", "Beyaz Diş", "Küçük Prens", "Dönüşüm", "Yabancı"
    ]

    for _ in range(50):
        title = random.choice(book_titles) + " - " + fake.word().capitalize()
        author = fake.name()
        location = f"Raf-{random.randint(1, 20)}-{random.choice(['A', 'B', 'C'])}"
        cursor.execute("INSERT INTO books (title, author, isbn, location) VALUES (?, ?, ?, ?)",
                       (title, author, fake.isbn13(), location))

    # B. RASTGELE ÜYELER EKLE
    for _ in range(20):
        cursor.execute("INSERT INTO members (name, phone, email, join_date) VALUES (?, ?, ?, ?)",
                       (fake.name(), fake.phone_number(), fake.email(), fake.date_this_decade()))

    # C. HAREKETLER (TRANSACTIONS) EKLE
    # Kritik Nokta: Ekranda kırmızı uyarı çıksın diye bilerek GEÇMİŞ tarihli işlem ekliyoruz.

    book_ids = [row[0] for row in cursor.execute("SELECT id FROM books").fetchall()]
    member_ids = [row[0] for row in cursor.execute("SELECT id FROM members").fetchall()]

    for _ in range(15):  # 15 tane aktif işlem
        book_id = random.choice(book_ids)
        member_id = random.choice(member_ids)

        # Senaryo: %40 ihtimalle teslim tarihi geçmiş olsun
        if random.random() < 0.4:
            days_ago = random.randint(20, 60)  # 20-60 gün önce alınmış
            issue_date = datetime.now() - timedelta(days=days_ago)
            due_date = issue_date + timedelta(days=15)  # Teslim tarihi geçmiş
        else:
            days_ago = random.randint(1, 10)
            issue_date = datetime.now() - timedelta(days=days_ago)
            due_date = issue_date + timedelta(days=15)  # Süresi var

        # Veritabanına kaydet
        cursor.execute('''
            INSERT INTO transactions (book_id, member_id, issue_date, due_date, status)
            VALUES (?, ?, ?, ?, 'Aktif')
        ''', (book_id, member_id, issue_date.strftime('%Y-%m-%d'), due_date.strftime('%Y-%m-%d')))

        # Kitabı 'Ödünçte' olarak işaretle
        cursor.execute("UPDATE books SET status = 'Ödünçte' WHERE id = ?", (book_id,))

    conn.commit()
    print("✅ Veritabanı oluşturuldu ve içine sahte veriler basıldı!")


if __name__ == "__main__":
    conn = create_connection()
    create_tables(conn)
    generate_mock_data(conn)
    conn.close()