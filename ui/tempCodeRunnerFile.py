import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk
import re
import os
import csv
from PIL import Image 
from datetime import datetime

# --- IMPORT ADJUSTMENT ---
from compiler.lexer import LuminaLexer 

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class TabbedEditor(ctk.CTkFrame):
    """Custom tabbed editor widget"""
    def __init__(self, master, main_app, **kwargs):
        super().__init__(master, **kwargs)
        self.main_app = main_app  
        self.current_file = None
        self.tabs = {}  
        self.tab_counter = 0   
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # --- Tab Header Area ---
        self.tab_header = ctk.CTkFrame(self, fg_color=self.main_app.colors["panel"], height=38, corner_radius=0)
        self.tab_header.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        
        self.tab_buttons_frame = ctk.CTkFrame(self.tab_header, fg_color="transparent")
        self.tab_buttons_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
        
        # Add (+) Button
        self.add_tab_btn = ctk.CTkButton(self.tab_header, text="+", width=34, height=28,
                                         command=self.main_app.add_new_file,
                                         fg_color=self.main_app.colors["accent"], text_color="#000000",
                                         hover_color="#1bcde5",
                                         corner_radius=8,
                                         font=("Segoe UI", 13, "bold"))
        self.add_tab_btn.pack(side=tk.RIGHT, padx=(0, 10), pady=5)
        
        # --- Editor Area ---
        self.editor_area = ctk.CTkFrame(self, fg_color=self.main_app.colors["editor"], corner_radius=0)
        self.editor_area.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        
        # Initialize with one empty tab
        self.create_new_tab("Untitled.lum")

    def create_new_tab(self, filename, filepath=None, content=""):
        """Create a new tab with editor widget"""
        
        self.tab_counter += 1
        tab_id = self.tab_counter
        tab_frame = ctk.CTkFrame(self.tab_buttons_frame, fg_color="transparent", width=140, height=30)
        tab_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 0))
        
        # Tab Label
        display_name = filename
        tab_label = ctk.CTkLabel(tab_frame, text=display_name, font=("Segoe UI", 11), text_color=self.main_app.colors["muted"])
        tab_label.pack(side=tk.LEFT, padx=(12, 5), pady=6)
        
        # Close Button (x)
        close_btn = ctk.CTkButton(tab_frame, text="✕", width=22, height=22,
                                 command=lambda: self.close_tab(tab_id),
                                 fg_color="transparent", hover_color="#c42b1c",
                                 text_color=self.main_app.colors["muted"],
                                 font=("Segoe UI", 10), corner_radius=6)
        close_btn.pack(side=tk.LEFT, padx=(0, 8), pady=0)
        
        # Text Editor Widget
        editor = tk.Text(self.editor_area,
                         bg=self.main_app.colors["editor"],
                         fg=self.main_app.colors["text"],
                         font=("JetBrains Mono", 11),
                         insertbackground=self.main_app.colors["accent"],
                         selectbackground="#1e293b",
                         relief=tk.FLAT,
                         borderwidth=0,
                         highlightthickness=0)
        
        editor.pack_forget()  
        
        # Insert Content
        if content:
            editor.insert("1.0", content)
        
        # Apply Tags
        self.setup_highlight_tags(editor)
        
        # Bindings
        def on_key_release(event):
            self.highlight_syntax(editor)
            
            if filepath and content:
                current_content = editor.get("1.0", tk.END).rstrip()
                if current_content != content.rstrip():
                    self.set_tab_changed(tab_id, True)
        
        editor.bind('<KeyRelease>', on_key_release)
        
        # Store Data
        self.tabs[tab_id] = {
            'frame': tab_frame,
            'label': tab_label,
            'editor': editor,
            'filename': filename,
            'filepath': filepath,
            'changed': False,
            'close_btn': close_btn,
            'original_content': content,
            'tokens': [] 
        }
        
        # Tab Selection Logic
        def select_tab(event, tab_id=tab_id):
            self.switch_to_tab(tab_id)
        
        tab_label.bind("<Button-1>", select_tab)
        tab_frame.bind("<Button-1>", select_tab)
        
        # Activate the new tab
        self.switch_to_tab(tab_id)
        return tab_id

    def switch_to_tab(self, tab_id):
        """Switch to specified tab"""
        if tab_id not in self.tabs:
            return
            
        # Hide all others
        for tab_data in self.tabs.values():
            tab_data['editor'].pack_forget()
            tab_data['frame'].configure(fg_color="transparent")
            tab_data['label'].configure(text_color=self.main_app.colors["muted"])
        
        # Show selected
        tab_data = self.tabs[tab_id]
        tab_data['editor'].pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        tab_data['frame'].configure(fg_color=self.main_app.colors["panel"])
        tab_data['label'].configure(text_color=self.main_app.colors["text"])
        
        # Update app state
        self.current_file = tab_data['filepath'] or tab_data['filename']
        
        # Refresh highlighting
        self.highlight_syntax(tab_data['editor'])
        
        # --- Restore tokens and apply filter ---
        current_tokens_from_tab = tab_data.get('tokens', [])
        
        if hasattr(self.main_app, 'all_tokens'):
            self.main_app.all_tokens = current_tokens_from_tab
            self.main_app.apply_filter(self.main_app.filter_var.get())
        else:
            self.main_app.render_tokens(current_tokens_from_tab)
        
        # Update Window Title
        if tab_data['changed']:
            self.main_app.root.title(f"Lumina Studio - *{tab_data['filename']}")
        else:
            self.main_app.root.title(f"Lumina Studio - {tab_data['filename']}")

    def close_tab(self, tab_id):
        """Close a tab"""
        if tab_id not in self.tabs:
            return
            
        tab_data = self.tabs[tab_id]
        
        if tab_data['changed']:
            response = messagebox.askyesnocancel(
                "Unsaved Changes",
                f"Do you want to save changes to {tab_data['filename']}?"
            )
            
            if response is None:
                return
            elif response:
                self.main_app.save_file(tab_id)
        
        tab_data['editor'].destroy()
        tab_data['frame'].destroy()
        del self.tabs[tab_id]
        
        if not self.tabs:
            self.create_new_tab("Untitled.lum")
        else:
            first_tab_id = next(iter(self.tabs))
            self.switch_to_tab(first_tab_id)

    def setup_highlight_tags(self, editor):
        """Setup syntax highlighting tags"""
        editor.tag_configure("KEYWORD", foreground="#569cd6")
        editor.tag_configure("TYPE", foreground="#4ec9b0")
        editor.tag_configure("STRING", foreground="#ce9178")
        editor.tag_configure("COMMENT", foreground="#6a9955")
        editor.tag_configure("NUMBER", foreground="#b5cea8")
        editor.tag_configure("CONTRACT", foreground="#c586c0")

    def highlight_syntax(self, editor):
        """Apply syntax highlighting"""
        code = editor.get("1.0", tk.END)
        for tag in ["KEYWORD", "TYPE", "STRING", "COMMENT", "NUMBER", "CONTRACT"]:
            editor.tag_remove(tag, "1.0", tk.END)

        patterns = [
            ("COMMENT", r'//.*|/\*[\s\S]*?\*/'),
            ("STRING", r'"[^"]*"'),
            ("KEYWORD", r'\b(func|main|let|var|struct|type|if|else|switch|case|default|break|while|do|for|display|read|return)\b'),
            ("CONTRACT", r'\b(requires|ensures|invariant)\b'),
            ("TYPE", r'\b(int|float|double|string|bool|void|char)\b|[A-Z][a-zA-Z0-9_]*'),
            ("NUMBER", r'\b\d+\b'),
        ]

        for tag, regex in patterns:
            for match in re.finditer(regex, code):
                start = f"1.0 + {match.start()} chars"
                end = f"1.0 + {match.end()} chars"
                editor.tag_add(tag, start, end)

    def get_current_editor(self):
        for tab_data in self.tabs.values():
            if tab_data['editor'].winfo_ismapped():
                return tab_data['editor']
        return None

    def get_current_tab_id(self):
        for tab_id, tab_data in self.tabs.items():
            if tab_data['editor'].winfo_ismapped():
                return tab_id
        return None

    def get_editor_content(self, tab_id):
        if tab_id in self.tabs:
            return self.tabs[tab_id]['editor'].get("1.0", tk.END).rstrip()
        return ""

    def set_tab_changed(self, tab_id, changed=True):
        if tab_id in self.tabs:
            tab_data = self.tabs[tab_id]
            tab_data['changed'] = changed
            filename = tab_data['filename']
            display_text = f"*{filename}" if changed else filename
            tab_data['label'].configure(text=display_text)
            
            if tab_data['editor'].winfo_ismapped():
                if changed:
                    self.main_app.root.title(f"Lumina Studio - *{filename}")
                else:
                    self.main_app.root.title(f"Lumina Studio - {filename}")

