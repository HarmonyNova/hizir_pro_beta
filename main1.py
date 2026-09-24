import customtkinter as ctk
from customtkinter import filedialog
import tkinter.messagebox as messagebox
import sqlite3
import os
from datetime import datetime
import pymupdf  # PyMuPDF
import pytesseract  # OCR Motoru
from PIL import Image
import io
import re

# Uygulama Teması (Koyu ve Modern)
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

DB_PATH = "hizir_paket.db"

def veritabanini_hazirla():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Kullanıcılar Tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS kullanicilar (id INTEGER PRIMARY KEY, kullanici_adi TEXT UNIQUE, sifre TEXT)''')
    
    # Varsayılan yönetici hesabı yoksa oluştur (Kullanıcı: admin, Şifre: 1234)
    c.execute("SELECT COUNT(*) FROM kullanicilar")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO kullanicilar (kullanici_adi, sifre) VALUES (?, ?)", ("admin", "1234"))
        
    # Diğer Tablolar
    c.execute('''CREATE TABLE IF NOT EXISTS kuryeler (id INTEGER PRIMARY KEY, ad_soyad TEXT UNIQUE)''')
    try: c.execute("ALTER TABLE kuryeler ADD COLUMN kayit_tarihi TEXT")
    except: pass
    
    c.execute('''CREATE TABLE IF NOT EXISTS kurye_avans (id INTEGER PRIMARY KEY, kurye_ad TEXT, tarih TEXT, tutar REAL, aciklama TEXT, odendi_mi INTEGER DEFAULT 0)''')
    try: c.execute("ALTER TABLE kurye_avans ADD COLUMN odendi_mi INTEGER DEFAULT 0")
    except: pass
        
    c.execute('''CREATE TABLE IF NOT EXISTS hakedisler (id INTEGER PRIMARY KEY, kurye_ad TEXT, tarih TEXT, hakedis REAL, kesilen_avans REAL, ustundeki_nakit REAL, net_odeme REAL)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS restoranlar (id INTEGER PRIMARY KEY, ad TEXT UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS restoran_islem (id INTEGER PRIMARY KEY, restoran_ad TEXT, tarih TEXT, tutar REAL, aciklama TEXT)''')
                 
    conn.commit()
    conn.close()


# ================= GİRİŞ EKRANI (LOGIN WINDOW) =================
class GirisPenceresi(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Hızır Paket PRO - Giriş Yap")
        self.geometry("450x380")
        self.resizable(False, False)
        
        # Pencereyi ekranın ortasına al
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        veritabanini_hazirla()

        # Arayüz Elemanları
        ctk.CTkLabel(self, text="🛵 Hızır Paket PRO", font=ctk.CTkFont(size=24, weight="bold"), text_color="#3498db").pack(pady=(40, 20))
        
        self.kullanici_gir = ctk.CTkEntry(self, placeholder_text="Kullanıcı Adı", height=45, width=320, font=ctk.CTkFont(size=14))
        self.kullanici_gir.pack(pady=10)
        
        self.sifre_gir = ctk.CTkEntry(self, placeholder_text="Şifre", show="*", height=45, width=320, font=ctk.CTkFont(size=14))
        self.sifre_gir.pack(pady=10)
        self.sifre_gir.bind("<Return>", lambda event: self.giris_yap())

        ctk.CTkButton(self, text="Giriş Yap", fg_color="#2ecc71", hover_color="#27ae60", height=45, width=320, font=ctk.CTkFont(size=15, weight="bold"), command=self.giris_yap).pack(pady=20)
        
        ctk.CTkLabel(self, text="Varsayılan: admin / 1234", font=ctk.CTkFont(size=11), text_color="gray").pack(side="bottom", pady=15)

    def giris_yap(self):
        k_adi = self.kullanici_gir.get().strip()
        sifre = self.sifre_gir.get().strip()

        if not k_adi or not sifre:
            messagebox.showwarning("Uyarı", "Lütfen kullanıcı adı ve şifrenizi girin!")
            return

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM kullanicilar WHERE kullanici_adi = ? AND sifre = ?", (k_adi, sifre))
        kullanici = c.fetchone()
        conn.close()

        if kullanici:
            self.destroy()  # Giriş penceresini kapat
            app = HizirPaketPro()  # Ana uygulamayı başlat
            app.mainloop()
        else:
            messagebox.showerror("Hata", "Kullanıcı adı veya şifre hatalı!")


# ================= ANA UYGULAMA =================
class HizirPaketPro(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Hızır Paket PRO - Tekirdağ (Ana Panel)")
        self.geometry("1280x800")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.db_path = DB_PATH

        # --- SOL MENÜ (SIDEBAR) ---
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color="#1a1a1a")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar, text="🛵 Hızır Pro", font=ctk.CTkFont(size=28, weight="bold"), text_color="#3498db")
        self.logo_label.grid(row=0, column=0, padx=20, pady=(40, 30))

        self.menu_buttons = {}
        self.btn_dash = self.create_nav_button("📊 Dashboard", 1, "dashboard")
        self.btn_avans = self.create_nav_button("💸 Avans Yönetimi", 2, "avans")
        self.btn_hakedis = self.create_nav_button("📝 Hakedişler", 3, "hakedis")
        self.btn_restoran = self.create_nav_button("🏪 Restoranlar", 4, "restoran")

        # Çıkış Yap Butonu (Sol Menünün En Altı)
        ctk.CTkButton(self.sidebar, text="🚪 Oturumu Kapat", fg_color="#c0392b", hover_color="#e74c3c", 
                      font=ctk.CTkFont(size=14, weight="bold"), height=40, command=self.cikis_yap).grid(row=6, column=0, padx=15, pady=20, sticky="ew")

        # --- SAYFALAR (FRAMES) ---
        self.frames = {}
        
        self.setup_dashboard_frame()
        self.setup_avans_frame()
        self.setup_hakedis_frame()
        self.setup_restoran_frame()
        
        self.show_frame("dashboard")

    def cikis_yap(self):
        if messagebox.askyesno("Çıkış", "Oturumu kapatmak istediğinize emin misiniz?"):
            self.destroy()
            # Tekrar giriş penceresini aç
            giris = GirisPenceresi()
            giris.mainloop()

    def create_nav_button(self, text, row, frame_name):
        btn = ctk.CTkButton(self.sidebar, text=text, fg_color="transparent", 
                            text_color=("gray30", "gray80"), hover_color=("gray70", "gray25"), 
                            anchor="w", font=ctk.CTkFont(size=16, weight="bold"), height=45,
                            command=lambda: self.show_frame(frame_name))
        btn.grid(row=row, column=0, padx=15, pady=8, sticky="ew")
        self.menu_buttons[frame_name] = btn
        return btn

    def show_frame(self, frame_name):
        for name, btn in self.menu_buttons.items():
            if name == frame_name:
                btn.configure(fg_color="#2b2b2b", text_color="#3498db")
            else:
                btn.configure(fg_color="transparent", text_color=("gray30", "gray80"))

        for frame in self.frames.values():
            frame.grid_forget()

        if frame_name in self.frames:
            self.frames[frame_name].grid(row=0, column=1, padx=30, pady=30, sticky="nsew")
            
            if frame_name == "dashboard":
                self.dashboard_kartlari_guncelle()
                self.dash_kurye_listesini_guncelle()
            elif frame_name == "hakedis":
                self.hak_kurye_sec.configure(values=self.kurye_listesini_getir())
                self.gecmis_hakedisleri_getir()
                self.hakedis_canli_hesapla()
            elif frame_name == "restoran":
                self.res_sec.configure(values=self.restoran_listesini_getir())
                self.restoran_bakiyeleri_guncelle()

    def kurye_listesini_getir(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT ad_soyad FROM kuryeler ORDER BY ad_soyad ASC")
        kuryeler = [row[0] for row in c.fetchall()]
        conn.close()
        return kuryeler if kuryeler else ["Önce Kurye Ekleyin!"]

    def restoran_listesini_getir(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT ad FROM restoranlar ORDER BY ad ASC")
        restoranlar = [row[0] for row in c.fetchall()]
        conn.close()
        return restoranlar if restoranlar else ["Önce Restoran Ekleyin!"]

    def create_table_header(self, parent_frame, headers, weights):
        header_frame = ctk.CTkFrame(parent_frame, fg_color="#1a1a1a", corner_radius=5)
        header_frame.pack(fill="x", padx=5, pady=(0, 5))
        for col_idx, (text, weight) in enumerate(zip(headers, weights)):
            header_frame.grid_columnconfigure(col_idx, weight=weight)
            ctk.CTkLabel(header_frame, text=text, font=ctk.CTkFont(size=13, weight="bold"), text_color="gray").grid(row=0, column=col_idx, padx=10, pady=8, sticky="w")

    # ================= OCR VE PDF İŞLEMLERİ =================
    def pdf_ocr_ile_oku(self, dosya_yolu):
        try:
            doc = pymupdf.open(dosya_yolu)
            tum_metin = ""
            for page in doc:
                pix = page.get_pixmap(dpi=300)
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                metin = pytesseract.image_to_string(img, lang='tur+eng')
                tum_metin += metin + "\n"
            doc.close()
            return tum_metin
        except Exception as e:
            messagebox.showerror("OCR Hatası", f"PDF taranamadı:\n{e}")
            return ""

    def kurye_pdf_yukle(self):
        dosya_yolu = filedialog.askopenfilename(title="Kurye Raporu Seç", filetypes=[("PDF Dosyaları", "*.pdf")])
        if not dosya_yolu: return

        metin = self.pdf_ocr_ile_oku(dosya_yolu)
        if not metin: return

        eslesme = re.search(r"Hakedis.*?(\d{1,3}(?:\.\d{3})*,\d{2})", metin, re.IGNORECASE | re.DOTALL)
        if not eslesme:
            rakamlar = re.findall(r"\d{1,3}(?:\.\d{3})*,\d{2}", metin)
            temiz_rakam = rakamlar[-1] if rakamlar else None
        else:
            temiz_rakam = eslesme.group(1)

        if temiz_rakam:
            self.hak_tutar_gir.delete(0, 'end')
            self.hak_tutar_gir.insert(0, temiz_rakam)
            self.hakedis_canli_hesapla()
        else:
            messagebox.showwarning("Bulunamadı", "PDF içinde hakediş tutarı saptanamadı.")

    def restoran_pdf_yukle(self):
        dosya_yolu = filedialog.askopenfilename(title="Restoran Raporu Seç", filetypes=[("PDF Dosyaları", "*.pdf")])
        if not dosya_yolu: return

        metin = self.pdf_ocr_ile_oku(dosya_yolu)
        if not metin: return

        eslesme = re.search(r"(?:Teslim Edeceğimiz Tutar|Banka Yoluyla).*?(\d{1,3}(?:\.\d{3})*,\d{2})", metin, re.IGNORECASE | re.DOTALL)
        
        if eslesme:
            temiz_rakam = eslesme.group(1)
            self.res_tutar_gir.delete(0, 'end')
            self.res_tutar_gir.insert(0, temiz_rakam)
            self.res_yon_sec.set("Biz Restorana Borçluyuz (-)")
        else:
            rakamlar = re.findall(r"\d{1,3}(?:\.\d{3})*,\d{2}", metin)
            if rakamlar:
                temiz_rakam = rakamlar[-2] if len(rakamlar) > 1 else rakamlar[-1]
                self.res_tutar_gir.delete(0, 'end')
                self.res_tutar_gir.insert(0, temiz_rakam)
                self.res_yon_sec.set("Biz Restorana Borçluyuz (-)")
            else:
                messagebox.showwarning("Bulunamadı", "PDF içinde tutar saptanamadı.")

    # ================= DASHBOARD =================
    def setup_dashboard_frame(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid_columnconfigure((0, 1, 2), weight=1)
        self.frames["dashboard"] = frame

        ctk.CTkLabel(frame, text="Dashboard & Operasyon Özeti", font=ctk.CTkFont(size=32, weight="bold")).grid(row=0, column=0, sticky="w", pady=(0, 20))

        self.kart_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self.kart_frame.grid(row=1, column=0, columnspan=3, sticky="nsew")
        self.kart_frame.grid_columnconfigure((0, 1, 2), weight=1)

        yonetim_frame = ctk.CTkFrame(frame, fg_color="transparent")
        yonetim_frame.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=30)
        yonetim_frame.grid_columnconfigure((0, 1), weight=1)
        yonetim_frame.grid_rowconfigure(0, weight=1)

        ekle_frame = ctk.CTkFrame(yonetim_frame, corner_radius=10)
        ekle_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        ctk.CTkLabel(ekle_frame, text="Yeni Kurye Ekle", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20, padx=20, anchor="w")
        self.dash_kurye_isim_gir = ctk.CTkEntry(ekle_frame, placeholder_text="Kurye Adı ve Soyadı", height=45, font=ctk.CTkFont(size=14))
        self.dash_kurye_isim_gir.pack(pady=10, padx=20, fill="x")
        ctk.CTkButton(ekle_frame, text="Sisteme Kaydet", fg_color="#2ecc71", hover_color="#27ae60", height=45, font=ctk.CTkFont(size=15, weight="bold"), command=self.dash_kurye_ekle).pack(pady=20, padx=20, fill="x")
        
        self.dash_kurye_liste_frame = ctk.CTkScrollableFrame(yonetim_frame, label_text="Sistemdeki Kuryeler ve Bekleyen Avanslar", label_font=ctk.CTkFont(size=16, weight="bold"))
        self.dash_kurye_liste_frame.grid(row=0, column=1, sticky="nsew", padx=(15, 0))

    def dashboard_kartlari_guncelle(self):
        for widget in self.kart_frame.winfo_children(): widget.destroy()
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM kuryeler")
        kurye_sayisi = c.fetchone()[0]
        
        bugun = datetime.now().strftime("%Y-%m-%d")
        c.execute("SELECT SUM(tutar) FROM kurye_avans WHERE tarih LIKE ?", (f"{bugun}%",))
        avans_toplam = c.fetchone()[0] or 0.0
        
        c.execute("SELECT SUM(tutar) FROM restoran_islem")
        res_bakiye = c.fetchone()[0] or 0.0
        conn.close()

        bakiye_metin = f"{res_bakiye:,.2f} TL"
        bakiye_renk = "#2ecc71" if res_bakiye >= 0 else "#e74c3c"

        self.create_card(self.kart_frame, 0, 0, "Aktif Kurye Sayısı", str(kurye_sayisi), "#3498db")
        self.create_card(self.kart_frame, 0, 1, "Bugünkü Avans Çıkışı", f"{avans_toplam:,.2f} TL", "#e74c3c")
        self.create_card(self.kart_frame, 0, 2, "Net Restoran Bakiyesi", bakiye_metin, bakiye_renk)

    def create_card(self, parent, row, col, title, value, color):
        card = ctk.CTkFrame(parent, fg_color="#242424", corner_radius=12, border_width=1, border_color="#333333")
        card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=14, weight="bold"), text_color="gray").pack(pady=(20, 5), padx=20, anchor="w")
        ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=28, weight="bold"), text_color=color).pack(pady=(0, 20), padx=20, anchor="w")

    def dash_kurye_ekle(self):
        ad = self.dash_kurye_isim_gir.get().strip()
        tarih = datetime.now().strftime("%Y-%m-%d")
        if not ad: return
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            try:
                c.execute("INSERT INTO kuryeler (ad_soyad, kayit_tarihi) VALUES (?, ?)", (ad, tarih))
            except sqlite3.OperationalError:
                c.execute("INSERT INTO kuryeler (ad_soyad) VALUES (?)", (ad,))
            conn.commit()
            conn.close()
            self.dash_kurye_isim_gir.delete(0, 'end')
            self.dash_kurye_listesini_guncelle()
            self.dashboard_kartlari_guncelle()
        except sqlite3.IntegrityError:
            messagebox.showwarning("Hata", "Bu kurye zaten sistemde kayıtlı!")

    def dash_kurye_sil(self, kurye_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM kuryeler WHERE id = ?", (kurye_id,))
        conn.commit()
        conn.close()
        self.dash_kurye_listesini_guncelle()
        self.dashboard_kartlari_guncelle()

    def dash_kurye_listesini_guncelle(self):
        for widget in self.dash_kurye_liste_frame.winfo_children(): widget.destroy()
        
        self.create_table_header(self.dash_kurye_liste_frame, ["İsim", "Bekleyen Avans", "İşlem"], [3, 2, 1])
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id, ad_soyad FROM kuryeler ORDER BY ad_soyad ASC")
        kuryeler = c.fetchall()
        
        if not kuryeler:
            ctk.CTkLabel(self.dash_kurye_liste_frame, text="Sistemde hiç kurye yok.", text_color="gray").pack(pady=20)
            conn.close()
            return
            
        for k_id, ad in kuryeler:
            c.execute("SELECT SUM(tutar) FROM kurye_avans WHERE kurye_ad = ? AND odendi_mi = 0", (ad,))
            bekleyen_avans = c.fetchone()[0] or 0.0
            avans_renk = "#e74c3c" if bekleyen_avans > 0 else "gray"
            
            satir = ctk.CTkFrame(self.dash_kurye_liste_frame, fg_color="#2b2b2b", corner_radius=5)
            satir.pack(fill="x", padx=5, pady=3)
            satir.grid_columnconfigure((0,1,2), weight=1)
            
            ctk.CTkLabel(satir, text=ad, font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=10, pady=10, sticky="w")
            ctk.CTkLabel(satir, text=f"- {bekleyen_avans:,.2f} TL", font=ctk.CTkFont(size=14, weight="bold"), text_color=avans_renk).grid(row=0, column=1, padx=10, pady=10, sticky="w")
            
            btn_frame = ctk.CTkFrame(satir, fg_color="transparent")
            btn_frame.grid(row=0, column=2, sticky="e", padx=10)
            ctk.CTkButton(btn_frame, text="🗑️", width=35, height=30, fg_color="#c0392b", hover_color="#e74c3c", command=lambda i=k_id: self.dash_kurye_sil(i)).pack(side="right")
        
        conn.close()

    # ================= AVANS YÖNETİMİ =================
    def setup_avans_frame(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid_columnconfigure((0, 1), weight=1)
        self.frames["avans"] = frame
        ctk.CTkLabel(frame, text="Kurye Avans Yönetimi", font=ctk.CTkFont(size=32, weight="bold")).grid(row=0, column=0, sticky="w", pady=(0, 20))
        
        form_frame = ctk.CTkFrame(frame, corner_radius=10)
        form_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 15))
        ctk.CTkLabel(form_frame, text="Yeni Avans Çıkışı", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20, padx=20, anchor="w")
        
        self.kurye_sec = ctk.CTkOptionMenu(form_frame, values=self.kurye_listesini_getir(), height=40)
        self.kurye_sec.pack(pady=10, padx=20, fill="x")
        self.tutar_gir = ctk.CTkEntry(form_frame, placeholder_text="Tutar (TL)", height=40)
        self.tutar_gir.pack(pady=10, padx=20, fill="x")
        self.aciklama_gir = ctk.CTkEntry(form_frame, placeholder_text="Açıklama (Örn: Yakıt, Yemek)", height=40)
        self.aciklama_gir.pack(pady=10, padx=20, fill="x")
        ctk.CTkButton(form_frame, text="Avansı Kaydet", fg_color="#2ecc71", hover_color="#27ae60", height=45, font=ctk.CTkFont(size=15, weight="bold"), command=self.avansi_veritabanina_yaz).pack(pady=30, padx=20, fill="x")
        
        sag_kapsayici = ctk.CTkFrame(frame, fg_color="transparent")
        sag_kapsayici.grid(row=1, column=1, sticky="nsew", padx=(10, 0))
        sag_kapsayici.grid_rowconfigure(1, weight=1)
        sag_kapsayici.grid_columnconfigure(0, weight=1)
        
        self.avans_sekme = ctk.CTkSegmentedButton(sag_kapsayici, values=["Bugünün İşlemleri", "Geçmiş Detaylı Rapor"], command=self.avans_sekme_degistir)
        self.avans_sekme.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.avans_sekme.set("Bugünün İşlemleri")
        
        self.liste_frame = ctk.CTkScrollableFrame(sag_kapsayici)
        self.liste_frame.grid(row=1, column=0, sticky="nsew")
        
        self.gecmis_frame = ctk.CTkFrame(sag_kapsayici, fg_color="transparent")
        filtre_alan = ctk.CTkFrame(self.gecmis_frame)
        filtre_alan.pack(fill="x", pady=(0, 10))
        self.gecmis_kurye_sec = ctk.CTkOptionMenu(filtre_alan, values=["Tüm Kuryeler"] + self.kurye_listesini_getir(), height=35)
        self.gecmis_kurye_sec.pack(side="left", padx=10, pady=10, fill="x", expand=True)
        ctk.CTkButton(filtre_alan, text="Listele", width=120, height=35, command=self.gecmis_avans_listele).pack(side="right", padx=10, pady=10)
        self.gecmis_sonuc_frame = ctk.CTkScrollableFrame(self.gecmis_frame)
        self.gecmis_sonuc_frame.pack(fill="both", expand=True)
        
        self.avans_listesini_guncelle()

    def avans_sekme_degistir(self, secilen_sekme):
        if secilen_sekme == "Bugünün İşlemleri":
            self.gecmis_frame.grid_forget()
            self.liste_frame.grid(row=1, column=0, sticky="nsew")
            self.avans_listesini_guncelle()
        else:
            self.liste_frame.grid_forget()
            self.gecmis_frame.grid(row=1, column=0, sticky="nsew")
            self.gecmis_avans_listele()

    def avansi_veritabanina_yaz(self):
        kurye = self.kurye_sec.get()
        tutar_str = self.tutar_gir.get().strip()
        aciklama = self.aciklama_gir.get()
        tarih = datetime.now().strftime("%Y-%m-%d %H:%M")
        if not tutar_str or kurye == "Önce Kurye Ekleyin!": return
        try:
            tutar = float(tutar_str.replace('.', '').replace(',', '.'))
        except ValueError:
            return
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO kurye_avans (kurye_ad, tarih, tutar, aciklama, odendi_mi) VALUES (?, ?, ?, ?, 0)", (kurye, tarih, tutar, aciklama))
        conn.commit()
        conn.close()
        
        self.tutar_gir.delete(0, 'end')
        self.aciklama_gir.delete(0, 'end')
        self.avans_listesini_guncelle()
        self.gecmis_avans_listele()
        self.dashboard_kartlari_guncelle()

    def liste_satirlarini_olustur(self, parent_frame, avanslar, tarih_goster=False):
        basliklar = ["Tarih & Saat", "Kurye İsmı", "Açıklama", "Tutar", ""] if tarih_goster else ["Saat", "Kurye İsmı", "Açıklama", "Tutar", ""]
        self.create_table_header(parent_frame, basliklar, [2, 2, 3, 2, 1])

        for kayit_id, kurye, tutar, aciklama, tarih, odendi_mi in avanslar:
            satir = ctk.CTkFrame(parent_frame, fg_color="#2b2b2b", corner_radius=5)
            satir.pack(fill="x", padx=5, pady=3)
            satir.grid_columnconfigure((0,1,2,3,4), weight=1)
            
            tarih_obj = datetime.strptime(tarih, "%Y-%m-%d %H:%M")
            gosterim_tarih = tarih_obj.strftime("%d %b %H:%M") if tarih_goster else tarih_obj.strftime("%H:%M")
            durum_renk = "#2ecc71" if odendi_mi else "#e74c3c"
            
            ctk.CTkLabel(satir, text=gosterim_tarih, font=ctk.CTkFont(size=13), text_color="gray").grid(row=0, column=0, padx=10, pady=8, sticky="w")
            ctk.CTkLabel(satir, text=kurye, font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=1, padx=10, pady=8, sticky="w")
            ctk.CTkLabel(satir, text=aciklama, font=ctk.CTkFont(size=13)).grid(row=0, column=2, padx=10, pady=8, sticky="w")
            ctk.CTkLabel(satir, text=f"{tutar:,.2f} TL", font=ctk.CTkFont(size=15, weight="bold"), text_color=durum_renk).grid(row=0, column=3, padx=10, pady=8, sticky="w")
            
            btn_frame = ctk.CTkFrame(satir, fg_color="transparent")
            btn_frame.grid(row=0, column=4, sticky="e", padx=10)
            
            if not odendi_mi:
                ctk.CTkButton(btn_frame, text="🗑️", width=35, height=30, fg_color="#c0392b", hover_color="#e74c3c", command=lambda i=kayit_id: self.avans_sil(i)).pack(side="right")
            else:
                ctk.CTkLabel(btn_frame, text="Ödendi", text_color="#2ecc71", font=ctk.CTkFont(size=12, weight="bold")).pack(side="right")

    def avans_listesini_guncelle(self):
        for widget in self.liste_frame.winfo_children(): widget.destroy()
        bugun = datetime.now().strftime("%Y-%m-%d")
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id, kurye_ad, tutar, aciklama, tarih, odendi_mi FROM kurye_avans WHERE tarih LIKE ? ORDER BY id DESC", (f"{bugun}%",))
        avanslar = c.fetchall()
        conn.close()
        if not avanslar:
            ctk.CTkLabel(self.liste_frame, text="Bugün henüz avans çıkışı yapılmadı.", font=ctk.CTkFont(size=14), text_color="gray").pack(pady=30)
            return
        self.liste_satirlarini_olustur(self.liste_frame, avanslar, tarih_goster=False)

    def gecmis_avans_listele(self):
        for widget in self.gecmis_sonuc_frame.winfo_children(): widget.destroy()
        kurye = self.gecmis_kurye_sec.get()
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        if kurye == "Tüm Kuryeler" or kurye == "Önce Kurye Ekleyin!":
            c.execute("SELECT id, kurye_ad, tutar, aciklama, tarih, odendi_mi FROM kurye_avans ORDER BY tarih DESC")
        else:
            c.execute("SELECT id, kurye_ad, tutar, aciklama, tarih, odendi_mi FROM kurye_avans WHERE kurye_ad = ? ORDER BY tarih DESC", (kurye,))
        avanslar = c.fetchall()
        conn.close()
        if not avanslar:
            ctk.CTkLabel(self.gecmis_sonuc_frame, text="Geçmiş kayıt bulunamadı.", font=ctk.CTkFont(size=14), text_color="gray").pack(pady=30)
            return
        self.liste_satirlarini_olustur(self.gecmis_sonuc_frame, avanslar, tarih_goster=True)

    def avans_sil(self, kayit_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM kurye_avans WHERE id = ?", (kayit_id,))
        conn.commit()
        conn.close()
        self.avans_listesini_guncelle()
        self.gecmis_avans_listele()
        self.dashboard_kartlari_guncelle()

    # ================= HAKEDİŞLER =================
    def setup_hakedis_frame(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid_columnconfigure((0, 1), weight=1)
        self.frames["hakedis"] = frame
        ctk.CTkLabel(frame, text="Hakediş & Maaş Kapatma", font=ctk.CTkFont(size=32, weight="bold")).grid(row=0, column=0, sticky="w", pady=(0, 20))
        
        form_frame = ctk.CTkFrame(frame, corner_radius=10)
        form_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 15))
        ctk.CTkLabel(form_frame, text="Bordro Hesaplama", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20, padx=20, anchor="w")
        
        self.hak_kurye_sec = ctk.CTkOptionMenu(form_frame, values=self.kurye_listesini_getir(), command=self.hakedis_canli_hesapla, height=40)
        self.hak_kurye_sec.pack(pady=10, padx=20, fill="x")
        
        self.hak_tutar_gir = ctk.CTkEntry(form_frame, placeholder_text="Maaş / Hak Ediş Tutarı (TL)", height=40)
        self.hak_tutar_gir.pack(pady=10, padx=20, fill="x")
        self.hak_tutar_gir.bind("<KeyRelease>", self.hakedis_canli_hesapla)
        
        ctk.CTkButton(form_frame, text="📄 PDF'den Otomatik Çek (OCR)", fg_color="#8e44ad", hover_color="#9b59b6", command=self.kurye_pdf_yukle).pack(pady=5, padx=20, fill="x")
        
        self.hak_nakit_gir = ctk.CTkEntry(form_frame, placeholder_text="Üstündeki Nakit (TL) - Yoksa boş bırakın", height=40)
        self.hak_nakit_gir.pack(pady=10, padx=20, fill="x")
        self.hak_nakit_gir.bind("<KeyRelease>", self.hakedis_canli_hesapla)
        
        self.btn_hakedis_kaydet = ctk.CTkButton(form_frame, text="✅ Hakedişi Onayla (Avansları Kapat)", fg_color="#2ecc71", hover_color="#27ae60", height=45, font=ctk.CTkFont(size=15, weight="bold"), state="disabled", command=self.hakedis_kaydet)
        self.btn_hakedis_kaydet.pack(pady=30, padx=20, fill="x")
        
        sag_kapsayici = ctk.CTkFrame(frame, fg_color="transparent")
        sag_kapsayici.grid(row=1, column=1, sticky="nsew", padx=(10, 0))
        sag_kapsayici.grid_rowconfigure(1, weight=1)
        
        makbuz_frame = ctk.CTkFrame(sag_kapsayici, fg_color="#1a2530", corner_radius=10, border_width=1, border_color="#2c3e50")
        makbuz_frame.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(makbuz_frame, text="HESAPLAMA FİŞİ", font=ctk.CTkFont(size=20, weight="bold"), text_color="#3498db").pack(pady=(15, 10))
        
        self.fis_kurye_lbl = ctk.CTkLabel(makbuz_frame, text="Kurye: Bekleniyor...", font=ctk.CTkFont(size=15, weight="bold"))
        self.fis_kurye_lbl.pack(anchor="w", padx=25)
        
        self.fis_avans_detay_frame = ctk.CTkFrame(makbuz_frame, fg_color="transparent")
        self.fis_avans_detay_frame.pack(fill="x", padx=25, pady=10)
        
        self.fis_hakedis_lbl = ctk.CTkLabel(makbuz_frame, text="Hak Ediş: 0.00 TL", font=ctk.CTkFont(size=15))
        self.fis_hakedis_lbl.pack(anchor="w", padx=25)
        self.fis_avans_lbl = ctk.CTkLabel(makbuz_frame, text="Toplam Avans Kesintisi: - 0.00 TL", font=ctk.CTkFont(size=15), text_color="#ffcccc")
        self.fis_avans_lbl.pack(anchor="w", padx=25)
        self.fis_nakit_lbl = ctk.CTkLabel(makbuz_frame, text="Üstündeki Nakit: - 0.00 TL", font=ctk.CTkFont(size=15), text_color="#ffcccc")
        self.fis_nakit_lbl.pack(anchor="w", padx=25)
        
        ctk.CTkFrame(makbuz_frame, height=2, fg_color="#2c3e50").pack(fill="x", padx=20, pady=10)
        self.fis_net_lbl = ctk.CTkLabel(makbuz_frame, text="NET YATACAK: 0.00 TL", font=ctk.CTkFont(size=26, weight="bold"), text_color="#2ecc71")
        self.fis_net_lbl.pack(pady=(0, 15))

        ctk.CTkLabel(sag_kapsayici, text="Son Kapanan Bordrolar", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", pady=(10, 5))
        self.hakedis_liste_frame = ctk.CTkScrollableFrame(sag_kapsayici)
        self.hakedis_liste_frame.pack(fill="both", expand=True)

    def hakedis_canli_hesapla(self, event=None, *args):
        kurye = self.hak_kurye_sec.get()
        if kurye == "Önce Kurye Ekleyin!" or not kurye: return
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT tarih, tutar, aciklama FROM kurye_avans WHERE kurye_ad = ? AND odendi_mi = 0 ORDER BY tarih ASC", (kurye,))
        avans_detaylari = c.fetchall()
        conn.close()
        
        toplam_avans = sum(item[1] for item in avans_detaylari)
        hakedis_str = self.hak_tutar_gir.get().strip()
        nakit_str = self.hak_nakit_gir.get().strip()
        
        try: 
            hakedis = float(hakedis_str.replace('.', '').replace(',', '.')) if hakedis_str else 0.0
        except ValueError: 
            hakedis = 0.0
            
        try: 
            nakit = float(nakit_str.replace('.', '').replace(',', '.')) if nakit_str else 0.0
        except ValueError: 
            nakit = 0.0
        
        net_yatacak = hakedis - toplam_avans - nakit

        self.fis_kurye_lbl.configure(text=f"👤 Personel: {kurye}")
        self.fis_hakedis_lbl.configure(text=f"💵 Brüt Hak Ediş: {hakedis:,.2f} TL")
        self.fis_avans_lbl.configure(text=f"🔻 Avans Kesintisi: - {toplam_avans:,.2f} TL")
        self.fis_nakit_lbl.configure(text=f"🔻 Nakit Kesintisi: - {nakit:,.2f} TL")
        self.fis_net_lbl.configure(text=f"NET YATACAK: {net_yatacak:,.2f} TL")

        for widget in self.fis_avans_detay_frame.winfo_children(): widget.destroy()
        
        if avans_detaylari:
            ctk.CTkLabel(self.fis_avans_detay_frame, text="--- Kesilecek Avans Detayları ---", font=ctk.CTkFont(size=12), text_color="gray").pack(anchor="w", pady=(5,2))
            for tarih, tutar, aciklama in avans_detaylari:
                tarih_kisa = datetime.strptime(tarih, "%Y-%m-%d %H:%M").strftime("%d %b")
                metin = f"• {tarih_kisa} | {aciklama}: {tutar} TL"
                ctk.CTkLabel(self.fis_avans_detay_frame, text=metin, font=ctk.CTkFont(size=12), text_color="#ffb3b3").pack(anchor="w")
            ctk.CTkLabel(self.fis_avans_detay_frame, text="-----------------------------------", font=ctk.CTkFont(size=12), text_color="gray").pack(anchor="w", pady=(2,5))

        if hakedis_str:
            self.btn_hakedis_kaydet.configure(state="normal")
            self.aktif_hesaplama = {"kurye": kurye, "hakedis": hakedis, "avans": toplam_avans, "nakit": nakit, "net": net_yatacak}
        else:
            self.btn_hakedis_kaydet.configure(state="disabled")

    def hakedis_kaydet(self):
        if not hasattr(self, 'aktif_hesaplama'): return
        k, h, a, n, net = self.aktif_hesaplama.values()
        tarih = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO hakedisler (kurye_ad, tarih, hakedis, kesilen_avans, ustundeki_nakit, net_odeme) VALUES (?, ?, ?, ?, ?, ?)", (k, tarih, h, a, n, net))
        c.execute("UPDATE kurye_avans SET odendi_mi = 1 WHERE kurye_ad = ? AND odendi_mi = 0", (k,))
        conn.commit()
        conn.close()

        self.hak_tutar_gir.delete(0, 'end')
        self.hak_nakit_gir.delete(0, 'end')
        self.btn_hakedis_kaydet.configure(state="disabled")
        self.gecmis_hakedisleri_getir()
        self.hakedis_canli_hesapla()
        self.dashboard_kartlari_guncelle()

    def gecmis_hakedisleri_getir(self):
        for widget in self.hakedis_liste_frame.winfo_children(): widget.destroy()
        self.create_table_header(self.hakedis_liste_frame, ["Onay Tarihi", "Kurye", "Net Ödenen", ""], [2, 3, 2, 1])
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id, kurye_ad, tarih, net_odeme FROM hakedisler ORDER BY id DESC LIMIT 20")
        gecmis = c.fetchall()
        conn.close()
        
        if not gecmis:
            ctk.CTkLabel(self.hakedis_liste_frame, text="Henüz onaylanmış hakediş yok.", text_color="gray").pack(pady=20)
            return
            
        for h_id, kurye, tarih, net in gecmis:
            satir = ctk.CTkFrame(self.hakedis_liste_frame, fg_color="#2b2b2b", corner_radius=5)
            satir.pack(fill="x", padx=5, pady=3)
            satir.grid_columnconfigure((0,1,2,3), weight=1)
            
            tarih_formatli = datetime.strptime(tarih, "%Y-%m-%d %H:%M").strftime("%d %b %Y - %H:%M")
            
            ctk.CTkLabel(satir, text=tarih_formatli, font=ctk.CTkFont(size=13), text_color="gray").grid(row=0, column=0, padx=10, pady=8, sticky="w")
            ctk.CTkLabel(satir, text=kurye, font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=1, padx=10, pady=8, sticky="w")
            ctk.CTkLabel(satir, text=f"{net:,.2f} TL", font=ctk.CTkFont(size=15, weight="bold"), text_color="#3498db").grid(row=0, column=2, padx=10, pady=8, sticky="w")
            
            btn_frame = ctk.CTkFrame(satir, fg_color="transparent")
            btn_frame.grid(row=0, column=3, sticky="e", padx=10)
            ctk.CTkButton(btn_frame, text="🗑️", width=35, height=30, fg_color="#c0392b", hover_color="#e74c3c", command=lambda i=h_id: self.hakedis_sil(i)).pack(side="right")

    def hakedis_sil(self, h_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM hakedisler WHERE id = ?", (h_id,))
        conn.commit()
        conn.close()
        self.gecmis_hakedisleri_getir()
        self.dashboard_kartlari_guncelle()

    # ================= RESTORANLAR MODÜLÜ =================
    def popup_yeni_restoran(self):
        pencere = ctk.CTkToplevel(self)
        pencere.title("Yeni Restoran Ekle")
        pencere.geometry("400x250")
        pencere.attributes("-topmost", True)
        ctk.CTkLabel(pencere, text="Restoran Adı:", font=ctk.CTkFont(size=16)).pack(pady=(20, 10))
        isim_girisi = ctk.CTkEntry(pencere, width=250, placeholder_text="Örn: Burger King Çarşı")
        isim_girisi.pack(pady=10)
        def kaydet():
            yeni_ad = isim_girisi.get().strip()
            if yeni_ad:
                try:
                    conn = sqlite3.connect(self.db_path)
                    c = conn.cursor()
                    c.execute("INSERT INTO restoranlar (ad) VALUES (?)", (yeni_ad,))
                    conn.commit()
                    conn.close()
                    self.res_sec.configure(values=self.restoran_listesini_getir())
                    self.res_sec.set(yeni_ad)
                    self.restoran_bakiyeleri_guncelle()
                    pencere.destroy()
                except sqlite3.IntegrityError:
                    messagebox.showwarning("Hata", "Bu restoran kayıtlı!")
        ctk.CTkButton(pencere, text="Kaydet", fg_color="#2ecc71", command=kaydet).pack(pady=20)

    def setup_restoran_frame(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid_columnconfigure((0, 1), weight=1)
        self.frames["restoran"] = frame

        ctk.CTkLabel(frame, text="Restoran Bakiye İşlemleri", font=ctk.CTkFont(size=32, weight="bold")).grid(row=0, column=0, sticky="w", pady=(0, 20))

        form_frame = ctk.CTkFrame(frame, corner_radius=10)
        form_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 15))
        
        ust_alan = ctk.CTkFrame(form_frame, fg_color="transparent")
        ust_alan.pack(fill="x", padx=15, pady=15)
        ctk.CTkLabel(ust_alan, text="Yeni İşlem", font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
        ctk.CTkButton(ust_alan, text="+ Restoran Ekle", width=120, command=self.popup_yeni_restoran).pack(side="right")
        
        self.res_sec = ctk.CTkOptionMenu(form_frame, values=self.restoran_listesini_getir(), height=40)
        self.res_sec.pack(pady=10, padx=20, fill="x")
        self.res_tutar_gir = ctk.CTkEntry(form_frame, placeholder_text="Tutar (TL)", height=40)
        self.res_tutar_gir.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkButton(form_frame, text="📄 PDF'den Otomatik Çek (OCR)", fg_color="#8e44ad", hover_color="#9b59b6", command=self.restoran_pdf_yukle).pack(pady=5, padx=20, fill="x")
        
        self.res_yon_sec = ctk.CTkSegmentedButton(form_frame, values=["Restoran Bize Borçlu (+)", "Biz Restorana Borçluyuz (-)"])
        self.res_yon_sec.pack(pady=15, padx=20, fill="x")
        self.res_yon_sec.set("Restoran Bize Borçlu (+)")
        self.res_aciklama_gir = ctk.CTkEntry(form_frame, placeholder_text="Açıklama (Örn: Haftalık Kesinti)", height=40)
        self.res_aciklama_gir.pack(pady=10, padx=20, fill="x")
        ctk.CTkButton(form_frame, text="İşlemi Kaydet", fg_color="#3498db", hover_color="#2980b9", height=45, font=ctk.CTkFont(size=15, weight="bold"), command=self.restoran_islem_kaydet).pack(pady=30, padx=20, fill="x")

        sag_kapsayici = ctk.CTkFrame(frame, fg_color="transparent")
        sag_kapsayici.grid(row=1, column=1, sticky="nsew", padx=(10, 0))
        sag_kapsayici.grid_rowconfigure(1, weight=1)
        sag_kapsayici.grid_columnconfigure(0, weight=1)

        self.res_sekme = ctk.CTkSegmentedButton(sag_kapsayici, values=["Güncel Bakiyeler", "Tüm İşlem Geçmişi"], command=self.restoran_sekme_degistir)
        self.res_sekme.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.res_sekme.set("Güncel Bakiyeler")

        self.res_bakiye_frame = ctk.CTkScrollableFrame(sag_kapsayici)
        self.res_bakiye_frame.grid(row=1, column=0, sticky="nsew")
        self.res_gecmis_frame = ctk.CTkScrollableFrame(sag_kapsayici)

    def restoran_sekme_degistir(self, secilen_sekme):
        if secilen_sekme == "Güncel Bakiyeler":
            self.res_gecmis_frame.grid_forget()
            self.res_bakiye_frame.grid(row=1, column=0, sticky="nsew")
            self.restoran_bakiyeleri_guncelle()
        else:
            self.res_bakiye_frame.grid_forget()
            self.res_gecmis_frame.grid(row=1, column=0, sticky="nsew")
            self.restoran_son_islemler_guncelle()

    def restoran_islem_kaydet(self):
        res = self.res_sec.get()
        tutar_str = self.res_tutar_gir.get().strip()
        yon = self.res_yon_sec.get()
        aciklama = self.res_aciklama_gir.get()
        tarih = datetime.now().strftime("%Y-%m-%d %H:%M")
        if res == "Önce Restoran Ekleyin!" or not tutar_str: return
        try:
            tutar = float(tutar_str.replace('.', '').replace(',', '.'))
            if "Biz Restorana Borçluyuz" in yon: tutar = tutar * -1
        except ValueError: return
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO restoran_islem (restoran_ad, tarih, tutar, aciklama) VALUES (?, ?, ?, ?)", (res, tarih, tutar, aciklama))
        conn.commit()
        conn.close()
        self.res_tutar_gir.delete(0, 'end')
        self.res_aciklama_gir.delete(0, 'end')
        self.restoran_bakiyeleri_guncelle()
        self.restoran_son_islemler_guncelle()
        self.dashboard_kartlari_guncelle()

    def restoran_bakiyeleri_guncelle(self):
        for widget in self.res_bakiye_frame.winfo_children(): widget.destroy()
        self.create_table_header(self.res_bakiye_frame, ["Restoran", "Son İşlem", "Durum", "Net Bakiye"], [2, 2, 2, 2])
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT restoran_ad, SUM(tutar), MAX(tarih) FROM restoran_islem GROUP BY restoran_ad ORDER BY restoran_ad ASC")
        bakiyeler = c.fetchall()
        conn.close()

        if not bakiyeler:
            ctk.CTkLabel(self.res_bakiye_frame, text="Henüz bakiye işlemi yapılmadı.", text_color="gray").pack(pady=20)
            return

        for ad, net, son_tarih in bakiyeler:
            renk = "#2ecc71" if net > 0 else ("#e74c3c" if net < 0 else "gray")
            durum = "Alacaklıyız" if net > 0 else ("Ödeyeceğiz" if net < 0 else "Ödeştik")
            
            satir = ctk.CTkFrame(self.res_bakiye_frame, fg_color="#2b2b2b", corner_radius=5)
            satir.pack(fill="x", padx=5, pady=3)
            satir.grid_columnconfigure((0,1,2,3), weight=1)
            
            tarih_formatli = datetime.strptime(son_tarih, "%Y-%m-%d %H:%M").strftime("%d %b %Y") if son_tarih else "Bilinmiyor"
            
            ctk.CTkLabel(satir, text=ad, font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=10, pady=10, sticky="w")
            ctk.CTkLabel(satir, text=tarih_formatli, font=ctk.CTkFont(size=13), text_color="gray").grid(row=0, column=1, padx=10, pady=10, sticky="w")
            ctk.CTkLabel(satir, text=durum, font=ctk.CTkFont(size=13)).grid(row=0, column=2, padx=10, pady=10, sticky="w")
            ctk.CTkLabel(satir, text=f"{net:,.2f} TL", font=ctk.CTkFont(size=16, weight="bold"), text_color=renk).grid(row=0, column=3, padx=10, pady=10, sticky="w")

    def restoran_son_islemler_guncelle(self):
        for widget in self.res_gecmis_frame.winfo_children(): widget.destroy()
        self.create_table_header(self.res_gecmis_frame, ["Tarih & Saat", "Restoran", "Açıklama", "Tutar", ""], [2, 2, 2, 2, 1])
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id, restoran_ad, tarih, tutar, aciklama FROM restoran_islem ORDER BY id DESC LIMIT 50")
        islemler = c.fetchall()
        conn.close()

        if not islemler:
            ctk.CTkLabel(self.res_gecmis_frame, text="Henüz işlem geçmişi yok.", text_color="gray").pack(pady=20)
            return

        for islem_id, ad, tarih, tutar, aciklama in islemler:
            renk = "#2ecc71" if tutar > 0 else "#e74c3c"
            sembol = "+" if tutar > 0 else ""
            
            satir = ctk.CTkFrame(self.res_gecmis_frame, fg_color="#2b2b2b", corner_radius=5)
            satir.pack(fill="x", padx=5, pady=3)
            satir.grid_columnconfigure((0,1,2,3,4), weight=1)
            
            tarih_formatli = datetime.strptime(tarih, "%Y-%m-%d %H:%M").strftime("%d %b %H:%M")
            
            ctk.CTkLabel(satir, text=tarih_formatli, font=ctk.CTkFont(size=13), text_color="gray").grid(row=0, column=0, padx=10, pady=8, sticky="w")
            ctk.CTkLabel(satir, text=ad, font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=1, padx=10, pady=8, sticky="w")
            ctk.CTkLabel(satir, text=aciklama, font=ctk.CTkFont(size=13)).grid(row=0, column=2, padx=10, pady=8, sticky="w")
            ctk.CTkLabel(satir, text=f"{sembol}{tutar:,.2f} TL", font=ctk.CTkFont(size=15, weight="bold"), text_color=renk).grid(row=0, column=3, padx=10, pady=8, sticky="w")
            
            btn_frame = ctk.CTkFrame(satir, fg_color="transparent")
            btn_frame.grid(row=0, column=4, sticky="e", padx=10)
            ctk.CTkButton(btn_frame, text="🗑️", width=35, height=30, fg_color="#c0392b", hover_color="#e74c3c", command=lambda i=islem_id: self.restoran_islem_sil(i)).pack(side="right")

    def restoran_islem_sil(self, islem_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM restoran_islem WHERE id = ?", (islem_id,))
        conn.commit()
        conn.close()
        self.restoran_bakiyeleri_guncelle()
        self.restoran_son_islemler_guncelle()
        self.dashboard_kartlari_guncelle()

if __name__ == "__main__":
    app = GirisPenceresi()
    app.mainloop()
