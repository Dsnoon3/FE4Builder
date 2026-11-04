from ui_common import ask_unsaved
"""Existing reinforcement spawn and turn editing with normal ROM history."""
import tkinter as tk
from tkinter import ttk,messagebox
from events import CHAPTERS
from reinforcements import catalogue,Reinforcement

class ReinforcementWindow(tk.Toplevel):
    def __init__(self,app):
        super().__init__(app);self.app=app;self.rom=app.rom;self.model=None;self.current=None;self.unit=None
        self.title('FE4Builder — Reinforcement Editor');self.geometry('1180x760');self.minsize(1000,680)
        self.transient(app);self.grab_set()
        top=ttk.Frame(self,padding=12);top.pack(fill='x')
        ttk.Label(top,text='Reinforcement Editor',style='Title.TLabel').pack(side='left')
        ttk.Button(top,text='Write to ROM',command=self.save).pack(side='right')
        ttk.Button(top,text='Save & Launch (F5)',command=self.launch).pack(side='right',padx=8)
        body=ttk.Panedwindow(self,orient='horizontal');body.pack(fill='both',expand=True,padx=12,pady=8)
        left=ttk.Frame(body);body.add(left,weight=1)
        self.chapter=ttk.Combobox(left,state='readonly',values=CHAPTERS);self.chapter.current(0);self.chapter.pack(fill='x')
        self.chapter.bind('<<ComboboxSelected>>',self.change_chapter)
        self.list=self.listbox(left);self.list.bind('<<ListboxSelect>>',self.select)
        from ui_common import scrollable_frame
        right_shell=ttk.Frame(body);body.add(right_shell,weight=3)
        right=scrollable_frame(right_shell,padding=12)
        self.heading=tk.StringVar();ttk.Label(right,textvariable=self.heading,font=('Segoe UI',12,'bold')).pack(anchor='w')
        ttk.Label(right,text='Existing scripted loads only. Group destinations and unit records are edited in Army Editor.\n'
                  'Changing a turn keeps all flag, phase, AI and story conditions. Camera movement and\n'
                  'later scripted paths are separate: test the event after moving a spawn.',wraplength=710).pack(anchor='w',pady=8)
        self.units=self.listbox(right,height=6);self.units.bind('<<ListboxSelect>>',self.select_unit)
        self.identity=tk.StringVar();ttk.Label(right,textvariable=self.identity,wraplength=710).pack(anchor='w',pady=6)
        fields=ttk.LabelFrame(right,text='Selected spawn (zero-based map coordinates)',padding=8);fields.pack(fill='x')
        self.variables=[tk.StringVar() for _ in range(5)];self.boxes=[]
        for i,label in enumerate(['Entry X','Entry Y','Destination X','Destination Y','Movement speed']):
            ttk.Label(fields,text=label).grid(row=i//3*2,column=i%3,sticky='w',padx=8)
            box=ttk.Spinbox(fields,from_=0,to=7 if i==4 else 63,textvariable=self.variables[i],width=10)
            box.grid(row=i//3*2+1,column=i%3,sticky='w',padx=8,pady=(0,6));self.boxes.append(box)
        self.turn_frame=ttk.LabelFrame(right,text='Turn triggers',padding=8);self.turn_frame.pack(fill='x',pady=8)
        self.turn_vars=[]
        bar=ttk.Frame(right);bar.pack(fill='x',pady=6)
        ttk.Button(bar,text='Reload',command=self.reload).pack(side='left')
        ttk.Button(bar,text='Undo ROM',command=lambda:self.history(False)).pack(side='left',padx=6)
        ttk.Button(bar,text='Redo ROM',command=lambda:self.history(True)).pack(side='left')
        ttk.Button(bar,text='Open Event Editor…',command=self.view_event).pack(side='left',padx=6)
        ttk.Button(bar,text='Open Army Editor',command=self.open_army).pack(side='left')
        ttk.Label(right,text='58 verified scripts / 542 loads. Other event formats remain viewable in Event Editor.\n'
                  'This editor changes fixed-size operands; it does not add units, expand the ROM or rewrite dialogue.',wraplength=710).pack(anchor='w',pady=6)
        self.status=tk.StringVar();ttk.Label(self,textvariable=self.status,relief='sunken',padding=8,wraplength=1100).pack(fill='x',side='bottom')
        self.protocol('WM_DELETE_WINDOW',self.close);self.bind('<F5>',lambda _:self.launch())
        self.populate()

    def listbox(self,parent,**kwargs):
        frame=ttk.Frame(parent);frame.pack(fill='both',expand=True,pady=6)
        listing=tk.Listbox(frame,exportselection=False,width=32,**kwargs)
        scroll=ttk.Scrollbar(frame,command=listing.yview);scroll.pack(side='right',fill='y')
        listing.config(yscrollcommand=scroll.set);listing.pack(fill='both',expand=True);return listing

    def populate(self):
        self.visible=[i for i,e in enumerate(catalogue()['entries']) if e['chapter']==self.chapter.current()]
        self.list.delete(0,'end')
        for i in self.visible:self.list.insert('end',catalogue()['entries'][i]['label'])
        if self.visible:self.list.selection_set(0);self.load(self.visible[0])
        else:self.clear();self.status.set('No supported spawn scripts in this chapter.')

    def clear(self):
        self.model=None;self.unit=None;self.units.delete(0,'end');self.identity.set('');self.heading.set('')
        for var,box in zip(self.variables,self.boxes):var.set('');box.config(state='disabled')
        for child in self.turn_frame.winfo_children():child.destroy()
        self.turn_vars=[]

    def load(self,index):
        self.clear();self.current=index
        try:self.model=Reinforcement(self.rom,index)
        except ValueError as error:self.status.set(str(error));return
        self.heading.set(self.model.entry['label']);self.drafts=[[str(v) for v in u['values']] for u in self.model.units]
        from rom import army_modules
        try:
            self.army_names={self.rom.address(table,i):table.names[i] for table in army_modules(self.rom)[:12] for i in range(table.count)}
        except ValueError:self.army_names={}
        for j,u in enumerate(self.model.units):
            name=f'{u["label"].split(",")[0]} (${u["identity"]:04X})' if u['kind']=='direct' else f'Group ${u["group"]:02X} / record ${u["identity"]:04X}'
            if u['kind']!='direct':
                base=0x1c000+self.rom.header
                pointer=int.from_bytes(self.rom.data[base+u['group']*2:base+u['group']*2+2],'little')
                # Native rlLoadUNITAsHidden indexes one-based eight-byte UNIT entries.
                address=base+pointer+(u['identity']-1)*8
                if address in self.army_names:name=self.army_names[address]+f' (record {u["identity"]})'
            self.units.insert('end',f'{j+1}. {name}')
        for j,t in enumerate(self.model.triggers):
            var=tk.StringVar(value='Any turn' if t['turn']==255 else str(t['turn']));self.turn_vars.append(var)
            ttk.Label(self.turn_frame,text=f'Condition ${t["address"]:06X} · faction {t["faction"]} · turn').grid(row=j,column=0,sticky='w')
            ttk.Combobox(self.turn_frame,state='readonly',values=['Any turn']+list(map(str,range(1,255))),textvariable=var,width=9).grid(row=j,column=1,padx=8)
            ttk.Label(self.turn_frame,text=f'Shared by {len(t["shared"])} event(s): '+', '.join(f'{v:03X}' for v in t['shared'])).grid(row=j,column=2,sticky='w')
        ttk.Label(self.turn_frame,text='Any turn keeps the other event conditions.' if self.turn_vars else 'No verified turn condition links to this event. Its trigger is story / action driven.').grid(row=len(self.turn_vars),column=0,columnspan=3,sticky='w',pady=4)
        self.units.selection_set(0);self.select_unit();self.loaded=self.values()
        self.status.set('Edits remain staged until Write to ROM. Backups and undo history apply.')

    def remember_unit(self):
        if self.model is not None and self.unit is not None:
            indices=[0,1,2,3,4] if self.model.units[self.unit]['kind']=='direct' else [0,1,4]
            self.drafts[self.unit]=[self.variables[i].get() for i in indices]

    def select_unit(self,_=None):
        if self.model is None or not self.units.curselection():return
        self.remember_unit();self.unit=self.units.curselection()[0];u=self.model.units[self.unit]
        direct=u['kind']=='direct';indices=[0,1,2,3,4] if direct else [0,1,4]
        for var,box in zip(self.variables,self.boxes):var.set('');box.config(state='disabled')
        for i,value in zip(indices,self.drafts[self.unit]):self.variables[i].set(value);self.boxes[i].config(state='normal')
        self.identity.set((f'Faction slot {u["faction"]}. ' if direct else 'Destination comes from the Army record. ')+u['label'])

    def values(self):
        self.remember_unit()
        return (tuple(tuple(v) for v in self.drafts),tuple(v.get() for v in self.turn_vars)) if self.model else None

    def pending(self):return self.model is not None and self.values()!=self.loaded

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

    def save(self):
        if self.model is None:return False
        if self.app.rom is not self.rom:messagebox.showerror('ROM changed','Reopen this editor for the current ROM.',parent=self);return False
        before=bytes(self.rom.data)
        try:
            units,turns=self.values();details=self.model.write([[int(v) for v in row] for row in units],[255 if v=='Any turn' else int(v) for v in turns])
            self.rom.save_original('Reinforcements: '+self.model.entry['label'],details)
        except (ValueError,OSError) as error:
            self.rom.data[:]=before;messagebox.showerror('Cannot save reinforcements',str(error),parent=self);return False
        self.app.refresh_after_history();self.load(self.current);self.status.set('Saved to the original ROM with backup and undo history.');return True

    def reload(self):
        if self.current is not None and (not self.pending() or messagebox.askyesno('Reload','Discard unwritten edits?',parent=self)):self.load(self.current)

    def history(self,redo):
        if self.app.rom is self.rom and self.settle():self.app.history_step(redo);self.load(self.current)

    def view_event(self):
        if self.model is None or not self.settle():return
        window=self.app.edit_events(self.model.entry['id'])
        if window:
            window.transient(self)
            window.bind('<Destroy>',lambda event:self.grab_set() if event.widget is window and self.winfo_exists() else None,add='+')

    def launch(self):return self.app.save_and_launch(save_callback=self.save,parent=self)
    def open_army(self):
        if self.settle():self.destroy();self.app.show_editor('Army Editor')
    def close(self):
        if self.settle():self.destroy()

def open_reinforcement_window(app):
    if not app.rom:messagebox.showinfo('Reinforcement Editor','Open a ROM first.',parent=app);return
    if app.settle():return ReinforcementWindow(app)
