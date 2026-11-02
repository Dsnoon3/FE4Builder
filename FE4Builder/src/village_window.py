from ui_common import ask_unsaved
"""Chapter village rewards with explicit shared-slot and variant explanations."""
import tkinter as tk
from tkinter import ttk,messagebox
from villages import Village,VillageLocation,entries,CHAPTERS,STATS
from rom import character_modules


class VillageWindow(tk.Toplevel):
    def __init__(self,app):
        super().__init__(app)
        self.app,self.rom=app,app.rom;self.current=None;self.model=None;self.loaded=()
        self.title('FE4Builder — Village Rewards');self.geometry('1030x710');self.minsize(940,640)
        self.transient(app);self.grab_set()
        top=ttk.Frame(self,padding=14);top.pack(fill='x')
        ttk.Label(top,text='Village Rewards',style='Title.TLabel').pack(side='left')
        ttk.Button(top,text='Write rewards to ROM',command=self.save).pack(side='right')
        ttk.Button(top,text='Save & Launch (F5)',command=self.launch).pack(side='right',padx=8)
        body=ttk.Panedwindow(self,orient='horizontal');body.pack(fill='both',expand=True,padx=14,pady=8)
        left=ttk.Frame(body,width=280);body.add(left,weight=1)
        self.chapter=ttk.Combobox(left,state='readonly',values=CHAPTERS);self.chapter.current(0)
        self.chapter.pack(fill='x');self.chapter.bind('<<ComboboxSelected>>',self.change_chapter)
        list_frame=ttk.Frame(left);list_frame.pack(fill='both',expand=True,pady=10)
        self.list=tk.Listbox(list_frame,exportselection=False,width=32)
        scroll=ttk.Scrollbar(list_frame,command=self.list.yview);scroll.pack(side='right',fill='y')
        self.list.config(yscrollcommand=scroll.set);self.list.pack(fill='both',expand=True)
        self.list.bind('<<ListboxSelect>>',self.select)
        from ui_common import scrollable_frame
        right_shell=ttk.Frame(body);body.add(right_shell,weight=3)
        right=scrollable_frame(right_shell,padding=16)
        self.heading=tk.StringVar();ttk.Label(right,textvariable=self.heading,font=('Segoe UI',13,'bold')).pack(anchor='w')
        self.info=tk.StringVar();ttk.Label(right,textvariable=self.info,wraplength=570).pack(anchor='w',pady=12)
        location=ttk.LabelFrame(right,text='Village visit location',padding=10);location.pack(fill='x',pady=(0,10))
        self.location_info=tk.StringVar()
        ttk.Label(location,textvariable=self.location_info,wraplength=550).pack(anchor='w')
        self.location_button=ttk.Button(location,text='Pick location on map…',command=self.pick_location)
        self.location_button.pack(anchor='w',pady=6)
        ttk.Label(location,text='Click the visitable entrance tile. This moves the interaction, not the village artwork.\nMove the village tiles separately in Map Editor; scripted raids may also need updating.',wraplength=550).pack(anchor='w')
        fields=ttk.LabelFrame(right,text='Rewards',padding=14);fields.pack(fill='x')
        field=next(f for f in character_modules()[0].fields if f.reference=='FE4 Player Equipment.txt')
        self.item_options={'None':0}
        self.item_options.update({f'{slot} — {name}':slot for slot,name in self.rom.field_options(field).items() if 1<=slot<=142})
        self.reward_type=tk.StringVar()
        self.reward_types={'Gold only / no special reward':'none','Item':'item','Stat increase':'stat','Item and stat increase':'item+stat'}
        ttk.Label(fields,text='Special reward type').grid(row=4,column=0,sticky='w',pady=6)
        box=ttk.Combobox(fields,textvariable=self.reward_type,state='readonly',values=list(self.reward_types),width=30)
        box.grid(row=4,column=1,sticky='w',padx=10,pady=6)
        box.bind('<<ComboboxSelected>>',self.change_reward_type)
        self.item=tk.StringVar();self.gold=tk.StringVar();self.stat=tk.StringVar();self.amount=tk.StringVar()
        ttk.Label(fields,text='Item reward').grid(row=0,column=0,sticky='w',pady=6)
        self.item_box=ttk.Combobox(fields,textvariable=self.item,state='readonly',values=list(self.item_options),width=36)
        self.item_box.grid(row=0,column=1,sticky='ew',padx=10,pady=6)
        ttk.Label(fields,text='Extra gold at visit').grid(row=1,column=0,sticky='w',pady=6)
        ttk.Spinbox(fields,from_=0,to=50000,textvariable=self.gold,width=12).grid(row=1,column=1,sticky='w',padx=10,pady=6)
        ttk.Label(fields,text='Existing stat reward').grid(row=2,column=0,sticky='w',pady=6)
        self.stat_box=ttk.Combobox(fields,textvariable=self.stat,state='readonly',values=STATS,width=20)
        self.stat_box.grid(row=2,column=1,sticky='w',padx=10,pady=6)
        ttk.Label(fields,text='Stat increase').grid(row=3,column=0,sticky='w',pady=6)
        self.amount_box=ttk.Spinbox(fields,from_=0,to=30,textvariable=self.amount,width=12)
        self.amount_box.grid(row=3,column=1,sticky='w',padx=10,pady=6)
        fields.columnconfigure(1,weight=1)
        base=int.from_bytes(self.rom.data[0x7f475+self.rom.header:0x7f477+self.rom.header],'little')
        ttk.Label(right,text=f'Normal village gold starts at {base:,} and falls with raid damage.\n'
                  'Extra gold is paid in addition, without changing raid damage or destruction timing.\n\n'
                  'Some villages have visitor-dependent variants. Edit each relevant variant;\n'
                  'the original conditions and story events stay in place. Special rewards can\n'
                  'be replaced or combined. Normal raid-dependent gold remains unchanged.\n\n'
                  'Item rewards use shared player inventory slots. Selecting a slot already used\n'
                  'by a character, shop or another reward can move that same item instance.\n'
                  'Village dialogue is not rewritten automatically; update its text separately.',
                  wraplength=570,justify='left').pack(anchor='w',pady=16)
        controls=ttk.Frame(right);controls.pack(fill='x',pady=8)
        ttk.Button(controls,text='Edit village dialogue…',command=self.dialogue).pack(side='left')
        ttk.Button(controls,text='Reload',command=self.reload).pack(side='left',padx=6)
        ttk.Button(controls,text='Undo ROM',command=lambda:self.history(False)).pack(side='left',padx=6)
        ttk.Button(controls,text='Redo ROM',command=lambda:self.history(True)).pack(side='left')
        self.status=tk.StringVar();ttk.Label(self,textvariable=self.status,relief='sunken',padding=8).pack(side='bottom',fill='x')
        self.bind('<F5>',lambda _:self.launch());self.protocol('WM_DELETE_WINDOW',self.close)
        self.populate();self.list.selection_set(0);self.select()

    def values(self):return tuple(v.get() for v in (self.item,self.gold,self.stat,self.amount,self.reward_type))+(getattr(self,'location_position',None),)
    def pending(self):return self.model is not None and self.values()!=self.loaded

    def change_reward_type(self,_=None):
        kind=self.reward_types[self.reward_type.get()]
        self.item_box.config(state='readonly' if kind in ('item','item+stat') else 'disabled')
        enabled=kind in ('stat','item+stat')
        self.stat_box.config(state='readonly' if enabled else 'disabled')
        self.amount_box.config(state='normal' if enabled else 'disabled')

    def show_location(self):
        x,y=self.location_position
        shared='; shared by '+', '.join(self.location_model.variants) if len(self.location_model.variants)>1 else ''
        self.location_info.set(f'Visit tile: X {x}, Y {y} (village ID {self.location_model.location["id"]})'+shared)

    def pick_location(self):
        if self.location_model is None:return
        try:return VillageLocationPicker(self)
        except (ValueError,IndexError) as error:
            messagebox.showerror('Cannot display village map',str(error),parent=self)

    def populate(self):
        self.visible=[i for i,e in enumerate(entries()) if e['chapter']==self.chapter.current()]
        self.list.delete(0,'end')
        for i in self.visible:self.list.insert('end',entries()[i]['label'])

    def load(self,index):
        try:model=Village(self.rom,index)
        except ValueError as error:
            messagebox.showerror('Unsupported village event',str(error),parent=self);return False
        self.current=index;self.model=model
        try:
            self.location_model=VillageLocation(self.rom,index)
            self.location_position=self.location_model.position
            self.show_location();self.location_button.config(state='normal')
        except ValueError as error:
            self.location_model=None;self.location_position=None
            self.location_info.set(str(error));self.location_button.config(state='disabled')
        self.heading.set(CHAPTERS[model.entry['chapter']]+' — '+model.entry['label'])
        reward='Item' if model.kind=='item' else 'Stat gain' if model.kind=='stat' else 'Gold only'
        self.info.set(f'Original event: {reward}. Special reward recipient: {model.recipient}.\n'
                      'Choose the special reward type below; normal village gold is separate.')
        self.item.set(next((name for name,value in self.item_options.items() if value==model.item),'None'))
        self.gold.set(str(model.gold));self.stat.set(STATS[model.stat] if model.stat is not None and model.stat<8 else STATS[0])
        self.amount.set(str(model.amount or 0))
        self.reward_type.set(next(k for k,v in self.reward_types.items() if v==model.reward_type))
        self.change_reward_type()
        self.loaded=self.values();self.status.set('Changes stay staged until Write rewards to ROM. No ROM expansion is needed.')
        return True

    def select(self,_=None):
        selected=self.list.curselection()
        if not selected:return
        target=self.visible[selected[0]]
        if target==self.current:return
        if not self.settle():
            self.list.selection_clear(0,'end')
            if self.current in self.visible:self.list.selection_set(self.visible.index(self.current))
            return
        self.load(target)

    def change_chapter(self,_=None):
        if not self.settle():
            if self.current is not None:self.chapter.current(entries()[self.current]['chapter'])
            return
        self.populate()
        if self.visible:self.load(self.visible[0]);self.list.selection_set(0)

    def save(self):
        if self.app.rom is not self.rom:
            messagebox.showerror('ROM changed','Reopen the village editor for this ROM.',parent=self);return False
        if self.model is None:return False
        before=bytes(self.rom.data)
        try:
            item=self.item_options[self.item.get()];gold=int(self.gold.get())
            kind=self.reward_types[self.reward_type.get()]
            stat=STATS.index(self.stat.get()) if kind in ('stat','item+stat') else None
            amount=int(self.amount.get()) if stat is not None else None
            details=self.model.write(item,gold,stat,amount,reward_type=kind)
            if self.location_model is not None:details+=self.location_model.write(*self.location_position)
            if len(self.rom.data)>len(before) and not messagebox.askyesno('ROM expansion required',f'This reward change will increase the ROM from {len(before):,} to {len(self.rom.data):,} bytes. Continue?',parent=self):
                self.rom.data[:]=before
                return False
            self.rom.save_original(f'Village rewards: {self.heading.get()}',details)
        except (KeyError,ValueError,OSError) as error:
            self.rom.data[:]=before;messagebox.showerror('Cannot write village rewards',str(error),parent=self);return False
        self.app.refresh_after_history();self.load(self.current)
        self.status.set('Village rewards saved with automatic backup and undo history.')
        return True

    def settle(self):
        if not self.pending():return True
        answer=ask_unsaved(self,'Write the staged rewards to this ROM?')
        if answer is None:return False
        return self.save() if answer else True

    def reload(self):
        if self.current is not None and (not self.pending() or messagebox.askyesno('Reload village','Discard the unwritten rewards?',parent=self)):self.load(self.current)

    def history(self,redo):
        if self.app.rom is self.rom and self.settle():self.app.history_step(redo);self.load(self.current)

    def dialogue(self):
        if self.model is None or not self.settle():return
        from dialogue import catalogue
        e=self.model.entry;scenes=catalogue()['entries']
        index=next((i for i,scene in enumerate(scenes) if e['start']<=scene['address']<e['start']+e['length']),None)
        if index is None:
            messagebox.showinfo('Village dialogue','No linked scene was found for this variant.',parent=self);return
        window=self.app.edit_dialogue()
        if window is None:return
        window.transient(self);window.group.set(CHAPTERS[e['chapter']]);window.populate();window.load(index)
        if index in window.visible:window.list.selection_set(window.visible.index(index))
        def closed(event):
            if event.widget is window and self.winfo_exists():self.load(self.current);self.grab_set()
        window.bind('<Destroy>',closed)

    def launch(self):return self.app.save_and_launch(save_callback=self.save,parent=self)
    def close(self):
        if self.settle():self.destroy()


