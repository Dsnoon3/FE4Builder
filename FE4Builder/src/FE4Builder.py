"""Run with Python 3.10+; Tk is included in the standard Windows installer."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from rom import Rom, character_modules, army_modules, class_modules, category_modules, EDITOR_CATEGORIES, number, BUILDER_DIR, ROOT

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('FE4Builder')
        icon=BUILDER_DIR / 'assets' / 'sigurd.ico'
        if self.tk.call('tk','windowingsystem')=='win32' and icon.exists():
            self.iconbitmap(str(icon))
            self.iconbitmap(default=str(icon))
        else:
            png=BUILDER_DIR / 'assets' / 'sigurd-standing.png'
            if png.exists():
                self.app_icon=tk.PhotoImage(master=self,file=str(png))
                self.iconphoto(True,self.app_icon)
        self.geometry('1180x820')
        self.minsize(980, 650)
        self.rom = None
        self.editor_windows=[]
        self.modules = character_modules()
        self.mode = 'Character Editor'
        self.record = None
        self.editors = []
        self.loaded = []
        self.visible = []
        self.navigation = []
        self.linked_buttons = {}
        self._validation_job = None
        self.equipment_icons = {}
        self.promotion=None
        from ui_common import ContextStore
        self.ui_context=ContextStore();self.ui_context_ready=False
        self.field_controls=[];self._rendering=False;self.advanced_expanded=False;self.usage_index=None
        style = ttk.Style(self)
        style.theme_use('vista' if 'vista' in style.theme_names() else 'clam')
        style.configure('Title.TLabel', font=('Segoe UI', 17, 'bold'))
        style.configure('Subtitle.TLabel', foreground='#526274')
        style.configure('Changed.TLabel',foreground='#905300');style.configure('Error.TLabel',foreground='#b12b2b');style.configure('Warning.TLabel',foreground='#926400')
        menu = tk.Menu(self)
        file = tk.Menu(menu, tearoff=False)
        file.add_command(label='Open ROM…', command=self.open_rom, accelerator='Ctrl+O')
        file.add_command(label='Write to ROM',command=self.shortcut_write,accelerator='Ctrl+S')
        file.add_command(label='Save a copy…', command=self.save, accelerator='Ctrl+Shift+S')
        file.add_command(label='Show / copy ROM path…',command=self.show_rom_path)
        file.add_separator()
        file.add_command(label='Exit', command=self.close)
        menu.add_cascade(label='File', menu=file)
        self.edit_menu=tk.Menu(menu,tearoff=False)
        self.edit_menu.add_command(label='Undo ROM edit',command=lambda: self.history_step(False),accelerator='Ctrl+Z',state='disabled')
        self.edit_menu.add_command(label='Redo ROM edit',command=lambda: self.history_step(True),accelerator='Ctrl+Y',state='disabled')
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label='Change history / Backups…',command=self.show_history)
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label='Check current record / Shared data...',command=self.check_current_record)
        self.edit_menu.add_command(label='Check map and portrait pointers...',command=self.check_structure)
        menu.add_cascade(label='Edit',menu=self.edit_menu)
        emulator_menu=tk.Menu(menu,tearoff=False)
        emulator_menu.add_command(label='Save & Launch ROM',command=self.save_and_launch,accelerator='F5')
        emulator_menu.add_command(label='Emulator settings...',command=self.configure_emulator)
        menu.add_cascade(label='Emulator',menu=emulator_menu)
        menu.add_command(label='Patches',command=self.edit_patches)
        self.config(menu=menu)
        bar = ttk.Frame(self, padding=12)
        self.top_bar=bar
        bar.pack(fill='x')
        ttk.Label(bar, text='FE4Builder', style='Title.TLabel').pack(side='left')
        self.breadcrumb = ttk.Label(bar, text='  /  Main Menu', style='Subtitle.TLabel')
        self.breadcrumb.pack(side='left')
        ttk.Button(bar, text='Main Menu', command=self.show_menu).pack(side='left', padx=16)
        self.back_button=ttk.Button(bar,text='Back',command=self.link_back,state='disabled')
        self.back_button.pack(side='left')
        ttk.Button(bar, text='Save a copy…', command=self.save).pack(side='right')
        ttk.Button(bar, text='Open ROM…', command=self.open_rom).pack(side='right', padx=8)
        self.file_label = ttk.Label(self, text='Open a Fire Emblem 4 ROM to begin.', padding=(12, 4))
        self.file_label.pack(fill='x')
        history_bar=ttk.Frame(self,padding=(12,4))
        self.history_bar=history_bar
        history_bar.pack(fill='x')
        self.undo_button=ttk.Button(history_bar,text='Undo',command=lambda: self.history_step(False),state='disabled')
        self.undo_button.pack(side='left')
        self.redo_button=ttk.Button(history_bar,text='Redo',command=lambda: self.history_step(True),state='disabled')
        self.redo_button.pack(side='left',padx=6)
        ttk.Button(history_bar,text='Change History / Backups',command=self.show_history).pack(side='left',padx=6)
        ttk.Label(history_bar,text='Automatic backup before every overwrite',style='Subtitle.TLabel').pack(side='left',padx=12)
        self.save_indicator=tk.StringVar(value='No ROM loaded')
        self.save_state_label=ttk.Label(self,textvariable=self.save_indicator,padding=(12,2),foreground='#905300')
        self.save_state_label.pack(fill='x')
        ttk.Button(history_bar,text='Save & Launch (F5)',command=self.save_and_launch).pack(side='right')
        ttk.Button(history_bar,text='Emulator...',command=self.configure_emulator).pack(side='right',padx=8)
        from home_menu import build_home
        self.home=build_home(self)
        body = self.body = ttk.Panedwindow(self, orient='horizontal')
        left = ttk.Frame(body, width=245)
        body.add(left, weight=0)
        self.table_label = ttk.Label(left, text='Character table')
        self.table_label.pack(anchor='w')
        self.table = ttk.Combobox(left, state='readonly', values=[m.name.replace('FE4 ', '') for m in self.modules])
        self.table.current(0)
        self.table.pack(fill='x', pady=(5, 12))
        self.table.bind('<<ComboboxSelected>>', self.change_table)
        self.search = tk.StringVar()
        ttk.Entry(left, textvariable=self.search).pack(fill='x')
        ttk.Label(left, text='Search by name or record number', style='Subtitle.TLabel').pack(anchor='w', pady=(3, 8))
        self.search.trace_add('write', lambda *_: self.populate())
        self.list = tk.Listbox(left, font=('Segoe UI', 11), activestyle='none', exportselection=False)
        self.list.pack(fill='both', expand=True)
        self.list.bind('<<ListboxSelect>>', self.select)
        right = ttk.Frame(body, padding=(14, 0, 0, 0))
        body.add(right, weight=1)
        self.heading = ttk.Label(right, text='No ROM loaded', style='Title.TLabel')
        self.heading.pack(anchor='w')
        self.address = ttk.Label(right, text='Base stats • Growth rates • Skills • Holy blood • Equipment', style='Subtitle.TLabel')
        self.address.pack(anchor='w', pady=(4, 8))
        actions = ttk.Frame(right)
        actions.pack(fill='x', pady=(0, 8))
        self.apply_button = ttk.Button(actions, text='Write to ROM', command=self.write_original, state='disabled')
        self.apply_button.pack(side='right')
        ttk.Button(actions, text='Reload record', command=self.reload).pack(side='right', padx=8)
        self.name_button = ttk.Button(actions,text='Edit character name…',command=self.edit_selected_name,state='disabled')
        self.name_button.pack(side='left')
        self.map_button=ttk.Button(actions,text='Map Army Editor...',command=self.edit_army_map,state='disabled')
        self.map_button.pack(side='left',padx=8)
        self.sprite_button=ttk.Button(actions,text='Sprite sheets...',command=self.show_class_sprites,state='disabled')
        self.sprite_button.pack(side='left',padx=8)
        self.item_browser_button=ttk.Button(actions,text='Browse items...',command=self.browse_items,state='disabled')
        self.item_browser_button.pack(side='left',padx=8)
        self.portrait_frame=ttk.Frame(right)
        self.portrait_label=tk.Label(self.portrait_frame,bg='#172238',cursor='hand2')
        self.portrait_label.bind('<Button-1>',lambda e:self.open_linked_portrait())
        self.portrait_label.pack(side='left',padx=(0,12))
        self.portrait_info=ttk.Label(self.portrait_frame)
        self.portrait_info.pack(side='left')
        portrait_actions=ttk.Frame(self.portrait_frame)
        portrait_actions.pack(side='right')
        self.portrait_button=ttk.Button(portrait_actions,text='Portrait Editor…',command=self.open_linked_portrait)
        self.portrait_button.pack(fill='x',pady=2)
        self.portrait_import=ttk.Button(portrait_actions,text='Import PNG…',command=lambda:self.edit_portrait(self.current_portrait,'import'))
        self.portrait_import.pack(fill='x',pady=2)
        self.portrait_export=ttk.Button(portrait_actions,text='Export PNG…',command=lambda:self.edit_portrait(self.current_portrait,'export'))
        self.portrait_export.pack(fill='x',pady=2)
        self.current_portrait=None
        self.item_preview_frame=ttk.Frame(right,padding=(0,6))
        self.item_picture=ttk.Label(self.item_preview_frame)
        self.item_picture.grid(row=0,column=0,padx=(0,12))
        self.item_preview_frame.columnconfigure(1,weight=1)
        self.item_description=tk.StringVar()
        self.item_description_label=ttk.Label(self.item_preview_frame,textvariable=self.item_description,wraplength=550,justify='left')
        self.item_description_label.grid(row=0,column=1,sticky='ew')
        preview_controls=ttk.Frame(self.item_preview_frame)
        preview_controls.grid(row=0,column=2,sticky='ne',padx=(12,0))
        ttk.Label(preview_controls,text='Preview').pack(anchor='w')
        self.item_preview_view=ttk.Combobox(preview_controls,state='readonly',values=['Inventory icon','Held weapon'],width=15)
        self.item_preview_view.current(0);self.item_preview_view.pack(pady=4)
        self.item_preview_view.bind('<<ComboboxSelected>>',lambda e:self.update_equipment_visuals())
        self.item_preview_frame.bind('<Configure>',lambda e:self.item_description_label.configure(wraplength=max(200,e.width-self.item_picture.winfo_reqwidth()-preview_controls.winfo_reqwidth()-30)))
        self.shared_bar=ttk.Frame(right);self.shared_bar.pack(fill='x',pady=(0,4))
        self.shared_text=tk.StringVar();ttk.Label(self.shared_bar,textvariable=self.shared_text,wraplength=650,style='Subtitle.TLabel').pack(side='left',fill='x',expand=True)
        ttk.Button(self.shared_bar,text='See affected records…',command=self.show_shared_users).pack(side='right')
        help_panel=ttk.Frame(right)
        help_panel.pack(fill='x',pady=(0,8))
        self.help_expanded=False
        self.validation_counts=(0,0)
        self.help_toggle=ttk.Button(help_panel,text='[+] Field help / Validation',command=self.toggle_field_help)
        self.help_toggle.pack(anchor='w')
        help_box=self.field_help_body=ttk.Frame(help_panel,padding=8)
        self.field_help=tk.StringVar(value='Hover over or focus a field for an explanation.')
        self.field_help_label=ttk.Label(help_box,textvariable=self.field_help,wraplength=760,justify='left')
        self.field_help_label.pack(anchor='w')
        help_box.bind('<Configure>',lambda e:self.field_help_label.configure(wraplength=max(200,e.width-20)))
        help_actions=ttk.Frame(help_box);help_actions.pack(fill='x',pady=(5,0))
        self.validation_summary=tk.StringVar(value='Open a ROM to validate records.')
        self.validation_label=ttk.Label(help_actions,textvariable=self.validation_summary,wraplength=540)
        self.validation_label.pack(side='left',fill='x',expand=True)
        ttk.Button(help_actions,text='Check record / Shared data...',command=self.check_current_record).pack(side='right')
        ttk.Button(help_actions,text='Go to first issue',command=self.focus_first_issue).pack(side='right',padx=6)
        self.canvas = tk.Canvas(right, highlightthickness=0, background='#f0f0f0')
        scroll = ttk.Scrollbar(right, orient='vertical', command=self.canvas.yview)
        scroll.pack(side='right', fill='y')
        self.canvas.pack(fill='both', expand=True)
        self.canvas.configure(yscrollcommand=scroll.set)
        self.fields_frame = ttk.Frame(self.canvas)
        self.window = self.canvas.create_window(0, 0, window=self.fields_frame, anchor='nw')
        self.fields_frame.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfigure(self.window, width=e.width))
        for sequence in ('<MouseWheel>','<Button-4>','<Button-5>'):self.bind(sequence,self.scroll_editor)
        self.status = tk.StringVar(value='Ready — Write to ROM saves directly to the opened file.')
        self.status_label = ttk.Label(self, textvariable=self.status, relief='sunken', padding=6)
        self.status_label.pack(fill='x', side='bottom')
        self.bind('<F5>',lambda e:self.save_and_launch())
        self.bind('<Control-o>', lambda e: self.open_rom())
        self.bind('<Control-Shift-S>', lambda e: self.save())
        self.bind('<Control-s>',self.shortcut_write)
        self.bind('<Control-z>',lambda e: self.history_step(False))
        self.bind('<Control-y>',lambda e: self.history_step(True))
        self.protocol('WM_DELETE_WINDOW', self.close)
        from rom_selector import last_rom
        self.last_rom_path=last_rom()
        self.rom_selector=ttk.Frame(self,padding=36)
        ttk.Label(self.rom_selector,text='Choose a Fire Emblem 4 ROM',style='Title.TLabel').pack(anchor='w',pady=(0,12))
        ttk.Label(self.rom_selector,text='Open a ROM to access the editors. Your last ROM location is remembered.',style='Subtitle.TLabel').pack(anchor='w',pady=(0,24))
        ttk.Button(self.rom_selector,text='Browse for ROM…',command=self.open_rom).pack(anchor='w',ipadx=24,ipady=12)
        ttk.Label(self.rom_selector,text='Last opened ROM',font=('Segoe UI',11,'bold')).pack(anchor='w',pady=(28,8))
        self.last_rom_label=ttk.Label(self.rom_selector,wraplength=850)
        self.last_rom_label.pack(anchor='w')
        self.reopen_button=ttk.Button(self.rom_selector,text='Open last ROM',command=lambda:self.open_rom(self.last_rom_path))
        self.reopen_button.pack(anchor='w',pady=12,ipadx=24,ipady=8)
        self.show_rom_selector()
        from ui_common import fit_window
        fit_window(self)

    def view_tilesets(self,chapter=0):
        if not self.rom:
            messagebox.showinfo('Open a ROM','Open a ROM to view its tilesets.')
            return
        from tileset_window import TilesetWindow
        return self.prepare_window(TilesetWindow(self,chapter),restore=False)

    def show_class_sprites(self):
        if self.rom and self.record and self.mode=='Class Editor':
            from sprite_window import SpriteWindow
            SpriteWindow(self,self.record[1])

    def configure_emulator(self,parent=None):
        from emulator_window import configure_emulator
        return configure_emulator(self,parent)

    def save_and_launch(self,save_callback=None,parent=None):
        owner=parent or self
        if not self.rom:
            messagebox.showinfo('Open a ROM','Open a ROM before launching the emulator.',parent=owner)
            return False
        if not self.rom.path.is_file():
            messagebox.showerror('Cannot launch emulator','The opened ROM file is missing. Reopen the ROM before testing.',parent=owner)
            return False
        from emulator import load_config,command,launch
        try:
            config=load_config()
            command(config,self.rom.path) # Validate launch settings before saving.
        except (ValueError,OSError):
            config=self.configure_emulator(owner)
            if config is None:return False
            try:command(config,self.rom.path)
            except (ValueError,OSError) as error:
                messagebox.showerror('Cannot launch emulator',str(error),parent=owner)
                return False
        if save_callback is not None and save_callback() is not True:return False
        if self.record is not None:
            if not self.write_original():return False
        else:
            try:self.rom.save_original('Save for emulator testing')
            except (ValueError,OSError) as error:
                messagebox.showerror('Cannot save ROM',str(error),parent=owner);return False
            self.update_history_controls()
        try:
            self.emulator_process=launch(config,self.rom.path)
        except (ValueError,OSError) as error:
            messagebox.showerror('Cannot launch emulator','The ROM was saved, but the emulator could not start.\n'+str(error),parent=owner)
            self.status.set('ROM saved; emulator launch failed.')
            return False
        self.status.set(f'Saved and launched {self.rom.path.name} in {Path(config["executable"]).name}.')
        return True

    def browse_items(self):
        if not self.rom:return
        from item_browser import ItemBrowser
        ItemBrowser(self,self.open_linked_item)

    def open_linked_item(self,item):
        if not self.settle_link():return False
        from rom import Field
        from linked_editors import field_target
        target=field_target(self.rom,Field('Item',0,1,{},reference='FE4 Weapon List.txt'),item)
        origin=self.navigation_context()
        if self.go_to_record(*target):
            self.navigation.append(origin);self.back_button.configure(state='normal')
            return True
        return False

    def browse_equipment(self,field,var,options):
        from item_browser import ItemBrowser
        try:current=options[var.get()] if var.get() in options else number(var.get().strip())
        except ValueError:current=None
        def choose(value):
            var.set(next((label for label,key in options.items() if key==value),str(value)))
        ItemBrowser(self,choose,field,self.rom.field_options(field),current)

    def update_equipment_visuals(self):
        if not self.rom or self.record is None or not hasattr(self,'item_art'):return
        from portraits import export_png
        import base64
        for field_index,label in self.equipment_icons.items():
            field=self.modules[self.record[0]].fields[field_index]
            var,options=self.editors[field_index]
            try:
                value=options[var.get()] if var.get() in options else number(var.get().strip())
                item=self.item_art.resolve(field,value)
                if item is None:
                    label.configure(image='',text='-');continue
                rows,colors=self.item_art.icon(item)
                label.image=tk.PhotoImage(master=self,data=base64.b64encode(export_png(rows,colors))).zoom(2)
                label.configure(image=label.image,text='')
            except (ValueError,OverflowError):label.configure(image='',text='?')
        module=self.modules[self.record[0]]
        from item_art import item_for_record
        item=item_for_record(module,self.record[1])
        player_slot=module.name=='FE4 Player Weapon Editor'
        if player_slot:
            try:item=self.read_draft()[0]
            except ValueError:item=None
            if item==255:item=None
        self.item_preview_frame.pack_forget()
        if self.mode!='Item Editor' or item is None:return
        self.item_preview_frame.pack(fill='x',pady=(0,8),before=self.field_help_body.master)
        try:
            overrides=None
            values=self.read_draft()
            if module.name=='FE4 Item Sprite Editor by Lorena':overrides=tuple(values)
            if self.item_preview_view.current()==0:
                rows,colors=self.item_art.icon(item)
                note='Native inventory icon'
            else:
                rows,colors,note=self.item_art.art(item,overrides)
            self.item_picture.image=tk.PhotoImage(master=self,data=base64.b64encode(export_png(rows,colors))).zoom(4)
            self.item_picture.configure(image=self.item_picture.image)
            stats=dict(zip((f.name for f in module.fields),values)) if module.name not in ('FE4 Item Sprite Editor by Lorena','FE4 Player Weapon Editor') else None
            self.item_description.set(self.item_art.name(item,stats)+'\n'+self.item_art.summary(item,stats)+'\n'+note)
        except (ValueError,OverflowError) as error:
            self.item_picture.configure(image='')
            self.item_description.set('Preview unavailable: '+str(error))

    def update_help_caption(self):
        errors,warnings=self.validation_counts
        suffix=f' ({errors} errors, {warnings} warnings)' if errors or warnings else ''
        self.help_toggle.configure(text=('[-]' if self.help_expanded else '[+]')+' Field help / Validation'+suffix)

    def toggle_field_help(self):
        self.help_expanded=not self.help_expanded
        if self.help_expanded:
            self.field_help_body.pack(fill='x')
        else:
            self.field_help_body.pack_forget()
        self.update_help_caption()

    def read_draft(self):
        module=self.modules[self.record[0]]
        values=[]
        for field,(var,options) in zip(module.fields,self.editors):
            try:values.append(options[var.get()] if var.get() in options else number(var.get().strip()))
            except ValueError:raise ValueError(f'{field.name}: enter a number or choose a named option.')
        return values

    def schedule_validation(self,*_):
        self.refresh_draft_state()
        if self._validation_job is not None:
            self.after_cancel(self._validation_job)
        self._validation_job=self.after(250,self.update_validation)

    def update_validation(self):
        if self._validation_job is not None:
            self.after_cancel(self._validation_job)
        self._validation_job=None
        if not self.rom or self.record is None:return []
        self.update_equipment_visuals()
        from validation import validate_record,Issue
        try:issues=validate_record(self.rom,self.modules[self.record[0]],self.record[1],self.read_draft())
        except (ValueError,OverflowError) as error:issues=[Issue('Error',str(error).split(':',1)[0],str(error))]
        if self.promotion and self.promotion['var'].get()!=self.promotion['loaded']:
            try:self.promotion_plan(self.read_draft())
            except ValueError as error:issues.append(Issue('Error','Promotion Class',str(error)))
        errors=sum(i.severity=='Error' for i in issues);warnings=len(issues)-errors
        self.validation_counts=(errors,warnings)
        self.update_help_caption()
        self.validation_summary.set((f'{errors} error(s), {warnings} warning(s). '+issues[0].field+': '+issues[0].message) if issues else 'No issues found by current record checks.')
        self.validation_label.configure(foreground='#b12b2b' if errors else '#926400' if warnings else '#376549')
        self.current_issues=issues
        self.refresh_draft_state()
        self.update_shared_feedback()
        return issues

    def refresh_draft_state(self):
        if self._rendering or not hasattr(self,'save_indicator'):return
        dirty=bool(self.rom and (self.pending() or self.rom.dirty))
        self.save_indicator.set('Unsaved changes to the opened ROM — Ctrl+S writes; Save a copy keeps this editing target' if dirty else 'No pending edits — automatic backups protect every overwrite' if self.rom else 'Choose a ROM to begin')
        self.apply_button.config(state='normal' if dirty and self.record is not None else 'disabled')
        self.title(self.title().removesuffix(' *')+(' *' if dirty else ''))
        issues=getattr(self,'current_issues',[])
        for i,info in enumerate(self.field_controls):
            if i>=len(self.loaded):continue
            changed=info['var'].get()!=self.loaded[i]
            found=[issue for issue in issues if issue.field==info['name']]
            severity='Error' if any(x.severity=='Error' for x in found) else 'Warning' if found else 'Changed' if changed else ''
            info['label'].config(text=info['display']+(' *' if changed else ''),style=severity+'.TLabel' if severity else 'TLabel')
            if found:
                info['issue'].config(text=' '.join(x.message for x in found));info['issue'].grid(row=1,column=0,columnspan=5,sticky='w')
            else:info['issue'].grid_remove()

    def focus_first_issue(self):
        issues=getattr(self,'current_issues',[])
        if not issues:return
        name='Minimum Range' if issues[0].field=='Range' else issues[0].field
        if name=='Promotion Class' and self.promotion:
            self.promotion['widget'].focus_set();self.canvas.yview_moveto(0);return
        info=next((f for f in self.field_controls if f['name']==name),None)
        if not info:return
        if info['advanced'] and not self.advanced_expanded:self.toggle_advanced()
        self.update_idletasks();widget=info['widget'];getattr(widget,'button',widget).focus_set()
        y=widget.winfo_rooty()-self.fields_frame.winfo_rooty()
        self.canvas.yview_moveto(max(0,y-30)/max(1,self.fields_frame.winfo_height()))

    def show_rom_path(self):
        if not self.rom:return
        dialog=tk.Toplevel(self);dialog.title('Currently opened ROM');dialog.transient(self)
        ttk.Label(dialog,text='Write to ROM always overwrites this file.',padding=12).pack(anchor='w')
        text=tk.StringVar(value=str(self.rom.path.resolve()));ttk.Entry(dialog,textvariable=text,state='readonly',width=100).pack(fill='x',padx=12)
        ttk.Button(dialog,text='Copy path',command=lambda:(dialog.clipboard_clear(),dialog.clipboard_append(text.get()))).pack(side='left',padx=12,pady=12)
        ttk.Button(dialog,text='Close',command=dialog.destroy).pack(side='right',padx=12,pady=12)

    def shortcut_write(self,event=None):
        if not self.rom:return 'break'
        if self.record is not None:self.write_original()
        else:
            try:self.rom.save_original('Write staged ROM edits')
            except (ValueError,OSError) as error:messagebox.showerror('Cannot write ROM',str(error),parent=self)
            self.update_history_controls();self.refresh_draft_state()
        return 'break'

    def remember_editor(self):
        if not self.rom or self.record is None:return
        table,index=self.record
        try:self.ui_context.put(self.rom,'main:'+self.mode,{'table':self.modules[table].name,'record':index,'search':self.search.get(),'scroll':self.canvas.yview()[0]},self.ui_context_ready)
        except OSError:pass

    def prepare_window(self,window,restore=True):
        from ui_common import prepare_window
        return prepare_window(self,window,restore)

    def update_shared_feedback(self):
        if not self.rom or self.record is None:return
        module=self.modules[self.record[0]]
        if module.name=='FE4 Player Weapon Editor' and hasattr(self,'slot_locations'):
            rows=self.slot_locations.rows[self.record[1]+1]
            self.shared_rows=[(row.title,row.target[1:]) for row in rows if row.target[0]=='record']
            self.shared_text.set(f'Slot {self.record[1]+1:02X}: {len(rows)} indexed appearances. Reward and inheritance details are listed below.')
            return
        from usage import UsageIndex
        stamp=id(self.rom.original)
        if self.usage_index is None or self.usage_index.stamp!=stamp:self.usage_index=UsageIndex(self.rom)
        try:values=self.read_draft()
        except ValueError:values=self.rom.values(module,self.record[1])
        self.shared_rows=self.usage_index.for_record(module,self.record[1],values)
        self.shared_text.set(self.usage_index.summary(module,self.record[1],values))

    def show_shared_users(self):
        if not self.rom or self.record is None:return
        from usage import show_users
        self.update_shared_feedback();show_users(self,getattr(self,'shared_rows',[]))

    def explain_selected_field(self,module,field):
        from validation import explain_field
        self.field_help.set(explain_field(module,field))

    def check_current_record(self):
        if not self.rom or self.record is None:
            messagebox.showinfo('Select a record','Open a ROM and select a record to check.')
            return
        from validation import shared_notes
        from validation_window import show_report
        issues=self.update_validation()
        try:values=self.read_draft()
        except ValueError:values=None
        notes=shared_notes(self.rom,self.modules[self.record[0]],self.record[1],self.current_portrait,values)
        notes.append('Reference counts reflect loaded ROM data; unsaved changes and event scripts may change those references.')
        show_report(self,'Current record - '+self.heading.cget('text'),issues,notes)

    def check_structure(self):
        if not self.rom:
            messagebox.showinfo('Open a ROM','Open a ROM to check its pointers.')
            return
        from validation import validate_structure
        from validation_window import show_report
        self.configure(cursor='watch');self.update_idletasks()
        try:issues=validate_structure(self.rom)
        finally:self.configure(cursor='')
        show_report(self,'Map / portrait pointer checks',issues,['Checks the loaded ROM data, including army group structure, all 12 chapter map resources and all 248 portrait graphics/palettes. Unwritten form fields are checked separately by Check record.'])

    def destroy(self):
        if self._validation_job is not None:
            self.after_cancel(self._validation_job)
            self._validation_job=None
        super().destroy()

    def show_history(self):
        if not self.rom:
            messagebox.showinfo('Open a ROM','Open a ROM to see its change history.')
            return
        from history_window import open_history_window
        open_history_window(self)

    def update_history_controls(self):
        for widget,enabled,index in ((self.undo_button,self.rom and self.rom.history.can_undo,0),
                                     (self.redo_button,self.rom and self.rom.history.can_redo,1)):
            widget.config(state='normal' if enabled else 'disabled')
            self.edit_menu.entryconfig(index,state='normal' if enabled else 'disabled')

    def history_step(self,redo):
        if not self.rom or not self.settle():
            return 'break'
        if self.rom.dirty:
            answer=messagebox.askyesnocancel('Staged changes','Save staged ROM changes before undo/redo?')
            if answer is None:
                return 'break'
            if answer:
                try:
                    self.rom.save_original('Save staged edits before undo/redo')
                except (ValueError,OSError) as error:
                    messagebox.showerror('Cannot save ROM',str(error))
                    return 'break'
            else:
                self.rom.data[:]=self.rom.original
        try:
            changed=self.rom.redo() if redo else self.rom.undo()
        except (ValueError,OSError) as error:
            messagebox.showerror('Cannot redo' if redo else 'Cannot undo',str(error))
            return 'break'
        if changed:
            self.refresh_after_history()
            self.status.set(('Redone' if redo else 'Undone')+f' and saved to {self.rom.path.name}. Backup created.')
        self.update_history_controls()
        return 'break'

    def refresh_after_history(self):
        self.usage_index=None
        self.modules=self.editor_modules(self.mode,self.rom)
        self.table.config(values=[m.name.replace('FE4 ','') for m in self.modules])
        if self.record is not None:
            table,index=self.record
            if table<len(self.modules) and index<self.modules[table].count:
                self.table.current(table)
                self.render()
            else:
                self.record=None
                self.apply_button.config(state='disabled')
                self.name_button.config(state='disabled')
                for widget in self.fields_frame.winfo_children():
                    widget.destroy()
        self.populate()
        self.update_history_controls()

    def edit_context(self):
        if self.record is None:
            return 'ROM edit',[]
        table,index=self.record
        module=self.modules[table]
        address=self.rom.address(module,index)
        details=[]
        for field,after in zip(module.fields,self.rom.values(module,index)):
            before=int.from_bytes(self.rom.original[address+field.offset:address+field.offset+field.size],'little',signed=field.signed)
            if before!=after:
                details.append(f'{field.name}: {before} → {after}')
        if self.promotion:
            at=self.promotion['address']
            before=self.rom.original[at];after=self.rom.data[at]
            if before!=after:details.append(f'Promotion Class: {before} → {after}')
        return f'{self.mode}: {module.name} / {self.record_name(module,index)}',details

    def scroll_editor(self, event):
        # Only the character form needs wheel scrolling. Listboxes and popup
        # lists handle their own wheels through Tk's native class bindings.
        if self.mode == 'Army Editor' or not self.body.winfo_ismapped():
            return
        if self.tk.call('grab', 'current'):
            return
        widget = event.widget
        if isinstance(widget, (ttk.Combobox, ttk.Spinbox)):
            return
        path = str(widget)
        canvas_path = str(self.canvas)
        if path != canvas_path and not path.startswith(canvas_path + '.'):
            return
        bounds = self.canvas.bbox('all')
        if not bounds or bounds[3] - bounds[1] <= self.canvas.winfo_height():
            return
        from ui_common import wheel_steps
        steps = wheel_steps(event)
        if steps:
            self.canvas.yview_scroll(steps, 'units')
            return 'break'

    def show_menu(self):
        if self.rom is None:
            self.show_rom_selector();return
        if not self.settle():
            return
        self.top_bar.pack(fill='x',before=self.save_state_label)
        self.file_label.pack(fill='x',before=self.save_state_label)
        self.history_bar.pack(fill='x',before=self.save_state_label)
        self.remember_editor()
        # Discarded field edits must not reappear when reopening the editor.
        if self.record is not None:
            self.render()
        self.navigation.clear()
        self.back_button.config(state='disabled')
        self.body.pack_forget()
        self.rom_selector.pack_forget()
        self.home.pack(fill='both', expand=True, before=self.status_label)
        self.breadcrumb.config(text='  /  Main Menu')
        self.title('FE4Builder — Main Menu')
        self.refresh_draft_state()

    def show_rom_selector(self):
        self.home.pack_forget();self.body.pack_forget();self.history_bar.pack_forget();self.top_bar.pack_forget();self.file_label.pack_forget()
        self.rom_selector.pack(fill='both',expand=True,before=self.status_label)
        self.last_rom_label.config(text=self.last_rom_path or 'No ROM has been opened yet.')
        self.reopen_button.config(state='normal' if self.last_rom_path else 'disabled')
        self.breadcrumb.config(text='  /  ROM Selector')
        self.title('FE4Builder — ROM Selector')

    def edit_name(self, name_id=0):
        from name_window import open_name_window
        return self.prepare_window(open_name_window(self,name_id),restore=False)

    def edit_portrait(self,portrait_id=0,action=None):
        from portrait_window import open_portrait_window
        return self.prepare_window(open_portrait_window(self,portrait_id,action),restore=False)

    def edit_background(self,index=0):
        from background_window import open_background_window
        return self.prepare_window(open_background_window(self,index),restore=False)

    def edit_intro(self):
        from intro_window import open_intro_window
        return self.prepare_window(open_intro_window(self))

    def edit_patches(self):
        from patch_window import open_patch_window
        return open_patch_window(self)

    def edit_stat_bonuses(self,kind='weapon',value=1):
        from bonus_window import open_bonus_window
        return self.prepare_window(open_bonus_window(self,kind,value),restore=False)

    def edit_dialogue(self):
        from dialogue_window import open_dialogue_window
        return self.prepare_window(open_dialogue_window(self))


    def open_audio(self,kind=None,value=None,autoplay=False):
        from audio_window import open_audio_window
        return self.prepare_window(open_audio_window(self,kind,value,autoplay),restore=kind is None)

    def view_ai(self,chapter=None,faction=None,number=None):
        from ai_window import open_ai_window
        return self.prepare_window(open_ai_window(self,chapter,faction,number),restore=chapter is None)

    def edit_events(self,event_id=None):
        from event_command_window import open_event_command_window
        return self.prepare_window(open_event_command_window(self,event_id),restore=event_id is None)

    def edit_reinforcements(self):
        from reinforcement_window import open_reinforcement_window
        return self.prepare_window(open_reinforcement_window(self))

    def edit_conversations(self):
        from conversation_window import open_conversation_window
        return self.prepare_window(open_conversation_window(self))

    def edit_objectives(self):
        from objective_window import open_objective_window
        return self.prepare_window(open_objective_window(self))

    def edit_villages(self):
        from village_window import open_village_window
        return self.prepare_window(open_village_window(self))

    def edit_selected_bonus(self,index):
        field=self.modules[self.record[0]].fields[index]
        kind='weapon' if field.reference=='FE4 Weapon Bonus.txt' else 'ring'
        try:value=self.read_draft()[index]
        except ValueError as error:
            messagebox.showerror('Invalid field value',str(error),parent=self);return
        return self.edit_stat_bonuses(kind,value)

    def edit_army_map(self):
        from map_window import open_map_window
        chapter=self.record[0] if self.mode=='Army Editor' and self.record and self.record[0]<12 else 0
        return self.prepare_window(open_map_window(self,chapter,mode='army'),restore=not (self.mode=='Army Editor' and self.record is not None))

    def edit_map(self):
        from map_window import open_map_window
        chapter=self.record[0] if self.mode=='Army Editor' and self.record and self.record[0]<12 else 0
        return self.prepare_window(open_map_window(self,chapter),restore=not (self.mode=='Army Editor' and self.record is not None))

    def update_portrait_preview(self,module,index):
        self.portrait_frame.pack_forget()
        self.current_portrait=None
        if not self.rom:
            return
        from portraits import Portrait,character_portrait_id
        from portrait_window import photo
        values={field.name:value for field,value in zip(module.fields,self.rom.values(module,index))}
        character=next((values[key] for key in ('Char no.','Chararacter Number','Character Number') if key in values),None)
        try:
            if character is not None:
                portrait_id=character_portrait_id(self.rom,character,values.get('Class'))
            elif self.mode=='Class Editor':
                offset=0xb9ff8+self.rom.header+index*2
                portrait_id=int.from_bytes(self.rom.data[offset:offset+2],'little')
            else:
                return
            model=Portrait(self.rom,portrait_id)
            self.current_portrait=portrait_id
            self.portrait_label.image=photo(self,model.rows,model.colors,2)
            self.portrait_label.config(image=self.portrait_label.image)
            self.portrait_info.config(text=f'Portrait {portrait_id:02X}\n48 × 64 pixels')
            self.portrait_button.config(state='normal')
            self.portrait_import.config(state='normal')
            self.portrait_export.config(state='normal')
        except ValueError as error:
            self.portrait_label.config(image='')
            self.portrait_info.config(text=f'Portrait preview unavailable: {error}')
            self.portrait_button.config(state='disabled')
            self.portrait_import.config(state='disabled')
            self.portrait_export.config(state='disabled')
        self.portrait_frame.pack(fill='x',pady=(0,8),before=self.canvas)

    def edit_selected_name(self):
        if not self.record or not self.rom or not self.settle():
            return
        table,index = self.record
        module = self.modules[table]
        values = self.rom.values(module,index)
        name_id = next((value for field,value in zip(module.fields,values) if field.name == 'Char Name'),0)
        self.edit_name(name_id)

    def settle_link(self):
        if not self.rom or self.record is None or not self.settle():
            return False
        if self.pending():
            # Discard was explicitly chosen; clear the draft before navigating.
            self.render()
        return True

    def open_linked_portrait(self):
        if not self.settle_link():
            return
        self.update_portrait_preview(self.modules[self.record[0]],self.record[1])
        if self.current_portrait is not None:
            self.edit_portrait(self.current_portrait)

    def navigation_context(self):
        table,index=self.record
        return self.mode,self.modules[table].name,index,self.search.get()

    def go_to_record(self,mode,module_name,index,query=''):
        modules=self.editor_modules(mode,self.rom)
        table=next((i for i,m in enumerate(modules) if m.name==module_name),None)
        if table is None or not 0<=index<modules[table].count:
            raise ValueError('The linked record is outside its editor table.')
        if not self.show_editor(mode,linked=True):
            return False
        self.record=None
        self.table.current(table)
        self.search.set(query)
        self.populate()
        if index not in self.visible:
            self.search.set('');self.populate()
        self.list.selection_clear(0,'end')
        position=self.visible.index(index)
        self.list.selection_set(position);self.list.see(position)
        self.record=table,index
        self.render()
        return True

    def open_linked_field(self,field_index):
        if not self.settle_link():
            return
        module=self.modules[self.record[0]]
        field=module.fields[field_index]
        value=self.rom.values(module,self.record[1])[field_index]
        from linked_editors import field_target
        try:
            target=field_target(self.rom,field,value)
            if target is None:
                self.status.set('Nothing is assigned to this equipment slot.')
                return
            origin=self.navigation_context()
            if self.go_to_record(*target):
                self.navigation.append(origin)
                self.back_button.config(state='normal')
                self.status.set('Opened linked record. Back returns to the previous editor.')
        except (ValueError,OSError) as error:
            messagebox.showerror('Cannot open linked editor',str(error))

    def link_back(self):
        if not self.navigation or not self.settle_link():
            return
        try:
            if self.go_to_record(*self.navigation[-1]):
                self.navigation.pop()
                self.back_button.config(state='normal' if self.navigation else 'disabled')
        except (ValueError,OSError) as error:
            messagebox.showerror('Cannot return to editor',str(error))

    def show_editor(self, mode,linked=False):
        if not self.settle():
            return False
        self.remember_editor()
        if not linked:
            self.navigation.clear()
            self.back_button.config(state='disabled')
        self.top_bar.pack(fill='x',before=self.save_state_label)
        self.file_label.pack(fill='x',before=self.save_state_label)
        self.history_bar.pack(fill='x',before=self.save_state_label)
        self.mode = mode
        self.record = None
        try:
            modules = self.editor_modules(mode, self.rom)
        except (ValueError, OSError) as error:
            messagebox.showerror('Cannot load editor', str(error))
            self.show_menu()
            return False
        self.modules = modules
        self.table.config(values=[m.name.replace('FE4 ', '') for m in self.modules])
        self.table.current(0)
        self.table_label.config(text={'Character Editor': 'Character table', 'Class Editor': 'Class table',
                                      'Army Editor': 'Chapter / advanced table'}.get(mode, 'Module / table'))
        self.search.set('')
        self.populate()
        self.home.pack_forget()
        self.rom_selector.pack_forget()
        self.body.pack(fill='both', expand=True, padx=12, pady=10, before=self.status_label)
        self.breadcrumb.config(text=f'  /  {mode}')
        self.title(f'FE4Builder — {mode}')
        if self.rom:
            context=self.ui_context.get(self.rom,'main:'+mode) if not linked else {}
            table=next((i for i,m in enumerate(self.modules) if m.name==context.get('table')),0)
            self.table.current(table);self.search.set(context.get('search',''));self.populate()
            index=context.get('record',0)
            if not isinstance(index,int) or not 0<=index<self.modules[table].count:index=0
            if self.modules[table].count:
                self.record=table,index;self.render()
                if index in self.visible:self.list.selection_set(self.visible.index(index));self.list.see(self.visible.index(index))
                self.canvas.yview_moveto(context.get('scroll',0))
        else:
            for child in self.fields_frame.winfo_children():
                child.destroy()
            self.heading.config(text='Open a ROM to begin')
            self.apply_button.config(state='disabled')
        return True

    def pending(self):
        return self.record is not None and ([var.get() for var, _ in self.editors] != self.loaded or
                bool(self.promotion and self.promotion['var'].get()!=self.promotion['loaded']))

    def promotion_plan(self,values):
        from promotions import plan
        promotion=self.promotion
        text=promotion['var'].get()
        try:value=promotion['options'][text] if text in promotion['options'] else number(text.strip())
        except ValueError:raise ValueError('Promotion Class: choose a class or None.')
        return plan(self.rom,self.modules[self.record[0]],values,promotion['id'],value)

    def load_promotion(self):
        if not self.promotion:return
        from promotions import character_id,address
        module=self.modules[self.record[0]]
        identity=character_id(module,self.rom.values(module,self.record[1]))
        if identity is None:return
        promotion=self.promotion;promotion['id']=identity
        promotion['address']=address(self.rom,identity)
        value=self.rom.data[promotion['address']]
        text=next((label for label,key in promotion['options'].items() if key==value),str(value))
        promotion['var'].set(text);promotion['loaded']=text

    @staticmethod
    def editor_modules(mode, rom):
        if mode == 'Character Editor':
            return character_modules()
        if mode == 'Class Editor':
            return class_modules()
        if mode == 'Army Editor':
            return army_modules(rom)
        return category_modules(mode)

    def settle(self):
        if not self.pending():
            return True
        from ui_common import ask_unsaved
        answer = ask_unsaved(self, 'Write the current record changes directly to the opened ROM?')
        return self.write_original() if answer else answer is False

    def open_rom(self,path=None):
        if not self.settle():
            return
        if self.rom and self.rom.dirty and not messagebox.askyesno('Unsaved ROM', 'Discard the unsaved ROM changes and open another file?'):
            return
        from rom_selector import initial_directory,remember
        selecting=bool(self.rom_selector.winfo_manager())
        if path is None:
            path = filedialog.askopenfilename(parent=self,title='Choose a Fire Emblem 4 ROM',initialdir=initial_directory(self.last_rom_path), filetypes=[('SNES ROM', '*.sfc *.smc'), ('All files', '*')])
        if not path:
            return
        try:
            rom = Rom(path)
            modules = self.editor_modules(self.mode, rom)
            for module in modules:
                if module.count:
                    rom.address(module, module.count-1)
        except (OSError, ValueError) as error:
            messagebox.showerror('Cannot open ROM', str(error))
            return
        if not self.close_editor_windows():return False
        # Closing an editor can save to this same path. Load again so reopening
        # the ROM cannot replace those just-saved bytes with the earlier read.
        try:
            rom=Rom(path);modules=self.editor_modules(self.mode,rom)
            for module in modules:
                if module.count:rom.address(module,module.count-1)
        except (OSError,ValueError) as error:
            messagebox.showerror('Cannot open ROM',str(error));return False
        self.remember_editor()
        self.rom = rom
        self.ui_context_ready=True;self.usage_index=None
        self.navigation.clear()
        self.back_button.config(state='disabled')
        self.update_history_controls()
        self.modules = modules
        self.table.config(values=[m.name.replace('FE4 ', '') for m in modules])
        self.table.current(0)
        self.record = None
        self.file_label.config(text=f'{rom.path.name}  |  {len(rom.data):,} bytes  |  Copier header: {rom.header} bytes')
        self.populate()
        self.list.selection_set(0)
        self.select()
        self.last_rom_path=str(rom.path.resolve())
        try:remember(rom.path)
        except OSError as error:self.status.set(f'ROM opened, but its location could not be remembered: {error}')
        if selecting:self.show_menu()
        return True

    def populate(self):
        module = self.modules[self.table.current()]
        query = self.search.get().lower()
        names = [self.record_name(module,i) for i in range(module.count)]
        first=1 if module.name=='FE4 Player Weapon Editor' else 0
        self.visible = [i for i, name in enumerate(names) if query in f'{i+first:02X} {name}'.lower()]
        self.list.delete(0, 'end')
        for i in self.visible:
            self.list.insert('end', f'{i+first:02X}  {names[i]}')

    def record_name(self, module, index):
        if self.rom and module.name=='FE4 Player Weapon Editor':
            from item_art import ItemArt
            item=self.rom.values(module,index)[0]
            if item==255:return 'Nothing'
            engine=getattr(self,'item_art',None)
            if engine is None or engine.rom is not self.rom:
                engine=ItemArt(self.rom);self.item_art=engine
            try:return engine.name(item)
            except ValueError:return module.fields[0].options.get(item,f'Unknown item {item:02X}')
        if self.rom:
            from names import NameEditor
            field_index = next((i for i,f in enumerate(module.fields)
                                if f.reference=='FE4 Character Name Numbers.txt' or f.name=='Char Name'),None)
            if field_index is not None:
                field=module.fields[field_index]
                name_id=self.rom.values(module,index)[field_index]
                try:
                    return NameEditor(self.rom,name_id).current
                except ValueError:
                    return field.options.get(name_id) or f'Unknown name 0x{name_id:04X}'
        return module.names[index]

    def change_table(self, event=None):
        if not self.settle():
            self.table.current(self.record[0])
            return
        self.record = None
        self.search.set('')
        self.populate()
        if self.rom:
            self.list.selection_set(0)
            self.select()

    def select(self, event=None):
        selection = self.list.curselection()
        if not self.rom or not selection:
            return
        target = (self.table.current(), self.visible[selection[0]])
        if target == self.record:
            return
        if not self.settle():
            self.list.selection_clear(0, 'end')
            if self.record and self.record[1] in self.visible:
                self.list.selection_set(self.visible.index(self.record[1]))
            return
        self.record = target
        self.render()

    def render(self):
        self._rendering=True;self.field_controls=[];self.current_issues=[]
        if self._validation_job is not None:
            self.after_cancel(self._validation_job)
            self._validation_job=None
        self.field_help.set('Hover over or focus a field for an explanation. Check record shows shared-data references.')
        table, index = self.record
        module = self.modules[table]
        self.name_button.config(state='normal' if any(f.name=='Char Name' for f in module.fields) else 'disabled')
        self.map_button.config(state='normal' if self.mode=='Army Editor' and table<12 else 'disabled')
        self.sprite_button.config(state='normal' if self.mode=='Class Editor' else 'disabled')
        self.update_portrait_preview(module,index)
        from item_art import ItemArt
        self.item_art=ItemArt(self.rom)
        self.equipment_icons={}
        self.item_browser_button.pack_forget()
        if module.name=='FE4 Item Sprite Editor by Lorena':
            self.item_preview_view.current(1)
        elif module.name=='FE4 Player Weapon Editor':
            self.item_preview_view.current(0)
        if self.mode=='Item Editor':
            self.item_browser_button.configure(state='normal')
            self.item_browser_button.pack(side='left',padx=8)
        for child in self.fields_frame.winfo_children():
            child.destroy()
        self.editors = []
        self.promotion=None
        self.linked_buttons = {}
        self.heading.config(text=self.record_name(module,index))
        self.address.config(text=f'Record {index:02X}  •  File address 0x{self.rom.address(module, index):06X}  •  Size {module.stride} bytes')
        if module.name=='FE4 Player Weapon Editor':
            self.heading.config(text=f'{index+1:02X} {self.record_name(module,index)}')
            self.address.config(text=f'Player item slot {index+1:02X} · File address 0x{self.rom.address(module,index):06X} · 1 byte')
        groups = {}
        counts = {}
        self.advanced_shell=ttk.Frame(self.fields_frame)
        self.advanced_toggle=ttk.Button(self.advanced_shell,text='▶ Advanced / raw data',command=self.toggle_advanced)
        self.advanced_toggle.pack(anchor='w')
        self.advanced_body=ttk.Frame(self.advanced_shell)
        for field_index,(field, value) in enumerate(zip(module.fields, self.rom.values(module, index))):
            advanced=field.name in ('Character Type','Char no.','Char Name','Unit Number','Unknown','Address','Relative group pointer') or 'pointer' in field.name.lower()
            group = ('Base stats' if field.name.startswith('Base ') else 'Growth rates' if 'Growth' in field.name else
                     'Skills & holy blood' if field.name.startswith(('Skills', 'Blood')) else
                     'Class skills' if field.name.startswith('Class Skills') else
                     'Weapon ranks' if field.name.endswith(' Rank') else
                     'Equipment' if field.name.startswith('Equipment') else 'Identity & settings')
            if self.mode == 'Army Editor':
                group = 'Deployment' if module.addresses is not None else 'Army pointers (raw values)'
            if group not in groups:
                box = ttk.LabelFrame(self.fields_frame, text=group, padding=10)
                box.pack(fill='x', pady=(0, 10))
                for col in ((1,) if group=='Equipment' else (1,3)):
                    box.columnconfigure(col, weight=1)
                groups[group], counts[group] = box, 0
            if advanced:
                group='Advanced: '+group
                if group not in groups:
                    groups[group]=ttk.LabelFrame(self.advanced_body,text=group.removeprefix('Advanced: '),padding=10);groups[group].pack(fill='x',pady=6)
                    groups[group].columnconfigure(1,weight=1);groups[group].columnconfigure(3,weight=1);counts[group]=0
            box = groups[group]
            slot = counts[group]
            counts[group] += 1
            row,col=(slot,0) if group=='Equipment' else (slot//2,(slot%2)*2)
            display=field.name+(' (%)' if 'Growth' in field.name else ' (stars)' if field.name=='Leadership' else '')
            label=ttk.Label(box,text=display)
            label.grid(row=row,column=col,sticky='w',padx=(0,8),pady=4)
            label.bind('<Enter>',lambda e,m=module,f=field:self.explain_selected_field(m,f))
            from linked_editors import REFERENCES
            linked=field.reference in REFERENCES
            if linked:
                label.configure(foreground='#1769a5',cursor='hand2')
                label.bind('<Button-1>',lambda e,i=field_index:self.open_linked_field(i))
            control=ttk.Frame(box)
            control.grid(row=row,column=col+1,sticky='ew',padx=(0,14),pady=4)
            equipment=field.reference in ('FE4 Player Equipment.txt','FE4 Weapon List.txt')
            value_column=1 if equipment else 0
            control.columnconfigure(value_column,weight=1)
            if equipment:
                icon=ttk.Label(control,width=4,cursor='hand2')
                icon.bind('<Button-1>',lambda e,i=field_index:self.open_linked_field(i))
                icon.grid(row=0,column=0,padx=(0,6))
                self.equipment_icons[field_index]=icon
            options = {f'{label or "(unnamed)"} (0x{key:X})': key for key, label in self.rom.field_options(field).items()
                       if not field.name.startswith(('Skills', 'Class Skills')) or (label.strip() and
                           ('Unused (' not in label and 'Unknown flag (' not in label or key == value))}
            if field.name.startswith(('Skills', 'Class Skills')):
                options = dict(sorted(options.items(), key=lambda item: (item[1].bit_count(), item[1])))
            text = next((label for label, key in options.items() if key == value), str(value))
            var = tk.StringVar(value=text)
            if field.name.startswith(('Skills','Class Skills','Blood')):
                from ui_controls import FlagPicker
                widget=FlagPicker(control,var,options,field)
            elif options:
                widget = ttk.Combobox(control, textvariable=var, values=list(options), width=48 if field.name in ('Stat Bonus','Stat Bonuses') else 18 if equipment else 24)
            else:
                minimum = -(1 << (field.size*8-1)) if field.signed else 0
                maximum = (1 << (field.size*8-int(field.signed)))-1
                widget = ttk.Spinbox(control, textvariable=var, from_=minimum, to=maximum, width=9)
            widget.grid(row=0,column=value_column,sticky='ew')
            widget.bind('<FocusIn>',lambda e,m=module,f=field:self.explain_selected_field(m,f))
            widget.bind('<Enter>',lambda e,m=module,f=field:self.explain_selected_field(m,f))
            var.trace_add('write',self.schedule_validation)
            if linked:
                button=ttk.Button(control,text='Edit...',width=6,command=lambda i=field_index:self.open_linked_field(i))
                button.grid(row=0,column=value_column+1,padx=(4,0))
                self.linked_buttons[field.name]=button
            if equipment:
                ttk.Button(control,text='Browse...',command=lambda f=field,v=var,o=options:self.browse_equipment(f,v,o)).grid(row=0,column=value_column+2,padx=(4,0))
            if self.mode=='Item Editor' and field.name in ('Stat Bonus','Stat Bonuses'):
                ttk.Button(control,text='Edit bonuses...',command=lambda i=field_index:self.edit_selected_bonus(i)).grid(row=0,column=value_column+1,padx=(4,0))
            multiplier=1000 if 'Money' in field.name and '*1000' in field.name else 100 if 'Gold' in field.name and ('100' in field.name) else None
            if multiplier:
                money=tk.StringVar()
                def show_money(*_,v=var,out=money,m=multiplier):
                    try:out.set(f'{number(v.get())*m:,} gold')
                    except ValueError:out.set('Invalid amount')
                var.trace_add('write',show_money);show_money()
                ttk.Label(control,textvariable=money).grid(row=2,column=0,columnspan=3,sticky='w')
            self.editors.append((var, options))
            issue=ttk.Label(control,wraplength=300,foreground='#a12c20')
            self.field_controls.append({'widget':widget,'label':label,'var':var,'name':field.name,'display':display,'issue':issue,'advanced':advanced})
        if self.mode=='Character Editor':
            from promotions import character_id,address,options as promotion_options
            identity=character_id(module,self.rom.values(module,index))
            if identity is not None:
                box=groups['Identity & settings']
                slot=counts['Identity & settings'];row,col=slot//2,(slot%2)*2
                label=ttk.Label(box,text='Promotion Class')
                label.grid(row=row,column=col,sticky='w',padx=(0,8),pady=4)
                choices={f'{name} (0x{key:X})':key for key,name in promotion_options().items()}
                variable=tk.StringVar()
                widget=ttk.Combobox(box,textvariable=variable,values=list(choices),width=24)
                widget.grid(row=row,column=col+1,sticky='ew',padx=(0,14),pady=4)
                self.promotion={'id':identity,'address':address(self.rom,identity),'var':variable,'options':choices,'loaded':'','widget':widget}
                self.load_promotion()
                variable.trace_add('write',self.schedule_validation)
                help_text='Character-specific promotion target, stored in a separate table. None disables normal promotion. The destination class sets the required level (normally 20). This field is saved together with this character’s other edits.'
                for control in (label,widget):
                    control.bind('<Enter>',lambda e,text=help_text:self.field_help.set(text))
                    control.bind('<FocusIn>',lambda e,text=help_text:self.field_help.set(text))
        self.loaded = [var.get() for var, _ in self.editors]
        self.advanced_shell.pack(fill='x',pady=6)
        if self.advanced_expanded:self.advanced_body.pack(fill='x');self.advanced_toggle.config(text='▼ Advanced / raw data')
        if self.mode == 'Army Editor':
            ttk.Label(self.fields_frame, text='Deployments follow the ROM’s group pointers, grouped by chapter.\nList labels show group ID, deployment group and character.\nAdvanced pointers are relative to file offset 0x1C000 (plus copier header).', style='Subtitle.TLabel').pack(anchor='w', pady=8)
        elif self.mode == 'Class Editor':
            ttk.Label(self.fields_frame, text='Class changes affect all characters using this class.\nPromotion-Into Level is the minimum character level to promote into this destination class (normally 20).\nGold is stored in units of 100. Weapon ranks use the ROM’s A / B / C / unavailable values.', style='Subtitle.TLabel').pack(anchor='w', pady=8)
        elif self.mode == 'Character Editor' and table >= 4:
            ttk.Label(self.fields_frame, text='Children inherit stats, growths, skills and holy blood from their parents.\nThis table edits only their stored starting fields.', style='Subtitle.TLabel').pack(anchor='w', pady=8)
        elif module.name=='FE4 Player Weapon Editor':
            self.show_item_slot_locations(index+1)
        elif self.mode in EDITOR_CATEGORIES:
            ttk.Label(self.fields_frame, text='Fields and labels follow the selected Nightmare module.\nPointer / graphics tables edit data values; they do not preview or import graphics.\nNumbers accept decimal or 0x hexadecimal. Table sizes remain fixed.', style='Subtitle.TLabel').pack(anchor='w', pady=8)
        self._rendering=False
        self.update_validation()
        self.canvas.yview_moveto(0)

    def show_item_slot_locations(self,slot):
        import hashlib
        from player_items import SlotLocations
        stamp=hashlib.sha256(self.rom.data).digest()
        if getattr(self,'slot_location_stamp',None)!=stamp:
            self.slot_locations=SlotLocations(self.rom);self.slot_location_stamp=stamp
        index=self.slot_locations
        panel=ttk.LabelFrame(self.fields_frame,text=f'Appearances of player item slot {slot:02X}',padding=10)
        panel.pack(fill='x',pady=8)
        ttk.Label(panel,text=index.summary(slot),wraplength=690,justify='left').pack(anchor='w',pady=(0,8))
        self.slot_appearance_rows=index.rows[slot]
        for location in self.slot_appearance_rows:
            row=ttk.Frame(panel);row.pack(fill='x',pady=6)
            ttk.Button(row,text='Go to location',command=lambda target=location:self.open_item_slot_location(target)).pack(side='right',padx=(8,0))
            ttk.Label(row,text=location.title,wraplength=540,justify='left').pack(anchor='w')
            ttk.Label(row,text=location.note,wraplength=540,justify='left',style='Subtitle.TLabel').pack(anchor='w')
        if not self.slot_appearance_rows:
            ttk.Label(panel,text='No appearances found in the decoded inventories, drops, rewards or inheritance routes.').pack(anchor='w')
        ttk.Label(panel,text='Locations follow the current ROM. ASM callbacks and actual save-state ownership/pairings are not simulated.',wraplength=690,style='Subtitle.TLabel').pack(anchor='w',pady=(10,0))
        if index.warnings:
            ttk.Button(panel,text=f'Coverage notes ({len(index.warnings)})',command=self.show_item_slot_coverage).pack(anchor='w',pady=6)

    def show_item_slot_coverage(self):
        dialog=tk.Toplevel(self);dialog.title('Player item slot coverage');dialog.geometry('850x480')
        area=tk.Text(dialog,wrap='word');area.pack(fill='both',expand=True)
        area.insert('end','These paths could not be fully decoded; their slot appearances may be incomplete.\n\n'+'\n'.join(self.slot_locations.warnings));area.config(state='disabled')
        self.prepare_window(dialog,restore=False)

    def open_item_slot_location(self,location):
        if not self.settle_link():return False
        target=location.target;origin=self.navigation_context()
        if target[0]=='record':
            if self.go_to_record(*target[1:]):
                self.navigation.append(origin);self.back_button.config(state='normal')
                if location.address is not None:
                    module=self.modules[self.record[0]]
                    base=self.rom.address(module,self.record[1])
                    field=next((i for i,f in enumerate(module.fields) if base+f.offset==location.address),None)
                    if field is not None:
                        self.update_idletasks();widget=self.field_controls[field]['widget'];widget.focus_set()
                        self.canvas.yview_moveto(max(0,widget.winfo_rooty()-self.fields_frame.winfo_rooty()-20)/max(1,self.fields_frame.winfo_height()))
                return True
            return False
        if target[0]=='village':
            dialog=self.edit_villages()
            if dialog is None:return False
            dialog.chapter.current(target[1]);dialog.populate()
            if not dialog.load(target[2]):return False
            dialog.list.selection_clear(0,'end');dialog.list.selection_set(dialog.visible.index(target[2]));dialog.list.see(dialog.visible.index(target[2]))
            return True
        if target[0]=='event':
            dialog=self.edit_events(target[2])
            if dialog is None:return False
            return dialog.focus_event(target[2],target[3])
        return False

    def toggle_advanced(self):
        self.advanced_expanded=not self.advanced_expanded
        if self.advanced_expanded:self.advanced_body.pack(fill='x')
        else:self.advanced_body.pack_forget()
        self.advanced_toggle.config(text=('▼' if self.advanced_expanded else '▶')+' Advanced / raw data')

    def apply(self):
        if self.record is None:
            return True
        before = bytes(self.rom.data)
        try:
            values = self.read_draft()
            issues=self.update_validation()
            errors=[f'{i.field}: {i.message}' for i in issues if i.severity=='Error']
            if errors:
                raise ValueError('Validation failed:\n'+'\n'.join(errors))
            table, index = self.record
            promotion_edit=self.promotion_plan(values) if self.promotion and self.promotion['var'].get()!=self.promotion['loaded'] else None
            self.rom.write(self.modules[table], index, values)
            if promotion_edit:
                at,value=promotion_edit;self.rom.data[at]=value
            if self.mode == 'Army Editor':
                # Validate pointer edits before saving and refresh affected labels/addresses.
                refreshed = army_modules(self.rom)
        except (ValueError, OverflowError) as error:
            self.rom.data[:] = before
            messagebox.showerror('Invalid field value', str(error) + '\nEnter a decimal number, 0x hexadecimal value, or select a dropdown option.')
            return False
        self.usage_index=None
        self.loaded = [var.get() for var, _ in self.editors]
        if self.promotion:self.promotion['loaded']=self.promotion['var'].get()
        if self.mode == 'Army Editor':
            self.modules = refreshed
            self.populate()
        self.status.set('Record staged in memory — save to keep your changes.')
        return True

    def write_original(self):
        if not self.rom or self.record is None:
            return True
        before = bytes(self.rom.data)
        loaded = self.loaded[:]
        promotion_loaded=self.promotion['loaded'] if self.promotion else None
        if not self.apply():
            return False
        try:
            description,details=self.edit_context()
            self.rom.save_original(description,details)
        except (OSError, ValueError) as error:
            self.rom.data[:] = before
            self.loaded = loaded
            if self.promotion:self.promotion['loaded']=promotion_loaded
            messagebox.showerror('Cannot write ROM', str(error))
            self.status.set('Write failed — the current fields remain unsaved.')
            self.refresh_draft_state()
            return False
        self.status.set(f'Written directly to {self.rom.path.name}')
        if self.modules[self.record[0]].name=='FE4 Player Weapon Editor':
            selected=self.record[1]
            self.populate()
            if selected in self.visible:
                self.list.selection_set(self.visible.index(selected));self.list.see(self.visible.index(selected))
            self.render()
        self.update_equipment_visuals()
        self.update_history_controls()
        self.load_promotion()
        self.refresh_draft_state()
        return True

    def reload(self):
        if self.record is not None and (not self.pending() or messagebox.askyesno('Reload character', 'Discard the unwritten field changes?')):
            self.render()

    def save(self):
        if not self.rom:
            messagebox.showinfo('Open a ROM', 'Open a FE4 ROM first.')
            return
        path = filedialog.asksaveasfilename(initialdir=self.rom.path.parent, initialfile=self.rom.path.stem + '_edited.sfc', defaultextension='.sfc', filetypes=[('SNES ROM', '*.sfc *.smc')])
        if path:
            before=bytes(self.rom.data);loaded=self.loaded[:];modules=self.modules
            selection=self.list.curselection();scroll=self.list.yview()[0]
            promotion_loaded=self.promotion['loaded'] if self.promotion else None
            try:
                if not self.apply():return
                self.rom.save_copy(path)
                self.status.set(f'Copy saved: {path}. Still editing {self.rom.path.name}; original-file draft is unchanged.')
            except (OSError, ValueError) as error:
                messagebox.showerror('Cannot save ROM', str(error))
            finally:
                self.rom.data[:]=before;self.loaded=loaded;self.modules=modules
                if self.promotion:self.promotion['loaded']=promotion_loaded
                self.usage_index=None
                if self.mode=='Army Editor':
                    self.populate()
                    for selected in selection:
                        if selected<self.list.size():self.list.selection_set(selected)
                    self.list.yview_moveto(scroll)
                self.refresh_draft_state()

    def close_editor_windows(self):
        for window in reversed(tuple(self.editor_windows)):
            if not window.winfo_exists():continue
            close=getattr(window,'close',None)
            if callable(close):close()
            else:
                command=window.protocol('WM_DELETE_WINDOW')
                if command:window.tk.call(command)
                else:window.destroy()
            if window.winfo_exists():return False
        return True

    def close(self):
        if not self.settle():
            return
        if not self.close_editor_windows():return
        if self.rom and self.rom.dirty and not messagebox.askyesno('Unsaved ROM', 'Exit and discard the unsaved ROM changes?'):
            return
        self.remember_editor();self.destroy()

if __name__ == '__main__':
    App().mainloop()
