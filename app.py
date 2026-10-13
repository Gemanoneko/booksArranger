"""Books Arranger milestone 1: a read-only scanner and sorting preview."""
import argparse
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from catalog_owner import BASE, catalog_lock
from metadata import GENRES
from scanner import Inventory, DEFAULT_ROOTS

class App:
    def __init__(self, window, inventory):
        self.window, self.inventory = window, inventory
        self.offset = 0
        self.page_size = 250
        self.items = {}
        self.refresh_key = None
        self.closing = False
        window.title('Books Arranger — inventory prototype')
        window.geometry('1250x780')
        window.minsize(950, 650)
        window.protocol('WM_DELETE_WINDOW', self.close)
        outer = ttk.Frame(window, padding=12)
        outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='Read-only inventory and sorting preview. Your library files stay untouched.').pack(anchor='w')
        controls = ttk.Frame(outer)
        controls.pack(fill='x', pady=8)
        self.label = tk.StringVar(value=next(iter(inventory.roots)))
        roots = ttk.Combobox(controls, textvariable=self.label, values=list(inventory.roots), state='readonly', width=18)
        roots.pack(side='left')
        roots.bind('<<ComboboxSelected>>', self.root_changed)
        self.start_btn = ttk.Button(controls, text='Start scanning', command=lambda: self.launch(False))
        self.start_btn.pack(side='left', padx=6)
        self.stop_btn = ttk.Button(controls, text='Stop scanning', command=self.stop)
        self.stop_btn.pack(side='left', padx=6)
        self.resume_btn = ttk.Button(controls, text='Resume scanning', command=lambda: self.launch(True))
        self.resume_btn.pack(side='left', padx=6)
        self.root_text = tk.StringVar()
        ttk.Label(outer, textvariable=self.root_text).pack(anchor='w')
        self.status = tk.StringVar()
        ttk.Label(outer, textvariable=self.status, wraplength=1180).pack(anchor='w', pady=5)
        self.current = tk.StringVar()
        ttk.Label(outer, textvariable=self.current, wraplength=1180).pack(anchor='w')
        filter_bar = ttk.Frame(outer)
        filter_bar.pack(fill='x', pady=6)
        ttk.Label(filter_bar, text='Path contains:').pack(side='left')
        self.search = tk.StringVar()
        field = ttk.Entry(filter_bar, textvariable=self.search, width=35)
        field.pack(side='left', padx=6)
        field.bind('<Return>', lambda _event: self.reset_page())
        ttk.Button(filter_bar, text='Search', command=self.reset_page).pack(side='left')
        ttk.Button(filter_bar, text='Previous', command=lambda: self.page(-1)).pack(side='left', padx=6)
        ttk.Button(filter_bar, text='Next', command=lambda: self.page(1)).pack(side='left')
        self.page_label = tk.StringVar()
        ttk.Label(filter_bar, textvariable=self.page_label).pack(side='left', padx=10)
        table_frame = ttk.Frame(outer)
        table_frame.pack(fill='both', expand=True)
        columns = ('kind', 'arrival', 'title', 'author', 'confidence', 'path')
        self.table = ttk.Treeview(table_frame, columns=columns, show='headings', height=12, selectmode='browse')
        for column, heading, width in zip(columns, ('Type', 'Arrival', 'Existing title / filename clue', 'Existing author / artist', 'Preview status', 'Proposed destination'), (90,65,240,190,135,350)):
            self.table.heading(column, text=heading)
            self.table.column(column, width=width, minwidth=60)
        vertical = ttk.Scrollbar(table_frame, orient='vertical', command=self.table.yview)
        horizontal = ttk.Scrollbar(table_frame, orient='horizontal', command=self.table.xview)
        self.table.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.table.grid(row=0, column=0, sticky='nsew')
        vertical.grid(row=0, column=1, sticky='ns')
        horizontal.grid(row=1, column=0, sticky='ew')
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.table.bind('<<TreeviewSelect>>', self.selected)
        detail_bar = ttk.Frame(outer)
        detail_bar.pack(fill='x', pady=5)
        ttk.Label(detail_bar, text='Selected file — source evidence and preview').pack(side='left')
        ttk.Button(detail_bar, text='Review canonical metadata…', command=self.review).pack(side='right')
        self.detail = tk.Text(outer, height=10, wrap='word', state='disabled')
        self.detail.pack(fill='x')
        self.poll()

    def root_changed(self, _event=None):
        self.offset = 0
        self.refresh_key = None
        self.refresh()

    def reset_page(self):
        self.offset = 0
        self.refresh_key = None
        self.refresh()

    def page(self, direction):
        self.offset = max(0, self.offset + direction * self.page_size)
        self.refresh_key = None
        self.refresh()

    def launch(self, resume):
        try:
            self.inventory.launch(self.label.get(), resume)
            self.refresh_key = None
        except Exception as error:
            messagebox.showerror('Scan could not start', str(error), parent=self.window)

    def stop(self):
        self.inventory.stop()
        self.status.set('Stopping… completed results are saved; waiting for the active read to finish safely.')

    def poll(self):
        if self.closing:
            return
        self.refresh()
        self.window.after(700, self.poll)

    def refresh(self):
        label = self.label.get()
        state = self.inventory.status(label)
        active = bool(self.inventory.worker and self.inventory.worker.is_alive())
        stopped = state['state'] in {'stopped', 'offline', 'failed'}
        self.start_btn.configure(state='disabled' if active or stopped else 'normal')
        self.stop_btn.configure(state='normal' if active and not self.inventory.stop_event.is_set() else 'disabled')
        self.resume_btn.configure(state='normal' if stopped and not active else 'disabled')
        self.root_text.set(f'Source: {self.inventory.roots[label]}')
        self.table.heading('author',text='Existing author / artist clue' if label=='Audiobooks' else 'Existing author / artist')
        status = 'Stopping…' if active and self.inventory.stop_event.is_set() else state['state']
        self.status.set(f'{status} | Catalog: {state["count"]} files | Checked this scan: {state["checked"]} | Reused: {state["reused"]} | Pending tasks: {state["pending"]} | Read errors: {state["errors"]}')
        self.current.set(state.get('current') or 'Scans only read files. Review edits below are stored in the local catalog.')
        key = (label, state['count'], state['checked'], state['state'], self.offset, self.search.get())
        if key == self.refresh_key:
            return
        self.refresh_key = key
        selected = self.table.selection()
        selected_path = self.items.get(selected[0], {}).get('path') if selected else None
        self.table.delete(*self.table.get_children())
        self.items = {}
        rows = self.inventory.rows(label, self.page_size, self.offset, self.search.get())
        for index, row in enumerate(rows):
            item = str(index)
            metadata, preview = row['metadata'], row['preview']
            self.items[item] = row
            self.table.insert('', 'end', iid=item, values=(row['kind'], 'Yes' if row['arrival'] else '',
                metadata.get('title') or Path(row['path']).name, metadata.get('author', ''), preview['confidence'], preview['path'] or 'Needs review'))
            if row['path'] == selected_path:
                self.table.selection_set(item)
        self.page_label.set(f'Rows {self.offset + 1 if rows else 0}–{self.offset + len(rows)} (250 per page)')
        if not self.table.selection():
            self.show_detail('Select a file to inspect its metadata. Canonical English/Russian identities are never invented.')

    def show_detail(self, text):
        self.detail.configure(state='normal')
        self.detail.delete('1.0', 'end')
        self.detail.insert('1.0', text)
        self.detail.configure(state='disabled')

    def selected_row(self):
        selected = self.table.selection()
        return self.items.get(selected[0]) if selected else None

    def selected(self, _event=None):
        row = self.selected_row()
        if not row:
            return
        metadata = row['metadata']
        lines = [f'Source: {row["path"]}', f'Preview: {row["preview"]["path"] or "Not proposed until reviewed"}',
                 row['preview']['reason'], f'Read method: {metadata.get("method", "unavailable")}',
                 f'Edition language (not original language): {metadata.get("edition_language", "")}',
                 f'Series clue: {metadata.get("series", "")} / position: {metadata.get("number", "")}',
                 f'Existing genre clue: {metadata.get("genre", "")}', *metadata.get('notes', [])]
        if row['error']:
            lines.append('Error: ' + row['error'])
        if row['kind']=='audiobook':
            source_artist = metadata.get('artist') or next((value for key,value in metadata.get('tags',{}).items() if key.lower()=='artist'),'')
            tag = row['tag_preview']
            comment_values = tag['comment_fields']
            comments = '\n'.join(f'{item["field"]}: {item["value"]}' for item in comment_values) if len(comment_values)>1 else tag['existing_comments']
            if tag['narrator_appended']:
                comments += ('\n' if comments else '') + 'Narrator: ' + tag['narrator']
            lines.extend(['Existing Artist (role unverified): ' + str(source_artist or 'Unknown'),
                          'Future tag preview — source tags unchanged',
                          'Artist: ' + (tag['ARTIST'] or 'Needs author review'),
                          'Uses reviewed author folder credit.' if tag['artist_from_folder'] else '',
                          'Reader / narrator: ' + (tag['narrator'] or 'Not reviewed'),
                          'Comments: ' + (comments or 'No existing comments')])
        lines.extend(['Existing tags (read-only snapshot; no source rewriting):',json.dumps(metadata.get('tags',{}),ensure_ascii=False,indent=2)])
        self.show_detail('\n'.join(lines))

    def review(self):
        row = self.selected_row()
        if not row or row['kind'] not in {'audiobook', 'ebook'}:
            messagebox.showinfo('Review', 'Select an audiobook or ebook. Podcast and companion files are preserved.', parent=self.window)
            return
        dialog = tk.Toplevel(self.window)
        dialog.title('Canonical metadata — local preview only')
        dialog.transient(self.window)
        panel = ttk.Frame(dialog, padding=12)
        panel.pack(fill='both', expand=True)
        ttk.Label(panel, text='Enter verified book identity. Existing tags are clues, not verified translations.', wraplength=600).grid(row=0, column=0, columnspan=2, sticky='w', pady=5)
        existing = row['review'] or {}
        variables = {}
        fields = [('original_language', 'Original work language', ('Unknown', 'Russian', 'Other')),
                  ('title', 'Canonical title', None), ('author', 'Author folder name (Surname Firstname)', None),
                  ('series', 'Series / cycle (blank for standalone)', None), ('number', 'Number in series', None),
                  ('genre', 'Ebook main genre', GENRES), ('topic', 'Nonfiction topic', None)]
        if row['kind']=='audiobook':
            fields[3:3]=[('canonical_author','Author for Artist tag',None),('narrator','Reader / narrator (for comments)',None)]
        widgets = {}
        row_index = 1
        author_help = tk.StringVar(value='')
        audio_help = {'canonical_author':'Enter the verified author credit, such as Stephen King. Do not enter the reader here.',
                      'narrator':'Preserve the verified reader in comments alongside existing comments.'}
        for name, label, choices in fields:
            ttk.Label(panel, text=label).grid(row=row_index, column=0, sticky='w', padx=4, pady=4)
            variables[name] = tk.StringVar(value=existing.get(name, 'Unknown' if name == 'original_language' else ''))
            widget = ttk.Combobox(panel, textvariable=variables[name], values=choices, state='readonly', width=42) if choices else ttk.Entry(panel, textvariable=variables[name], width=45)
            widget.grid(row=row_index, column=1, sticky='ew', padx=4, pady=4)
            widgets[name]=widget
            row_index+=1
            if name=='author':
                ttk.Label(panel,textvariable=author_help,wraplength=580).grid(row=row_index,column=0,columnspan=2,sticky='w')
                row_index+=1
            if name in audio_help:
                ttk.Label(panel,text=audio_help[name],wraplength=580).grid(row=row_index,column=0,columnspan=2,sticky='w')
                row_index+=1
        multi = tk.BooleanVar(value=existing.get('multi_author', False))
        anthology = tk.BooleanVar(value=existing.get('anthology',False))
        series_help = tk.StringVar(value='')
        def routing_controls():
            enabled = row['kind']=='audiobook' and anthology.get()
            widgets['author'].configure(state='disabled' if enabled else 'normal')
            multi_control.configure(state='disabled' if enabled else 'normal')
            author_help.set('Anthologies use the Сборники folder.' if enabled else '')
            series_help.set('Anthology series stay inside Сборники.' if enabled else '')
        if row['kind']=='audiobook':
            ttk.Checkbutton(panel,text='Short-story collection by multiple authors',variable=anthology,command=routing_controls).grid(row=row_index,column=0,columnspan=2,sticky='w',pady=6)
            row_index+=1
            ttk.Label(panel,text='Place this audiobook in Сборники, or Сборники/Series when a series is entered.',wraplength=580).grid(row=row_index,column=0,columnspan=2,sticky='w')
            row_index+=1
        multi_control=ttk.Checkbutton(panel,text='Series has multiple authors: place its series folder at the library root',variable=multi)
        multi_control.grid(row=row_index,column=0,columnspan=2,sticky='w',pady=8)
        row_index+=1
        ttk.Label(panel,textvariable=series_help,wraplength=580).grid(row=row_index,column=0,columnspan=2,sticky='w')
        row_index+=1
        routing_controls()
        def save():
            values = {key: variable.get().strip() for key, variable in variables.items()}
            values['multi_author'] = multi.get()
            if row['kind']=='audiobook':
                values['anthology'] = anthology.get()
            try:
                self.inventory.save_review(row['root'], row['path'], values, row['size'], row['modified'])
            except Exception as error:
                messagebox.showerror('Review not saved', str(error), parent=dialog)
                return
            self.refresh_key = None
            self.refresh()
            self.selected()
            dialog.destroy()
        ttk.Button(panel, text='Save preview metadata', command=save).grid(row=row_index, column=1, sticky='e', pady=8)

    def close(self):
        self.closing = True
        self.inventory.stop()
        self.status.set('Closing… stopping the active read and saving the queue.')
        self._finish_close()

    def _finish_close(self):
        # Let the cooperative probe cancel/reap its child before exiting.
        if self.inventory.worker and self.inventory.worker.is_alive():
            self.window.after(100, self._finish_close)
        else:
            self.window.destroy()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default=str(BASE / 'data' / 'inventory.sqlite3'))
    parser.add_argument('--roots-json', help='Optional JSON file mapping Audiobooks, Podcasts, Ebooks to source paths')
    args = parser.parse_args()
    roots = DEFAULT_ROOTS
    if args.roots_json:
        roots = json.loads(Path(args.roots_json).read_text(encoding='utf-8'))
        if set(roots) != set(DEFAULT_ROOTS):
            parser.error('Root configuration must contain exactly Audiobooks, Podcasts, Ebooks')
    with catalog_lock(args.database, roots):
        inventory = Inventory(args.database, roots)
        window = tk.Tk()
        App(window, inventory)
        window.mainloop()

if __name__ == '__main__':
    main()
