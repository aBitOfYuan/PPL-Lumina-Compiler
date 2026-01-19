import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
import re
import os
import csv
from datetime import datetime
from compiler.lexer import LuminaLexer

# --- CONFIGURATION ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class TabbedEditor(ctk.CTkFrame):
    """Custom tabbed editor widget"""
    def __init__(self, master, main_app, **kwargs):
        super().__init__(master, **kwargs)
        self.main_app = main_app  # Reference to main LuminaIDE instance
        self.current_file = None
        self.tabs = {}  # tab_id -> (filepath, editor_widget, content_changed)
        self.tab_counter = 0  # Counter for generating unique tab IDs
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Tab header area - REMOVED padx to align with border
        self.tab_header = ctk.CTkFrame(self, fg_color="#252526", height=35, corner_radius=0)
        self.tab_header.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        
        # Tab buttons container - NO padding on left
        self.tab_buttons_frame = ctk.CTkFrame(self.tab_header, fg_color="transparent")
        self.tab_buttons_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=0)
        
        # Add tab button
        self.add_tab_btn = ctk.CTkButton(self.tab_header, text="+", width=35, height=28,
                                        command=self.main_app.add_new_file,
                                        fg_color="transparent", hover_color="#3e3e42",
                                        font=("Segoe UI", 12))
        self.add_tab_btn.pack(side=tk.RIGHT, padx=(0, 5), pady=3)
        
        # Editor area
        self.editor_area = ctk.CTkFrame(self, fg_color=self.main_app.colors["bg"], corner_radius=0)
        self.editor_area.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        
        # Create initial tab
        self.create_new_tab("Untitled.lum")

    def create_new_tab(self, filename, filepath=None, content=""):
        """Create a new tab with editor widget"""
        # Create tab button
        self.tab_counter += 1
        tab_id = self.tab_counter
        tab_frame = ctk.CTkFrame(self.tab_buttons_frame, fg_color="transparent", width=140, height=30)
        tab_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 0))
        
        # Display name - INCREASED FONT SIZE to 11
        display_name = filename
        tab_label = ctk.CTkLabel(tab_frame, text=display_name, font=("Segoe UI", 11))
        tab_label.pack(side=tk.LEFT, padx=(12, 5), pady=6)
        
        # Close button - Slightly larger
        close_btn = ctk.CTkButton(tab_frame, text="✕", width=22, height=22,
                                 command=lambda: self.close_tab(tab_id),
                                 fg_color="transparent", hover_color="#c42b1c",
                                 font=("Segoe UI", 10))
        close_btn.pack(side=tk.LEFT, padx=(0, 8), pady=0)
        
        # Create editor widget - INCREASED EDITOR FONT SIZE to 14
        editor = tk.Text(self.editor_area,
                        bg=self.main_app.colors["bg"],
                        fg=self.main_app.colors["text"],
                        font=("Consolas", 14),  # INCREASED from 13 to 14
                        insertbackground="white",
                        selectbackground="#264f78",
                        relief=tk.FLAT,
                        borderwidth=0,
                        highlightthickness=0)
        
        editor.pack_forget()  # Hide initially
        
        # Insert content
        if content:
            editor.insert("1.0", content)
        
        # Setup syntax highlighting
        self.setup_highlight_tags(editor)
        
        # Bind events
        def on_key_release(event):
            self.highlight_syntax(editor)
            # Mark as changed if content differs from original
            if filepath and content:
                current_content = editor.get("1.0", tk.END).rstrip()
                if current_content != content.rstrip():
                    self.set_tab_changed(tab_id, True)
        
        editor.bind('<KeyRelease>', on_key_release)
        
        # Store tab data
        self.tabs[tab_id] = {
            'frame': tab_frame,
            'label': tab_label,
            'editor': editor,
            'filename': filename,
            'filepath': filepath,
            'changed': False,
            'close_btn': close_btn,
            'original_content': content
        }
        
        # Bind tab selection
        def select_tab(event, tab_id=tab_id):
            self.switch_to_tab(tab_id)
        
        tab_label.bind("<Button-1>", select_tab)
        tab_frame.bind("<Button-1>", select_tab)
        
        # Switch to new tab
        self.switch_to_tab(tab_id)
        return tab_id

    def switch_to_tab(self, tab_id):
        """Switch to specified tab"""
        if tab_id not in self.tabs:
            return
            
        # Hide all editors
        for tab_data in self.tabs.values():
            tab_data['editor'].pack_forget()
            tab_data['frame'].configure(fg_color="transparent")
            tab_data['label'].configure(text_color="gray")
        
        # Show selected editor
        tab_data = self.tabs[tab_id]
        tab_data['editor'].pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        tab_data['frame'].configure(fg_color="#1e1e1e")
        tab_data['label'].configure(text_color="white")
        
        # Update current file
        self.current_file = tab_data['filepath'] or tab_data['filename']
        
        # Update syntax highlighting
        self.highlight_syntax(tab_data['editor'])
        
        # Update main window title
        if tab_data['changed']:
            self.main_app.root.title(f"Lumina Studio - *{tab_data['filename']}")
        else:
            self.main_app.root.title(f"Lumina Studio - {tab_data['filename']}")

    def close_tab(self, tab_id):
        """Close a tab"""
        if tab_id not in self.tabs:
            return
            
        tab_data = self.tabs[tab_id]
        
        # Check for unsaved changes
        if tab_data['changed']:
            response = messagebox.askyesnocancel(
                "Unsaved Changes",
                f"Do you want to save changes to {tab_data['filename']}?"
            )
            
            if response is None:  # Cancel
                return
            elif response:  # Yes
                self.main_app.save_file(tab_id)
        
        # Destroy widgets
        tab_data['editor'].destroy()
        tab_data['frame'].destroy()
        
        # Remove from tabs dict
        del self.tabs[tab_id]
        
        # If this was the last tab, create a new one
        if not self.tabs:
            self.create_new_tab("Untitled.lum")
        else:
            # Switch to another tab
            first_tab_id = next(iter(self.tabs))
            self.switch_to_tab(first_tab_id)

    def setup_highlight_tags(self, editor):
        """Setup syntax highlighting tags for an editor"""
        editor.tag_configure("KEYWORD", foreground="#569cd6")
        editor.tag_configure("TYPE", foreground="#4ec9b0")
        editor.tag_configure("STRING", foreground="#ce9178")
        editor.tag_configure("COMMENT", foreground="#6a9955")
        editor.tag_configure("NUMBER", foreground="#b5cea8")
        editor.tag_configure("CONTRACT", foreground="#c586c0")

    def highlight_syntax(self, editor):
        """Apply syntax highlighting to editor"""
        code = editor.get("1.0", tk.END)
        for tag in ["KEYWORD", "TYPE", "STRING", "COMMENT", "NUMBER", "CONTRACT"]:
            editor.tag_remove(tag, "1.0", tk.END)

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
                editor.tag_add(tag, start, end)

    def get_current_editor(self):
        """Get currently active editor widget"""
        for tab_data in self.tabs.values():
            if tab_data['editor'].winfo_ismapped():
                return tab_data['editor']
        return None

    def get_current_tab_id(self):
        """Get ID of currently active tab"""
        for tab_id, tab_data in self.tabs.items():
            if tab_data['editor'].winfo_ismapped():
                return tab_id
        return None

    def get_editor_content(self, tab_id):
        """Get content of specific editor"""
        if tab_id in self.tabs:
            return self.tabs[tab_id]['editor'].get("1.0", tk.END).rstrip()
        return ""

    def set_tab_changed(self, tab_id, changed=True):
        """Mark tab as changed/unchanged"""
        if tab_id in self.tabs:
            tab_data = self.tabs[tab_id]
            tab_data['changed'] = changed
            filename = tab_data['filename']
            display_text = f"*{filename}" if changed else filename
            
            # Update tab label
            tab_data['label'].configure(text=display_text)
            
            # Update window title if this is the current tab
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
        self.sidebar.grid_rowconfigure(6, weight=1)  # Added one more row for Exit button

        self.create_sidebar_content()

        # 2. MAIN SPLIT VIEW
        self.paned_window = tk.PanedWindow(root, orient=tk.HORIZONTAL, 
                                           bg=self.colors["bg"], 
                                           bd=0,
                                           sashwidth=4,
                                           sashrelief=tk.FLAT)
        
        self.paned_window.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)

        # -- LEFT PANE: TABBED EDITOR --
        self.editor_frame = ctk.CTkFrame(self.paned_window, fg_color=self.colors["bg"], corner_radius=0)
        self.paned_window.add(self.editor_frame, width=700)
        
        # Create tabbed editor with reference to self
        self.tabbed_editor = TabbedEditor(self.editor_frame, self, fg_color=self.colors["bg"])
        self.tabbed_editor.pack(fill=tk.BOTH, expand=True)

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
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        subtitle = ctk.CTkLabel(self.sidebar, text="Compiler Environment", font=("Segoe UI", 12), text_color="gray")
        subtitle.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")

        # Container frame for buttons to align them properly
        buttons_container = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        buttons_container.grid(row=2, column=0, sticky="nsew", padx=0, pady=0, rowspan=4)
        buttons_container.grid_columnconfigure(0, weight=1)
        buttons_container.grid_rowconfigure(4, weight=1)  # Add weight to push content up

        # Buttons - INCREASED FONT SIZE to 12 for sidebar buttons
        # LEFT ALIGNED for all buttons
        self.btn_new = ctk.CTkButton(buttons_container, text="📄 New File", command=self.add_new_file,
                                    fg_color="transparent", border_width=0, border_color="#3e3e42",
                                    hover_color="#3e3e42", corner_radius=0,
                                    font=("Segoe UI", 12), anchor="w")  # LEFT ALIGNED
        self.btn_new.grid(row=0, column=0, padx=0, pady=1, sticky="ew")

        self.btn_open = ctk.CTkButton(buttons_container, text="📂 Open File", command=self.open_file,
                                    fg_color="transparent", border_width=0, border_color="#3e3e42",
                                    hover_color="#3e3e42", corner_radius=0,
                                    font=("Segoe UI", 12), anchor="w")  # LEFT ALIGNED
        self.btn_open.grid(row=1, column=0, padx=0, pady=1, sticky="ew")

        self.btn_save = ctk.CTkButton(buttons_container, text="💾 Save File", command=self.save_current_file,
                                    fg_color="transparent", border_width=0, border_color="#3e3e42",
                                    hover_color="#3e3e42", corner_radius=0,
                                    font=("Segoe UI", 12), anchor="w")  # LEFT ALIGNED
        self.btn_save.grid(row=2, column=0, padx=0, pady=1, sticky="ew")

        self.btn_run = ctk.CTkButton(buttons_container, text="▶ Run Analysis", command=self.run_lexer,
                                    fg_color=self.colors["accent"], hover_color="#005f9e", 
                                    corner_radius=0, font=("Segoe UI", 12), anchor="w")  # LEFT ALIGNED
        self.btn_run.grid(row=3, column=0, padx=0, pady=1, sticky="ew")

        # Bottom Exit Button - AT THE VERY BOTTOM EDGE
        self.btn_exit = ctk.CTkButton(self.sidebar, text="Exit", command=self.root.quit,
                                    fg_color="#333333", hover_color="#c42b1c", 
                                    corner_radius=0, font=("Segoe UI", 12))
        self.btn_exit.grid(row=6, column=0, padx=0, pady=0, sticky="sew")

    def create_table_area(self):
        header_frame = ctk.CTkFrame(self.table_frame, fg_color="#252526", height=30, corner_radius=0)
        header_frame.pack(fill=tk.X)
        
        # Title label
        lbl_tok = ctk.CTkLabel(header_frame, text="  Tokens  ", font=("Segoe UI", 11, "bold"), text_color="#cccccc")
        lbl_tok.pack(side=tk.LEFT, padx=10)
        
        # Add save table button on the right
        self.btn_save_table = ctk.CTkButton(header_frame, text="💾 Save Tokens", 
                                          command=self.save_token_table,
                                          width=120, height=25,
                                          fg_color="transparent", 
                                          border_width=0,
                                          border_color="#3e3e42",
                                          hover_color="#3e3e42",
                                          font=("Segoe UI", 10))
        self.btn_save_table.pack(side=tk.RIGHT, padx=10, pady=2)

        # Treeview Style (Dark)
        style = ttk.Style()
        style.theme_use("clam")
        
        style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])
        style.configure("Treeview", 
                        background="#252526", 
                        foreground="white", 
                        fieldbackground="#252526", 
                        borderwidth=0,
                        font=('Consolas', 11))  # INCREASED from 10 to 11
        style.configure("Treeview.Heading", 
                        background="#333333", 
                        foreground="white", 
                        relief="flat",
                        font=('Segoe UI', 11))  # INCREASED heading font
        
        style.map("Treeview", background=[('selected', '#37373d')])

        # Table
        columns = ("line", "token", "lexeme")
        self.token_tree = ttk.Treeview(self.table_frame, columns=columns, show="headings", style="Treeview")
        
        self.token_tree.heading("line", text="Line")
        self.token_tree.heading("token", text="Type")
        self.token_tree.heading("lexeme", text="Lexeme")

        self.token_tree.column("line", width=50, anchor="center")  # Slightly wider
        self.token_tree.column("token", width=130)  # Slightly wider
        self.token_tree.column("lexeme", width=160)  # Slightly wider

        self.token_tree.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

    def create_terminal_area(self):
        # Terminal Header
        header = ctk.CTkFrame(self.terminal_frame, fg_color="#252526", height=25, corner_radius=0)
        header.pack(fill=tk.X)
        lbl = ctk.CTkLabel(header, text="  TERMINAL / OUTPUT", font=("Consolas", 11, "bold"), text_color="gray")  # INCREASED from 10 to 11
        lbl.pack(side=tk.LEFT, padx=5)

        # Terminal Text - INCREASED FONT SIZE to 11
        self.console_output = tk.Text(self.terminal_frame, height=6,
                                    bg="#181818", fg="#cccccc",
                                    font=("Consolas", 11),  # INCREASED from 10 to 11
                                    relief=tk.FLAT,
                                    borderwidth=0,
                                    highlightthickness=0)
        self.console_output.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.console_output.config(state=tk.DISABLED)

    # -------------------------------------------------------------------------
    # FILE OPERATIONS
    # -------------------------------------------------------------------------
    def add_new_file(self):
        """Add a new empty file tab"""
        # Count untitled files to generate unique name
        untitled_count = sum(1 for tab in self.tabbed_editor.tabs.values() 
                           if tab['filename'].startswith("Untitled"))
        filename = f"Untitled{untitled_count + 1}.lum" if untitled_count > 0 else "Untitled.lum"
        
        self.tabbed_editor.create_new_tab(filename)
        self.log_console(f"Created new file: {filename}")

    def open_file(self):
        """Open file in new tab"""
        file_path = filedialog.askopenfilename(
            filetypes=[("Lumina Files", "*.lum"), ("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, "r") as file:
                    content = file.read()
                
                filename = os.path.basename(file_path)
                
                # Check if file is already open
                for tab_id, tab_data in self.tabbed_editor.tabs.items():
                    if tab_data['filepath'] == file_path:
                        self.tabbed_editor.switch_to_tab(tab_id)
                        self.log_console(f"Switched to already open file: {filename}")
                        return
                
                # Create new tab with file content
                tab_id = self.tabbed_editor.create_new_tab(filename, file_path, content)
                self.tabbed_editor.set_tab_changed(tab_id, False)
                self.log_console(f"Opened: {filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open file: {str(e)}")

    def save_current_file(self):
        """Save current file - BOTH CODE AND TOKEN TABLE"""
        current_tab_id = self.tabbed_editor.get_current_tab_id()
        if current_tab_id:
            # First save the code file
            self.save_file(current_tab_id)
            
            # Then check if there are tokens to save
            tokens = []
            for child in self.token_tree.get_children():
                item = self.token_tree.item(child)
                values = item['values']
                if values:
                    # Ensure all values are strings
                    tokens.append([
                        str(values[0]) if values[0] is not None else "1",
                        str(values[1]) if values[1] is not None else "UNKNOWN",
                        str(values[2]) if values[2] is not None else ""
                    ])
            
            if tokens:
                # Ask if user wants to save token table too
                response = messagebox.askyesno(
                    "Save Token Table",
                    "Do you also want to save the token table?"
                )
                
                if response:
                    # Save token table in same location as code file
                    tab_data = self.tabbed_editor.tabs[current_tab_id]
                    if tab_data['filepath']:
                        code_file_path = tab_data['filepath']
                        base_name = os.path.splitext(os.path.basename(code_file_path))[0]
                        parent_dir = os.path.dirname(code_file_path)
                        
                        # Create token table filename based on code filename
                        token_file_path = os.path.join(parent_dir, f"{base_name}_tokens.txt")
                        
                        # Ask for confirmation or modification
                        token_file_path = filedialog.asksaveasfilename(
                            defaultextension=".txt",
                            initialfile=f"{base_name}_tokens.txt",
                            initialdir=parent_dir,
                            filetypes=[
                                ("Text Files", "*.txt"),
                                ("CSV Files", "*.csv"),
                                ("All Files", "*.*")
                            ],
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
        """Save specific tab's content (code only)"""
        if tab_id not in self.tabbed_editor.tabs:
            return
            
        tab_data = self.tabbed_editor.tabs[tab_id]
        
        if not tab_data['filepath']:
            # File not saved before, show save dialog
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

    # -------------------------------------------------------------------------
    # TOKEN TABLE SAVE OPERATIONS
    # -------------------------------------------------------------------------
    def save_token_table(self):
        """Save ONLY the token table to a file (NOT the program code)"""
        # Get all tokens from the treeview
        tokens = []
        for child in self.token_tree.get_children():
            item = self.token_tree.item(child)
            values = item['values']
            if values:
                # Ensure all values are strings
                tokens.append([
                    str(values[0]) if values[0] is not None else "1",
                    str(values[1]) if values[1] is not None else "UNKNOWN",
                    str(values[2]) if values[2] is not None else ""
                ])
        
        if not tokens:
            messagebox.showwarning("Warning", "No tokens to save! Run analysis first.")
            return
        
        # Ask for save location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[
                ("Text Files", "*.txt"),
                ("CSV Files", "*.csv"),
                ("All Files", "*.*")
            ],
            title="Save Token Table As"
        )
        
        if not file_path:
            return
        
        try:
            # Determine file format based on extension
            if file_path.lower().endswith('.csv'):
                self._save_as_csv(file_path, tokens)
            else:
                self._save_as_text(file_path, tokens)
            
            self.log_console(f"Token table saved to: {os.path.basename(file_path)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save token table: {str(e)}")

    def _save_as_text(self, file_path, tokens):
        """Save tokens as formatted text file"""
        with open(file_path, 'w', encoding='utf-8') as f:
            # Write header
            f.write("=" * 60 + "\n")
            f.write("LEXICAL ANALYSIS TOKEN TABLE\n")
            f.write("=" * 60 + "\n")
            f.write(f"Generated on: {self._get_current_timestamp()}\n")
            f.write("-" * 60 + "\n")
            f.write(f"{'Line':<6} | {'Token Type':<20} | {'Lexeme'}\n")
            f.write("-" * 60 + "\n")
            
            # Write tokens
            for line, token_type, lexeme in tokens:
                # All values are already strings, but ensure for safety
                line_str = str(line) if not isinstance(line, str) else line
                token_type_str = str(token_type) if not isinstance(token_type, str) else token_type
                lexeme_str = str(lexeme) if not isinstance(lexeme, str) else lexeme
                
                # Format for better readability
                formatted_lexeme = lexeme_str
                if len(lexeme_str) > 30:
                    formatted_lexeme = lexeme_str[:27] + "..."
                
                f.write(f"{line_str:<6} | {token_type_str:<20} | {formatted_lexeme}\n")
            
            # Write summary
            f.write("-" * 60 + "\n")
            f.write(f"Total tokens: {len(tokens)}\n")
            f.write("=" * 60 + "\n")
            
            # Add statistics
            self._add_token_statistics(f, tokens)

    def _save_as_csv(self, file_path, tokens):
        """Save tokens as CSV file"""
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(["Line", "Token Type", "Lexeme"])
            
            # Write tokens
            for token in tokens:
                writer.writerow(token)
            
            # Add summary/metadata as comments
            f.write(f"\n# Generated on: {self._get_current_timestamp()}\n")
            f.write(f"# Total tokens: {len(tokens)}\n")
            
            # Add statistics
            self._add_token_statistics(f, tokens, csv_format=True)

    def _get_current_timestamp(self):
        """Get formatted current timestamp"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _add_token_statistics(self, file_handle, tokens, csv_format=False):
        """Add token statistics to the file"""
        # Count token types
        token_counts = {}
        for _, token_type, _ in tokens:
            # Convert token_type to string for consistent counting
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

    # -------------------------------------------------------------------------
    # LOGIC
    # -------------------------------------------------------------------------
    def log_console(self, message):
        self.console_output.config(state=tk.NORMAL)
        self.console_output.insert(tk.END, f">> {message}\n")
        self.console_output.see(tk.END)
        self.console_output.config(state=tk.DISABLED)

    def run_lexer(self):
        """Run lexical analysis on current editor"""
        editor = self.tabbed_editor.get_current_editor()
        if not editor:
            messagebox.showwarning("Warning", "No active editor!")
            return
            
        source_code = editor.get("1.0", tk.END).strip()
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

# -------------------------------------------------------------------------
# MAIN ENTRY
# -------------------------------------------------------------------------
if __name__ == "__main__":
    root = ctk.CTk()
    app = LuminaIDE(root)
    root.mainloop()