"""Movement step editor. Every save makes a private route for one caller."""
import tkinter as tk
from tkinter import ttk,messagebox
from route_editor import RouteDraft,DIRECTIONS,SIMPLE,encode_steps
from ui_common import ask_unsaved

class RouteWindow(tk.Toplevel):
    def __init__(self,parent,event,command,camera=False):
        from camera_routes import CameraRouteDraft,encode_camera_steps
        self.draft_type=CameraRouteDraft if camera else RouteDraft
        self.encode_step=encode_camera_steps if camera else encode_steps
        self.simple={'End'} if camera else set(SIMPLE.values())
        draft=self.draft_type(parent.rom,event,command)
        title='Camera route' if camera else 'Movement route'
        super().__init__(parent);self.parent=parent;self.draft=draft;self.steps=list(draft.steps)
        self.title(title+' editor');self.geometry('760x680');self.transient(parent);self.grab_set()
        ttk.Label(self,text=title+' - private copy',font=('Segoe UI',12,'bold')).pack(anchor='w',padx=12,pady=8)
        entry=draft.users
        selected=next((label for i,n,label in entry if (i,n)==(event,command)),'Selected command')
        ttk.Label(self,text='Editing: '+selected,wraplength=730).pack(anchor='w',padx=12)
        ttk.Label(self,text='Known callers of this route (verified chapter catalogue):').pack(anchor='w',padx=12,pady=(8,0))
        users=tk.Listbox(self,height=4,exportselection=False);users.pack(fill='x',padx=12)
        for _,_,label in entry:users.insert('end',label)
        ttk.Label(self,text=f'{len(entry)} known caller(s). Custom scripts and uncatalogued callers may not be indexed. '+('Some catalogued events could not be verified. ' if draft.unavailable else '')+'Saving changes only this command; all existing route bytes and other callers are preserved.',wraplength=730).pack(anchor='w',padx=12,pady=8)
        frame=ttk.Frame(self);frame.pack(fill='both',expand=True,padx=12)
        self.list=tk.Listbox(frame,exportselection=False);self.list.pack(side='left',fill='both',expand=True)
        bar=ttk.Scrollbar(frame,command=self.list.yview);bar.pack(side='right',fill='y');self.list.config(yscrollcommand=bar.set)
        controls=ttk.Frame(self);controls.pack(fill='x',padx=12,pady=8)
        self.kind=ttk.Combobox(controls,state='readonly',values=list(DIRECTIONS)+(['Speed','End'] if camera else ['Wait','Speed']+list(SIMPLE.values())),width=20);self.kind.set('Right');self.kind.pack(side='left')
        self.amount=tk.StringVar(value='1');ttk.Spinbox(controls,from_=1,to=255,textvariable=self.amount,width=7).pack(side='left',padx=6)
        ttk.Button(controls,text='Add before selected',command=lambda:self.edit('add')).pack(side='left')
        ttk.Button(controls,text='Update step',command=lambda:self.edit('update')).pack(side='left',padx=6)
        actions=ttk.Frame(self);actions.pack(fill='x',padx=12,pady=8)
        for label,action in [('Remove','remove'),('Move up','up'),('Move down','down')]:ttk.Button(actions,text=label,command=lambda a=action:self.edit(a)).pack(side='left',padx=3)
        ttk.Button(actions,text='Write private route to ROM',command=self.save).pack(side='right')
        ttk.Label(self,text=('Camera distances: tiles; speed: pixels per update, 1-255. End must be last. Legacy $12 is preserved as-is; it is not a supported timed pause. Routes start at the camera’s position when called. Backups and undo/redo apply.' if camera else 'Amounts: movement in tiles, Wait in ticks, Speed 1-5. End must be the last step. Writes use automatic backups and ROM undo/redo.'),wraplength=730).pack(padx=12,pady=8)
        self.list.bind('<<ListboxSelect>>',self.select);self.protocol('WM_DELETE_WINDOW',self.close);self.refresh()
    def refresh(self,index=0):
        self.list.delete(0,'end')
        for n,(kind,value) in enumerate(self.steps):self.list.insert('end',f'{n+1}. {kind}'+(f' {value}' if value else ''))
        if self.steps:self.list.selection_set(min(index,len(self.steps)-1));self.list.see(min(index,len(self.steps)-1))
    def select(self,_=None):
        if self.list.curselection():
            kind,value=self.steps[self.list.curselection()[0]];self.kind.set(kind);self.amount.set(str(value or 1))
    def edit(self,action):
        index=self.list.curselection()[0] if self.list.curselection() else len(self.steps)
        try:
            if action in ('add','update'):
                kind=self.kind.get();value=0 if kind in self.simple else int(self.amount.get());step=(kind,value)
                self.encode_step([step,('End',0)] if kind!='End' else [step])
                if action=='add':self.steps.insert(index,step)
                elif index<len(self.steps):self.steps[index]=step
            elif index<len(self.steps):
                if action=='remove':self.steps.pop(index)
                else:
                    other=index+(-1 if action=='up' else 1)
                    if 0<=other<len(self.steps):self.steps[index],self.steps[other]=self.steps[other],self.steps[index];index=other
            self.refresh(index)
        except ValueError as error:messagebox.showerror('Invalid step',str(error),parent=self)
    def save(self):
        if self.parent.app.rom is not self.draft.rom:messagebox.showerror('ROM changed','Reopen the route editor.',parent=self);return False
        before=bytes(self.draft.rom.data)
        try:
            details=self.draft.write(self.steps)
            if details:self.draft.rom.save_original('Edit '+self.draft.route_name+' route: '+self.parent.model.entry['label'],details)
        except (ValueError,OSError) as error:
            self.draft.rom.data[:]=before;messagebox.showerror('Cannot save route',str(error),parent=self);return False
        self.parent.app.refresh_after_history();self.parent.load(self.parent.current)
        self.draft=self.draft_type(self.parent.rom,self.draft.event,self.draft.command)
        self.destroy();return True
    def close(self):
        if self.steps!=self.draft.steps:
            answer=ask_unsaved(self,'Write this private '+self.draft.route_name+' route to the opened ROM?')
            if answer is None:return
            if answer:return self.save()
        self.destroy()
    def destroy(self):
        super().destroy()
        if self.parent.winfo_exists():self.parent.grab_set()
