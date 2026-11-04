from ui_common import ask_unsaved
"""Chapter talk participants, existing recruitment commands and dialogue links."""
import tkinter as tk
from tkinter import ttk,messagebox
from conversations import catalogue,Conversation,character_names
from events import CHAPTERS,catalogue as event_catalogue

class ConversationWindow(tk.Toplevel):
    def __init__(self,app):
        super().__init__(app);self.app=app;self.rom=app.rom;self.current=None;self.model=None
        self.names=character_names(self.rom);self.title('FE4Builder — Recruitment & Conversations')
        self.geometry('1190x790');self.minsize(1000,690);self.transient(app);self.grab_set()
        top=ttk.Frame(self,padding=12);top.pack(fill='x')
        ttk.Label(top,text='Recruitment & Conversations',style='Title.TLabel').pack(side='left')
        ttk.Button(top,text='Write to ROM',command=self.save).pack(side='right')
        ttk.Button(top,text='Save & Launch (F5)',command=self.launch).pack(side='right',padx=8)
        body=ttk.Panedwindow(self,orient='horizontal');body.pack(fill='both',expand=True,padx=12,pady=8)
        left=ttk.Frame(body);body.add(left,weight=1)
        self.chapter=ttk.Combobox(left,state='readonly',values=CHAPTERS);self.chapter.current(0);self.chapter.pack(fill='x')
        self.chapter.bind('<<ComboboxSelected>>',self.change_chapter)
        filters=ttk.Frame(left);filters.pack(fill='x',pady=6)
        self.search=tk.StringVar();entry=ttk.Entry(filters,textvariable=self.search);entry.pack(side='left',fill='x',expand=True)
        entry.bind('<Return>',lambda _:self.filter());ttk.Button(filters,text='Find',command=self.filter).pack(side='left')
        frame=ttk.Frame(left);frame.pack(fill='both',expand=True)
        self.list=tk.Listbox(frame,width=37,exportselection=False);scroll=ttk.Scrollbar(frame,command=self.list.yview)
        scroll.pack(side='right',fill='y');self.list.config(yscrollcommand=scroll.set);self.list.pack(fill='both',expand=True)
        self.list.bind('<<ListboxSelect>>',self.select)
        right=ttk.Frame(body,padding=(12,0));body.add(right,weight=3)
        self.heading=tk.StringVar();ttk.Label(right,textvariable=self.heading,font=('Segoe UI',12,'bold'),wraplength=720).pack(anchor='w',pady=(0,8))
        self.tabs=ttk.Notebook(right);self.tabs.pack(fill='both',expand=True)
        from ui_common import scrollable_tab
        edit=scrollable_tab(self.tabs,'Conversation')
        self.condition_text=self.text_tab('Conditions (reference)');self.action_text=self.text_tab('Actions (reference)')
        self.info=tk.StringVar();ttk.Label(edit,textvariable=self.info,wraplength=680).pack(anchor='w',pady=(0,10))
        fields=ttk.LabelFrame(edit,text='Who talks to whom',padding=10);fields.pack(fill='x')
        self.initiator=tk.StringVar();self.target=tk.StringVar();self.options={}
        self.boxes=[]
        for row,(label,var) in enumerate([('Initiator',self.initiator),('Target',self.target)]):
            ttk.Label(fields,text=label).grid(row=row,column=0,sticky='w',padx=(0,10),pady=4)
            box=ttk.Combobox(fields,textvariable=var,state='readonly',width=44);box.grid(row=row,column=1,sticky='ew',pady=4);self.boxes.append(box)
        fields.columnconfigure(1,weight=1)
        self.recruit_frame=ttk.LabelFrame(edit,text='Existing recruitment commands',padding=10);self.recruit_frame.pack(fill='x',pady=12)
        self.recruit_vars=[]
        dialogue=ttk.LabelFrame(edit,text='Dialogue in this event',padding=10);dialogue.pack(fill='x')
        self.scene=ttk.Combobox(dialogue,state='readonly',width=42);self.scene.pack(side='left',fill='x',expand=True)
        self.dialogue_button=ttk.Button(dialogue,text='Edit dialogue…',command=self.open_dialogue);self.dialogue_button.pack(side='left',padx=(8,0))
        ttk.Label(edit,text='Participant edits synchronize verified Talk menu entries and matching Talk targets.\n'
                  'Dialogue portraits, item rewards, later conversations and other hardcoded characters remain\n'
                  'as scripted. Recruitment checkboxes affect the named character, even if participants change.\n\n'
                  'Disabling a recruitment skips only its faction-change command. The dialogue, event flags,\n'
                  'payments and later story actions still run. Test edited scenes in-game.\n'
                  'Substitute-aware or unverified participant routes are read-only in this first version.',wraplength=680,justify='left').pack(anchor='w',pady=12)
        controls=ttk.Frame(right);controls.pack(fill='x',pady=8)
        ttk.Button(controls,text='Reload',command=self.reload).pack(side='left')
        ttk.Button(controls,text='Undo ROM',command=lambda:self.history(False)).pack(side='left',padx=6)
        ttk.Button(controls,text='Redo ROM',command=lambda:self.history(True)).pack(side='left')
        ttk.Button(controls,text='Edit linked event…',command=self.view_event).pack(side='left',padx=6)
        self.status=tk.StringVar();ttk.Label(self,textvariable=self.status,relief='sunken',padding=8,wraplength=1100).pack(fill='x',side='bottom')
        self.protocol('WM_DELETE_WINDOW',self.close);self.bind('<F5>',lambda _:self.launch());self.populate()

    def text_tab(self,title):
        frame=ttk.Frame(self.tabs);self.tabs.add(frame,text=title)
        text=tk.Text(frame,wrap='word',font=('Consolas',10),state='disabled')
        scroll=ttk.Scrollbar(frame,command=text.yview);scroll.pack(side='right',fill='y')
        text.config(yscrollcommand=scroll.set);text.pack(fill='both',expand=True);return text

    def put(self,widget,text):
        widget.config(state='normal');widget.delete('1.0','end');widget.insert('1.0',text);widget.config(state='disabled')

    def name(self,value):return 'Any character' if value==65535 else self.names.get(value,f'Character ${value:04X}')

    def live_pair(self,e):
        at=e['checks'][0]+self.rom.header
        return [int.from_bytes(self.rom.data[at+i:at+i+2],'little') for i in (2,4)]

    def populate(self):
        query=self.search.get().strip().casefold();self.visible=[];self.list.delete(0,'end')
        for i,e in enumerate(catalogue()['entries']):
            if e['chapter']!=self.chapter.current():continue
            label=self.list_label(e)
            if query and query not in (label+' '+' '.join(e['labels'])).casefold():continue
            self.visible.append(i);self.list.insert('end',label)
        if self.visible:self.list.selection_set(0);self.load(self.visible[0])
        else:self.clear();self.current=None;self.status.set('No matching conversations in this chapter.')

    def list_label(self,e):
        a,b=self.live_pair(e)
        return f'{self.name(a)} → {self.name(b)}'+(' [Recruit]' if e['recruits'] else '')+(' [Editable]' if e['editable'] else ' [Participants read-only]')

    def refresh_labels(self):
        self.list.delete(0,'end')
        for i in self.visible:self.list.insert('end',self.list_label(catalogue()['entries'][i]))
        if self.current in self.visible:self.list.selection_set(self.visible.index(self.current))

    def clear(self):
        self.model=None;self.heading.set('');self.info.set('');self.initiator.set('');self.target.set('')
        for box in self.boxes:box.config(state='disabled')
        for child in self.recruit_frame.winfo_children():child.destroy()
        self.recruit_vars=[];self.scenes=[];self.scene.set('');self.scene.config(values=[]);self.dialogue_button.config(state='disabled')
        self.put(self.condition_text,'');self.put(self.action_text,'')

    def load(self,index):
        self.clear();self.current=index;e=catalogue()['entries'][index]
        try:self.model=Conversation(self.rom,index)
        except ValueError as error:self.status.set(str(error));return
        a,b=self.model.pair;self.heading.set(f'{CHAPTERS[e["chapter"]]} · {self.name(a)} → {self.name(b)}')
        self.options={f'${key:04X} — {value}':key for key,value in sorted(self.names.items())}
        self.options['$FFFF — Any character']=65535
        for value in (a,b):
            if value not in self.options.values():self.options[f'${value:04X} — {self.name(value)}']=value
        for var,value,box in zip((self.initiator,self.target),(a,b),self.boxes):
            var.set(next(label for label,key in self.options.items() if key==value))
            box.config(values=list(self.options),state='readonly' if e['editable'] else 'disabled')
        flags=[]
        for at in e['checks']:
            flag=self.rom.data[at+self.rom.header+1];flags.append(f'${flag:02X}')
        route='Participants editable' if e['editable'] else 'Participants read-only: substitute-aware or unverified Talk availability'
        self.info.set(f'{route}.\nTalk flags: {", ".join(flags)} · {len(e["tables"])} linked table entries · {len(e["markers"])} linked Talk targets\n'
                      'Events: '+', '.join(f'${value:03X}' for value in e['events'])+'. Conditions and story actions are shown in the reference tabs.')
        for r,on in zip(e['recruits'],self.model.enabled):
            var=tk.BooleanVar(value=on);self.recruit_vars.append(var)
            who=self.name(r['character']) if r['character']!=65535 else 'event unit 1 (the initiator)'
            shared=sum(any(x['address']==r['address'] for x in other['recruits']) for other in catalogue()['entries'])
            ttk.Checkbutton(self.recruit_frame,text=f'{who} joins player faction · shared by {shared} conversation route(s)',variable=var).pack(anchor='w')
        if not self.recruit_vars:ttk.Label(self.recruit_frame,text='No verified direct recruitment command in this event. Custom routines may have other effects.',wraplength=660).pack(anchor='w')
        from dialogue import catalogue as dialogues
        self.scenes=[(i,d) for i,d in enumerate(dialogues()['entries']) if d['address'] in e['scenes']]
        self.scene.config(values=[d['label'] for _,d in self.scenes])
        if self.scenes:self.scene.current(0);self.dialogue_button.config(state='normal')
        self.put(self.condition_text,'Reference conditions: participant names below reflect the original script. Live participants are shown in the Conversation tab.\n\n'+catalogue()['chapters'][e['chapter']]['source'])
        byid={x['id']:x for x in event_catalogue()['events']}
        self.put(self.action_text,'\n\n'.join(f'Event ${event:03X}\n'+byid[event]['source'] for event in e['events'] if event in byid))
        self.loaded=self.values();self.status.set('Changes are staged until Write to ROM. Script size and ROM size stay unchanged.')

    def values(self):return (self.initiator.get(),self.target.get(),tuple(v.get() for v in self.recruit_vars))
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

    def filter(self):
        if self.settle():self.populate()

    def save(self):
        if self.model is None:return False
        if self.app.rom is not self.rom:messagebox.showerror('ROM changed','Reopen this editor for the current ROM.',parent=self);return False
        before=bytes(self.rom.data)
        try:
            a,b,on=self.values();details=self.model.write(self.options[a],self.options[b],list(on))
            self.rom.save_original('Conversation: '+self.heading.get(),details)
        except (ValueError,KeyError,OSError) as error:
            self.rom.data[:]=before;messagebox.showerror('Cannot save conversation',str(error),parent=self);return False
        self.app.refresh_after_history();self.refresh_labels();self.load(self.current);self.status.set('Saved to the original ROM with automatic backup and undo history.');return True

    def reload(self):
        if self.current is not None and (not self.pending() or messagebox.askyesno('Reload','Discard unwritten edits?',parent=self)):self.load(self.current)

    def history(self,redo):
        if self.app.rom is self.rom and self.settle():self.app.history_step(redo);self.refresh_labels();self.load(self.current)

    def child_closed(self,window,event):
        if event.widget is window and self.winfo_exists():self.load(self.current);self.grab_set()

    def open_dialogue(self):
        if self.model is None or self.scene.current()<0 or not self.settle():return
        i,e=self.scenes[self.scene.current()];window=self.app.edit_dialogue()
        if window:
            window.transient(self);window.group.set(e['group']);window.populate();window.load(i)
            if i in window.visible:window.list.selection_clear(0,'end');window.list.selection_set(window.visible.index(i))
            window.bind('<Destroy>',lambda event:self.child_closed(window,event))

    def view_event(self):
        if self.model is None or not self.settle():return
        ids=self.model.entry['events']
        window=self.app.edit_events(ids[0] if ids else None)
        if window:
            window.transient(self)
            window.bind('<Destroy>',lambda event:self.child_closed(window,event),add='+')

    def launch(self):return self.app.save_and_launch(save_callback=self.save,parent=self)
    def close(self):
        if self.settle():self.destroy()

def open_conversation_window(app):
    if not app.rom:messagebox.showinfo('Recruitment & Conversations','Open a ROM first.',parent=app);return
    if app.settle():return ConversationWindow(app)
