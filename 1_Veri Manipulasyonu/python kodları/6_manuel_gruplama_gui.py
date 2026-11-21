import os
import sys
import pandas as pd
import tkinter as tk
from tkinter import messagebox, simpledialog
from ttkbootstrap import Style
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import copy
import re
import json
import time

# --- AYARLAR ---
BASE_PATH = os.path.join(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")), "1_Veri Manipulasyonu")

import sys
CURRENCY = ""
if len(sys.argv) > 1:
    for arg in sys.argv:
        if arg.upper() in ["USD", "EUR", "TRY"]:
            CURRENCY = arg.upper()
            break

DATA_PATH = os.path.join(BASE_PATH, "0_Datasetler", f"Veri_Havuzu_{CURRENCY}.xlsx" if CURRENCY else "Veri_Havuzu_USD.xlsx")

if not CURRENCY:
    if "USD" in DATA_PATH: CURRENCY = "USD"
    elif "EUR" in DATA_PATH: CURRENCY = "EUR"
    elif "TRY" in DATA_PATH: CURRENCY = "TRY"

OUT_DIR = os.path.join(BASE_PATH, r"raporlar\6_Manuel_Gruplama")
CACHE_DIR = os.path.join(OUT_DIR, f".cache_{CURRENCY}" if CURRENCY else ".cache")
IGNORE_COLS = {'Dönem', 'Firma Adı', 'Year', 'Month', 'Dnem', 'Firma Ad', 'Sektör'}

class ManualGroupingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Tez - Global Özellik Konsolidasyonu (BULK & SMART NLP & BLAZING FAST)")
        self.root.geometry("1600x950")
        
        # Tema ve Stil
        self.style = Style(theme="cyborg")
        
        # Treeview Stilini Kökten Düzenle
        self.style.configure("Treeview", font=("Segoe UI", 11), rowheight=80)
        self.style.configure("INFO.Treeview", font=("Segoe UI", 11), rowheight=80)
        self.style.configure("Treeview.Heading", font=("Segoe UI", 12, "bold"))
        
        # Renk ve Background Sabitle
        self.style.map("INFO.Treeview", 
            background=[('selected', '#343a40')],
            foreground=[('selected', '#ffffff')]
        )
        self.style.configure("Treeview.Heading", font=("Segoe UI", 13, "bold"))
        
        # Veri Saklama
        self.full_df = None            
        self.all_features = []         
        self.fill_rates = {}           
        self.mappings = {}             
        self.history = []              
        
        # DnD State
        self.dragging_source = None
        self.dragging_names = []
        self.dragging_old_parent = None
        self.drag_label = None
        self.drag_start_pos = (0, 0)
        
        # UI Dinamik Başlıklar
        self.left_header_var = tk.StringVar(value="Global Havuz")
        self.right_header_var = tk.StringVar(value="Global Grup Analizi")
        
        self.initialize_ui()
        self.root.after(100, self.load_global_data)
        
        # Kısayollar
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Delete>", lambda e: self.delete_selected_group() or self.remove_from_group())

    def push_history(self):
        self.history.append(copy.deepcopy(self.mappings))
        if len(self.history) > 100: self.history.pop(0)

    def undo(self):
        if not self.history: return
        self.mappings = self.history.pop()
        self.refresh_feature_list(); self.refresh_group_tree()
        self.status_label.config(text="Geri Alındı (Ctrl+Z)")

    def initialize_ui(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Kaydet", command=self.save_mapping)
        file_menu.add_command(label="Geri Al", command=self.undo)
        menubar.add_cascade(label="Dosya", menu=file_menu)
        self.root.config(menu=menubar)

        header = ttk.Frame(self.root, bootstyle=SECONDARY)
        header.pack(fill=X, padx=10, pady=5)
        ttk.Label(header, text="🛡️ Global Analitik Gruplama - Smart NLP (Cached)", font=("Helvetica", 16, "bold"), bootstyle=INVERSE).pack(side=LEFT, padx=15, pady=10)
        self.status_label = ttk.Label(header, text="Sistem Hazırlanıyor...", font=("Segoe UI", 10), bootstyle=INVERSE)
        self.status_label.pack(side=RIGHT, padx=20)
        
        main_paned = ttk.Panedwindow(self.root, orient=HORIZONTAL)
        main_paned.pack(fill=BOTH, expand=True, padx=10, pady=5)

        # Sol Panel
        self.left_panel = ttk.Frame(main_paned, width=600, padding=10)
        main_paned.add(self.left_panel, weight=1)
        ttk.Label(self.left_panel, textvariable=self.left_header_var, font=("Segoe UI", 13, "bold")).pack(pady=5)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_features)
        ttk.Entry(self.left_panel, textvariable=self.search_var, font=("Segoe UI", 12)).pack(fill=X, pady=5)
        self.feature_listbox = tk.Listbox(self.left_panel, bg="#1a1d20", fg="#5bc0de", font=("Segoe UI", 12), 
                                         selectbackground="#343a40", selectmode=EXTENDED, exportselection=False)
        self.feature_listbox.pack(fill=BOTH, expand=True)
        self.feature_listbox.bind("<ButtonPress-1>", self.start_drag_list)
        self.feature_listbox.bind("<B1-Motion>", self.do_drag)
        self.feature_listbox.bind("<ButtonRelease-1>", self.stop_drag)

        # Sağ Panel
        self.right_panel = ttk.Frame(main_paned, width=1000, padding=10)
        main_paned.add(self.right_panel, weight=2)
        top_row = ttk.Frame(self.right_panel)
        top_row.pack(fill=X, pady=10)
        ttk.Label(top_row, textvariable=self.right_header_var, font=("Segoe UI", 14, "bold")).pack(side=LEFT)
        btn_box = ttk.Frame(top_row); btn_box.pack(side=RIGHT)
        ttk.Button(btn_box, text="🤖 NLP OTOMATİK GRUPLA", command=self.run_nlp_auto_grouping, bootstyle=SUCCESS).pack(side=LEFT, padx=5)
        ttk.Button(btn_box, text="+ Yeni Grup", command=self.add_new_group, bootstyle="info").pack(side=LEFT)

        columns = ("Action", "Count", "Collision", "TotalFill")
        self.group_tree = ttk.Treeview(self.right_panel, columns=columns, show='tree headings', bootstyle=INFO)
        self.group_tree.heading("#0", text="Grup / Özellik", anchor=W)
        self.group_tree.heading("Action", text="Sil", anchor=CENTER); self.group_tree.heading("Count", text="Üye", anchor=CENTER)
        self.group_tree.heading("Collision", text="Çakışma", anchor=CENTER); self.group_tree.heading("TotalFill", text="Doluluk %", anchor=CENTER)
        self.group_tree.column("#0", width=650, minwidth=400); self.group_tree.column("Action", width=80, anchor=CENTER)
        self.group_tree.column("Count", width=100, anchor=CENTER); self.group_tree.column("Collision", width=180, anchor=CENTER)
        self.group_tree.column("TotalFill", width=220, anchor=CENTER); self.group_tree.pack(fill=BOTH, expand=True)
        self.group_tree.bind("<ButtonPress-1>", self.start_drag_tree); self.group_tree.bind("<B1-Motion>", self.do_drag)
        self.group_tree.bind("<ButtonRelease-1>", self.stop_drag); self.group_tree.bind("<Double-1>", self.on_tree_double_click)

        footer = ttk.Frame(self.root)
        footer.pack(fill=X, padx=10, pady=10)
        ttk.Button(footer, text="💾 TÜMÜNÜ KAYDET", command=self.save_mapping, bootstyle=SUCCESS, width=25).pack(side=RIGHT, padx=5)
        ttk.Label(footer, text="💡 Veriler önbelleğe alınmıştır. Excel değiştiğinde otomatik güncellenir.", font=("Segoe UI", 9, "italic"), bootstyle=LIGHT).pack(side=LEFT)

    # --- CACHE ENGINE ---
    def get_cache_info(self):
        meta_path = os.path.join(CACHE_DIR, "meta.json")
        df_path = os.path.join(CACHE_DIR, "data.pkl")
        if not (os.path.exists(meta_path) and os.path.exists(df_path)): return None
        try:
            with open(meta_path, 'r', encoding='utf-8') as f: meta = json.load(f)
            excel_mtime = os.path.getmtime(DATA_PATH)
            if meta.get("timestamp") == excel_mtime: return meta
        except: pass
        return None

    def save_cache(self):
        os.makedirs(CACHE_DIR, exist_ok=True)
        meta = {"timestamp": os.path.getmtime(DATA_PATH), "all_features": self.all_features, "fill_rates": self.fill_rates}
        with open(os.path.join(CACHE_DIR, "meta.json"), 'w', encoding='utf-8') as f: json.dump(meta, f)
        self.full_df.to_pickle(os.path.join(CACHE_DIR, "data.pkl"))

    def load_global_data(self):
        cache = self.get_cache_info()
        if cache:
            self.status_label.config(text="🚀 Önbellekten hızlı yükleniyor...")
            self.root.update_idletasks()
            self.all_features = cache["all_features"]
            self.fill_rates = cache["fill_rates"]
            self.full_df = pd.read_pickle(os.path.join(CACHE_DIR, "data.pkl"))
            self.refresh_feature_list(); self.refresh_group_tree()
            self.export_features_to_txt()
            self.status_label.config(text="Hazır (Önbellekten Yüklendi)")
            return

        # Cache yoksa veya eskiyse normal yükle
        try:
            xl = pd.ExcelFile(DATA_PATH)
            all_dfs, feats = [], set()
            for sheet in xl.sheet_names:
                df = pd.read_excel(xl, sheet_name=sheet)
                rel = [c for c in df.columns if c not in IGNORE_COLS]
                feats.update(rel); all_dfs.append(df[rel])
            self.full_df = pd.concat(all_dfs, axis=0, ignore_index=True)
            self.all_features = sorted(list(feats))
            t = len(self.full_df)
            for f in self.all_features: self.fill_rates[f] = f"{(self.full_df[f].notna().sum()/t)*100:.1f}%"
            self.save_cache()
            
            self.refresh_feature_list(); self.refresh_group_tree()
            self.export_features_to_txt()
            self.status_label.config(text="Hazır (Yeni Analiz Tamamlandı)")
        except Exception as e: messagebox.showerror("Hata", str(e))

    def export_features_to_txt(self):
        try:
            os.makedirs(OUT_DIR, exist_ok=True)
            txt_name = f"tum_ozellikler_listesi_{CURRENCY}.txt" if CURRENCY else "tum_ozellikler_listesi.txt"
            txt_path = os.path.join(OUT_DIR, txt_name)
            with open(txt_path, "w", encoding="utf-8") as f:
                # Doluluk oranı olmadan sadece isimler
                f.write("\n".join(self.all_features))
        except: pass

    # --- NLP & LOGIC ---
    def refresh_feature_list(self):
        self.feature_listbox.delete(0, tk.END)
        grouped = []
        for v in self.mappings.values(): grouped.extend(v)
        keywords = self.search_var.get().lower().split()
        count = 0
        for f in self.all_features:
            if f not in grouped and all(k in f.lower() for k in keywords):
                self.feature_listbox.insert(tk.END, f"{f} ({self.fill_rates.get(f, '0%')})")
                count += 1
        self.left_header_var.set(f"Global Pool ({count} adet)")

    def refresh_group_tree(self):
        for i in self.group_tree.get_children(): self.group_tree.delete(i)
        gt = 0
        for master, members in self.mappings.items():
            if not members:
                self.group_tree.insert("", tk.END, text=master, values=("❌", 0, 0, "0.0%"), open=True)
                continue
            sub = self.full_df[members]
            c = (sub.notna().sum(axis=1) > 1).sum()
            f = (sub.notna().sum(axis=1) > 0).mean() * 100
            parent = self.group_tree.insert("", tk.END, text=master, values=("❌", len(members), c, f"{f:.1f}%"), open=True)
            mask = (sub.notna().sum(axis=1) > 1)
            for m in members:
                mc = (mask & sub[m].notna()).sum()
                self.group_tree.insert(parent, tk.END, text=m, values=("➖", "-", f"🚨 {mc}" if mc>0 else "Temiz", f"Doluluk: {self.fill_rates.get(m)}"))
                gt += 1
        self.right_header_var.set(f"Anlık Grup Analizi ({len(self.mappings)} Grup | {gt} Özellik)")

    def calculate_stats(self, master):
        # Treeview içinde inline yapıldı
        pass

    def filter_features(self, *args): self.refresh_feature_list()
    def add_new_group(self):
        n = simpledialog.askstring("Grup", "Adı:", parent=self.root)
        if n:
            n = n.strip().upper()
            if n not in self.mappings: self.mappings[n] = []; self.refresh_group_tree()

    def run_nlp_auto_grouping(self):
        grouped = []
        for v in self.mappings.values(): grouped.extend(v)
        candidates = [f for f in self.all_features if f not in grouped]
        if not candidates: return
        self.push_history(); self.status_label.config(text="🤖 NLP Analiz Yapıyor..."); self.root.update_idletasks()
        processed, new_groups_count = set(), 0
        for i in range(len(candidates)):
            f1 = candidates[i]
            if f1 in processed: continue
            current_group = [f1]
            processed.add(f1)
            for j in range(i + 1, len(candidates)):
                f2 = candidates[j]
                if f2 in processed: continue
                # Similarity logic
                if self.is_similar(f1, f2): current_group.append(f2); processed.add(f2)
            if len(current_group) > 1:
                master = sorted(current_group, key=len)[0].upper()
                if master not in self.mappings: self.mappings[master] = []
                self.mappings[master].extend(current_group); new_groups_count += 1
        self.refresh_feature_list(); self.refresh_group_tree()
        self.status_label.config(text=f"NLP Bitti! {new_groups_count} grup.")

    def is_similar(self, s1, s2):
        ops = {'zarar', 'olmayan', 'olumsuz', 'eksi'}; t1l, t2l = s1.lower(), s2.lower()
        for o in ops: 
            if (o in t1l and o not in t2l) or (o in t2l and o not in t1l): return False
        for suf in ['-me', '-ma', 'memiş', 'mamış']:
            if (suf in t1l and suf not in t2l) or (suf in t2l and suf not in t1l): return False
        n1, n2 = set(re.sub(r'[^\w\s]', '', t1l).split()), set(re.sub(r'[^\w\s]', '', t2l).split())
        if not n1 or not n2: return False
        inter = len(n1.intersection(n2))
        return (2.0 * inter) / (len(n1) + len(n2)) >= 0.85

    # --- DnD & ACTIONS ---
    def start_drag_list(self, event):
        idx = self.feature_listbox.nearest(event.y)
        if idx in self.feature_listbox.curselection(): self.drag_start_pos = (event.x, event.y); self.dragging_source = "listbox"; return "break"
        self.drag_start_pos = (event.x, event.y); self.dragging_source = "listbox"
    def start_drag_tree(self, event):
        items = self.group_tree.selection()
        if not items: return
        self.dragging_source = "treeview"
        self.dragging_names = []
        for it in items:
            p = self.group_tree.parent(it)
            if p: # Sadece üyeler sürüklenebilir
                self.dragging_names.append(self.group_tree.item(it, "text"))
                self.dragging_old_parent = self.group_tree.item(p, "text")
        
        if not self.dragging_names: return
        txt = self.dragging_names[0] if len(self.dragging_names) == 1 else f"{len(self.dragging_names)} özellik..."
        self.create_ghost(event, txt)
    def do_drag(self, event):
        if self.dragging_source == "listbox" and not self.drag_label:
            if abs(event.x - self.drag_start_pos[0]) > 5 or abs(event.y - self.drag_start_pos[1]) > 5:
                idx = self.feature_listbox.curselection()
                if not idx: return
                self.dragging_names = [self.feature_listbox.get(i).rsplit(" (", 1)[0] for i in idx]
                self.create_ghost(event, f"{len(self.dragging_names)} özellik...")
        if self.drag_label: self.drag_label.geometry(f"+{event.x_root + 15}+{event.y_root + 15}"); return "break" if self.dragging_source=="listbox" else None
    def create_ghost(self, event, text):
        self.drag_label = tk.Toplevel(self.root); self.drag_label.overrideredirect(True); self.drag_label.attributes("-topmost", True, "-alpha", 0.8)
        tk.Label(self.drag_label, text=text, bg="#17a2b8", fg="white", padx=10, pady=5, relief="solid").pack()
    def stop_drag(self, event):
        if not self.drag_label: return
        self.drag_label.destroy(); self.drag_label = None
        target = self.root.winfo_containing(event.x_root, event.y_root)
        
        # 1. Grup Paneline Bırakıldıysa (Ekleme veya Yer Değiştirme)
        if target and (target == self.group_tree or target.master == self.group_tree):
            self.push_history()
            ly = event.y_root - self.group_tree.winfo_rooty()
            tid = self.group_tree.identify_row(ly)
            
            # Eğer Treeview'den geliyorsa, eski yerinden siliyoruz
            if self.dragging_source == "treeview" and self.dragging_old_parent:
                for name in self.dragging_names:
                    if name in self.mappings.get(self.dragging_old_parent, []):
                        self.mappings[self.dragging_old_parent].remove(name)
            
            if tid:
                # Bir grubun üstüne veya içine bırakıldı
                p = self.group_tree.parent(tid)
                master = self.group_tree.item(tid, "text") if not p else self.group_tree.item(p, "text")
                if master not in self.mappings: self.mappings[master] = []
                for n in self.dragging_names:
                    if n not in self.mappings[master]: self.mappings[master].append(n)
            else:
                # Boş alana bırakıldı -> Yeni grup yap
                master = self.dragging_names[0].upper()
                if master not in self.mappings: self.mappings[master] = []
                for n in self.dragging_names:
                    if n not in self.mappings[master]: self.mappings[master].append(n)
            
            self.refresh_feature_list(); self.refresh_group_tree()
            
        # 2. Dışarıya Bırakıldıysa (Gruptan Çıkar ve Sola Gönder)
        elif self.dragging_source == "treeview" and self.dragging_old_parent:
            self.push_history()
            for name in self.dragging_names:
                if name in self.mappings.get(self.dragging_old_parent, []):
                    self.mappings[self.dragging_old_parent].remove(name)
            self.refresh_feature_list(); self.refresh_group_tree()
            self.status_label.config(text="Özellikler havuza geri gönderildi.")
    def on_tree_double_click(self, event):
        iid = self.group_tree.identify_row(event.y); col = self.group_tree.identify_column(event.x)
        if col == "#1" and iid:
            self.push_history(); p = self.group_tree.parent(iid)
            if p: self.mappings[self.group_tree.item(p, "text")].remove(self.group_tree.item(iid, "text"))
            else: self.mappings.pop(self.group_tree.item(iid, "text"))
            self.refresh_feature_list(); self.refresh_group_tree()
    def delete_selected_group(self):
        it_tuple = self.group_tree.selection()
        if not it_tuple: return
        self.push_history()
        changed = False
        for it in it_tuple:
            name = self.group_tree.item(it, "text")
            if name in self.mappings:
                self.mappings.pop(name)
                changed = True
        if changed: self.refresh_feature_list(); self.refresh_group_tree()

    def remove_from_group(self):
        it_tuple = self.group_tree.selection()
        if not it_tuple: return
        self.push_history()
        changed = False
        for it in it_tuple:
            p = self.group_tree.parent(it)
            if p:
                master = self.group_tree.item(p, "text")
                name = self.group_tree.item(it, "text")
                if master in self.mappings and name in self.mappings[master]:
                    self.mappings[master].remove(name)
                    changed = True
        if changed: self.refresh_feature_list(); self.refresh_group_tree()
    def save_mapping(self):
        if not self.mappings: return
        os.makedirs(OUT_DIR, exist_ok=True)
        report_name = f"manuel_onay_listesi_{CURRENCY}.xlsx" if CURRENCY else "manuel_onay_listesi.xlsx"
        path = os.path.join(OUT_DIR, report_name); rows = []
        for master, members in self.mappings.items():
            if not members: continue
            subset = self.full_df[members]; c = (subset.notna().sum(axis=1) > 1).sum(); f = (subset.notna().sum(axis=1) > 0).mean() * 100
            rows.append({"Yeni Hücre Adı": master, "Birleşen Hücre Adları": "\n".join(members), "Kaç Hücre Birleşti": len(members), "Çakışma Sayısı": c, "Toplam Doluluk (%)": f"{f:.1f}%", "Kaynak": "Smart GLOBAL_CACHED"})
        pd.DataFrame(rows).to_excel(path, index=False); messagebox.showinfo("Başarılı", f"Kaydedildi: {path}")

if __name__ == "__main__":
    root = ttk.Window(); app = ManualGroupingApp(root); root.mainloop()