class LuminaIDE:
    def __init__(self, root):
        self.root = root
        self.root.title("Lumina Studio")
        self.root.geometry("1200x800")
        
        self.colors = {
            "bg": "#0f172a",
            "sidebar": "#1e293b",
            "panel": "#1e293b",
            "editor": "#020617",
            "accent": "#22d3ee",
            "text": "#f8fafc",
            "muted": "#94a3b8",
            "border": "#334155"
        }

        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # 1. Sidebar
        self.sidebar = ctk.CTkFrame(root, width=200, corner_radius=0, fg_color=self.colors["sidebar"])
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1) 

        self.create_sidebar_content()

        # 2. Main Paned Window
        self.paned_window = tk.PanedWindow(root, orient=tk.HORIZONTAL, 
                                           bg=self.colors["bg"], 
                                           bd=0,
                                           sashwidth=4,
                                           sashrelief=tk.FLAT)
        self.paned_window.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)

        # A. Editor Frame
        self.editor_frame = ctk.CTkFrame(self.paned_window, fg_color=self.colors["bg"], corner_radius=0)
        self.paned_window.add(self.editor_frame, width=700)
        
        # B. Table Frame
        self.table_frame = ctk.CTkFrame(self.paned_window, fg_color=self.colors["sidebar"], corner_radius=0)
        self.paned_window.add(self.table_frame, width=400)
        
        self.create_table_area() 

        # C. Tabbed Editor
        self.tabbed_editor = TabbedEditor(self.editor_frame, self, fg_color=self.colors["bg"])
        self.tabbed_editor.pack(fill=tk.BOTH, expand=True)

        # 3. Terminal
        self.terminal_frame = ctk.CTkFrame(root, height=150, fg_color=self.colors["panel"], corner_radius=0)
        self.terminal_frame.grid(row=1, column=1, sticky="ew")
        
        self.create_terminal_area()


    def create_sidebar_content(self):
        header_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=16, pady=(18, 6), sticky="w")
        
        icon_path = "ui/icon.png" 
        try:
            raw_image = Image.open(icon_path)
            ctk_icon = ctk.CTkImage(light_image=raw_image, dark_image=raw_image, size=(30, 30))
            icon_label = ctk.CTkLabel(header_frame, text="", image=ctk_icon)
            icon_label.pack(side=tk.LEFT, padx=(0, 10))
            icon_label.image = ctk_icon
        except Exception:
            empty_image = Image.new("RGBA", (30, 30), color="#22d3ee") 
            ctk_icon_fallback = ctk.CTkImage(light_image=empty_image, dark_image=empty_image, size=(30, 30))
            icon_label = ctk.CTkLabel(header_frame, text="", image=ctk_icon_fallback)
            icon_label.pack(side=tk.LEFT, padx=(0, 10))
            icon_label.image = ctk_icon_fallback

        title_label = ctk.CTkLabel(header_frame, text="LUMINA", font=("Segoe UI", 22, "bold"), text_color=self.colors["text"])
        title_label.pack(side=tk.LEFT)
        
        subtitle = ctk.CTkLabel(self.sidebar, text="Compiler Environment", font=("Segoe UI", 12), text_color=self.colors["muted"])
        subtitle.grid(row=1, column=0, padx=16, pady=(0, 14), sticky="w")

        buttons_container = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        buttons_container.grid(row=2, column=0, sticky="nsew", padx=0, pady=0, rowspan=4)
        buttons_container.grid_columnconfigure(0, weight=1)
        buttons_container.grid_rowconfigure(4, weight=1)

        self.btn_new = ctk.CTkButton(buttons_container, text="📄  New File", command=self.add_new_file,
                                     fg_color="transparent", border_width=0,
                                     hover_color="#223043", corner_radius=6,
                                     font=("Segoe UI", 13), anchor="w",
                                     text_color=self.colors["text"])
        self.btn_new.grid(row=0, column=0, padx=8, pady=4, sticky="ew")

        self.btn_open = ctk.CTkButton(buttons_container, text="📂  Open File", command=self.open_file,
                                     fg_color="transparent", border_width=0,
                                     hover_color="#223043", corner_radius=6,
                                     font=("Segoe UI", 13), anchor="w",
                                     text_color=self.colors["text"])
        self.btn_open.grid(row=1, column=0, padx=8, pady=4, sticky="ew")

        self.btn_save = ctk.CTkButton(buttons_container, text="💾  Save File", command=self.save_current_file,
                                     fg_color="transparent", border_width=0,
                                     hover_color="#223043", corner_radius=6,
                                     font=("Segoe UI", 13), anchor="w",
                                     text_color=self.colors["text"])
        self.btn_save.grid(row=2, column=0, padx=8, pady=4, sticky="ew")

        self.btn_run = ctk.CTkButton(buttons_container, text="▶  Run Lexer", command=self.run_lexer,
                                     fg_color=self.colors["accent"], hover_color="#1bcde5", 
                                     corner_radius=8, font=("Segoe UI", 13, "bold"), anchor="w",
                                     text_color="#000000")
        self.btn_run.grid(row=3, column=0, padx=8, pady=6, sticky="ew")

        self.btn_exit = ctk.CTkButton(self.sidebar, text="Exit", command=self.root.quit,
                                     fg_color="#223043", hover_color="#c42b1c", 
                                     corner_radius=6, font=("Segoe UI", 12), text_color=self.colors["text"])
        self.btn_exit.grid(row=6, column=0, padx=0, pady=0, sticky="sew")

    def create_table_area(self):
        header_frame = ctk.CTkFrame(self.table_frame, fg_color=self.colors["panel"], height=34, corner_radius=0)
        header_frame.pack(fill=tk.X)
        
        # --- Filter Dropdown ---
        self.filter_var = ctk.StringVar(value="Show: All")
        self.filter_menu = ctk.CTkOptionMenu(
            header_frame,
            values=["Show: All", "Show: Errors", "Show: Identifiers", "Show: Keywords", "Show: Literals", "Show: Noise Words", "Show: Operators", "Show: Symbols"],
            command=self.apply_filter, 
            variable=self.filter_var,
            width=140,
            height=26,
            fg_color=self.colors["editor"],
            button_color=self.colors["border"],
            button_hover_color=self.colors["accent"],
            font=("Segoe UI", 11),
            text_color=self.colors["text"]
        )
        self.filter_menu.pack(side=tk.LEFT, padx=12, pady=4)

        self.btn_save_table = ctk.CTkButton(header_frame, text="💾 Save", 
                                            command=self.save_token_table,
                                            width=70, height=26,
                                            fg_color="transparent", 
                                            border_width=0,
                                            hover_color="#223043",
                                            font=("Segoe UI", 11),
                                            text_color=self.colors["text"])
        self.btn_save_table.pack(side=tk.RIGHT, padx=10, pady=4)

        # --- Table Container ---
        tree_container = ctk.CTkFrame(self.table_frame, fg_color=self.colors["panel"], corner_radius=0)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # --- Custom Style for Treeview ---
        style = ttk.Style()
        style.theme_use("clam")
        
        # --- FIX: Remove White Border ---
        # This layout override prevents the border from being drawn
        style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])
        
        # General Config
        style.configure("Treeview",
                        background="#0b172b",
                        foreground="#f8fafc",
                        fieldbackground="#0b172b",
                        borderwidth=0, # Ensure 0
                        rowheight=24,
                        font=("Segoe UI", 11))
        
        # Header Config
        style.configure("Treeview.Heading",
                        background="#1e293b",
                        foreground="#f8fafc",
                        relief="flat",
                        borderwidth=0, # Ensure 0
                        font=("Segoe UI", 12, "bold"))
        
        # Map Rows
        style.map("Treeview",
                  background=[('selected', '#1e293b'), ('active', '#0b172b')], 
                  foreground=[('selected', '#22d3ee'), ('active', '#f8fafc')])
        
        # Map Headings
        style.map("Treeview.Heading",
                  background=[('active', '#1e293b'), ('pressed', '#1e293b')], 
                  foreground=[('active', '#f8fafc'), ('pressed', '#f8fafc')])

        # Create Treeview
        columns = ("line", "type", "lexeme")
        self.tree = ttk.Treeview(tree_container, columns=columns, show="headings", selectmode="browse")
        
        # --- Columns Configuration ---
        self.tree.heading("line", text="Line", anchor="w")
        self.tree.heading("type", text="Token Type", anchor="w")
        self.tree.heading("lexeme", text="Lexeme", anchor="w")
        
        self.tree.column("line", width=50, anchor="w") 
        self.tree.column("type", width=120, anchor="w") 
        self.tree.column("lexeme", width=150, anchor="w") 
        
        # Scrollbar
        scrollbar = ctk.CTkScrollbar(tree_container, orientation="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Tags
        self.tree.tag_configure("ERROR", foreground="#ef4444")
        self.tree.tag_configure("LITERAL", foreground="#22c55e")
        self.tree.tag_configure("KEYWORD", foreground="#a855f7")
        self.tree.tag_configure("ID", foreground="#3b82f6")
        self.tree.tag_configure("OP", foreground="#ec4899")
        self.tree.tag_configure("SYMBOL", foreground="#f472b6")
        self.tree.tag_configure("NOISE", foreground="#94a3b8")
        self.tree.tag_configure("NORMAL", foreground="#f8fafc")
        
        self.all_tokens = []     
        self.current_tokens = [] 
        self.render_tokens([])

    def apply_filter(self, choice):
        if not hasattr(self, 'all_tokens') or not self.all_tokens:
            self.render_tokens([])
            return

        filtered_list = []

        def is_error(token):
            t_type = token['type'].upper()
            return "INVALID" in t_type or "ERROR" in t_type or "UNKNOWN" in t_type

        if choice == "Show: All":
            filtered_list = self.all_tokens
            
        elif choice == "Show: Errors":
            filtered_list = [t for t in self.all_tokens if is_error(t)]
            
        elif choice == "Show: Identifiers":
            filtered_list = [
                t for t in self.all_tokens 
                if "ID" in t['type'] and not is_error(t)
            ]
            
        elif choice == "Show: Keywords":
            filtered_list = [
                t for t in self.all_tokens 
                if "KEYWORD" in t['type'] and not is_error(t)
            ]
            
        elif choice == "Show: Literals":
            literals = ["STRING", "INTEGER", "FLOAT", "CHAR", "BOOL"]
            filtered_list = [
                t for t in self.all_tokens 
                if any(lit in t['type'] for lit in literals) and not is_error(t)
            ]
        
        elif choice == "Show: Noise Words":
            filtered_list = [
                t for t in self.all_tokens 
                if "NOISE" in t['type'] and not is_error(t)
            ]
            
        elif choice == "Show: Operators":
            filtered_list = [
                t for t in self.all_tokens 
                if "OP" in t['type'] and not is_error(t)
            ]
            
        elif choice == "Show: Symbols":
            filtered_list = [
                t for t in self.all_tokens 
                if "SYMBOL" in t['type'] and not is_error(t)
            ]

        self.render_tokens(filtered_list)

    def render_tokens(self, tokens):
        self.current_tokens = tokens 
        
        if not hasattr(self, 'tree'):
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        if not tokens:
            return

        for token in tokens:
            t_type = str(token['type']).upper()
            tag = "NORMAL"
            
            if "INVALID" in t_type or "ERROR" in t_type or "UNKNOWN" in t_type:
                tag = "ERROR"
            elif any(lit in t_type for lit in ["STRING", "INTEGER", "FLOAT", "CHAR", "BOOL"]):
                tag = "LITERAL"
            elif "KEYWORD" in t_type:
                tag = "KEYWORD"
            elif "ID" in t_type:
                tag = "ID"
            elif "OP" in t_type:
                tag = "OP"
            elif "SYMBOL" in t_type:
                tag = "SYMBOL"
            elif "NOISE" in t_type:
                tag = "NOISE"
                
            self.tree.insert("", "end", values=(token['line'], token['type'], token['lexeme']), tags=(tag,))

    def create_terminal_area(self):
        header = ctk.CTkFrame(self.terminal_frame, fg_color=self.colors["panel"], height=25, corner_radius=0)
        header.pack(fill=tk.X)
        lbl = ctk.CTkLabel(header, text="  TERMINAL / OUTPUT", font=("Segoe UI", 12, "bold"), text_color=self.colors["muted"])
        lbl.pack(side=tk.LEFT, padx=5)

        self.console_output = tk.Text(self.terminal_frame, height=6,
                                      bg=self.colors["editor"], fg=self.colors["text"],
                                      font=("Consolas", 12),
                                      relief=tk.FLAT,
                                      borderwidth=0,
                                      highlightthickness=0,
                                      insertbackground=self.colors["accent"])
        self.console_output.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.console_output.tag_config("error", foreground="#ef4444")
        self.console_output.tag_config("success", foreground="#22c55e")
        self.console_output.tag_config("normal", foreground=self.colors["text"])
        
        self.console_output.config(state=tk.DISABLED)

    # --- File Operations ---
    def add_new_file(self):
        untitled_count = sum(1 for tab in self.tabbed_editor.tabs.values() 
                           if tab['filename'].startswith("Untitled"))
        filename = f"Untitled{untitled_count + 1}.lum" if untitled_count > 0 else "Untitled.lum"
        
        self.tabbed_editor.create_new_tab(filename)
        self.log_console(f"Created new file: {filename}")

    def open_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Lumina Files", "*.lum"), ("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, "r") as file:
                    content = file.read()
                
                filename = os.path.basename(file_path)
                
                for tab_id, tab_data in self.tabbed_editor.tabs.items():
                    if tab_data['filepath'] == file_path:
                        self.tabbed_editor.switch_to_tab(tab_id)
                        self.log_console(f"Switched to already open file: {filename}")
                        return
                
                tab_id = self.tabbed_editor.create_new_tab(filename, file_path, content)
                self.tabbed_editor.set_tab_changed(tab_id, False)
                self.log_console(f"Opened: {filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open file: {str(e)}")

    def save_current_file(self):
        current_tab_id = self.tabbed_editor.get_current_tab_id()
        if current_tab_id:
            self.save_file(current_tab_id)
            
            tokens = [[str(t["line"]), str(t["type"]), str(t["lexeme"])] for t in self.current_tokens]
            
            if tokens:
                response = messagebox.askyesno(
                    "Save Token Table",
                    "Do you also want to save the token table?"
                )
                
                if response:
                    tab_data = self.tabbed_editor.tabs[current_tab_id]
                    if tab_data['filepath']:
                        code_file_path = tab_data['filepath']
                        base_name = os.path.splitext(os.path.basename(code_file_path))[0]
                        parent_dir = os.path.dirname(code_file_path)
                        
                        token_file_path = filedialog.asksaveasfilename(
                            defaultextension=".txt",
                            initialfile=f"{base_name}_tokens.txt",
                            initialdir=parent_dir,
                            filetypes=[("Text Files", "*.txt"), ("CSV Files", "*.csv"), ("All Files", "*.*")],
                            title="Save Token Table As"
                        )
                        
                        if token_file_path:
                            try:
                                if token_file_path.lower().endswith('.csv'):
                                    self._save_as_csv(token_file_path, tokens)
                                else:
                                    self._save_as_text(token_file_path, tokens)
                                self.log_console(f"Token table saved to: {os.path.basename(token_file_path)}")
                            except Exception as e:
                                messagebox.showerror("Error", f"Failed to save token table: {str(e)}")

    def save_file(self, tab_id):
        if tab_id not in self.tabbed_editor.tabs:
            return
            
        tab_data = self.tabbed_editor.tabs[tab_id]
        
        if not tab_data['filepath']:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".lum",
                filetypes=[("Lumina Files", "*.lum"), ("Text Files", "*.txt"), ("All Files", "*.*")]
            )
            if not file_path:
                return
            tab_data['filepath'] = file_path
            tab_data['filename'] = os.path.basename(file_path)
            tab_data['label'].configure(text=tab_data['filename'])
        
        try:
            content = self.tabbed_editor.get_editor_content(tab_id)
            with open(tab_data['filepath'], "w") as file:
                file.write(content)
            
            self.tabbed_editor.set_tab_changed(tab_id, False)
            self.log_console(f"Code saved: {tab_data['filename']}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {str(e)}")

    def save_token_table(self):
        tokens = [[str(t["line"]), str(t["type"]), str(t["lexeme"])] for t in self.current_tokens]
        
        if not tokens:
            messagebox.showwarning("Warning", "No tokens to save! Run analysis first.")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="Save Token Table As"
        )
        
        if not file_path:
            return
        
        try:
            if file_path.lower().endswith('.csv'):
                self._save_as_csv(file_path, tokens)
            else:
                self._save_as_text(file_path, tokens)
            
            self.log_console(f"Token table saved to: {os.path.basename(file_path)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save token table: {str(e)}")

    def _save_as_text(self, file_path, tokens):
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("LEXICAL ANALYSIS TOKEN TABLE\n")
            f.write("=" * 60 + "\n")
            f.write(f"Generated on: {self._get_current_timestamp()}\n")
            f.write("-" * 60 + "\n")
            f.write(f"{'Line':<6} | {'Token Type':<20} | {'Lexeme'}\n")
            f.write("-" * 60 + "\n")
            
            for line, token_type, lexeme in tokens:
                line_str = str(line) if not isinstance(line, str) else line
                token_type_str = str(token_type) if not isinstance(token_type, str) else token_type
                lexeme_str = str(lexeme) if not isinstance(lexeme, str) else lexeme
                
                formatted_lexeme = lexeme_str
                if len(lexeme_str) > 30:
                    formatted_lexeme = lexeme_str[:27] + "..."
                
                f.write(f"{line_str:<6} | {token_type_str:<20} | {formatted_lexeme}\n")
            
            f.write("-" * 60 + "\n")
            f.write(f"Total tokens: {len(tokens)}\n")
            f.write("=" * 60 + "\n")
            self._add_token_statistics(f, tokens)

    def _save_as_csv(self, file_path, tokens):
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Line", "Token Type", "Lexeme"])
            for token in tokens:
                writer.writerow(token)
            f.write(f"\n# Generated on: {self._get_current_timestamp()}\n")
            f.write(f"# Total tokens: {len(tokens)}\n")
            self._add_token_statistics(f, tokens, csv_format=True)

    def _get_current_timestamp(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _add_token_statistics(self, file_handle, tokens, csv_format=False):
        token_counts = {}
        for _, token_type, _ in tokens:
            token_type_str = str(token_type) if not isinstance(token_type, str) else token_type
            token_counts[token_type_str] = token_counts.get(token_type_str, 0) + 1
        
        if csv_format:
            file_handle.write("# Token Statistics:\n")
            for token_type, count in sorted(token_counts.items()):
                file_handle.write(f"# {token_type}: {count}\n")
        else:
            file_handle.write("\nToken Statistics:\n")
            file_handle.write("-" * 40 + "\n")
            for token_type, count in sorted(token_counts.items()):
                file_handle.write(f"{token_type:<20}: {count:>4}\n")

    def log_console(self, message, msg_type="normal"):
        self.console_output.config(state=tk.NORMAL)
        prefix = ">> "
        if msg_type == "error":
            prefix = "!! "
        elif msg_type == "success":
            prefix = "OK "
        self.console_output.insert(tk.END, f"{prefix}{message}\n", msg_type)
        self.console_output.see(tk.END)
        self.console_output.config(state=tk.DISABLED)

    def run_lexer(self):
        editor = self.tabbed_editor.get_current_editor()
        current_tab_id = self.tabbed_editor.get_current_tab_id()

        if not editor:
            messagebox.showwarning("Warning", "No active editor!")
            return
            
        source_code = editor.get("1.0", tk.END).strip()
        if not source_code:
            if current_tab_id:
                self.tabbed_editor.tabs[current_tab_id]['tokens'] = []
            
            self.all_tokens = []
            self.render_tokens([])
            self.log_console("Source code is empty.", "error")
            return

        self.log_console("Running Lexical Analysis...", "normal")

        try:
            lexer = LuminaLexer(source_code)
            tokens = lexer.tokenize()

            normalized = [{"line": token.line, "type": token.type, "lexeme": token.value} for token in tokens]
            
            self.all_tokens = normalized 
            
            if current_tab_id:
                self.tabbed_editor.tabs[current_tab_id]['tokens'] = normalized

            self.apply_filter(self.filter_var.get())
            
            if hasattr(lexer, 'errors') and lexer.errors:
                self.log_console(f"Analysis completed with {len(lexer.errors)} error(s):", "error")
                for err in lexer.errors:
                    self.log_console(f"  {err}", "error")
                messagebox.showerror("Lexical Errors", f"Found {len(lexer.errors)} lexical errors.\nCheck terminal for details.")
            else:
                self.log_console(f"Success! Generated {len(tokens)} tokens with no errors.", "success")
            
        except Exception as e:
            self.all_tokens = []
            self.render_tokens([])
            if current_tab_id:
                self.tabbed_editor.tabs[current_tab_id]['tokens'] = []
            self.log_console(f"CRITICAL ERROR: {str(e)}", "error")


if __name__ == "__main__":
    root = ctk.CTk()
    app = LuminaIDE(root)
    root.mainloop()