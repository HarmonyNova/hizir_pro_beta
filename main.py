import platform
import customtkinter as ctk
from customtkinter import filedialog
import tkinter.messagebox as messagebox
from tkinter import simpledialog
import os
from datetime import datetime
import pytesseract  # OCR Motoru (Görsel okuma için geri döndük)
from PIL import Image, ImageTk
import io
import re
import sys
import csv
import pandas as pd
from supabase import create_client, Client

# Uygulama Teması
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CONFIG_DOSYASI = "hatirla.txt"

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.abspath(".")

# İşletim Sistemine Göre Taşınabilir / Sistem Tesseract Tespiti
if platform.system() == "Windows":
    tesseract_yolu = os.path.join(base_path, "tesseract", "tesseract.exe")
    if os.path.exists(tesseract_yolu):
        pytesseract.pytesseract.tesseract_cmd = tesseract_yolu
    else:
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
else:
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

# Supabase Bağlantı Bilgileri
URL = "https://fmowvcmbqboykevfslwh.supabase.co/"
KEY = "sb_publishable_BHxK8vbTzP0Ht6B9ZgyEQA_WcKyWDMT"

supabase: Client = create_client(URL, KEY)
print("Supabase bağlantısı başarılı!")

def pencere_ikonu_ayarla(pencere):
    icon_path = os.path.join(base_path, "logo.ico")
    if os.path.exists(icon_path):
        try:
            img = Image.open(icon_path)
            photo = ImageTk.PhotoImage(img)
            pencere.iconphoto(True, photo)
            pencere._icon_photo = photo
        except: pass

def veritabanini_hazirla():
    try:
        res = supabase.table("kullanicilar").select("*").eq("rol", "admin").execute()
        if not res.data:
            supabase.table("kullanicilar").insert({"kullanici_adi": "admin", "sifre": "1234", "rol": "admin"}).execute()
    except Exception as e:
        print(f"Veritabanı hazırlık kontrolü uyarısı: {e}")

def temiz_float(deger_str):
    if not deger_str: return 0.0
    deger_str = str(deger_str).strip()
    deger_str = re.sub(r'[^\d.,-]', '', deger_str)
    if not deger_str or deger_str == '-': return 0.0
    if '.' in deger_str and ',' in deger_str:
        if deger_str.rfind(',') > deger_str.rfind('.'): deger_str = deger_str.replace('.', '').replace(',', '.')
        else: deger_str = deger_str.replace(',', '')
    elif ',' in deger_str: deger_str = deger_str.replace(',', '.')
    try: return float(deger_str)
    except: return 0.0

# ================= MİNİ TAKVİM =================
class TarihSeciciPenceresi(ctk.CTkToplevel):
    def __init__(self, parent, hedef_entry):
        super().__init__(parent)
        self.title("Tarih Seç")
        self.geometry("320x220")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.hedef_entry = hedef_entry
        pencere_ikonu_ayarla(self)
        ctk.CTkLabel(self, text="📅 Tarih Seçimi", font=ctk.CTkFont(size=16, weight="bold"), text_color="#3498db").pack(pady=15)
        secim_frame = ctk.CTkFrame(self, fg_color="transparent")
        secim_frame.pack(pady=5)
        simdi = datetime.now()
        self.yil_menu = ctk.CTkOptionMenu(secim_frame, values=[str(y) for y in range(simdi.year - 2, simdi.year + 3)], width=95)
        self.yil_menu.set(str(simdi.year))
        self.yil_menu.pack(side="left", padx=5)
        self.ay_menu = ctk.CTkOptionMenu(secim_frame, values=[f"{m:02d}" for m in range(1, 13)], width=75)
        self.ay_menu.set(f"{simdi.month:02d}")
        self.ay_menu.pack(side="left", padx=5)
        self.gun_menu = ctk.CTkOptionMenu(secim_frame, values=[f"{d:02d}" for d in range(1, 32)], width=75)
        self.gun_menu.set(f"{simdi.day:02d}")
        self.gun_menu.pack(side="left", padx=5)
        ctk.CTkButton(self, text="Seçimi Uygula", fg_color="#2ecc71", hover_color="#27ae60", height=40, font=ctk.CTkFont(size=14, weight="bold"), command=self.tarihi_aktar).pack(pady=20, padx=30, fill="x")
    def tarihi_aktar(self):
        self.hedef_entry.delete(0, 'end')
        self.hedef_entry.insert(0, f"{self.yil_menu.get()}-{self.ay_menu.get()}-{self.gun_menu.get()}")
        self.destroy()

