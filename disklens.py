import os
import sys
import string
import threading
import shutil
import ctypes
import tkinter as tk
from tkinter import ttk, messagebox, font

# ─── Color Palette ─────────────────────────────────────────────────────────────
BG_APP           = "#f5f4f0"   # App background — warm milk
BG_SIDEBAR       = "#edecea"   # Sidebar background
BG_SURFACE       = "#faf9f7"   # Treeview / input background
BG_ITEM_HOVER    = "#e2e0db"   # Row hover background
BTN_PRIMARY      = "#5b7fe8"   # Primary (scan) button
BTN_PRIMARY_PRESSED = "#3f62cc"  # Primary button pressed
BTN_DELETE       = "#e05260"   # Delete button
BTN_DELETE_PRESSED  = "#b03a46"  # Delete button pressed
TEXT_MAIN        = "#1e1e2e"   # Main text — near black
TEXT_MUTED       = "#6b6b80"   # Secondary / dimmed text
COLOR_BORDER     = "#d8d5cf"   # Subtle borders
COLOR_SUCCESS    = "#2e8b57"   # Scan complete indicator

def get_drive_label(drive):
    volume_name_buf = ctypes.create_unicode_buffer(1024)
    try:
        res = ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(drive), volume_name_buf,
            ctypes.sizeof(volume_name_buf), None, None, None, None, 0
        )
        if res and volume_name_buf.value:
            return f"{drive}  {volume_name_buf.value}"
    except Exception:
        pass
    return drive

class DiskScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DiskLens — Drive Analyzer")
        self.root.geometry("960x680")
        self.root.minsize(760, 540)
        self.root.configure(bg=BG_APP)

        self.is_scanning    = False
        self.total_size_bytes = 0
        self.items_scanned  = 0
        self.dir_sizes      = {}
        self.target_drive   = "C:\\"

        self._setup_styles()
        self._build_ui()

    # ─── Styles ────────────────────────────────────────────────────────────────
    def _setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Global
        self.style.configure(".", background=BG_APP, foreground=TEXT_MAIN,
                             font=("Segoe UI", 10))

        # Frames
        self.style.configure("Card.TFrame", background=BG_SIDEBAR)
        self.style.configure("Surface.TFrame", background=BG_SURFACE)

        # Labels
        self.style.configure("Title.TLabel", background=BG_APP,
                             foreground=TEXT_MAIN, font=("Segoe UI", 22, "bold"))
        self.style.configure("Sub.TLabel",   background=BG_APP,
                             foreground=TEXT_MUTED, font=("Segoe UI", 10))
        self.style.configure("Card.TLabel",  background=BG_SIDEBAR,
                             foreground=TEXT_MAIN, font=("Segoe UI", 10))
        self.style.configure("CardTitle.TLabel", background=BG_SIDEBAR,
                             foreground=TEXT_MUTED, font=("Segoe UI", 9))
        self.style.configure("CardValue.TLabel", background=BG_SIDEBAR,
                             foreground=TEXT_MAIN, font=("Segoe UI", 18, "bold"))
        self.style.configure("Status.TLabel", background=BG_APP,
                             foreground=TEXT_MUTED, font=("Segoe UI", 9))

        # Combobox
        self.style.configure("TCombobox",
                             fieldbackground=BG_SURFACE, background=BG_SURFACE,
                             foreground=TEXT_MAIN, arrowcolor=BTN_PRIMARY,
                             selectbackground=BTN_PRIMARY, selectforeground=TEXT_MAIN)
        self.style.map("TCombobox",
                       fieldbackground=[("readonly", BG_SURFACE)],
                       foreground=[("readonly", TEXT_MAIN)])

        # Progress bar
        self.style.configure("Accent.Horizontal.TProgressbar",
                             troughcolor=BG_SURFACE, background=BTN_PRIMARY,
                             thickness=6, borderwidth=0)

        # Treeview
        self.style.configure("Treeview",
                             background=BG_SURFACE, foreground=TEXT_MAIN,
                             fieldbackground=BG_SURFACE, borderwidth=0,
                             rowheight=30, font=("Segoe UI", 10))
        self.style.configure("Treeview.Heading",
                             background=BG_SIDEBAR, foreground=TEXT_MUTED,
                             font=("Segoe UI", 9, "bold"), borderwidth=0,
                             relief="flat")
        self.style.map("Treeview",
                       background=[("selected", BTN_PRIMARY)],
                       foreground=[("selected", TEXT_MAIN)])

        # Scrollbar
        self.style.configure("Vertical.TScrollbar",
                             troughcolor=BG_SURFACE, background=BG_ITEM_HOVER,
                             borderwidth=0, arrowsize=0)

    # ─── UI Build ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Sidebar ────────────────────────────────────────────────────────────
        sidebar = tk.Frame(self.root, bg=BG_SIDEBAR, width=240)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        # Logo / title
        tk.Label(sidebar, text="💿", bg=BG_SIDEBAR, fg=BTN_PRIMARY,
                 font=("Segoe UI", 28)).pack(pady=(36, 4))
        tk.Label(sidebar, text="DiskLens", bg=BG_SIDEBAR, fg=TEXT_MAIN,
                 font=("Segoe UI", 16, "bold")).pack()
        tk.Label(sidebar, text="Drive Analyzer", bg=BG_SIDEBAR, fg=TEXT_MUTED,
                 font=("Segoe UI", 9)).pack(pady=(0, 30))

        # Separator
        tk.Frame(sidebar, bg=COLOR_BORDER, height=1).pack(fill=tk.X, padx=20, pady=(0, 24))

        # Drive selection
        tk.Label(sidebar, text="SELECT DRIVE", bg=BG_SIDEBAR, fg=TEXT_MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor=tk.W, padx=20)

        drives_raw = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
        self.drive_labels = [get_drive_label(d) for d in drives_raw]
        self.drive_paths   = drives_raw

        default_idx = 0
        for i, d in enumerate(drives_raw):
            if d.startswith("C:\\"):
                default_idx = i
                break

        self.drive_var = tk.StringVar(value=self.drive_labels[default_idx] if self.drive_labels else "")
        self.drive_dropdown = ttk.Combobox(sidebar, textvariable=self.drive_var,
                                           values=self.drive_labels, state="readonly",
                                           font=("Segoe UI", 10))
        self.drive_dropdown.pack(fill=tk.X, padx=20, pady=(6, 24))

        # Separator
        tk.Frame(sidebar, bg=COLOR_BORDER, height=1).pack(fill=tk.X, padx=20, pady=(0, 24))

        # Stat cards in sidebar
        self._lbl_items_val = self._make_stat_card(sidebar, "FILES SCANNED", "—")
        self._lbl_found_val = self._make_stat_card(sidebar, "TOTAL FOUND",   "—")

        # Spacer
        tk.Frame(sidebar, bg=BG_SIDEBAR).pack(fill=tk.BOTH, expand=True)

        # Scan button
        self.btn_scan = tk.Button(
            sidebar, text="▶  Start Scan", command=self.start_scan,
            bg=BTN_PRIMARY, fg="white", font=("Segoe UI", 11, "bold"),
            relief=tk.FLAT, cursor="hand2", padx=0, pady=12,
            activebackground=BTN_PRIMARY_PRESSED, activeforeground="white", bd=0
        )
        self.btn_scan.pack(fill=tk.X, padx=20, pady=(0, 12))

        # Delete button
        self.btn_delete = tk.Button(
            sidebar, text="🗑  Delete Selected", command=self.delete_selected,
            bg=BTN_DELETE, fg="white", font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT, cursor="hand2", padx=0, pady=10,
            activebackground=BTN_DELETE_PRESSED, activeforeground="white", bd=0
        )
        self.btn_delete.pack(fill=tk.X, padx=20, pady=(0, 24))

        # ── Main content ───────────────────────────────────────────────────────
        content = tk.Frame(self.root, bg=BG_APP)
        content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Top bar
        topbar = tk.Frame(content, bg=BG_APP, height=64)
        topbar.pack(fill=tk.X, padx=24, pady=(20, 0))
        topbar.pack_propagate(False)

        tk.Label(topbar, text="Drive Analysis", bg=BG_APP,
                 fg=TEXT_MAIN, font=("Segoe UI", 18, "bold")).pack(side=tk.LEFT, anchor=tk.W)

        self.lbl_status = tk.Label(topbar, text="Ready to scan…",
                                   bg=BG_APP, fg=TEXT_MUTED,
                                   font=("Segoe UI", 9))
        self.lbl_status.pack(side=tk.RIGHT, anchor=tk.E)

        # Progress bar
        prog_frame = tk.Frame(content, bg=BG_APP)
        prog_frame.pack(fill=tk.X, padx=24, pady=(8, 4))

        self.progress = ttk.Progressbar(prog_frame, style="Accent.Horizontal.TProgressbar",
                                        mode='determinate')
        self.progress.pack(fill=tk.X)

        # Tree container
        tree_frame = tk.Frame(content, bg=BG_SURFACE, bd=0,
                              highlightthickness=1, highlightbackground=COLOR_BORDER)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=(8, 20))

        columns = ('size',)
        self.tree = ttk.Treeview(tree_frame, columns=columns,
                                 show='tree headings', selectmode='extended')
        self.tree.heading('#0',   text='  File / Folder', anchor=tk.W)
        self.tree.heading('size', text='Size', anchor=tk.E)
        self.tree.column('#0',   minwidth=200, stretch=True)
        self.tree.column('size', width=110, anchor=tk.E, stretch=False)

        self.tree.tag_configure('folder', foreground=TEXT_MAIN)
        self.tree.tag_configure('file',   foreground=TEXT_MAIN)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                                  command=self.tree.yview, style="Vertical.TScrollbar")
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tree.bind('<<TreeviewOpen>>', self.on_tree_expand)
        self.tree.bind('<Button-1>', self.on_tree_click)

        self.last_clicked_item = None

    def _make_stat_card(self, parent, title, initial):
        card = tk.Frame(parent, bg=BG_SIDEBAR)
        card.pack(fill=tk.X, padx=20, pady=(0, 14))
        tk.Label(card, text=title, bg=BG_SIDEBAR, fg=TEXT_MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor=tk.W)
        val_lbl = tk.Label(card, text=initial, bg=BG_SIDEBAR, fg=TEXT_MAIN,
                           font=("Segoe UI", 18, "bold"))
        val_lbl.pack(anchor=tk.W, pady=(2, 0))
        return val_lbl

    # ─── Logic ─────────────────────────────────────────────────────────────────
    def format_size(self, size_bytes):
        if size_bytes >= 1024**3:
            return f"{size_bytes / (1024**3):.2f} GB"
        if size_bytes >= 1024**2:
            return f"{size_bytes / (1024**2):.2f} MB"
        if size_bytes >= 1024:
            return f"{size_bytes / 1024:.2f} KB"
        return f"{size_bytes} B"

    def delete_selected(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("No Selection", "Please select one or more files/folders first.\n\nTip: Hold Ctrl or Shift to select multiple items.")
            return

        # Build list of valid paths
        paths = [iid for iid in selected_items if os.path.exists(iid)]
        if not paths:
            messagebox.showerror("Error", "None of the selected paths exist on disk.")
            return

        count = len(paths)
        if count == 1:
            path = paths[0]
            item_type = "folder" if os.path.isdir(path) else "file"
            msg = (f"You are about to PERMANENTLY delete this {item_type}:\n\n"
                   f"  {path}\n\n"
                   f"This action CANNOT be undone. Continue?")
        else:
            preview = "\n".join(f"  • {p}" for p in paths[:8])
            if count > 8:
                preview += f"\n  … and {count - 8} more"
            msg = (f"You are about to PERMANENTLY delete {count} items:\n\n"
                   f"{preview}\n\n"
                   f"This action CANNOT be undone. Continue?")

        confirm = messagebox.askyesno(
            f"⚠ Confirm Deletion of {count} item(s)",
            msg, icon='warning'
        )
        if not confirm:
            return

        failed = []
        deleted_iids = []
        for path in paths:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                deleted_iids.append(path)
            except Exception as e:
                failed.append(f"{path}\n    → {e}")

        for iid in deleted_iids:
            if self.tree.exists(iid):
                self.tree.delete(iid)

        if failed:
            messagebox.showwarning(
                "Partial Deletion",
                f"{len(deleted_iids)} item(s) deleted.\n\nFailed to delete {len(failed)}:\n" + "\n".join(failed)
            )
        else:
            messagebox.showinfo("Deleted", f"{len(deleted_iids)} item(s) deleted successfully.")

    def start_scan(self):
        if self.is_scanning:
            return
        sel = self.drive_var.get()
        # Match back to the raw path
        try:
            idx = self.drive_labels.index(sel)
            self.target_drive = self.drive_paths[idx]
        except ValueError:
            self.target_drive = sel.split(" ")[0]

        self.is_scanning = True
        self.btn_scan.config(text="⏳  Scanning...", bg=BTN_PRIMARY_PRESSED, state=tk.NORMAL)
        self.drive_dropdown.config(state=tk.DISABLED)
        self.tree.delete(*self.tree.get_children())
        self.total_size_bytes = 0
        self.items_scanned    = 0
        self.dir_sizes        = {}
        self.lbl_status.config(text="Initialising scan…", fg=TEXT_MUTED)
        self._lbl_items_val.config(text="—")
        self._lbl_found_val.config(text="—")
        threading.Thread(target=self.scan_drive, daemon=True).start()

    def get_folder_size(self, path):
        total_size = 0
        try:
            with os.scandir(path) as it:
                for entry in it:
                    self.items_scanned += 1
                    try:
                        if entry.is_file(follow_symlinks=False):
                            total_size += entry.stat(follow_symlinks=False).st_size
                        elif entry.is_dir(follow_symlinks=False):
                            total_size += self.get_folder_size(entry.path)
                    except (PermissionError, FileNotFoundError):
                        continue
        except (PermissionError, FileNotFoundError):
            pass
        self.dir_sizes[path] = total_size
        if self.items_scanned % 5000 == 0:
            self.root.after(0, self.update_stats_only)
        return total_size

    def update_stats_only(self):
        gb = self.total_size_bytes / (1024**3)
        self._lbl_items_val.config(text=f"{self.items_scanned:,}")
        self._lbl_found_val.config(text=f"{gb:.2f} GB")

    def scan_drive(self):
        try:
            entries = list(os.scandir(self.target_drive))
            self.root.after(0, lambda: self.progress.configure(maximum=max(len(entries), 1), value=0))
            for i, entry in enumerate(entries):
                label = f"Scanning  {entry.path}"
                self.root.after(0, self.update_status, label, i)
                try:
                    if entry.is_dir(follow_symlinks=False):
                        size = self.get_folder_size(entry.path)
                        self.total_size_bytes += size
                    elif entry.is_file(follow_symlinks=False):
                        size = entry.stat(follow_symlinks=False).st_size
                        self.total_size_bytes += size
                except (PermissionError, FileNotFoundError):
                    pass
        except PermissionError:
            self.root.after(0, lambda: messagebox.showwarning(
                "Permission Error", "Run as Administrator to scan all folders."))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        self.root.after(0, self.finish_scan)

    def update_status(self, text, progress_value):
        short = text if len(text) < 80 else "…" + text[-77:]
        self.lbl_status.config(text=short)
        self.update_stats_only()
        self.progress['value'] = progress_value

    def finish_scan(self):
        self.progress['value'] = self.progress['maximum']
        self.lbl_status.config(text="Building tree…", fg=TEXT_MUTED)
        self.update_stats_only()
        self.populate_tree_node('', self.target_drive)
        self.lbl_status.config(text="✔  Scan complete", fg=COLOR_SUCCESS)
        self.is_scanning = False
        self.btn_scan.config(text="▶  Start Scan", state=tk.NORMAL, bg=BTN_PRIMARY)
        self.drive_dropdown.config(state="readonly")

    def populate_tree_node(self, parent_id, path):
        try:
            dirs, files = [], []
            with os.scandir(path) as it:
                for entry in it:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            dirs.append((entry.name, entry.path,
                                         self.dir_sizes.get(entry.path, 0)))
                        elif entry.is_file(follow_symlinks=False):
                            files.append((entry.name, entry.path,
                                          entry.stat(follow_symlinks=False).st_size))
                    except (PermissionError, FileNotFoundError):
                        continue
            dirs.sort( key=lambda x: x[2], reverse=True)
            files.sort(key=lambda x: x[2], reverse=True)

            for name, e_path, size in dirs:
                if not self.tree.exists(e_path):
                    self.tree.insert(parent_id, tk.END, iid=e_path,
                                     text=f"  📁  {name}",
                                     values=(self.format_size(size),),
                                     tags=('folder',))
                    self.tree.insert(e_path, tk.END, iid=e_path + "|dummy", text="…")

            for name, e_path, size in files:
                if not self.tree.exists(e_path):
                    self.tree.insert(parent_id, tk.END, iid=e_path,
                                     text=f"  📄  {name}",
                                     values=(self.format_size(size),),
                                     tags=('file',))
        except (PermissionError, FileNotFoundError):
            pass

    def on_tree_click(self, event):
        item = self.tree.identify('item', event.x, event.y)
        if item:
            self.last_clicked_item = item

    def on_tree_expand(self, event):
        item = self.tree.focus() or self.last_clicked_item
        if not item:
            return
        children = self.tree.get_children(item)
        if len(children) == 1 and children[0].endswith("|dummy"):
            self.tree.delete(children[0])
            self.populate_tree_node(item, item)


if __name__ == "__main__":
    def is_admin():
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    if not is_admin():
        script = os.path.abspath(__file__)
        params = ' '.join([script] + sys.argv[1:])
        executable = sys.executable
        if executable.lower().endswith("python.exe"):
            executable = executable[:-10] + "pythonw.exe"
        ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, params, None, 1)
        sys.exit()

    root = tk.Tk()
    app  = DiskScannerApp(root)
    root.mainloop()