class VillageLocationPicker(tk.Toplevel):
    def __init__(self,owner):
        import base64
        from chapter_maps import ChapterMap
        from portraits import png_bytes
        # Decode before opening a window so unsupported maps leave no empty dialog.
        model=ChapterMap(owner.rom,owner.model.entry['chapter'])
        left,top,right,bottom=model.bounds
        pixels=model.pixels()
        cropped=[row[left*16:right*16] for row in pixels[top*16:bottom*16]]
        image_data=base64.b64encode(png_bytes(cropped,model.palette)).decode('ascii')
        super().__init__(owner)
        self.owner=owner;self.model=model;self.origin=(left,top)
        width,height=(right-left)*16,(bottom-top)*16
        self.title('Pick village visit location — '+CHAPTERS[model.chapter])
        self.geometry('940x800');self.transient(owner);self.grab_set()
        ttk.Label(self,text='Red square: visit tile. Blue rectangle: full 3×2 village area.\nClick once on the new entrance tile to select it. Changes stay staged until Write rewards to ROM.',padding=10).pack(fill='x')
        body=ttk.Frame(self);body.pack(fill='both',expand=True)
        self.canvas=tk.Canvas(body,background='#202020',highlightthickness=0,scrollregion=(0,0,width,height))
        horizontal=ttk.Scrollbar(body,orient='horizontal',command=self.canvas.xview)
        vertical=ttk.Scrollbar(body,orient='vertical',command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=horizontal.set,yscrollcommand=vertical.set)
        horizontal.pack(side='bottom',fill='x');vertical.pack(side='right',fill='y');self.canvas.pack(fill='both',expand=True)
        self.image=tk.PhotoImage(master=self,data=image_data)
        self.canvas.create_image(0,0,image=self.image,anchor='nw')
        x,y=owner.location_position
        px,py=(x-left)*16,(y-top)*16
        self.canvas.create_rectangle(px-16,py-16,px+32,py+16,outline='#409cff',width=3)
        self.canvas.create_rectangle(px,py,px+16,py+16,outline='#ff4040',width=3)
        self.canvas.create_text(px+8,py-5,text='Current',fill='white',anchor='s')
        self.status=tk.StringVar(value=f'Current visit tile: X {x}, Y {y}')
        ttk.Label(self,textvariable=self.status,padding=8).pack(fill='x')
        self.canvas.bind('<Motion>',self.hover)
        self.canvas.bind('<Button-1>',self.choose)
        self.canvas.bind('<MouseWheel>',self.scroll)
        self.canvas.bind('<Button-4>',lambda e:self.canvas.yview_scroll(-3,'units'))
        self.canvas.bind('<Button-5>',lambda e:self.canvas.yview_scroll(3,'units'))
        ttk.Button(self,text='Cancel',command=self.close).pack(pady=6)
        self.protocol('WM_DELETE_WINDOW',self.close)
        self.bind('<Escape>',lambda _:self.close())
        self.update_idletasks()
        self.canvas.xview_moveto(max(0,(px-self.canvas.winfo_width()/2)/width))
        self.canvas.yview_moveto(max(0,(py-self.canvas.winfo_height()/2)/height))

    def scroll(self,event):
        move=self.canvas.xview_scroll if event.state&1 else self.canvas.yview_scroll
        move(-3 if event.delta>0 else 3,'units')
        return 'break'

    def point(self,event):
        return self.origin[0]+int(self.canvas.canvasx(event.x)//16),self.origin[1]+int(self.canvas.canvasy(event.y)//16)

    def hover(self,event):
        x,y=self.point(event)
        self.status.set(f'X {x}, Y {y} — click to select the visitable entrance tile.')

    def choose(self,event):
        x,y=self.point(event)
        try:
            VillageLocation(self.owner.rom,self.owner.current).validate(x,y)
        except ValueError as error:
            self.status.set(str(error));return
        self.owner.location_position=(x,y);self.owner.show_location()
        self.owner.status.set('New village location staged. Write rewards to ROM to save it.')
        self.close()

    def close(self):
        owner=self.owner;self.destroy()
        if owner.winfo_exists():owner.grab_set()


def open_village_window(app):
    if not app.rom:
        messagebox.showinfo('Village Rewards','Open a ROM first.',parent=app);return
    if not app.settle():return
    try:Village(app.rom,0)
    except ValueError as error:
        messagebox.showerror('Unsupported village layout',str(error),parent=app);return
    return VillageWindow(app)