# ================= GİRİŞ EKRANI =================
class GirisPenceresi(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Hızır Pro - Giriş Yap")
        self.geometry("450x350")
        self.resizable(False, False)
        self.basarili_giris = False
        self.kullanici_adi = ""
        self.kullanici_rol = ""
        pencere_ikonu_ayarla(self)
        self.update_idletasks()
        self.geometry(f"+{(self.winfo_screenwidth()-450)//2}+{(self.winfo_screenheight()-350)//2}")
        veritabanini_hazirla()
        ctk.CTkLabel(self, text="🛵 Hızır Pro", font=ctk.CTkFont(size=26, weight="bold"), text_color="#3498db").pack(pady=(40, 20))
        self.kullanici_gir = ctk.CTkEntry(self, placeholder_text="Kullanıcı Adı", height=45, width=320)
        self.kullanici_gir.pack(pady=10)
        if os.path.exists(CONFIG_DOSYASI):
            try:
                with open(CONFIG_DOSYASI, "r", encoding="utf-8") as f:
                    self.kullanici_gir.insert(0, f.read().strip())
            except: pass
        self.sifre_gir = ctk.CTkEntry(self, placeholder_text="Şifre", show="*", height=45, width=320)
        self.sifre_gir.pack(pady=10)
        self.sifre_gir.bind("<Return>", lambda e: self.giris_yap())
        ctk.CTkButton(self, text="Giriş Yap", fg_color="#2ecc71", hover_color="#27ae60", height=45, width=320, command=self.giris_yap).pack(pady=20)

    def giris_yap(self):
        k_adi, sifre = self.kullanici_gir.get().strip(), self.sifre_gir.get().strip()
        if not k_adi or not sifre: return messagebox.showwarning("Uyarı", "Kullanıcı adı ve şifre girin!")
        
        try:
            res = supabase.table("kullanicilar").select("*").eq("kullanici_adi", k_adi).eq("sifre", sifre).execute()
            kullanici = res.data
            if kullanici:
                try: open(CONFIG_DOSYASI, "w", encoding="utf-8").write(k_adi)
                except: pass
                self.basarili_giris = True
                self.kullanici_adi = k_adi
                self.kullanici_rol = kullanici[0].get("rol", "kullanici")
                self.destroy()
            else: messagebox.showerror("Hata", "Kullanıcı adı veya şifre hatalı!")
        except Exception as e:
            messagebox.showerror("Bağlantı Hatası", f"Giriş yapılırken hata oluştu:\n{e}")

# ================= ANA UYGULAMA =================
class HizirPaketPro(ctk.CTk):
    def __init__(self, current_user, current_role):
        super().__init__()
        self.current_user = current_user
        self.current_role = current_role
        self.title(f"Hızır Pro - Tekirdağ Muhasebe (Kullanıcı: {self.current_user})")
        self.geometry("1350x900")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.cikis_yapildi = False
        pencere_ikonu_ayarla(self)

        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color="#1a1a1a")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(10, weight=1)

        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=15, pady=(35, 25), sticky="w")
        if os.path.exists(os.path.join(base_path, "logo.ico")):
            try:
                pil_img = Image.open(os.path.join(base_path, "logo.ico"))
                self.sidebar_logo = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(32, 32))
                ctk.CTkLabel(logo_frame, text="", image=self.sidebar_logo).pack(side="left", padx=(0, 10))
            except: pass
        ctk.CTkLabel(logo_frame, text="Hızır Pro", font=ctk.CTkFont(size=20, weight="bold"), text_color="#3498db").pack(side="left")

        self.menu_buttons = {}
        self.create_nav_button("📊 Dashboard", 1, "dashboard")
        self.create_nav_button("💸 Avans Yönetimi", 2, "avans")
        self.create_nav_button("📝 Hakedişler", 3, "hakedis")
        self.create_nav_button("🏪 Restoranlar", 4, "restoran")
        self.create_nav_button("📅 Kurye Vardiyaları", 5, "vardiya")
        self.create_nav_button("👥 Kullanıcılar" if self.current_role=="admin" else "🔑 Şifrem", 6, "kullanici")

        row_idx = 7
        if self.current_role == "admin":
            ctk.CTkButton(self.sidebar, text="📥 Excel Yedek Al", fg_color="#27ae60", hover_color="#2ecc71", command=self.excel_yedek_al).grid(row=row_idx, column=0, padx=15, pady=(10, 0), sticky="ew")
            row_idx += 1
            ctk.CTkButton(self.sidebar, text="📤 Excel'den Yükle", fg_color="#d35400", hover_color="#e67e22", command=self.excel_yedek_yukle).grid(row=row_idx, column=0, padx=15, pady=(6, 0), sticky="ew")
            row_idx += 1

        ctk.CTkButton(self.sidebar, text="🔄 Verileri Yenile", fg_color="#2980b9", hover_color="#3498db", command=self.verileri_yenile).grid(row=row_idx, column=0, padx=15, pady=(6 if self.current_role=="admin" else 15, 0), sticky="ew")
        row_idx += 1
        ctk.CTkButton(self.sidebar, text="🚪 Oturumu Kapat", fg_color="#c0392b", hover_color="#e74c3c", command=self.cikis_yap).grid(row=row_idx, column=0, padx=15, pady=20, sticky="ew")

        self.frames = {}
        self.setup_dashboard_frame()
        self.setup_avans_frame()
        self.setup_hakedis_frame()
        self.setup_restoran_frame()
        self.setup_vardiya_frame()
        self.setup_kullanici_yonetimi_frame()
        self.show_frame("dashboard")

    def create_nav_button(self, text, row, frame_name):
        btn = ctk.CTkButton(self.sidebar, text=text, fg_color="transparent", text_color=("gray30", "gray80"), hover_color=("gray70", "gray25"), anchor="w", font=ctk.CTkFont(size=16, weight="bold"), height=45, command=lambda: self.show_frame(frame_name))
        btn.grid(row=row, column=0, padx=15, pady=8, sticky="ew")
        self.menu_buttons[frame_name] = btn

    def show_frame(self, frame_name):
        for name, btn in self.menu_buttons.items():
            btn.configure(fg_color="#2b2b2b" if name==frame_name else "transparent", text_color="#3498db" if name==frame_name else ("gray30", "gray80"))
        for frame in self.frames.values(): frame.grid_forget()
        
        self.frames[frame_name].grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        if frame_name == "dashboard": 
            self.dashboard_kartlari_guncelle()
            self.dashboard_gorevleri_getir()
        elif frame_name == "avans":
            self.avans_kurye_sec.configure(values=self.kurye_listesini_getir())
            self.filtre_kurye_sec.configure(values=["Tüm Kuryeler"] + self.kurye_listesini_getir())
            self.gecmis_avans_listele()
        elif frame_name == "hakedis":
            kuryeler = self.kurye_listesini_getir()
            self.hak_kurye_sec.configure(values=kuryeler)
            self.hak_filtre_kurye_sec.configure(values=["Tüm Kuryeler"] + kuryeler)
            if kuryeler and kuryeler[0] != "Önce Kurye Ekleyin!":
                self.hak_kurye_sec.set(kuryeler[0])
            self.hakedis_kurye_degisti()
            self.gecmis_hakedisleri_getir()
        elif frame_name == "restoran":
            self.res_sec.configure(values=self.restoran_listesini_getir())
            self.res_filtre_restoran_sec.configure(values=["Tüm Restoranlar"] + self.restoran_listesini_getir())
            self.restoran_bakiyeleri_guncelle()
        elif frame_name == "vardiya":
            self.vardiya_hafta_menu_guncelle()
            self.vardiya_listesini_guncelle()
        elif frame_name == "kullanici" and self.current_role == "admin":
            self.kullanici_listesini_guncelle()

    def kurye_listesini_getir(self):
        try:
            res = supabase.table("kuryeler").select("ad_soyad").order("ad_soyad").execute()
            kuryeler = [row["ad_soyad"] for row in res.data] if res.data else []
            return kuryeler if kuryeler else ["Önce Kurye Ekleyin!"]
        except Exception:
            return ["Önce Kurye Ekleyin!"]

    def restoran_listesini_getir(self):
        try:
            res = supabase.table("restoranlar").select("ad").order("ad").execute()
            restoranlar = [row["ad"] for row in res.data] if res.data else []
            return restoranlar if restoranlar else ["Önce Restoran Ekleyin!"]
        except Exception:
            return ["Önce Restoran Ekleyin!"]

    def create_table_header(self, parent_frame, headers, widths):
        header_frame = ctk.CTkFrame(parent_frame, fg_color="#1a1a1a", corner_radius=5)
        header_frame.pack(fill="x", padx=5, pady=(0, 5))
        for col_idx, (text, w) in enumerate(zip(headers, widths)):
            header_frame.grid_columnconfigure(col_idx, weight=0, minsize=w)
            ctk.CTkLabel(header_frame, text=text, font=ctk.CTkFont(size=13, weight="bold"), text_color="#3498db", width=w, anchor="center").grid(row=0, column=col_idx, padx=5, pady=8)

    def cikis_yap(self):
        if messagebox.askyesno("Çıkış", "Oturumu kapatmak istediğinize emin misiniz?"):
            self.cikis_yapildi = True
            self.destroy()

    def verileri_yenile(self):
        active = next((n for n, f in self.frames.items() if f.winfo_ismapped()), None)
        if active: self.show_frame(active)
        messagebox.showinfo("Senkronizasyon", "Bulut verileri başarıyla yenilendi!")

    def excel_yedek_al(self):
        klasor = filedialog.askdirectory(title="Yedek Klasörü Seçin")
        if not klasor: return
        try:
            tablolar = ["kullanicilar", "kuryeler", "kurye_avans", "hakedisler", "restoranlar", "restoran_islem", "vardiyalar", "gorevler"]
            dosya_adlari = ["kullanicilar_yedek.csv", "kuryeler_yedek.csv","kurye_avans_yedek.csv","hakedisler_yedek.csv","restoranlar_yedek.csv","restoran_islem_yedek.csv","vardiyalar_yedek.csv", "gorevler_yedek.csv"]
            
            for d_adi, tbl in zip(dosya_adlari, tablolar):
                res = supabase.table(tbl).select("*").execute()
                data = res.data
                if data:
                    with open(os.path.join(klasor, d_adi), "w", newline="", encoding="utf-8-sig") as f:
                        writer = csv.writer(f)
                        writer.writerow(data[0].keys())
                        for row in data:
                            writer.writerow(row.values())
            messagebox.showinfo("Başarılı", "Tüm bulut verileri CSV olarak yedeklendi.")
        except Exception as e: messagebox.showerror("Hata", str(e))

    def excel_yedek_yukle(self):
        if not messagebox.askyesno("Onay", "Mevcut bulut veriler güncellenecektir. Devam edilsin mi?"): return
        klasor = filedialog.askdirectory()
        if not klasor: return
        try:
            tablolar = ["kullanicilar", "kuryeler", "kurye_avans", "hakedisler", "restoranlar", "restoran_islem", "vardiyalar", "gorevler"]
            dosya_adlari = ["kullanicilar_yedek.csv", "kuryeler_yedek.csv","kurye_avans_yedek.csv","hakedisler_yedek.csv","restoranlar_yedek.csv","restoran_islem_yedek.csv","vardiyalar_yedek.csv", "gorevler_yedek.csv"]
            
            for d_adi, tbl in zip(dosya_adlari, tablolar):
                yol = os.path.join(klasor, d_adi)
                if os.path.exists(yol):
                    with open(yol, "r", encoding="utf-8-sig") as f:
                        rows = list(csv.reader(f))
                        if len(rows) > 1:
                            header = rows[0]
                            for r in rows[1:]:
                                kayit = dict(zip(header, r))
                                supabase.table(tbl).upsert(kayit).execute()
            self.show_frame("dashboard")
            messagebox.showinfo("Başarılı", "Yedek buluta başarıyla yüklendi!")
        except Exception as e: messagebox.showerror("Hata", str(e))

    # ================= OCR MOTORU (TESSERACT İLE GÖRSEL OKUMA) =================
    def pdf_ocr_ile_oku(self, dosya_yolu):
        try:
            import fitz  # PyMuPDF (PDF'i resme çevirmek için)
            doc = fitz.open(dosya_yolu)
            tum_metin = ""
            for page in doc:
                pix = page.get_pixmap(dpi=300)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                tum_metin += pytesseract.image_to_string(img, lang='tur+eng') + "\n"
            doc.close()
            return re.sub(r'[₺€$£も]', ' ', tum_metin)
        except Exception as e:
            messagebox.showerror("OCR Hatası", f"PDF taranamadı:\n{e}")
            return ""

    def kurye_pdf_yukle(self):
        dosya_yolu = filedialog.askopenfilename(title="Kurye Raporu Seç", filetypes=[("PDF Dosyaları", "*.pdf")])
        if not dosya_yolu: return
        metin = self.pdf_ocr_ile_oku(dosya_yolu)
        if not metin: return

        eslesme = re.search(r"Hakedi[sş]\s*Tutar[ıi1].*?(\d{1,3}(?:\.\d{3})*,\d{2})", metin, re.IGNORECASE | re.DOTALL)
        temiz_rakam = eslesme.group(1) if eslesme else None
        
        if not temiz_rakam:
            eslesmeler = re.findall(r"Hakedi[sş].*?(\d{1,3}(?:\.\d{3})*,\d{2})", metin, re.IGNORECASE | re.DOTALL)
            if eslesmeler: temiz_rakam = eslesmeler[-1]

        if not temiz_rakam:
            rakamlar = re.findall(r"\d{1,3}(?:\.\d{3})*,\d{2}", metin)
            if rakamlar: temiz_rakam = rakamlar[-1]

        if temiz_rakam:
            self.hak_tutar_gir.delete(0, 'end'); self.hak_tutar_gir.insert(0, temiz_rakam)
            self.hakedis_canli_hesapla()
        else: messagebox.showwarning("Bulunamadı", "PDF içinde hakediş tutarı saptanamadı.")

    def restoran_pdf_yukle(self):
        dosya_yolu = filedialog.askopenfilename(title="Restoran Raporu Seç", filetypes=[("PDF Dosyaları", "*.pdf")])
        if not dosya_yolu: return
        metin = self.pdf_ocr_ile_oku(dosya_yolu)
        if not metin: return

        yon_metni = "Teslim Edeceğimiz Tutar (- Bakiye)"
        eslesme = re.search(r"(?:Teslim Edeceğimiz|Banka Yoluyla|Toplam).*?(\d{1,3}(?:\.\d{3})*,\d{2})", metin, re.IGNORECASE | re.DOTALL)
        
        if not eslesme:
            eslesme = re.search(r"(?:Bize Ödemeniz Gereken|Borç).*?(\d{1,3}(?:\.\d{3})*,\d{2})", metin, re.IGNORECASE | re.DOTALL)
            if eslesme: yon_metni = "Bize Ödemeniz Gereken (+ Bakiye)"

        temiz_rakam = eslesme.group(1) if eslesme else None
        if not temiz_rakam:
            rakamlar = re.findall(r"\d{1,3}(?:\.\d{3})*,\d{2}", metin)
            if rakamlar: temiz_rakam = rakamlar[-1]

        if temiz_rakam:
            self.res_tutar_gir.delete(0, 'end'); self.res_tutar_gir.insert(0, temiz_rakam)
            self.res_yon_sec.set(yon_metni)
        else: messagebox.showwarning("Bulunamadı", "PDF içinde tutar saptanamadı.")

    # ================= DASHBOARD =================
    def setup_dashboard_frame(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(3, weight=1)
        self.frames["dashboard"] = frame

        ctk.CTkLabel(frame, text="Dashboard & Operasyon Özeti", font=ctk.CTkFont(size=32, weight="bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))

        self.kart_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self.kart_frame.grid(row=1, column=0, sticky="nsew")
        self.kart_frame.grid_columnconfigure((0, 1, 2), weight=1)

        orta_panel = ctk.CTkFrame(frame, fg_color="transparent")
        orta_panel.grid(row=2, column=0, sticky="nsew", pady=10)
        orta_panel.grid_columnconfigure((0, 1, 2), weight=1)
        orta_panel.grid_rowconfigure(0, weight=1)

        formlar_kapsayici = ctk.CTkFrame(orta_panel, fg_color="transparent")
        formlar_kapsayici.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        k_ekle = ctk.CTkFrame(formlar_kapsayici, corner_radius=10)
        k_ekle.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(k_ekle, text="Yeni Kurye Ekle", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 5), padx=15, anchor="w")
        self.dash_kurye_isim_gir = ctk.CTkEntry(k_ekle, placeholder_text="Kurye Adı ve Soyadı", height=35)
        self.dash_kurye_isim_gir.pack(pady=5, padx=15, fill="x")
        ctk.CTkButton(k_ekle, text="Sisteme Kaydet", fg_color="#2ecc71", height=35, command=self.dash_kurye_ekle).pack(pady=(5, 15), padx=15, fill="x")

        r_ekle = ctk.CTkFrame(formlar_kapsayici, corner_radius=10)
        r_ekle.pack(fill="x")
        ctk.CTkLabel(r_ekle, text="Yeni Restoran Ekle", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 5), padx=15, anchor="w")
        self.dash_res_isim_gir = ctk.CTkEntry(r_ekle, placeholder_text="Restoran Adı", height=35)
        self.dash_res_isim_gir.pack(pady=5, padx=15, fill="x")
        ctk.CTkButton(r_ekle, text="Restoranı Kaydet", fg_color="#3498db", height=35, command=self.dash_res_ekle).pack(pady=(5, 15), padx=15, fill="x")

        self.dash_kurye_liste_kapsayici = ctk.CTkFrame(orta_panel, corner_radius=10)
        self.dash_kurye_liste_kapsayici.grid(row=0, column=1, sticky="nsew", padx=5)
        self.dash_kurye_liste_kapsayici.grid_rowconfigure(1, weight=1); self.dash_kurye_liste_kapsayici.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.dash_kurye_liste_kapsayici, text="Sistemdeki Kuryeler", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, pady=10, padx=15, sticky="w")
        self.dash_kurye_liste_scroll = ctk.CTkScrollableFrame(self.dash_kurye_liste_kapsayici, fg_color="transparent")
        self.dash_kurye_liste_scroll.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        self.dash_res_liste_kapsayici = ctk.CTkFrame(orta_panel, corner_radius=10)
        self.dash_res_liste_kapsayici.grid(row=0, column=2, sticky="nsew", padx=5)
        self.dash_res_liste_kapsayici.grid_rowconfigure(1, weight=1); self.dash_res_liste_kapsayici.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.dash_res_liste_kapsayici, text="Sistemdeki Restoranlar", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, pady=10, padx=15, sticky="w")
        self.dash_res_liste_scroll = ctk.CTkScrollableFrame(self.dash_res_liste_kapsayici, fg_color="transparent")
        self.dash_res_liste_scroll.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        gorev_panosu = ctk.CTkFrame(frame, corner_radius=10, fg_color="#1a1a1a")
        gorev_panosu.grid(row=3, column=0, sticky="nsew", pady=10)
        gorev_panosu.grid_rowconfigure(1, weight=1)
        gorev_panosu.grid_columnconfigure((0,1,2), weight=1)

        ust_baslik_frame = ctk.CTkFrame(gorev_panosu, fg_color="transparent")
        ust_baslik_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=15, pady=10)
        ctk.CTkLabel(ust_baslik_frame, text="📋 Görevler ve Yapılacaklar (Task Manager)", font=ctk.CTkFont(size=20, weight="bold"), text_color="#f1c40f").pack(side="left")
        
        yeni_gorev_gir = ctk.CTkEntry(ust_baslik_frame, placeholder_text="Yeni Görev Yazın...", width=300, height=35)
        yeni_gorev_gir.pack(side="left", padx=15)
        
        try:
            res_k = supabase.table("kullanicilar").select("kullanici_adi").execute()
            kullanici_listesi = [r["kullanici_adi"] for r in res_k.data] if res_k.data else []
        except:
            kullanici_listesi = []

        self.gorev_kisi_sec = ctk.CTkOptionMenu(ust_baslik_frame, values=["Görev Atanmadı"] + kullanici_listesi, width=140)
        self.gorev_kisi_sec.pack(side="left", padx=5)

        ctk.CTkButton(ust_baslik_frame, text="Ekle", fg_color="#2ecc71", width=80, height=35, command=lambda: self.yeni_gorev_ekle(yeni_gorev_gir)).pack(side="left", padx=5)

        self.col_yap = ctk.CTkScrollableFrame(gorev_panosu, fg_color="#212121", label_text="📌 Yapılacaklar", label_font=ctk.CTkFont(weight="bold"))
        self.col_yap.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.col_devam = ctk.CTkScrollableFrame(gorev_panosu, fg_color="#212121", label_text="⏳ Devam Edenler", label_font=ctk.CTkFont(weight="bold"))
        self.col_devam.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        self.col_tamam = ctk.CTkScrollableFrame(gorev_panosu, fg_color="#212121", label_text="✅ Tamamlananlar", label_font=ctk.CTkFont(weight="bold"))
        self.col_tamam.grid(row=1, column=2, sticky="nsew", padx=10, pady=10)

    def dashboard_kartlari_guncelle(self):
        for widget in self.kart_frame.winfo_children(): widget.destroy()
        try:
            k_sayisi = len(supabase.table("kuryeler").select("id", count="exact").execute().data)
            r_sayisi = len(supabase.table("restoranlar").select("id", count="exact").execute().data)
            g_sayisi = len(supabase.table("gorevler").select("id", count="exact").execute().data)
        except:
            k_sayisi, r_sayisi, g_sayisi = 0, 0, 0

        self.create_card(self.kart_frame, 0, 0, "Aktif Kurye Sayısı", str(k_sayisi), "#3498db")
        self.create_card(self.kart_frame, 0, 1, "Aktif Restoran Sayısı", str(r_sayisi), "#e67e22")
        self.create_card(self.kart_frame, 0, 2, "Sistemdeki Toplam Görev", str(g_sayisi), "#2ecc71")
        self.dash_kurye_listesini_guncelle(); self.dash_restoran_listesini_guncelle()

    def create_card(self, parent, row, col, title, value, color):
        card = ctk.CTkFrame(parent, fg_color="#242424", corner_radius=12)
        card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=14, weight="bold"), text_color="gray").pack(pady=(15, 5), padx=20, anchor="w")
        ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=26, weight="bold"), text_color=color).pack(pady=(0, 15), padx=20, anchor="w")

    def dash_kurye_ekle(self):
        ad = self.dash_kurye_isim_gir.get().strip()
        if not ad: return
        try:
            supabase.table("kuryeler").insert({"ad_soyad": ad, "kayit_tarihi": datetime.now().strftime("%Y-%m-%d")}).execute()
            self.dash_kurye_isim_gir.delete(0, 'end'); self.dashboard_kartlari_guncelle()
        except Exception as e: messagebox.showwarning("Hata", f"Bu kurye kayıtlı veya hata oluştu:\n{e}")

    def dash_res_ekle(self):
        ad = self.dash_res_isim_gir.get().strip()
        if not ad: return
        try:
            supabase.table("restoranlar").insert({"ad": ad}).execute()
            self.dash_res_isim_gir.delete(0, 'end'); self.dashboard_kartlari_guncelle()
        except Exception as e: messagebox.showwarning("Hata", f"Bu restoran kayıtlı veya hata oluştu:\n{e}")

    def dash_kurye_listesini_guncelle(self):
        for widget in self.dash_kurye_liste_scroll.winfo_children(): widget.destroy()
        w_list = [180, 60]
        self.create_table_header(self.dash_kurye_liste_scroll, ["İsim", "İşlem"], w_list)
        try:
            res = supabase.table("kuryeler").select("id, ad_soyad").order("ad_soyad").execute()
            kuryeler = res.data if res.data else []
            for k in kuryeler:
                k_id, ad = k["id"], k["ad_soyad"]
                satir = ctk.CTkFrame(self.dash_kurye_liste_scroll, fg_color="#2b2b2b", corner_radius=5)
                satir.pack(fill="x", padx=5, pady=2)
                for i, w in enumerate(w_list): satir.grid_columnconfigure(i, weight=0, minsize=w)
                ctk.CTkLabel(satir, text=ad, font=ctk.CTkFont(weight="bold"), width=w_list[0], anchor="center").grid(row=0, column=0, padx=5, pady=5)
                ctk.CTkButton(satir, text="🗑️", width=40, height=25, fg_color="#c0392b", command=lambda i=k_id: self.dash_kurye_sil(i)).grid(row=0, column=1, padx=5, pady=5)
        except Exception:
            pass

    def dash_restoran_listesini_guncelle(self):
        for widget in self.dash_res_liste_scroll.winfo_children(): widget.destroy()
        w_list = [220, 60]
        self.create_table_header(self.dash_res_liste_scroll, ["Restoran Adı", "İşlem"], w_list)
        try:
            res = supabase.table("restoranlar").select("id, ad").order("ad").execute()
            restoranlar = res.data if res.data else []
            for r in restoranlar:
                r_id, ad = r["id"], r["ad"]
                satir = ctk.CTkFrame(self.dash_res_liste_scroll, fg_color="#2b2b2b", corner_radius=5)
                satir.pack(fill="x", padx=5, pady=2)
                for i, w in enumerate(w_list): satir.grid_columnconfigure(i, weight=0, minsize=w)
                ctk.CTkLabel(satir, text=ad, font=ctk.CTkFont(weight="bold"), width=w_list[0], anchor="center").grid(row=0, column=0, padx=5, pady=5)
                ctk.CTkButton(satir, text="🗑️", width=40, height=25, fg_color="#c0392b", command=lambda i=r_id: self.dash_res_sil(i)).grid(row=0, column=1, padx=5, pady=5)
        except Exception:
            pass

    def dash_kurye_sil(self, k_id):
        try:
            supabase.table("kuryeler").delete().eq("id", k_id).execute()
            self.dashboard_kartlari_guncelle()
        except Exception as e:
            messagebox.showerror("Hata", f"Silinemedi: {e}")

    def dash_res_sil(self, r_id):
        if messagebox.askyesno("Onay", "Restoranı silmek istediğinize emin misiniz?"):
            try:
                supabase.table("restoranlar").delete().eq("id", r_id).execute()
                self.dashboard_kartlari_guncelle()
            except Exception as e:
                messagebox.showerror("Hata", f"Silinemedi: {e}")

    def yeni_gorev_ekle(self, entry_widget):
        baslik = entry_widget.get().strip()
        atanan = self.gorev_kisi_sec.get()
        if not baslik: return
        try:
            supabase.table("gorevler").insert({
                "baslik": baslik,
                "durum": "Yapılacak",
                "tarih": datetime.now().strftime("%d %b"),
                "atanan_kisi": atanan,
                "olusturan_kisi": self.current_user
            }).execute()
            entry_widget.delete(0, 'end')
            self.dashboard_gorevleri_getir(); self.dashboard_kartlari_guncelle()
        except Exception as e:
            messagebox.showerror("Hata", f"Görev eklenemedi: {e}")

    def gorev_durum_degistir(self, g_id, yeni_durum):
        try:
            supabase.table("gorevler").update({"durum": yeni_durum}).eq("id", g_id).execute()
            self.dashboard_gorevleri_getir()
        except Exception as e:
            messagebox.showerror("Hata", f"Durum güncellenemedi: {e}")

    def gorev_sil(self, g_id):
        try:
            supabase.table("gorevler").delete().eq("id", g_id).execute()
            self.dashboard_gorevleri_getir(); self.dashboard_kartlari_guncelle()
        except Exception as e:
            messagebox.showerror("Hata", f"Görev silinemedi: {e}")

    def dashboard_gorevleri_getir(self):
        for w in self.col_yap.winfo_children() + self.col_devam.winfo_children() + self.col_tamam.winfo_children(): w.destroy()
        try:
            res = supabase.table("gorevler").select("*").order("id", desc=True).execute()
            gorevler = res.data if res.data else []
        except:
            gorevler = []

        for g in gorevler:
            g_id = g.get("id")
            baslik = g.get("baslik")
            durum = g.get("durum")
            tarih = g.get("tarih")
            atanan = g.get("atanan_kisi")
            olusturan = g.get("olusturan_kisi", "")

            hedef_frame = self.col_yap if durum == "Yapılacak" else (self.col_devam if durum == "Devam Ediyor" else self.col_tamam)
            kart = ctk.CTkFrame(hedef_frame, fg_color="#2b2b2b", corner_radius=8)
            kart.pack(fill="x", padx=5, pady=5)
            
            ctk.CTkLabel(kart, text=baslik, wraplength=180, justify="left", font=ctk.CTkFont(weight="bold")).pack(pady=(10,2), padx=10, anchor="w")
            if atanan and atanan != "Görev Atanmadı":
                ctk.CTkLabel(kart, text=f"👤 Atanan: {atanan}", text_color="#f39c12", font=ctk.CTkFont(size=11, weight="bold")).pack(padx=10, anchor="w")
            
            alt_bilgi = f"{tarih}" + (f" | Açan: {olusturan}" if olusturan else "")
            ctk.CTkLabel(kart, text=alt_bilgi, text_color="gray", font=ctk.CTkFont(size=10)).pack(padx=10, anchor="w")
            
            btn_frame = ctk.CTkFrame(kart, fg_color="transparent")
            btn_frame.pack(fill="x", pady=5, padx=5)
            
            if self.current_role == "admin" or self.current_user == olusturan:
                ctk.CTkButton(btn_frame, text="🗑", width=25, height=25, fg_color="#c0392b", command=lambda i=g_id: self.gorev_sil(i)).pack(side="left", padx=2)
            
            if durum == "Yapılacak":
                ctk.CTkButton(btn_frame, text="Başla ➔", width=60, height=25, fg_color="#3498db", command=lambda i=g_id: self.gorev_durum_degistir(i, "Devam Ediyor")).pack(side="right", padx=2)
            elif durum == "Devam Ediyor":
                ctk.CTkButton(btn_frame, text="Bitti ➔", width=60, height=25, fg_color="#2ecc71", command=lambda i=g_id: self.gorev_durum_degistir(i, "Tamamlandı")).pack(side="right", padx=2)
                ctk.CTkButton(btn_frame, text="⬅ Geri", width=50, height=25, fg_color="#7f8c8d", command=lambda i=g_id: self.gorev_durum_degistir(i, "Yapılacak")).pack(side="right", padx=2)
            else:
                ctk.CTkButton(btn_frame, text="⬅ Geri", width=50, height=25, fg_color="#7f8c8d", command=lambda i=g_id: self.gorev_durum_degistir(i, "Devam Ediyor")).pack(side="right", padx=2)

    # ================= VARDİYA =================
    def setup_vardiya_frame(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid_rowconfigure(2, weight=1); frame.grid_columnconfigure(0, weight=1)
        self.frames["vardiya"] = frame
        ctk.CTkLabel(frame, text="📅 Kurye Haftalık Vardiya Çizelgesi", font=ctk.CTkFont(size=28, weight="bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))
        ust_kutu = ctk.CTkFrame(frame, corner_radius=10, height=50)
        ust_kutu.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(ust_kutu, text="Hafta Seçimi:", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=15, pady=10)
        self.vardiya_hafta_menu = ctk.CTkOptionMenu(ust_kutu, values=["Varsayılan"], command=lambda e: self.vardiya_listesini_guncelle(), width=180)
        self.vardiya_hafta_menu.pack(side="left", padx=5)
        ctk.CTkButton(ust_kutu, text="➕ Yeni Vardiya Ekle", fg_color="#2ecc71", command=self.vardiya_ekle_duzenle_popup).pack(side="left", padx=10)
        ctk.CTkButton(ust_kutu, text="📥 Excel'den Yükle", fg_color="#2980b9", command=self.vardiya_excel_ice_aktar).pack(side="left", padx=5)
        ctk.CTkButton(ust_kutu, text="📤 Dışa Aktar", fg_color="#16a085", command=self.vardiya_excel_disa_aktar).pack(side="left", padx=5)
        ctk.CTkButton(ust_kutu, text="🗑️ Haftayı Sil", fg_color="#c0392b", hover_color="#e74c3c", command=self.vardiya_haftayi_sil).pack(side="left", padx=10)
        tablo_kapsayici = ctk.CTkFrame(frame, fg_color="#1a1a1a")
        tablo_kapsayici.grid(row=2, column=0, sticky="nsew", pady=5)
        tablo_kapsayici.grid_rowconfigure(1, weight=1); tablo_kapsayici.grid_columnconfigure(0, weight=1)
        self.vardiya_liste_scroll = ctk.CTkScrollableFrame(tablo_kapsayici, fg_color="transparent")
        self.vardiya_liste_scroll.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

    def vardiya_hafta_menu_guncelle(self):
        try:
            res = supabase.table("vardiyalar").select("hafta").order("id", desc=True).execute()
            haftalar = list(set([row["hafta"] for row in res.data])) if res.data else []
        except:
            haftalar = []
        self.vardiya_hafta_menu.configure(values=haftalar if haftalar else ["24-30 Ağustos 2026"])
        if haftalar: self.vardiya_hafta_menu.set(haftalar[0])

    def vardiya_haftayi_sil(self):
        hafta = self.vardiya_hafta_menu.get()
        if not hafta or hafta == "Varsayılan": return
        if messagebox.askyesno("Onay", f"'{hafta}' haftasına ait TÜM vardiya kayıtlarını silmek istediğinize emin misiniz?"):
            try:
                supabase.table("vardiyalar").delete().eq("hafta", hafta).execute()
                self.vardiya_hafta_menu_guncelle()
                self.vardiya_listesini_guncelle()
                messagebox.showinfo("Başarılı", "Hafta başarıyla silindi.")
            except Exception as e:
                messagebox.showerror("Hata", f"Silinemedi: {e}")

    def vardiya_ekle_duzenle_popup(self, mevcut_kurye=None, data=None):
        pencere = ctk.CTkToplevel(self)
        pencere.title("Vardiya Düzenle" if mevcut_kurye else "Yeni Vardiya Ekle")
        pencere.geometry("450x580")
        pencere.attributes("-topmost", True)
        pencere_ikonu_ayarla(pencere)
        form_kutu = ctk.CTkFrame(pencere, fg_color="transparent")
        form_kutu.pack(fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(form_kutu, text="Hafta Adı:", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        hafta_gir = ctk.CTkEntry(form_kutu, height=35)
        hafta_gir.pack(fill="x", pady=(0, 10))
        hafta_gir.insert(0, self.vardiya_hafta_menu.get())
        ctk.CTkLabel(form_kutu, text="Kurye:", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        kurye_menu = ctk.CTkOptionMenu(form_kutu, values=self.kurye_listesini_getir(), height=35)
        kurye_menu.pack(fill="x", pady=(0, 10))
        if mevcut_kurye:
            kurye_menu.set(mevcut_kurye)
            kurye_menu.configure(state="disabled")

        gunler = [("Pazartesi", "pzt"), ("Salı", "sal"), ("Çarşamba", "car"), ("Perşembe", "per"), ("Cuma", "cum"), ("Cumartesi", "cts"), ("Pazar", "paz")]
        entries = {}
        for idx, (label, key) in enumerate(gunler):
            f = ctk.CTkFrame(form_kutu, fg_color="transparent")
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(f, text=label, width=100, anchor="w").pack(side="left")
            ent = ctk.CTkEntry(f, placeholder_text="09:00-18:00", height=30)
            ent.pack(side="left", fill="x", expand=True, padx=5)
            ent.insert(0, data[idx] if data else "09:00-18:00")
            ctk.CTkButton(f, text="🗑️ İzinli", width=30, fg_color="#e74c3c", command=lambda e=ent: (e.delete(0, 'end'), e.insert(0, "İzinli"))).pack(side="right")
            entries[key] = ent

        def kaydet():
            h_adi, k_adi = hafta_gir.get().strip(), kurye_menu.get()
            if not h_adi or k_adi == "Önce Kurye Ekleyin!": return
            vals = {k: v.get().strip() for k, v in entries.items()}
            try:
                supabase.table("vardiyalar").upsert({
                    "hafta": h_adi,
                    "kurye_ad": k_adi,
                    "pzt": vals['pzt'],
                    "sal": vals['sal'],
                    "car": vals['car'],
                    "per": vals['per'],
                    "cum": vals['cum'],
                    "cts": vals['cts'],
                    "paz": vals['paz']
                }, on_conflict="hafta,kurye_ad").execute()
                
                self.vardiya_hafta_menu_guncelle(); self.vardiya_hafta_menu.set(h_adi)
                self.vardiya_listesini_guncelle(); pencere.destroy()
            except Exception as e:
                messagebox.showerror("Hata", f"Kaydedilemedi: {e}")

        ctk.CTkButton(pencere, text="💾 Kaydet", fg_color="#2ecc71", height=40, command=kaydet).pack(pady=15, padx=20, fill="x")

    def vardiya_erken_saat_bul(self, gunler):
        saatler = [re.search(r'\d{2}:\d{2}', str(g)).group(0) for g in gunler if re.search(r'\d{2}:\d{2}', str(g))]
        return min(saatler) if saatler else "23:59"

    def vardiya_excel_ice_aktar(self):
        dosya_yolu = filedialog.askopenfilename(title="Vardiya Excel Seç", filetypes=[("Excel", "*.xlsx")])
        if not dosya_yolu: return
        try:
            df = pd.read_excel(dosya_yolu, header=None)
            header_idx = next((i for i, r in df.iterrows() if any(str(c).strip().lower()=='kurye' for c in r.values)), None)
            if header_idx is None: return messagebox.showerror("Hata", "'Kurye' sütunu bulunamadı!")
            h_adi = simpledialog.askstring("Hafta", "Hafta adı girin (Örn: 24-30 Ağustos 2026):", initialvalue="24-30 Ağustos 2026")
            if not h_adi: h_adi = "Haftalık Vardiya"
            
            for _, r in df.iloc[header_idx+1:].dropna(subset=[0]).iterrows():
                k = str(r.iloc[0]).strip()
                if not k or k.lower() == 'nan': continue
                g = [str(r.iloc[i]).strip() if len(r)>i and pd.notna(r.iloc[i]) else "İzinli" for i in range(1, 8)]
                
                supabase.table("vardiyalar").upsert({
                    "hafta": h_adi,
                    "kurye_ad": k,
                    "pzt": g[0], "sal": g[1], "car": g[2], "per": g[3], "cum": g[4], "cts": g[5], "paz": g[6]
                }, on_conflict="hafta,kurye_ad").execute()

            self.vardiya_hafta_menu_guncelle(); self.vardiya_hafta_menu.set(h_adi); self.vardiya_listesini_guncelle()
            messagebox.showinfo("Başarılı", "Vardiyalar buluta aktarıldı!")
        except Exception as e: messagebox.showerror("Hata", str(e))

    def vardiya_excel_disa_aktar(self):
        h = self.vardiya_hafta_menu.get()
        yol = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile=f"Vardiya_{h}.xlsx")
        if not yol: return
        try:
            res = supabase.table("vardiyalar").select("kurye_ad, pzt, sal, car, per, cum, cts, paz").eq("hafta", h).execute()
            data = res.data
            if data:
                df = pd.DataFrame(data)
                df.rename(columns={
                    "kurye_ad": "Kurye", "pzt": "Pazartesi", "sal": "Salı", 
                    "car": "Çarşamba", "per": "Perşembe", "cum": "Cuma", 
                    "cts": "Cumartesi", "paz": "Pazar"
                }, inplace=True)
                df.to_excel(yol, index=False)
                messagebox.showinfo("Başarılı", "Dışa aktarıldı.")
            else:
                messagebox.showwarning("Boş", "Dışa aktarılacak kayıt bulunamadı.")
        except Exception as e: messagebox.showerror("Hata", str(e))

    def vardiya_listesini_guncelle(self):
        for widget in self.vardiya_liste_scroll.winfo_children(): widget.destroy()
        w_list = [160, 95, 95, 95, 95, 95, 95, 95, 95]
        self.create_table_header(self.vardiya_liste_scroll, ["Kurye Adı", "Pzt", "Sal", "Çar", "Per", "Cum", "Cts", "Paz", "İşlem"], w_list)
        hafta = self.vardiya_hafta_menu.get()
        try:
            res = supabase.table("vardiyalar").select("kurye_ad, pzt, sal, car, per, cum, cts, paz").eq("hafta", hafta).execute()
            kayitlar = [(r["kurye_ad"], r["pzt"], r["sal"], r["car"], r["per"], r["cum"], r["cts"], r["paz"]) for r in res.data] if res.data else []
        except:
            kayitlar = []

        if not kayitlar: return ctk.CTkLabel(self.vardiya_liste_scroll, text="Kayıt bulunamadı.").pack(pady=30)
        
        for satir_data in sorted(kayitlar, key=lambda x: self.vardiya_erken_saat_bul(x[1:])):
            satir = ctk.CTkFrame(self.vardiya_liste_scroll, fg_color="#2b2b2b", corner_radius=5)
            satir.pack(fill="x", padx=5, pady=3)
            for i, w in enumerate(w_list): satir.grid_columnconfigure(i, weight=0, minsize=w)
            
            ctk.CTkLabel(satir, text=satir_data[0], font=ctk.CTkFont(weight="bold"), text_color="#3498db", width=w_list[0], anchor="center").grid(row=0, column=0, padx=5, pady=8)
            for idx, val in enumerate(satir_data[1:], start=1):
                renk = "#2ecc71" if any(x in str(val) for x in ["08:","09:","10:","11:"]) else ("gray" if "İzinli" in str(val) else "white")
                ctk.CTkLabel(satir, text=str(val), text_color=renk, width=w_list[idx], anchor="center").grid(row=0, column=idx, padx=5, pady=8)
            ctk.CTkButton(satir, text="⚙️ Düzenle", width=40, command=lambda k=satir_data[0], d=satir_data[1:]: self.vardiya_ekle_duzenle_popup(k, d)).grid(row=0, column=8, padx=5, pady=5)

    # ================= AVANS YÖNETİMİ =================
    def setup_avans_frame(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid_rowconfigure(2, weight=1); frame.grid_columnconfigure(0, weight=1)
        self.frames["avans"] = frame
        ctk.CTkLabel(frame, text="Kurye Avans Yönetimi", font=ctk.CTkFont(size=32, weight="bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))
        ust_ekle_frame = ctk.CTkFrame(frame, corner_radius=10, fg_color="#212121")
        ust_ekle_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15), padx=5)
        for i in range(4): ust_ekle_frame.grid_columnconfigure(i, weight=1)
        self.avans_kurye_sec = ctk.CTkOptionMenu(ust_ekle_frame, values=self.kurye_listesini_getir(), height=38)
        self.avans_kurye_sec.grid(row=0, column=0, padx=10, pady=12, sticky="ew")
        self.avans_tutar_gir = ctk.CTkEntry(ust_ekle_frame, placeholder_text="Tutar (Örn: 1.500,50)", height=38)
        self.avans_tutar_gir.grid(row=0, column=1, padx=10, pady=12, sticky="ew")
        self.avans_aciklama_gir = ctk.CTkEntry(ust_ekle_frame, placeholder_text="Açıklama (Örn: Yakıt)", height=38)
        self.avans_aciklama_gir.grid(row=0, column=2, padx=10, pady=12, sticky="ew")
        ctk.CTkButton(ust_ekle_frame, text="➕ Avans Ver", fg_color="#2ecc71", height=38, command=self.avansi_veritabanina_yaz).grid(row=0, column=3, padx=10, pady=12, sticky="ew")
        
        alt_liste_kapsayici = ctk.CTkFrame(frame, fg_color="transparent")
        alt_liste_kapsayici.grid(row=2, column=0, sticky="nsew", padx=5)
        alt_liste_kapsayici.grid_rowconfigure(1, weight=1); alt_liste_kapsayici.grid_columnconfigure(0, weight=1)
        filtre_kutu = ctk.CTkFrame(alt_liste_kapsayici, corner_radius=10)
        filtre_kutu.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.filtre_kurye_sec = ctk.CTkOptionMenu(filtre_kutu, values=["Tüm Kuryeler"] + self.kurye_listesini_getir(), width=160)
        self.filtre_kurye_sec.pack(side="left", padx=15, pady=10)
        self.filtre_baslangic = ctk.CTkEntry(filtre_kutu, placeholder_text="Başlangıç Tarihi", width=130)
        self.filtre_baslangic.pack(side="left", padx=(5, 0), pady=10)
        ctk.CTkButton(filtre_kutu, text="📅", width=35, command=lambda: TarihSeciciPenceresi(self, self.filtre_baslangic)).pack(side="left", padx=(0, 5), pady=10)
        self.filtre_bitis = ctk.CTkEntry(filtre_kutu, placeholder_text="Bitiş Tarihi", width=130)
        self.filtre_bitis.pack(side="left", padx=(5, 0), pady=10)
        ctk.CTkButton(filtre_kutu, text="📅", width=35, command=lambda: TarihSeciciPenceresi(self, self.filtre_bitis)).pack(side="left", padx=(0, 5), pady=10)
        self.filtre_bitis.insert(0, datetime.now().strftime("%Y-%m-%d"))
        ctk.CTkButton(filtre_kutu, text="🔍 Listele", width=100, command=self.gecmis_avans_listele).pack(side="right", padx=15, pady=10)
        self.gecmis_liste_scroll = ctk.CTkScrollableFrame(alt_liste_kapsayici)
        self.gecmis_liste_scroll.grid(row=1, column=0, sticky="nsew")

    def avansi_veritabanina_yaz(self):
        kurye, tutar_str, aciklama = self.avans_kurye_sec.get(), self.avans_tutar_gir.get().strip(), self.avans_aciklama_gir.get()
        if not tutar_str or kurye == "Önce Kurye Ekleyin!": return messagebox.showwarning("Eksik", "Lütfen bilgileri doldurun.")
        tutar_float = temiz_float(tutar_str)
        if tutar_float == 0.0: return messagebox.showerror("Hata", "Geçersiz Tutar!")
        
        try:
            supabase.table("kurye_avans").insert({
                "kurye_ad": kurye,
                "tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "tutar": tutar_float,
                "aciklama": aciklama,
                "odendi_mi": 0,
                "veren_kullanici": self.current_user
            }).execute()
            self.avans_tutar_gir.delete(0, 'end'); self.avans_aciklama_gir.delete(0, 'end')
            self.gecmis_avans_listele(); self.dashboard_kartlari_guncelle()
        except Exception as e:
            messagebox.showerror("Hata", f"Avans kaydedilemedi: {e}")

    def gecmis_avans_listele(self):
        for widget in self.gecmis_liste_scroll.winfo_children(): widget.destroy()
        w_list = [130, 160, 200, 120, 100, 100, 60]
        self.create_table_header(self.gecmis_liste_scroll, ["Tarih & Saat", "Kurye", "Açıklama", "Tutar", "Veren", "Durum", "İşlem"], w_list)
        kurye, bas, bit = self.filtre_kurye_sec.get(), self.filtre_baslangic.get(), self.filtre_bitis.get()
        
        try:
            query = supabase.table("kurye_avans").select("*")
            if kurye != "Tüm Kuryeler":
                query = query.eq("kurye_ad", kurye)
            if bas:
                query = query.gte("tarih", bas + " 00:00")
            if bit:
                query = query.lte("tarih", bit + " 23:59")
            
            res = query.order("id", desc=True).execute()
            avanslar = res.data if res.data else []
        except:
            avanslar = []

        for a in avanslar:
            a_id, k_ad, tutar, aciklama, tarih, odendi_mi, veren = a.get("id"), a.get("kurye_ad"), a.get("tutar"), a.get("aciklama"), a.get("tarih"), a.get("odendi_mi"), a.get("veren_kullanici")
            satir = ctk.CTkFrame(self.gecmis_liste_scroll, fg_color="#2b2b2b", corner_radius=5)
            satir.pack(fill="x", padx=5, pady=3)
            for i, w in enumerate(w_list): satir.grid_columnconfigure(i, weight=0, minsize=w)
            ctk.CTkLabel(satir, text=tarih[:16], text_color="gray", width=w_list[0], anchor="center").grid(row=0, column=0, padx=5, pady=8)
            ctk.CTkLabel(satir, text=k_ad, font=ctk.CTkFont(weight="bold"), width=w_list[1], anchor="center").grid(row=0, column=1, padx=5, pady=8)
            ctk.CTkLabel(satir, text=aciklama, width=w_list[2], anchor="center").grid(row=0, column=2, padx=5, pady=8)
            ctk.CTkLabel(satir, text=f"{tutar:,.2f} TL", width=w_list[3], anchor="center").grid(row=0, column=3, padx=5, pady=8)
            ctk.CTkLabel(satir, text=veren or "Admin", text_color="#3498db", width=w_list[4], anchor="center").grid(row=0, column=4, padx=5, pady=8)
            ctk.CTkLabel(satir, text="Ödendi" if odendi_mi else "Bekliyor", text_color="#2ecc71" if odendi_mi else "#e74c3c", width=w_list[5], anchor="center").grid(row=0, column=5, padx=5, pady=8)
            if not odendi_mi or self.current_role == "admin": ctk.CTkButton(satir, text="🗑️", width=40, fg_color="#c0392b", command=lambda i=a_id: self.avans_sil(i)).grid(row=0, column=6, padx=5, pady=5)

    def avans_sil(self, kayit_id):
        if messagebox.askyesno("Onay", "Emin misiniz?"):
            try:
                supabase.table("kurye_avans").delete().eq("id", kayit_id).execute()
                self.gecmis_avans_listele(); self.dashboard_kartlari_guncelle()
            except Exception as e:
                messagebox.showerror("Hata", f"Silinemedi: {e}")

    # ================= HAKEDİŞLER =================
    def setup_hakedis_frame(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid_rowconfigure(2, weight=1); frame.grid_columnconfigure(0, weight=1)
        self.frames["hakedis"] = frame
        ctk.CTkLabel(frame, text="Hakediş & Maaş Kapatma", font=ctk.CTkFont(size=32, weight="bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))
        ust_hakedis_kapsayici = ctk.CTkFrame(frame, fg_color="transparent")
        ust_hakedis_kapsayici.grid(row=1, column=0, sticky="ew", pady=(0, 15), padx=5)
        ust_hakedis_kapsayici.grid_columnconfigure((0, 1), weight=1)
        form_frame = ctk.CTkFrame(ust_hakedis_kapsayici, corner_radius=10, fg_color="#212121")
        form_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        ctk.CTkLabel(form_frame, text="Bordro Girdi Bilgileri", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(15, 10), padx=20, anchor="w")
        self.hak_kurye_sec = ctk.CTkOptionMenu(form_frame, values=self.kurye_listesini_getir(), command=self.hakedis_kurye_degisti, height=40)
        self.hak_kurye_sec.pack(pady=8, padx=20, fill="x")
        self.hak_tutar_gir = ctk.CTkEntry(form_frame, placeholder_text="Maaş / Hak Ediş (TL)", height=40)
        self.hak_tutar_gir.pack(pady=8, padx=20, fill="x")
        self.hak_tutar_gir.bind("<KeyRelease>", self.hakedis_canli_hesapla)
        ctk.CTkButton(form_frame, text="📄 PDF'den Otomatik Çek (OCR)", fg_color="#8e44ad", command=self.kurye_pdf_yukle).pack(pady=4, padx=20, fill="x")
        self.hak_nakit_gir = ctk.CTkEntry(form_frame, placeholder_text="Üstündeki Nakit (TL)", height=40)
        self.hak_nakit_gir.pack(pady=8, padx=20, fill="x")
        self.hak_nakit_gir.bind("<KeyRelease>", self.hakedis_canli_hesapla)
        self.btn_hakedis_kaydet = ctk.CTkButton(form_frame, text="✅ Hakedişi Onayla", fg_color="#2ecc71", height=42, state="disabled", command=self.hakedis_kaydet)
        self.btn_hakedis_kaydet.pack(pady=15, padx=20, fill="x")
        makbuz_frame = ctk.CTkFrame(ust_hakedis_kapsayici, fg_color="#1a2530", corner_radius=10)
        makbuz_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        makbuz_frame.grid_rowconfigure(2, weight=1); makbuz_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(makbuz_frame, text="HESAPLAMA FİŞİ", font=ctk.CTkFont(size=16, weight="bold"), text_color="#3498db").pack(pady=10)
        self.fis_kurye_lbl = ctk.CTkLabel(makbuz_frame, text="Kurye: -")
        self.fis_kurye_lbl.pack(anchor="w", padx=15)
        self.avans_secim_scroll = ctk.CTkScrollableFrame(makbuz_frame, fg_color="#111820", height=120)
        self.avans_secim_scroll.pack(fill="x", padx=15, pady=5)
        ozet_kutu = ctk.CTkFrame(makbuz_frame, fg_color="transparent")
        ozet_kutu.pack(fill="x", padx=15, pady=5)
        self.fis_hakedis_lbl = ctk.CTkLabel(ozet_kutu, text="Hak Ediş: 0.00 TL")
        self.fis_hakedis_lbl.pack(anchor="w")
        self.fis_avans_lbl = ctk.CTkLabel(ozet_kutu, text="Avans: - 0.00 TL", text_color="#ffcccc")
        self.fis_avans_lbl.pack(anchor="w")
        self.fis_nakit_lbl = ctk.CTkLabel(ozet_kutu, text="Nakit: - 0.00 TL", text_color="#ffcccc")
        self.fis_nakit_lbl.pack(anchor="w")
        self.fis_devir_lbl = ctk.CTkLabel(ozet_kutu, text="Devreden Borç: 0.00 TL", text_color="#f39c12")
        self.fis_devir_lbl.pack(anchor="w")
        self.fis_net_lbl = ctk.CTkLabel(makbuz_frame, text="NET: 0.00 TL", font=ctk.CTkFont(size=20, weight="bold"), text_color="#2ecc71")
        self.fis_net_lbl.pack(pady=(0, 10))
        
        alt_hakedis_kapsayici = ctk.CTkFrame(frame, fg_color="transparent")
        alt_hakedis_kapsayici.grid(row=2, column=0, sticky="nsew", padx=5)
        alt_hakedis_kapsayici.grid_rowconfigure(1, weight=1); alt_hakedis_kapsayici.grid_columnconfigure(0, weight=1)
        filtre_kutu = ctk.CTkFrame(alt_hakedis_kapsayici, corner_radius=10)
        filtre_kutu.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.hak_filtre_kurye_sec = ctk.CTkOptionMenu(filtre_kutu, values=["Tüm Kuryeler"] + self.kurye_listesini_getir(), width=160)
        self.hak_filtre_kurye_sec.pack(side="left", padx=15, pady=10)
        ctk.CTkButton(filtre_kutu, text="🔍 Listele", width=100, command=self.gecmis_hakedisleri_getir).pack(side="right", padx=15, pady=10)
        self.hakedis_liste_frame = ctk.CTkScrollableFrame(alt_hakedis_kapsayici)
        self.hakedis_liste_frame.grid(row=1, column=0, sticky="nsew")

    def hakedis_kurye_degisti(self, event=None):
        for widget in self.avans_secim_scroll.winfo_children(): widget.destroy()
        kurye = self.hak_kurye_sec.get()
        try:
            res = supabase.table("kurye_avans").select("id, tarih, tutar, aciklama").eq("kurye_ad", kurye).eq("odendi_mi", 0).execute()
            avanslar = [(r["id"], r["tarih"], r["tutar"], r["aciklama"]) for r in res.data] if res.data else []
        except:
            avanslar = []

        self.avans_checkboxlar = {}
        for a_id, tarih, tutar, aciklama in avanslar:
            var = ctk.BooleanVar(value=True)
            chk = ctk.CTkCheckBox(self.avans_secim_scroll, text=f"{tarih[5:10]} | {aciklama}: {tutar} TL", variable=var, command=self.hakedis_canli_hesapla)
            chk.pack(anchor="w", pady=2)
            self.avans_checkboxlar[a_id] = (var, tutar)
        self.hakedis_canli_hesapla()

    def hakedis_canli_hesapla(self, event=None, *args):
        kurye = self.hak_kurye_sec.get()
        a_toplam = sum(t for var, t in getattr(self, 'avans_checkboxlar', {}).values() if var.get())
        
        h = temiz_float(self.hak_tutar_gir.get())
        n = temiz_float(self.hak_nakit_gir.get())
        
        try:
            res = supabase.table("hakedisler").select("net_odeme").eq("kurye_ad", kurye).lt("net_odeme", 0).execute()
            devir_listesi = [r["net_odeme"] for r in res.data] if res.data else []
            devir = abs(sum(devir_listesi))
        except:
            devir = 0.0

        net = h - a_toplam - n - devir
        self.fis_kurye_lbl.configure(text=f"Kurye: {kurye}")
        self.fis_hakedis_lbl.configure(text=f"Hak Ediş: {h:,.2f} TL")
        self.fis_avans_lbl.configure(text=f"Avans: - {a_toplam:,.2f} TL")
        self.fis_nakit_lbl.configure(text=f"Nakit: - {n:,.2f} TL")
        self.fis_devir_lbl.configure(text=f"Devreden Borç: - {devir:,.2f} TL")
        self.fis_net_lbl.configure(text=f"NET YATACAK: {net:,.2f} TL")
        self.btn_hakedis_kaydet.configure(state="normal" if h > 0 or n > 0 or a_toplam > 0 else "disabled")
        self.aktif_hesaplama = {"k": kurye, "h": h, "a": a_toplam, "n": n, "devir": devir, "net": net, "ids": [i for i, (v, t) in getattr(self, 'avans_checkboxlar', {}).items() if v.get()]}

    def hakedis_kaydet(self):
        d = getattr(self, 'aktif_hesaplama', None)
        if not d: return
        tarih = datetime.now().strftime("%Y-%m-%d %H:%M")
        try:
            supabase.table("hakedisler").insert({
                "kurye_ad": d['k'],
                "tarih": tarih,
                "hakedis": d['h'],
                "kesilen_avans": d['a'] + d['devir'],
                "ustundeki_nakit": d['n'],
                "net_odeme": d['net']
            }).execute()

            if d['ids']:
                for i in d['ids']:
                    supabase.table("kurye_avans").update({"odendi_mi": 1}).eq("id", i).execute()

            if d['net'] < 0:
                supabase.table("kurye_avans").insert({
                    "kurye_ad": d['k'],
                    "tarih": tarih,
                    "tutar": abs(d['net']),
                    "aciklama": "Devreden Bakiye",
                    "odendi_mi": 0,
                    "veren_kullanici": self.current_user
                }).execute()

            self.hak_tutar_gir.delete(0, 'end'); self.hak_nakit_gir.delete(0, 'end')
            self.hakedis_kurye_degisti(); self.gecmis_hakedisleri_getir(); self.dashboard_kartlari_guncelle()
            messagebox.showinfo("Başarılı", "Hakediş kapatıldı.")
        except Exception as e:
            messagebox.showerror("Hata", f"Hakediş kaydedilemedi: {e}")

    def gecmis_hakedisleri_getir(self):
        for widget in self.hakedis_liste_frame.winfo_children(): widget.destroy()
        w_list = [130, 160, 130, 130, 130, 130, 60]
        self.create_table_header(self.hakedis_liste_frame, ["Tarih", "Kurye", "Brüt", "Kesilen Avans", "Nakit", "Net Ödenen", "İşlem"], w_list)
        kurye = self.hak_filtre_kurye_sec.get()
        
        try:
            query = supabase.table("hakedisler").select("*")
            if kurye != "Tüm Kuryeler":
                query = query.eq("kurye_ad", kurye)
            res = query.order("id", desc=True).execute()
            hakedisler = res.data if res.data else []
        except:
            hakedisler = []

        for h in hakedisler:
            h_id, k, t, b, a, nk, n = h.get("id"), h.get("kurye_ad"), h.get("tarih"), h.get("hakedis"), h.get("kesilen_avans"), h.get("ustundeki_nakit"), h.get("net_odeme")
            satir = ctk.CTkFrame(self.hakedis_liste_frame, fg_color="#2b2b2b", corner_radius=5)
            satir.pack(fill="x", padx=5, pady=3)
            for i, w in enumerate(w_list): satir.grid_columnconfigure(i, weight=0, minsize=w)
            ctk.CTkLabel(satir, text=t[:16], text_color="gray", width=w_list[0], anchor="center").grid(row=0, column=0, padx=5, pady=8)
            ctk.CTkLabel(satir, text=k, font=ctk.CTkFont(weight="bold"), width=w_list[1], anchor="center").grid(row=0, column=1, padx=5, pady=8)
            ctk.CTkLabel(satir, text=f"{b:,.2f} TL", width=w_list[2], anchor="center").grid(row=0, column=2, padx=5, pady=8)
            ctk.CTkLabel(satir, text=f"-{a:,.2f} TL", text_color="#ffcccc", width=w_list[3], anchor="center").grid(row=0, column=3, padx=5, pady=8)
            ctk.CTkLabel(satir, text=f"-{nk:,.2f} TL", text_color="#ffcccc", width=w_list[4], anchor="center").grid(row=0, column=4, padx=5, pady=8)
            ctk.CTkLabel(satir, text=f"{n:,.2f} TL", font=ctk.CTkFont(weight="bold"), text_color="#3498db" if n>=0 else "#e74c3c", width=w_list[5], anchor="center").grid(row=0, column=5, padx=5, pady=8)
            if self.current_role == "admin": ctk.CTkButton(satir, text="🗑️", width=40, fg_color="#c0392b", command=lambda i=h_id: self.hakedis_sil(i)).grid(row=0, column=6, padx=5, pady=5)

    def hakedis_sil(self, h_id):
        if messagebox.askyesno("Onay", "Emin misiniz?"):
            try:
                supabase.table("hakedisler").delete().eq("id", h_id).execute()
                self.gecmis_hakedisleri_getir()
            except Exception as e:
                messagebox.showerror("Hata", f"Silinemedi: {e}")

    # ================= RESTORANLAR =================
    def setup_restoran_frame(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid_rowconfigure(2, weight=1); frame.grid_columnconfigure(0, weight=1)
        self.frames["restoran"] = frame

        ctk.CTkLabel(frame, text="Restoran Bakiye & İşlem Yönetimi", font=ctk.CTkFont(size=32, weight="bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))

        ust_res_frame = ctk.CTkFrame(frame, corner_radius=10, fg_color="#212121")
        ust_res_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15), padx=5)
        ust_res_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.res_sec = ctk.CTkOptionMenu(ust_res_frame, values=self.restoran_listesini_getir(), height=38)
        self.res_sec.grid(row=0, column=0, padx=8, pady=12, sticky="ew")

        self.res_tutar_gir = ctk.CTkEntry(ust_res_frame, placeholder_text="Tutar (Örn: 500,50)", height=38)
        self.res_tutar_gir.grid(row=0, column=1, padx=8, pady=12, sticky="ew")

        self.res_yon_sec = ctk.CTkSegmentedButton(ust_res_frame, values=["Teslim Edeceğimiz Tutar (- Bakiye)", "Bize Ödemeniz Gereken (+ Bakiye)", "Devreden / Geçmiş Borç Kaydı"], height=38)
        self.res_yon_sec.grid(row=0, column=2, padx=8, pady=12, sticky="ew")
        self.res_yon_sec.set("Teslim Edeceğimiz Tutar (- Bakiye)")

        ctk.CTkButton(ust_res_frame, text="💾 Kaydet", fg_color="#2ecc71", height=38, command=self.restoran_islem_kaydet).grid(row=0, column=3, padx=8, pady=12)

        alt_res_kapsayici = ctk.CTkFrame(frame, fg_color="transparent")
        alt_res_kapsayici.grid(row=2, column=0, sticky="nsew", padx=5)
        alt_res_kapsayici.grid_rowconfigure(2, weight=1); alt_res_kapsayici.grid_columnconfigure(0, weight=1)

        res_filtre_kutu = ctk.CTkFrame(alt_res_kapsayici, corner_radius=10)
        res_filtre_kutu.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        self.res_filtre_restoran_sec = ctk.CTkOptionMenu(res_filtre_kutu, values=["Tüm Restoranlar"] + self.restoran_listesini_getir(), width=160)
        self.res_filtre_restoran_sec.pack(side="left", padx=15, pady=10)
        ctk.CTkButton(res_filtre_kutu, text="📄 PDF OCR (Fatura Okut)", fg_color="#8e44ad", command=self.restoran_pdf_yukle).pack(side="left", padx=15, pady=10)
        
        self.res_gorunum_secme = ctk.CTkSegmentedButton(alt_res_kapsayici, values=["💰 Restoran Borçları (Net Durum)", "📋 Tüm İşlem Geçmişi"], command=lambda e: self.restoran_bakiyeleri_guncelle())
        self.res_gorunum_secme.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.res_gorunum_secme.set("💰 Restoran Borçları (Net Durum)")

        self.res_liste_scroll = ctk.CTkScrollableFrame(alt_res_kapsayici)
        self.res_liste_scroll.grid(row=2, column=0, sticky="nsew")

    def restoran_islem_kaydet(self):
        res, yon = self.res_sec.get(), self.res_yon_sec.get()
        tutar = temiz_float(self.res_tutar_gir.get())
        
        if res == "Önce Restoran Ekleyin!" or tutar == 0.0: return messagebox.showwarning("Eksik", "Geçerli restoran ve tutar girin!")

        if "Teslim Edeceğimiz Tutar" in yon or ("Devreden" in yon and tutar > 0): 
            tutar = tutar * -1 if "Teslim" in yon else tutar
            
        aciklama = "Devreden / Geçmiş Borç Kaydı (Manuel)" if "Devreden" in yon else f"Manuel İşlem ({yon})"
        
        try:
            supabase.table("restoran_islem").insert({
                "restoran_ad": res,
                "tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "tutar": tutar,
                "aciklama": aciklama
            }).execute()
            self.res_tutar_gir.delete(0, 'end')
            self.restoran_bakiyeleri_guncelle(); self.dashboard_kartlari_guncelle()
        except Exception as e:
            messagebox.showerror("Hata", f"Restoran işlemi kaydedilemedi: {e}")

    def restoran_bakiyeleri_guncelle(self):
        for widget in self.res_liste_scroll.winfo_children(): widget.destroy()
        secim, filtre = self.res_gorunum_secme.get(), self.res_filtre_restoran_sec.get()

        try:
            res_query = supabase.table("restoran_islem").select("*")
            if filtre != "Tüm Restoranlar":
                res_query = res_query.eq("restoran_ad", filtre)
            islemler = res_query.execute().data or []
        except:
            islemler = []

        if "Net Durum" in secim:
            w_list = [280, 150, 150, 150, 130]
            self.create_table_header(self.res_liste_scroll, ["Restoran", "Son İşlem", "Devreden Borç", "Güncel Net Bakiye", "Durum"], w_list)
            
            restoranlar_dict = {}
            for row in islemler:
                ad = row["restoran_ad"]
                tutar = row["tutar"]
                tarih = row["tarih"]
                aciklama = row["aciklama"]
                
                if ad not in restoranlar_dict:
                    restoranlar_dict[ad] = {"net": 0.0, "son_islem": tarih, "devreden": 0.0}
                
                restoranlar_dict[ad]["net"] += tutar
                if tarih > restoranlar_dict[ad]["son_islem"]:
                    restoranlar_dict[ad]["son_islem"] = tarih
                if "Devreden" in aciklama:
                    restoranlar_dict[ad]["devreden"] += tutar

            for ad, info in restoranlar_dict.items():
                net = info["net"]
                son_islem = info["son_islem"]
                devreden = info["devreden"]

                satir = ctk.CTkFrame(self.res_liste_scroll, fg_color="#2b2b2b", corner_radius=5)
                satir.pack(fill="x", padx=5, pady=3)
                for i, w in enumerate(w_list): satir.grid_columnconfigure(i, weight=0, minsize=w)
                ctk.CTkLabel(satir, text=ad, font=ctk.CTkFont(size=14, weight="bold"), width=w_list[0], anchor="center").grid(row=0, column=0, padx=5, pady=8)
                ctk.CTkLabel(satir, text=son_islem[:16] if son_islem else "-", text_color="gray", width=w_list[1], anchor="center").grid(row=0, column=1, padx=5, pady=8)
                ctk.CTkLabel(satir, text=f"{devreden or 0:,.2f} TL", text_color="#f39c12", width=w_list[2], anchor="center").grid(row=0, column=2, padx=5, pady=8)
                ctk.CTkLabel(satir, text=f"{net:,.2f} TL", font=ctk.CTkFont(size=15, weight="bold"), text_color="#2ecc71" if net >= 0 else "#e74c3c", width=w_list[3], anchor="center").grid(row=0, column=3, padx=5, pady=8)
                ctk.CTkLabel(satir, text="Alacaklıyız" if net > 0 else ("Ödeyeceğiz" if net < 0 else "Ödeştik"), width=w_list[4], anchor="center").grid(row=0, column=4, padx=5, pady=8)
        else:
            w_list = [140, 220, 220, 140, 60]
            self.create_table_header(self.res_liste_scroll, ["Tarih", "Restoran", "Açıklama", "Tutar", "İşlem"], w_list)
            
            try:
                q2 = supabase.table("restoran_islem").select("*")
                if filtre != "Tüm Restoranlar":
                    q2 = q2.eq("restoran_ad", filtre)
                islemler_detay = q2.order("id", desc=True).execute().data or []
            except:
                islemler_detay = []

            for row in islemler_detay:
                islem_id, ad, tarih, tutar, aciklama = row.get("id"), row.get("restoran_ad"), row.get("tarih"), row.get("tutar"), row.get("aciklama")
                satir = ctk.CTkFrame(self.res_liste_scroll, fg_color="#2b2b2b", corner_radius=5)
                satir.pack(fill="x", padx=5, pady=3)
                for i, w in enumerate(w_list): satir.grid_columnconfigure(i, weight=0, minsize=w)
                ctk.CTkLabel(satir, text=tarih[:16], text_color="gray", width=w_list[0], anchor="center").grid(row=0, column=0, padx=5, pady=8)
                ctk.CTkLabel(satir, text=ad, font=ctk.CTkFont(weight="bold"), width=w_list[1], anchor="center").grid(row=0, column=1, padx=5, pady=8)
                ctk.CTkLabel(satir, text=aciklama, width=w_list[2], anchor="center").grid(row=0, column=2, padx=5, pady=8)
                ctk.CTkLabel(satir, text=f"{tutar:,.2f} TL", text_color="#2ecc71" if tutar > 0 else "#e74c3c", width=w_list[3], anchor="center").grid(row=0, column=3, padx=5, pady=8)
                if self.current_role == "admin": ctk.CTkButton(satir, text="🗑️", width=40, fg_color="#c0392b", command=lambda i=islem_id: self.restoran_islem_sil(i)).grid(row=0, column=4, padx=5, pady=5)

    def restoran_islem_sil(self, i_id):
        if messagebox.askyesno("Onay", "Silinsin mi?"):
            try:
                supabase.table("restoran_islem").delete().eq("id", i_id).execute()
                self.restoran_bakiyeleri_guncelle(); self.dashboard_kartlari_guncelle()
            except Exception as e:
                messagebox.showerror("Hata", f"Silinemedi: {e}")

    # ================= KULLANICI YÖNETİMİ PANELİ =================
    def setup_kullanici_yonetimi_frame(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid_columnconfigure((0, 1), weight=1)
        self.frames["kullanici"] = frame

        if self.current_role == "admin":
            ctk.CTkLabel(frame, text="Kullanıcı & Yönetim Paneli", font=ctk.CTkFont(size=32, weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 20))
            
            sol_kapsayici = ctk.CTkFrame(frame, fg_color="transparent")
            sol_kapsayici.grid(row=1, column=0, sticky="nsew", padx=(0, 15))
            
            kendi_form = ctk.CTkFrame(sol_kapsayici, corner_radius=10)
            kendi_form.pack(fill="x", pady=(0, 15))
            ctk.CTkLabel(kendi_form, text="Kendi Bilgilerimi Güncelle", font=ctk.CTkFont(size=18, weight="bold"), text_color="#3498db").pack(pady=(15, 5), padx=20, anchor="w")
            
            self.admin_yeni_ad_gir = ctk.CTkEntry(kendi_form, placeholder_text="Yeni Kullanıcı Adı", height=40)
            self.admin_yeni_ad_gir.pack(pady=5, padx=20, fill="x")
            self.admin_yeni_ad_gir.insert(0, self.current_user)

            self.admin_yeni_sifre_gir = ctk.CTkEntry(kendi_form, placeholder_text="Yeni Şifreniz", show="*", height=40)
            self.admin_yeni_sifre_gir.pack(pady=5, padx=20, fill="x")
            
            ctk.CTkButton(kendi_form, text="Bilgilerimi Güncelle", fg_color="#3498db", hover_color="#2980b9", height=40, command=self.admin_bilgileri_guncelle).pack(pady=(10, 15), padx=20, fill="x")

            form_frame = ctk.CTkFrame(sol_kapsayici, corner_radius=10)
            form_frame.pack(fill="x")
            ctk.CTkLabel(form_frame, text="Yeni Kullanıcı Oluştur", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(15, 5), padx=20, anchor="w")
            self.yeni_k_adi_gir = ctk.CTkEntry(form_frame, placeholder_text="Kullanıcı Adı", height=40)
            self.yeni_k_adi_gir.pack(pady=5, padx=20, fill="x")
            self.yeni_sifre_gir = ctk.CTkEntry(form_frame, placeholder_text="Şifre", show="*", height=40)
            self.yeni_sifre_gir.pack(pady=5, padx=20, fill="x")
            ctk.CTkButton(form_frame, text="Kaydet", fg_color="#2ecc71", height=40, command=self.yeni_kullanici_kaydet).pack(pady=(10, 15), padx=20, fill="x")
            
            sag_kapsayici = ctk.CTkFrame(frame, fg_color="transparent")
            sag_kapsayici.grid(row=1, column=1, sticky="nsew", padx=(10, 0))
            sag_kapsayici.grid_rowconfigure(0, weight=1)
            sag_kapsayici.grid_columnconfigure(0, weight=1)
            self.kullanici_liste_frame = ctk.CTkScrollableFrame(sag_kapsayici)
            self.kullanici_liste_frame.grid(row=0, column=0, sticky="nsew")
        else:
            ctk.CTkLabel(frame, text="Şifre İşlemleri", font=ctk.CTkFont(size=32, weight="bold")).grid(row=0, column=0, sticky="w", pady=(0, 20))
            normal_form = ctk.CTkFrame(frame, corner_radius=10, width=450)
            normal_form.grid(row=1, column=0, sticky="nw", padx=(0, 15))
            ctk.CTkLabel(normal_form, text=f"Giriş Yapılan Hesap: {self.current_user}", text_color="#3498db").pack(pady=20, padx=20, anchor="w")
            self.normal_yeni_sifre_gir = ctk.CTkEntry(normal_form, placeholder_text="Yeni Şifreniz", show="*", height=45, width=350)
            self.normal_yeni_sifre_gir.pack(pady=15, padx=20, anchor="w")
            ctk.CTkButton(normal_form, text="Şifremi Güncelle", fg_color="#2ecc71", height=45, width=350, command=self.kendi_sifremi_guncelle).pack(pady=20, padx=20, anchor="w")

    def admin_bilgileri_guncelle(self):
        yeni_ad = self.admin_yeni_ad_gir.get().strip()
        yeni_sifre = self.admin_yeni_sifre_gir.get().strip()
        
        if not yeni_ad or not yeni_sifre: return messagebox.showwarning("Uyarı", "Kullanıcı adı ve şifre boş olamaz!")
        
        try:
            supabase.table("kullanicilar").update({"kullanici_adi": yeni_ad, "sifre": yeni_sifre}).eq("kullanici_adi", self.current_user).execute()
            self.current_user = yeni_ad
            self.title(f"Hızır Pro - Tekirdağ Muhasebe (Kullanıcı: {self.current_user})")
            
            try:
                with open(CONFIG_DOSYASI, "w", encoding="utf-8") as f:
                    f.write(self.current_user)
            except: pass
            
            self.admin_yeni_sifre_gir.delete(0, 'end')
            messagebox.showinfo("Başarılı", f"Bilgileriniz güncellendi! Yeni adınız: {yeni_ad}")
        except Exception as e:
            messagebox.showerror("Hata", f"Güncellenemedi: {e}")

    def kendi_sifremi_guncelle(self):
        yeni_sifre = self.normal_yeni_sifre_gir.get().strip()
        if not yeni_sifre: return messagebox.showwarning("Uyarı", "Yeni şifre girin!")
        try:
            supabase.table("kullanicilar").update({"sifre": yeni_sifre}).eq("kullanici_adi", self.current_user).execute()
            self.normal_yeni_sifre_gir.delete(0, 'end')
            messagebox.showinfo("Başarılı", "Şifreniz güncellendi!")
        except Exception as e:
            messagebox.showerror("Hata", f"Güncellenemedi: {e}")

    def yeni_kullanici_kaydet(self):
        k_adi, sifre = self.yeni_k_adi_gir.get().strip(), self.yeni_sifre_gir.get().strip()
        if not k_adi or not sifre: return messagebox.showwarning("Uyarı", "Eksik bilgi!")
        try:
            supabase.table("kullanicilar").insert({"kullanici_adi": k_adi, "sifre": sifre, "rol": "kullanici"}).execute()
            self.yeni_k_adi_gir.delete(0, 'end'); self.yeni_sifre_gir.delete(0, 'end')
            self.kullanici_listesini_guncelle()
            messagebox.showinfo("Başarılı", "Yeni kullanıcı oluşturuldu.")
        except Exception as e: 
            messagebox.showerror("Hata", f"Kullanıcı kayıtlı veya hata oluştu:\n{e}")

    def kullanici_listesini_guncelle(self):
        for widget in self.kullanici_liste_frame.winfo_children(): widget.destroy()
        w_list = [200, 160]
        self.create_table_header(self.kullanici_liste_frame, ["Kullanıcı Adı", "İşlemler"], w_list)
        try:
            res = supabase.table("kullanicilar").select("id, kullanici_adi, rol").order("id").execute()
            kullanicilar = res.data if res.data else []
        except:
            kullanicilar = []

        for k in kullanicilar:
            k_id, k_adi, rol = k.get("id"), k.get("kullanici_adi"), k.get("rol")
            satir = ctk.CTkFrame(self.kullanici_liste_frame, fg_color="#2b2b2b", corner_radius=5)
            satir.pack(fill="x", padx=5, pady=3)
            for i, w in enumerate(w_list): satir.grid_columnconfigure(i, weight=0, minsize=w)
            
            ctk.CTkLabel(satir, text=f"{k_adi} {'(Admin)' if rol=='admin' else ''}", font=ctk.CTkFont(weight="bold"), text_color="#f1c40f" if rol=="admin" else "white", width=w_list[0], anchor="center").grid(row=0, column=0, padx=5, pady=8)
            
            btn_frame = ctk.CTkFrame(satir, fg_color="transparent")
            btn_frame.grid(row=0, column=1, padx=5, pady=5)
            ctk.CTkButton(btn_frame, text="🔑 Şifre", width=70, height=30, fg_color="#2980b9", command=lambda i=k_id, ad=k_adi: self.sifre_degistir_popup(i, ad)).pack(side="left", padx=5)
            
            if rol != "admin": 
                ctk.CTkButton(btn_frame, text="🗑️ Sil", width=60, height=30, fg_color="#c0392b", command=lambda i=k_id: self.kullanici_sil(i)).pack(side="left", padx=5)

    def sifre_degistir_popup(self, k_id, k_adi):
        pencere = ctk.CTkToplevel(self)
        pencere.title(f"Şifre Değiştir: {k_adi}")
        pencere.geometry("350x220")
        pencere.attributes("-topmost", True)
        ctk.CTkLabel(pencere, text=f"'{k_adi}' için yeni şifre:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20, 10))
        yeni_sifre_gir = ctk.CTkEntry(pencere, width=270, show="*", height=40, placeholder_text="Yeni Şifre")
        yeni_sifre_gir.pack(pady=10)
        
        def sifreyi_kaydet():
            yeni_sifre = yeni_sifre_gir.get().strip()
            if not yeni_sifre: return messagebox.showwarning("Uyarı", "Şifre boş olamaz!")
            try:
                supabase.table("kullanicilar").update({"sifre": yeni_sifre}).eq("id", k_id).execute()
                messagebox.showinfo("Başarılı", f"'{k_adi}' şifresi güncellendi.")
                pencere.destroy()
            except Exception as e:
                messagebox.showerror("Hata", f"Şifre güncellenemedi: {e}")
            
        ctk.CTkButton(pencere, text="Güncellemeyi Kaydet", fg_color="#2ecc71", height=40, command=sifreyi_kaydet).pack(pady=15)

    def kullanici_sil(self, k_id):
        try:
            supabase.table("kullanicilar").delete().eq("id", k_id).execute()
            self.kullanici_listesini_guncelle()
        except Exception as e:
            messagebox.showerror("Hata", f"Kullanıcı silinemedi: {e}")

if __name__ == "__main__":
    while True:
        giris_app = GirisPenceresi()
        giris_app.mainloop()

        if not getattr(giris_app, 'basarili_giris', False): break
        aktif_kullanici = giris_app.kullanici_adi
        aktif_rol = giris_app.kullanici_rol
        del giris_app  

        ana_app = HizirPaketPro(aktif_kullanici, aktif_rol)
        ana_app.mainloop()

        if not getattr(ana_app, 'cikis_yapildi', False): break
        del ana_app