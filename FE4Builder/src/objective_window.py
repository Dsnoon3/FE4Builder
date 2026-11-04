from ui_common import ask_unsaved
"""Existing chapter objective and global defeat settings with normal ROM history."""
import tkinter as tk
from tkinter import ttk,messagebox
from objectives import Objective,DefeatRule,catalogue
from conversations import character_names
from rom import character_modules
from events import CHAPTERS,catalogue as event_catalogue

KINDS={'Seize castle':2,'Unit defeated':15}
FACTIONS={f'{i} — '+('Player' if i==0 else 'Chapter faction') :i for i in range(7)}
FACTIONS['Any faction']=65535

class ObjectiveWindow(tk.Toplevel):
    def __init__(self,app):
        super().__init__(app);self.app=app;self.rom=app.rom;self.current=None;self.model=None;self.defeat=None
        self.names=character_names(self.rom);self.unit_options={f'${key:04X} — {name}':key for key,name in sorted(self.names.items()) if key>0}
        self.unit_options['$FFFF — Any character']=65535
        self.title('FE4Builder — Objectives & Progression');self.geometry('1200x800');self.minsize(1040,700)
        self.transient(app);self.grab_set()
        top=ttk.Frame(self,padding=12);top.pack(fill='x')
        ttk.Label(top,text='Objectives & Progression',style='Title.TLabel').pack(side='left')
        ttk.Button(top,text='Write to ROM',command=self.save).pack(side='right')
        ttk.Button(top,text='Save & Launch (F5)',command=self.launch).pack(side='right',padx=8)
        body=ttk.Panedwindow(self,orient='horizontal');body.pack(fill='both',expand=True,padx=12,pady=8)
        left=ttk.Frame(body);body.add(left,weight=1)
        self.chapter=ttk.Combobox(left,state='readonly',values=CHAPTERS);self.chapter.current(0);self.chapter.pack(fill='x')
        self.chapter.bind('<<ComboboxSelected>>',self.change_chapter)
        frame=ttk.Frame(left);frame.pack(fill='both',expand=True,pady=8)
        self.list=tk.Listbox(frame,width=37,exportselection=False);scroll=ttk.Scrollbar(frame,command=self.list.yview)
        scroll.pack(side='right',fill='y');self.list.config(yscrollcommand=scroll.set);self.list.pack(fill='both',expand=True)
        self.list.bind('<<ListboxSelect>>',self.select)
        right=ttk.Frame(body,padding=(12,0));body.add(right,weight=3)
        self.heading=tk.StringVar();ttk.Label(right,textvariable=self.heading,font=('Segoe UI',12,'bold'),wraplength=720).pack(anchor='w',pady=(0,6))
        self.tabs=ttk.Notebook(right);self.tabs.pack(fill='both',expand=True)
        from ui_common import scrollable_tab
        edit=scrollable_tab(self.tabs,'Objective & progression')
        self.reference=self.text_tab('Conditions / actions (reference)')
        self.info=tk.StringVar();ttk.Label(edit,textvariable=self.info,wraplength=680).pack(anchor='w',pady=(0,8))
        fields=ttk.LabelFrame(edit,text='Selected trigger',padding=10);fields.pack(fill='x')
        self.kind=tk.StringVar();self.faction=tk.StringVar();self.castle=tk.StringVar();self.unit=tk.StringVar()
        self.boxes=[]
        for row,(label,var,options) in enumerate([('Condition',self.kind,list(KINDS)),('Faction',self.faction,list(FACTIONS)),('Castle',self.castle,[]),('Defeated character',self.unit,list(self.unit_options))]):
            ttk.Label(fields,text=label).grid(row=row,column=0,sticky='w',padx=(0,12),pady=4)
            box=ttk.Combobox(fields,textvariable=var,state='readonly',values=options,width=45);box.grid(row=row,column=1,sticky='ew',pady=4);self.boxes.append(box)
        fields.columnconfigure(1,weight=1);self.boxes[0].bind('<<ComboboxSelected>>',self.change_kind)
        self.progression=tk.StringVar();ttk.Label(edit,textvariable=self.progression,wraplength=680).pack(anchor='w',pady=10)
        global_frame=ttk.LabelFrame(edit,text='Global defeat rule — applies to both generations',padding=10);global_frame.pack(fill='x')
        self.slot=tk.StringVar();self.slot_options=self.roster_options()
        self.slot_box=ttk.Combobox(global_frame,textvariable=self.slot,state='readonly',values=list(self.slot_options),width=66)
        self.slot_box.pack(fill='x')
        ttk.Label(global_frame,text='Losing a player unit in this roster slot triggers game over. Slot 1 is Sigurd / Seliph.\n'
                  'Changing it replaces that rule in every chapter. Scripted deaths can bypass this handler;\n'
                  'other defeat conditions and game-over messages remain unchanged.',wraplength=680).pack(anchor='w',pady=(6,0))
        self.help=tk.StringVar(value='▶ Field help / limitations')
        ttk.Button(edit,textvariable=self.help,command=self.toggle_help).pack(anchor='w',pady=(10,0))
        self.help_label=ttk.Label(edit,text='Only an existing six-byte trigger is changed. Its completion flag and linked story script\n'
                  'are preserved. Seize uses faction + castle; Unit defeated uses character + faction.\n'
                  'Intermediate captures, recruitment, map changes and other gates can still be required.\n'
                  'Changing a chapter-ending trigger does not rewrite dialogue, move units or reorder chapters.\n'
                  'Test edits in-game; save states may already contain loaded event conditions.',wraplength=680,justify='left')
        controls=ttk.Frame(right);controls.pack(fill='x',pady=8)
        for label,command in [('Reload',self.reload),('Undo ROM',lambda:self.history(False)),('Redo ROM',lambda:self.history(True)),('View linked event…',self.view_event),('Edit dialogue…',self.open_dialogue)]:
            ttk.Button(controls,text=label,command=command).pack(side='left',padx=(0,6))
        self.status=tk.StringVar();ttk.Label(self,textvariable=self.status,relief='sunken',padding=8,wraplength=1120).pack(fill='x',side='bottom')
        self.protocol('WM_DELETE_WINDOW',self.close);self.bind('<F5>',lambda _:self.launch());self.populate()

    def text_tab(self,title):
        frame=ttk.Frame(self.tabs);self.tabs.add(frame,text=title)
        text=tk.Text(frame,wrap='word',font=('Consolas',10),state='disabled');scroll=ttk.Scrollbar(frame,command=text.yview)
        scroll.pack(side='right',fill='y');text.config(yscrollcommand=scroll.set);text.pack(fill='both',expand=True);return text

    def roster_options(self):
        groups={i:[] for i in range(1,25)}
        for module in character_modules():
            number=next((i for i,f in enumerate(module.fields) if f.name=='Unit Number'),None)
            identity=next((i for i,f in enumerate(module.fields) if f.reference=='FE4 Character Numbers.txt'),None)
            if number is None or identity is None:continue
            for index in range(module.count):
                values=self.rom.values(module,index);slot=values[number];name=self.names.get(values[identity])
                if slot in groups and name and name not in groups[slot]:groups[slot].append(name)
        return {f'{slot:02} — '+(' / '.join(names) or 'Roster slot'):slot for slot,names in groups.items()}

    def name(self,number):return 'Any character' if number==65535 else self.names.get(number,f'Character ${number:04X}')

    def label(self,index):
        e=catalogue()['entries'][index];at=e['address']+self.rom.header;kind=self.rom.data[at]
        a=int.from_bytes(self.rom.data[at+2:at+4],'little');b=int.from_bytes(self.rom.data[at+4:at+6],'little')
        if kind==2:
            name=next((c['label'] for c in catalogue()['chapters'][e['chapter']]['castles'] if c['id']==b),f'Castle {b}')
            result='Seize '+name
        else:result='Defeat '+self.name(a)
        return result+(' [ending]' if e['ending'] else ' [progression]')

    def populate(self):
        self.visible=[i for i,e in enumerate(catalogue()['entries']) if e['chapter']==self.chapter.current()]
        self.list.delete(0,'end')
        for i in self.visible:self.list.insert('end',self.label(i))
        if self.visible:self.list.selection_set(0);self.load(self.visible[0])

    def load(self,index):
        self.current=index;self.model=None;self.defeat=None;self.kind.set('');self.faction.set('');self.castle.set('');self.unit.set('');self.slot.set('')
        errors=[]
        try:self.model=Objective(self.rom,index)
        except ValueError as error:errors.append(str(error))
        try:
            self.defeat=DefeatRule(self.rom);self.slot.set(next(label for label,value in self.slot_options.items() if value==self.defeat.slot))
        except ValueError as error:errors.append(str(error))
        self.slot_box.config(state='readonly' if self.defeat else 'disabled')
        e=catalogue()['entries'][index];self.heading.set(CHAPTERS[e['chapter']]+' · '+self.label(index))
        self.castle_options={f'{c["id"]} — {c["label"]}':c['id'] for c in catalogue()['chapters'][e['chapter']]['castles']}
        self.boxes[2].config(values=list(self.castle_options));self.scenes=[]
        if self.model:
            m=self.model;self.kind.set(next((label for label,value in KINDS.items() if value==m.kind),'Child/substitute death (read-only)'))
            faction=m.first if m.kind==2 else m.second
            self.faction.set(next((label for label,value in FACTIONS.items() if value==faction),f'Unknown faction {faction}'))
            if m.kind==2:self.castle.set(next((label for label,value in self.castle_options.items() if value==m.second),''))
            else:self.unit.set(next((label for label,value in self.unit_options.items() if value==m.first),''))
            self.info.set(f'PC ${e["address"]:06X} · completion flag ${m.flag:02X} (preserved)\n'
                          'Direct events: '+(', '.join(f'${v:03X}' for v in e['direct_events']) or 'None')+'\n'
                          'Later flag-dependent events: '+(', '.join(f'${v:03X}' for v in e['indirect_events']) or 'None verified')+'. Other conditions can still apply.')
            from dialogue import catalogue as dialogues
            self.scenes=[(i,d) for i,d in enumerate(dialogues()['entries']) if d['address'] in e['scenes']]
        else:self.info.set('This objective layout is unsupported; only an available global defeat rule can be saved.')
        ch=e['chapter'];next_label=CHAPTERS[ch+1] if ch<11 else 'the epilogue / ending'
        self.progression.set(f'Native chapter order: {CHAPTERS[ch]} → {next_label}.\n'
                             'The linked ending script and chapter order are preserved. '+('Chapter 5 → 6 also performs inheritance and the generation change.' if ch==5 else ''))
        byid={x['id']:x for x in event_catalogue()['events']}
        text='Reference scripts retain their original names and conditions; live fields are shown in the first tab.\n\n'+catalogue()['chapters'][ch]['source']
        text+='\n\n'+'\n\n'.join(f'Event ${v:03X}\n'+byid[v]['source'] for v in e['events'] if v in byid)
        self.reference.config(state='normal');self.reference.delete('1.0','end');self.reference.insert('1.0',text);self.reference.config(state='disabled')
        self.update_fields();self.loaded=self.values();self.status.set(' · '.join(errors) if errors else 'Changes are staged until Write to ROM. Backups and undo history apply.')

    def update_fields(self):
        editable=self.model is not None and self.model.entry['editable']
        for box in self.boxes:box.config(state='disabled')
        if editable:
            self.boxes[0].config(state='readonly');self.boxes[1].config(state='readonly')
            self.boxes[2 if self.kind.get()=='Seize castle' else 3].config(state='readonly')

    def change_kind(self,_=None):
        self.faction.set('0 — Player' if self.kind.get()=='Seize castle' else 'Any faction');self.update_fields()

    def toggle_help(self):
        if self.help_label.winfo_manager():self.help_label.pack_forget();self.help.set('▶ Field help / limitations')
        else:self.help_label.pack(anchor='w',pady=6);self.help.set('▼ Field help / limitations')

    def values(self):return tuple(v.get() for v in (self.kind,self.faction,self.castle,self.unit,self.slot))
    def pending(self):return self.values()!=self.loaded

    def settle(self):
        if not self.pending():return True
        answer=ask_unsaved(self,'Write staged edits to the ROM?')
        return False if answer is None else self.save() if answer else True

    def select(self,_=None):
        if not self.list.curselection():return
        index=self.visible[self.list.curselection()[0]]
        if index==self.current:return
        if self.settle():self.load(index)
        else:
            self.list.selection_clear(0,'end')
            if self.current in self.visible:self.list.selection_set(self.visible.index(self.current))

    def change_chapter(self,_=None):
        if self.settle():self.populate()
        elif self.current is not None:self.chapter.current(catalogue()['entries'][self.current]['chapter'])

    def refresh_labels(self):
        self.list.delete(0,'end')
        for i in self.visible:self.list.insert('end',self.label(i))
        if self.current in self.visible:self.list.selection_set(self.visible.index(self.current))

    def save(self):
        if self.app.rom is not self.rom:messagebox.showerror('ROM changed','Reopen this editor for the current ROM.',parent=self);return False
        before=bytes(self.rom.data)
        try:
            details=[]
            if self.model:
                if self.model.entry['editable']:
                    kind=KINDS[self.kind.get()];faction=FACTIONS[self.faction.get()]
                    first,second=(faction,self.castle_options[self.castle.get()]) if kind==2 else (self.unit_options[self.unit.get()],faction)
                    details+=self.model.write(kind,first,second)
            if self.defeat:details+=self.defeat.write(self.slot_options[self.slot.get()])
            if not self.model and not self.defeat:raise ValueError('There are no supported settings to save.')
            self.rom.save_original('Objectives: '+self.heading.get(),details)
        except (KeyError,ValueError,OSError) as error:
            self.rom.data[:]=before;messagebox.showerror('Cannot save objectives','Choose a value for each active field.' if isinstance(error,KeyError) else str(error),parent=self);return False
        self.app.refresh_after_history();self.refresh_labels();self.load(self.current);self.status.set('Saved to the original ROM with backup and undo history.');return True

    def reload(self):
        if self.current is not None and (not self.pending() or messagebox.askyesno('Reload','Discard unwritten edits?',parent=self)):self.load(self.current)

    def history(self,redo):
        if self.app.rom is self.rom and self.settle():self.app.history_step(redo);self.refresh_labels();self.load(self.current)

    def child_closed(self,window,event):
        if event.widget is window and self.winfo_exists():self.load(self.current);self.grab_set()

    def view_event(self):
        if self.current is None or not self.settle():return
        entry=catalogue()['entries'][self.current];ids=entry['events']
        window=self.app.edit_events(ids[0] if ids else None)
        if window:
            window.transient(self)
            if not ids:window.chapter.current(entry['chapter']);window.change_chapter()
            window.bind('<Destroy>',lambda event:self.child_closed(window,event),add='+')

    def open_dialogue(self):
        if not self.scenes or not self.settle():
            if not self.scenes:messagebox.showinfo('Objective dialogue','No direct catalogued dialogue was found; inspect the linked event for custom callbacks.',parent=self)
            return
        i,e=self.scenes[0];window=self.app.edit_dialogue()
        if window:
            window.transient(self);window.group.set(e['group']);window.populate();window.load(i)
            if i in window.visible:window.list.selection_clear(0,'end');window.list.selection_set(window.visible.index(i))
            window.bind('<Destroy>',lambda event:self.child_closed(window,event))

    def launch(self):return self.app.save_and_launch(save_callback=self.save,parent=self)
    def close(self):
        if self.settle():self.destroy()

def open_objective_window(app):
    if not app.rom:messagebox.showinfo('Objectives & Progression','Open a ROM first.',parent=app);return
    if app.settle():return ObjectiveWindow(app)
