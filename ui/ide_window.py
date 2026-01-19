import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
import re
from compiler.lexer import LuminaLexer

# --- CONFIGURATION ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class LuminaIDE:
    def __init__(self, root):
        self.root = root
        self.root.title("Lumina Studio")
        self.root.geometry("1200x800")
        
        # Color Palette (VS Code Dark Theme)
        self.colors = {
            "bg": "#1e1e1e",           # Editor Background
            "sidebar": "#252526",      # Sidebar Color
            "accent": "#007acc",       # Blue Accent
            "text": "#d4d4d4",         # Text Color
            "panel_border": "#3e3e42"  # Subtle Border
        }

        # --- LAYOUT SETUP ---
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # 1. SIDEBAR (Left)
        self.sidebar = ctk.CTkFrame(root, width=200, corner_radius=0, fg_color=self.colors["sidebar"])
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar.grid_rowconfigure(4, weight=1)

        self.create_sidebar_content()

        # 2. MAIN SPLIT VIEW (Using TK PanedWindow but stripped of borders)
        # We set bd=0 and sashrelief=flat to remove the ugly white borders
        self.paned_window = tk.PanedWindow(root, orient=tk.HORIZONTAL, 
                                           bg=self.colors["bg"], 
                                           bd=0,                   # REMOVES BORDER
                                           sashwidth=4,            # Thin separator
                                           sashrelief=tk.FLAT)     # Flat separator (no 3D effect)
        
        # NOTE: Removed padx/pady here so it touches the edges clean
        self.paned_window.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)

        # -- LEFT PANE: EDITOR --
        # We put the text widget inside a frame to give it a clean background
        self.editor_frame = ctk.CTkFrame(self.paned_window, fg_color=self.colors["bg"], corner_radius=0)
        self.paned_window.add(self.editor_frame, width=700)
        
        self.create_editor_area()

        # -- RIGHT PANE: TOKEN TABLE --
        self.table_frame = ctk.CTkFrame(self.paned_window, fg_color=self.colors["sidebar"], corner_radius=0)
        self.paned_window.add(self.table_frame, width=400)
        
        self.create_table_area()

        # 3. TERMINAL (Bottom)
        self.terminal_frame = ctk.CTkFrame(root, height=150, fg_color="#181818", corner_radius=0)
        self.terminal_frame.grid(row=1, column=1, sticky="ew")
        
        self.create_terminal_area()

    # -------------------------------------------------------------------------
    # UI COMPONENTS
    # -------------------------------------------------------------------------
    def create_sidebar_content(self):
        # Logo / Title
        title_label = ctk.CTkLabel(self.sidebar, text="LUMINA", font=("Montserrat", 24, "bold"), text_color="white")
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        subtitle = ctk.CTkLabel(self.sidebar, text="Compiler Environment", font=("Segoe UI", 12), text_color="gray")
        subtitle.grid(row=1, column=0, padx=20, pady=(0, 20))

        # Buttons
        self.btn_open = ctk.CTkButton(self.sidebar, text="📂 Open File", command=self.open_file, 
                                      fg_color="transparent", border_width=1, border_color="#3e3e42", 
                                      hover_color="#3e3e42", corner_radius=0)
        self.btn_open.grid(row=2, column=0, padx=0, pady=1, sticky="ew")

        self.btn_run = ctk.CTkButton(self.sidebar, text="▶ Run Analysis", command=self.run_lexer, 
                                     fg_color=self.colors["accent"], hover_color="#005f9e", corner_radius=0)
        self.btn_run.grid(row=3, column=0, padx=0, pady=1, sticky="ew")

        # Bottom Exit Button
        self.btn_exit = ctk.CTkButton(self.sidebar, text="Exit", command=self.root.quit, 
                                      fg_color="#333333", hover_color="#c42b1c", corner_radius=0)
        self.btn_exit.grid(row=5, column=0, padx=0, pady=0, sticky="ew")

    def create_editor_area(self):
        # Header strip
        header_frame = ctk.CTkFrame(self.editor_frame, fg_color="#252526", height=30, corner_radius=0)
        header_frame.pack(fill=tk.X)
        
        lbl_file = ctk.CTkLabel(header_frame, text="  main.lum  ", font=("Segoe UI", 11), text_color="#cccccc")
        lbl_file.pack(side=tk.LEFT, padx=10)

        # Actual Text Editor
        # borderwidth=0 and highlightthickness=0 REMOVES THE WHITE LINES
        self.code_editor = tk.Text(self.editor_frame, 
                                   bg=self.colors["bg"], 
                                   fg=self.colors["text"], 
                                   font=("Consolas", 13),
                                   insertbackground="white", 
                                   selectbackground="#264f78",
                                   relief=tk.FLAT,
                                   borderwidth=0,
                                   highlightthickness=0)
        
        self.code_editor.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Bind Highlighting
        self.setup_highlight_tags()
        self.code_editor.bind('<KeyRelease>', self.on_key_release)

    def create_table_area(self):
        header_frame = ctk.CTkFrame(self.table_frame, fg_color="#252526", height=30, corner_radius=0)
        header_frame.pack(fill=tk.X)
        
        lbl_tok = ctk.CTkLabel(header_frame, text="  Tokens  ", font=("Segoe UI", 11, "bold"), text_color="#cccccc")
        lbl_tok.pack(side=tk.LEFT, padx=10)

        # Treeview Style (Dark)
        style = ttk.Style()
        style.theme_use("clam")
        
        # IMPORTANT: Fix Treeview borders
        style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})]) # Removes default border
        style.configure("Treeview", 
                        background="#252526", 
                        foreground="white", 
                        fieldbackground="#252526", 
                        borderwidth=0,
                        font=('Consolas', 10))
        
        style.configure("Treeview.Heading", 
                        background="#333333", 
                        foreground="white", 
                        relief="flat")
        
        style.map("Treeview", background=[('selected', '#37373d')])

        # Table
        columns = ("line", "token", "lexeme")
        self.token_tree = ttk.Treeview(self.table_frame, columns=columns, show="headings", style="Treeview")
        
        self.token_tree.heading("line", text="Line")
        self.token_tree.heading("token", text="Type")
        self.token_tree.heading("lexeme", text="Lexeme")

        self.token_tree.column("line", width=40, anchor="center")
        self.token_tree.column("token", width=120)
        self.token_tree.column("lexeme", width=150)

        self.token_tree.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

    def create_terminal_area(self):
        # Terminal Header
        header = ctk.CTkFrame(self.terminal_frame, fg_color="#252526", height=25, corner_radius=0)
        header.pack(fill=tk.X)
        lbl = ctk.CTkLabel(header, text="  TERMINAL / OUTPUT", font=("Consolas", 10, "bold"), text_color="gray")
        lbl.pack(side=tk.LEFT, padx=5)

        # Terminal Text
        self.console_output = tk.Text(self.terminal_frame, height=6, 
                                      bg="#181818", fg="#cccccc", 
                                      font=("Consolas", 10),
                                      relief=tk.FLAT,
                                      borderwidth=0,
                                      highlightthickness=0)
        self.console_output.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.console_output.config(state=tk.DISABLED)

    # -------------------------------------------------------------------------
    # LOGIC
    # -------------------------------------------------------------------------
    def setup_highlight_tags(self):
        self.code_editor.tag_configure("KEYWORD", foreground="#569cd6")
        self.code_editor.tag_configure("TYPE", foreground="#4ec9b0")
        self.code_editor.tag_configure("STRING", foreground="#ce9178")
        self.code_editor.tag_configure("COMMENT", foreground="#6a9955")
        self.code_editor.tag_configure("NUMBER", foreground="#b5cea8")
        self.code_editor.tag_configure("CONTRACT", foreground="#c586c0")

    def on_key_release(self, event=None):
        self.highlight_syntax()

    def highlight_syntax(self):
        code = self.code_editor.get("1.0", tk.END)
        for tag in ["KEYWORD", "TYPE", "STRING", "COMMENT", "NUMBER", "CONTRACT"]:
            self.code_editor.tag_remove(tag, "1.0", tk.END)

        patterns = [
            ("COMMENT", r'//.*|/\*[\s\S]*?\*/'),
            ("STRING", r'"[^"]*"'),
            ("KEYWORD", r'\b(func|main|let|var|struct|void|if|else|switch|case|default|break|while|do|for|display|read|return)\b'),
            ("CONTRACT", r'\b(requires|ensures|invariant)\b'),
            ("TYPE", r'\b(int|float|string|bool|void|char)\b|[A-Z][a-zA-Z0-9_]*'),
            ("NUMBER", r'\b\d+\b'),
        ]

        for tag, regex in patterns:
            for match in re.finditer(regex, code):
                start = f"1.0 + {match.start()} chars"
                end = f"1.0 + {match.end()} chars"
                self.code_editor.tag_add(tag, start, end)

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Lumina Files", "*.lum"), ("Text Files", "*.txt")])
        if file_path:
            with open(file_path, "r") as file:
                self.code_editor.delete("1.0", tk.END)
                self.code_editor.insert("1.0", file.read())
                self.highlight_syntax()
            self.log_console(f"Loaded: {file_path}")

    def log_console(self, message):
        self.console_output.config(state=tk.NORMAL)
        self.console_output.insert(tk.END, f">> {message}\n")
        self.console_output.see(tk.END)
        self.console_output.config(state=tk.DISABLED)

    def run_lexer(self):
        source_code = self.code_editor.get("1.0", tk.END).strip()
        if not source_code:
            messagebox.showwarning("Warning", "Source code is empty!")
            return

        for row in self.token_tree.get_children():
            self.token_tree.delete(row)
        
        self.log_console("Running Lexical Analysis...")

        try:
            lexer = LuminaLexer(source_code)
            tokens = lexer.tokenize()

            for token in tokens:
                self.token_tree.insert("", tk.END, values=(token.line, token.type, token.value))
            
            self.log_console(f"Success! Generated {len(tokens)} tokens.")
            
        except Exception as e:
            self.log_console(f"ERROR: {str(e)}")
