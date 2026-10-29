"""Prologue command editor: edit verified operands, keep the surrounding script intact."""
import tkinter as tk
from tkinter import ttk,messagebox
from rom import number
from events import hex_dump
from event_commands import EventCommands,catalogue,FIELDS,HELP,schema,character_options,audio_kind,audio_options,deployment_options,talk_options,BACKGROUNDS,unit_groups,group_units
from ui_common import ask_unsaved,scrollable_frame

class EventCommandWindow(tk.Toplevel):
    def __init__(self,app,event_id=None):
        super().__init__(app);self.app=app;self.rom=app.rom;self.current=None;self.model=None;self.command=None;self.variables=[];self.field_options=[];self.drafts={};self.loaded={};self._parameter_reset=None
        self.title('FE4Builder — Event Editor (Prologue)');self.geometry('1200x780');self.minsize(940,620)
        self.names=character_options(self.rom)
        self.transient(app);self.grab_set()
        top=ttk.Frame(self,padding=12);top.pack(fill='x')
        ttk.Label(top,text='Event Editor · Prologue',style='Title.TLabel').pack(side='left')
        ttk.Button(top,text='Write to ROM',command=self.save).pack(side='right')
        ttk.Button(top,text='Save & Launch (F5)',command=self.launch).pack(side='right',padx=8)
        ttk.Label(self,text='Edit unit deployments, music, sound commands, sprite preparation, cameras, pauses and fades. Other commands are read-only.\n'
                  'Script length and command order are preserved. Route edits create private copies. Test edited scenes in-game.',padding=(12,0)).pack(anchor='w')
        body=ttk.Panedwindow(self,orient='horizontal');body.pack(fill='both',expand=True,padx=12,pady=8)
        left=ttk.Frame(body);body.add(left,weight=1)
        ttk.Label(left,text='Prologue scripts').pack(anchor='w')
        frame=ttk.Frame(left);frame.pack(fill='both',expand=True)
        self.list=tk.Listbox(frame,exportselection=False,width=32);bar=ttk.Scrollbar(frame,command=self.list.yview)
        bar.pack(side='right',fill='y');self.list.config(yscrollcommand=bar.set);self.list.pack(fill='both',expand=True)
        self.list.bind('<<ListboxSelect>>',self.select)
        right=ttk.Frame(body);body.add(right,weight=3)
        self.heading=tk.StringVar();ttk.Label(right,textvariable=self.heading,font=('Segoe UI',12,'bold')).pack(anchor='w')
        frame=ttk.Frame(right);frame.pack(fill='both',expand=True,pady=8)
        self.commands=ttk.Treeview(frame,columns=('state','address','command'),show='headings',selectmode='browse',height=9)
        for name,title,width in [('state','Capability',85),('address','PC address',85),('command','Command / loaded parameters',500)]:
            self.commands.heading(name,text=title);self.commands.column(name,width=width,stretch=name=='command')
        bar=ttk.Scrollbar(frame,command=self.commands.yview);bar.pack(side='right',fill='y')
        self.commands.config(yscrollcommand=bar.set);self.commands.pack(fill='both',expand=True)
        self.commands.bind('<<TreeviewSelect>>',self.select_command)
        shell=ttk.Frame(right,height=190);shell.pack(fill='both',expand=True)
        self.parameters=scrollable_frame(shell,padding=8);self.parameter_canvas=self.parameters.master
        self.command_heading=tk.StringVar();ttk.Label(self.parameters,textvariable=self.command_heading,font=('Segoe UI',11,'bold')).pack(anchor='w')
        self.help=tk.StringVar();self.help_label=ttk.Label(self.parameters,textvariable=self.help,wraplength=680,justify='left',anchor='nw')
        self.fields=ttk.Frame(self.parameters);self.fields.pack(fill='x')
        self.help_label.pack(anchor='w',pady=8)
        self.raw=tk.StringVar();self.raw_label=ttk.Label(self.parameters,textvariable=self.raw,font=('Consolas',10),wraplength=680,justify='left');self.raw_label.pack(anchor='w',pady=8)
        self.parameters.bind('<Configure>',self.wrap_parameter_help,add='+')
        actions=ttk.Frame(right);actions.pack(fill='x',pady=8)
        self.dialogue_button=ttk.Button(actions,text='Open in Dialogue Editor…',command=self.open_dialogue,state='disabled');self.dialogue_button.pack(side='right',padx=6)
        self.ai_button=ttk.Button(actions,text='Inspect selected AI…',command=self.inspect_ai,state='disabled');self.ai_button.pack(side='right',padx=6)
        self.audio_button=ttk.Button(actions,text='Preview audio…',command=self.preview_audio,state='disabled');self.audio_button.pack(side='right')
        ttk.Button(actions,text='Reload script',command=self.reload).pack(side='left')
        ttk.Button(actions,text='Undo ROM',command=lambda:self.history(False)).pack(side='left',padx=6)
        ttk.Button(actions,text='Redo ROM',command=lambda:self.history(True)).pack(side='left')
        ttk.Button(actions,text='View event / linked editors',command=self.open_viewer).pack(side='left',padx=6)
        self.status=tk.StringVar();ttk.Label(self,textvariable=self.status,padding=8,wraplength=1120,relief='sunken').pack(side='bottom',fill='x')
        self.visible=list(range(len(catalogue()['entries'])))
        for e in catalogue()['entries']:
            count=sum(c['editable'] for c in e['commands']);self.list.insert('end',f'{e["id"]:03X} · {e["label"]} ({count})')
        index=next((i for i,e in enumerate(catalogue()['entries']) if e['id']==event_id),0)
        self.list.selection_set(index);self.load(index)
        self.protocol('WM_DELETE_WINDOW',self.close);self.bind('<F5>',lambda _:self.launch())

    def remember_command(self):
        if self.command in self.drafts:
            self.drafts[self.command]=tuple(str(options.get(var.get(),var.get())) for var,options in zip(self.variables,self.field_options))
            item=str(self.command)
            if self.commands.exists(item):self.commands.set(item,'state','Editable *' if self.drafts[self.command]!=self.loaded.get(self.command) else 'Editable')
    def pending(self):
        self.remember_command();return self.model is not None and self.drafts!=self.loaded
    def settle(self):
        if not self.pending():return True
        answer=ask_unsaved(self,'Write the staged Prologue command changes to the opened ROM?')
        return False if answer is None else self.save() if answer else True
    def select(self,_=None):
        selected=self.list.curselection()
        if not selected:return
        index=self.visible[selected[0]]
        if index==self.current:return
        if self.settle():self.load(index)
        else:
            self.list.selection_clear(0,'end');self.list.selection_set(self.visible.index(self.current))
    def load(self,index):
        self.current=index;self.model=None;self.command=None;self.variables=[];self.field_options=[];self.drafts={};self.loaded={}
        self.commands.delete(*self.commands.get_children());self.command_heading.set('');self.help.set('');self.raw.set('')
        self.clear_parameter_fields()
        self.audio_button.config(state='disabled');self.ai_button.config(state='disabled');self.dialogue_button.config(state='disabled')
        self.heading.set(catalogue()['entries'][index]['label'])
        try:self.model=EventCommands(self.rom,index)
        except ValueError as error:self.status.set('Editing disabled: '+str(error));return
        for i,c in enumerate(self.model.commands):
            if c['editable']:self.drafts[i]=tuple(map(str,self.model.values(i)))
            self.commands.insert('','end',iid=str(i),values=('Editable' if c['editable'] else 'Read-only',f'{self.model.profile["start"]+c["offset"]:06X}',self.model.describe(i)))
        self.loaded=self.drafts.copy()
        selected=next(iter(self.drafts),0);self.commands.selection_set(str(selected));self.commands.see(str(selected));self.select_command()
        self.status.set('Loaded live operands from a verified layout. Edits remain pending until Write to ROM. No commands are inserted or removed.')
    def select_command(self,_=None):
        selected=self.commands.selection()
        if not selected or self.model is None:return
        index=int(selected[0])
        if index==self.command:return
        self.remember_command();self.command=index;self.variables=[];self.field_options=[]
        self.clear_parameter_fields()
        c=self.model.commands[index];self.dialogue_button.config(state='normal' if c['opcode'] in (0x0c,0x14) else 'disabled');self.ai_button.config(state='normal' if c['opcode']==0x24 else 'disabled');self.command_heading.set(f'Command {index+1} · '+c['name'].replace('_',' ').title())
        self.audio_button.config(state='normal' if c['opcode'] in (0x0e,0x11,0x12) else 'disabled')
        self.help.set(HELP.get(schema(c),'Read-only command. Use the linked dialogue, reinforcement, conversation or objective editor where supported.'))
        if FIELDS.get(schema(c)):self.fields.pack(fill='x',before=self.help_label)
        for i,(label,offset,size,low,high) in enumerate(FIELDS.get(schema(c),[])):
            ttk.Label(self.fields,text=label if c['opcode']==0x42 and i==1 else label+f' ({low}–{high})').grid(row=i,column=0,sticky='w',padx=(0,12),pady=4)
            options={f'{name} (0x{value:04X})':value for value,name in self.names.items()} if schema(c)=='character_sprite' else {}
            if c['opcode'] in (0x4b,0x4c):
                from event_commands import chapter_flag_options
                from events import CHAPTERS
                chapter=number(self.drafts[index][0])
                known=dict(enumerate(CHAPTERS)) if i==0 else chapter_flag_options(chapter)
                old=number(self.drafts[index][i])
                if old not in known:known[old]='Existing unsupported value (preserve only)'
                options={f'{name} [ID {value}]':value for value,name in known.items()}
            if c['opcode']==0x23 and i in (0,1):
                if i==0:known=unit_groups(self.rom)
                else:
                    group=number(self.drafts[index][0]);known={k:v['label'] for k,v in group_units(self.rom,group).items()}
                old=number(self.drafts[index][i])
                if old not in known:known[old]=f'Existing unknown value {old}'
                options={name+f' [ID {value}]':value for value,name in known.items()}
            if c['opcode']==0x42:
                known=dict(self.names) if i==0 else {0:'Slot 1',1:'Slot 2'}
                old=self.model.values(index)[i]
                if old not in known:known[old]=f'Existing value ${old:X}'
                options={f'{name} (${value:04X})':value for value,name in known.items()} if i==0 else {name:value for value,name in known.items()}
            if schema(c)=='talk_target':
                known=talk_options(self.rom,i);old=self.model.values(index)[i]
                if old not in known:known[old]=f'Existing unknown character ${old:02X}'
                options={f'{name} (${value:02X})':value for value,name in known.items()}
            if c['opcode'] in (0x24,0x27):
                from event_commands import temporary_options
                known=temporary_options(self.rom,i) if c['opcode']==0x27 else deployment_options(self.rom,i)
                if known:
                    current_value=self.model.values(index)[i]
                    if current_value not in known:known[current_value]=f'Existing unknown {current_value}'
                    options={f'{name} ({value})':value for value,name in known.items()}
            if audio_kind(c):
                known=audio_options(c)
                current_value=self.model.values(index)[i]
                if current_value not in known:known[current_value]=f'Existing unknown ${current_value:04X}'
                options={f'{name} (0x{value:04X})':value for value,name in known.items()}
            if c['opcode'] in (0x0c,0x14) and i==0:
                options={o['label']+f" (${o['pointer']:06X})":o['pointer'] for o in self.model.dialogues()}
                old=self.model.values(index)[i]
                if old not in options.values():options[f'Existing scene (${old:06X})']=old
            if c['opcode']==0x14 and i==1:
                known=dict(BACKGROUNDS);old=self.model.values(index)[i]
                if old not in known:known[old]=f'Existing unknown background {old}'
                options={f'{name} ({value})':value for value,name in known.items()}
            value=self.drafts[index][i]
            if options:value=next((label for label,key in options.items() if str(key)==value),value)
            var=tk.StringVar(value=value);self.variables.append(var);self.field_options.append(options)
            widget=ttk.Combobox(self.fields,state='readonly',textvariable=var,values=list(options),width=38) if options else ttk.Spinbox(self.fields,from_=low,to=high,textvariable=var,width=12)
            widget.grid(row=i,column=1,sticky='w')
            if c['opcode']==0x14 and i==1:
                ttk.Button(self.fields,text='Edit background…',command=self.open_background).grid(row=i,column=2,padx=6)
            if c['opcode'] in (0x0c,0x14) and i==0:
                widget.config(width=48)
                ttk.Button(self.fields,text='Find dialogue…',command=self.choose_dialogue).grid(row=i,column=2,padx=6)
            if c['opcode']==0x12:
                def explain_word(*_,v=var,choices=options):
                    from sound_words import describe_word
                    text=v.get()
                    try:value=choices[text] if text in choices else number(text)
                    except ValueError:self.help.set(HELP[0x12]);return
                    self.help.set(HELP[0x12]+'\n\n'+describe_word(value))
                var.trace_add('write',explain_word);explain_word()
        if c['opcode'] in (0x4b,0x4c):
            def update_flags(*_):
                from event_commands import chapter_flag_options
                chapter=self.field_options[0].get(self.variables[0].get())
                if chapter is None:return
                value=self.field_options[1].get(self.variables[1].get())
                if value is None:
                    try:value=number(self.variables[1].get())
                    except ValueError:return
                known=chapter_flag_options(chapter)
                if value not in known:known[value]='Existing unsupported value (preserve only)'
                options={f'{name} [ID {key}]':key for key,name in known.items()}
                self.field_options[1]=options
                self.fields.grid_slaves(row=1,column=1)[0].config(values=list(options))
                self.variables[1].set(next(label for label,key in options.items() if key==value))
                self.remember_command()
            self.variables[0].trace_add('write',update_flags)
        if c['opcode']==0x27:
            from movement_routes import route_preview
            raw_command=self.model.snapshot[c['offset']:c['offset']+c['size']]
            pointer=int.from_bytes(raw_command[7:10],'little')
            ttk.Button(self.fields,text='Edit movement route...',command=self.open_route).grid(row=6,column=0,columnspan=2,sticky='w',pady=8)
            self.help.set(HELP[0x27]+'\n\n'+route_preview(self.rom,pointer))
        if c['opcode']==0x23:
            self.configure_group_load(index,c)
        if c['opcode']==0x14:
            mode=self.model.snapshot[c['offset']+5]
            ttk.Label(self.fields,text=f'Dialogue Type: {mode} (read-only; preserved)').grid(row=3,column=0,columnspan=3,sticky='w',pady=6)
        raw=self.model.snapshot[c['offset']:c['offset']+c['size']]
        self.raw.set('Loaded command bytes (read-only):\n'+hex_dump(raw,self.model.profile['start']+c['offset']))
        if self._parameter_reset is not None:self.after_cancel(self._parameter_reset)
        self._parameter_reset=self.after_idle(self.reset_parameter_view)
    def configure_group_load(self,index,command):
        def value(i):
            text=self.variables[i].get()
            return self.field_options[i][text] if text in self.field_options[i] else number(text)
        def explain(*_):
            if self.command!=index:return
            try:unit=group_units(self.rom,value(0))[value(1)]
            except (ValueError,KeyError):self.help.set(HELP[0x23]+'\n\nChoose an existing entry in the selected group.');return
            color=self.model.snapshot[command['offset']+7]
            self.help.set(HELP[0x23]+f"\n\nArmy record (read-only here): {unit['label']}; destination ({unit['x']}, {unit['y']}); faction slot {unit['faction']}; AI {unit['ai']}; commander {'Yes' if unit['leader'] else 'No'}; formation {unit['formation']}. Stored sprite color: {color} (preserved).")
        def group_changed(*_):
            if self.command!=index:return
            try:previous=value(1)
            except ValueError:previous=None
            try:units=group_units(self.rom,value(0))
            except ValueError:return
            options={u['label']+f' [ID {k}]':k for k,u in units.items()}
            self.field_options[1]=options
            widget=self.fields.grid_slaves(row=1,column=1)[0];widget.config(values=list(options))
            self.variables[1].set(next((k for k,v in options.items() if v==previous),next(iter(options),'')))
            explain()
        self.variables[0].trace_add('write',group_changed);self.variables[1].trace_add('write',explain);explain()

    def clear_parameter_fields(self):
        # An empty grid frame can retain the previous command's requested height.
        # Recreate it, and only display it when the selected command has operands.
        self.fields.destroy();self.fields=ttk.Frame(self.parameters)
    def wrap_parameter_help(self,event):
        width=max(120,event.width-16)
        self.help_label.config(wraplength=width);self.raw_label.config(wraplength=width)
    def reset_parameter_view(self):
        self._parameter_reset=None
        if not self.winfo_exists():return
        self.update_idletasks()
        self.parameter_canvas.configure(scrollregion=self.parameter_canvas.bbox('all'))
        self.parameter_canvas.yview_moveto(0)

    def open_background(self):
        if self.model is None or self.command is None or self.model.commands[self.command]['opcode']!=0x14:return
        self.remember_command()
        try:index=number(self.drafts[self.command][1])
        except ValueError:return
        window=self.app.edit_background(index)
        if window:
            window.transient(self)
            window.bind('<Destroy>',lambda event:self.grab_set() if event.widget is window and self.winfo_exists() else None,add='+')

    def choose_dialogue(self):
        if self.model is None or self.command is None:return
        choices=self.model.dialogues()
        if not choices:messagebox.showinfo('Dialogue unavailable','No supported dialogue scenes are available for this ROM profile.',parent=self);return
        from dialogue_picker import DialoguePicker
        def chosen(scene):
            value=scene['pointer'];label=next(k for k,v in self.field_options[0].items() if v==value)
            self.variables[0].set(label);self.remember_command()
        DialoguePicker(self,choices,chosen)

    def open_dialogue(self):
        if self.model is None or self.command is None:return
        command=self.command
        if not self.settle():return
        # Discard also restores the loaded pointer before opening its text.
        self.load(self.current)
        node=self.model.commands[command]
        from dialogue import check_profile
        try:check_profile(self.rom)
        except ValueError as error:messagebox.showerror('Unsupported dialogue layout',str(error),parent=self);return
        entry=dict(address=self.model.profile['start']+node['offset']+1,group='Prologue',label=self.model.entry['label']+f' / command {command+1}',section='Events')
        from dialogue_window import DialogueWindow
        window=DialogueWindow(self.app,entry);window.transient(self)
        def closed(event):
            if event.widget is window and self.winfo_exists():
                self.load(self.current);self.commands.selection_set(str(command));self.select_command();self.grab_set()
        window.bind('<Destroy>',closed,add='+')

    def inspect_ai(self):
        if self.model is None or self.command is None or self.model.commands[self.command]['opcode']!=0x24:return
        self.remember_command()
        try:faction=number(self.drafts[self.command][1]);group=number(self.drafts[self.command][9])
        except ValueError:messagebox.showerror('Invalid AI selection','Choose a valid faction and AI group first.',parent=self);return
        window=self.app.view_ai(self.model.entry['chapter'],faction,group)
        if window:
            window.transient(self)
            window.bind('<Destroy>',lambda event:self.grab_set() if event.widget is window and self.winfo_exists() else None,add='+')

    def preview_audio(self):
        if self.model is None or self.command is None:return
        c=self.model.commands[self.command];kind={0x0e:'music',0x11:'byte',0x12:'word'}.get(c['opcode'])
        if kind is None:return
        self.remember_command()
        try:value=number(self.drafts[self.command][0])
        except ValueError:messagebox.showerror('Invalid audio selection','Choose a named music/effect option before previewing.',parent=self);return
        self.app.open_audio(kind,value,autoplay=True)

    def open_route(self):
        if self.model is None or self.command is None:return
        command=self.command
        if self.model.commands[command]['opcode']!=0x27:return
        if not self.settle():return
        if self.pending():self.load(self.current)
        from route_window import RouteWindow
        try:RouteWindow(self,self.current,command)
        except ValueError as error:messagebox.showerror('Route unavailable',str(error),parent=self)

    def save(self):
        if self.model is None:return False
        if self.app.rom is not self.rom:messagebox.showerror('ROM changed','Reopen Event Editor for the current ROM.',parent=self);return False
        if not self.pending():self.status.set('No pending command edits.');return True
        before=bytes(self.rom.data)
        try:
            updates={}
            for i,values in self.drafts.items():
                updates[i]=[]
                for value,field in zip(values,FIELDS[schema(self.model.commands[i])]):
                    try:updates[i].append(number(value.strip()))
                    except ValueError:raise ValueError(f'Command {i+1}: {field[0]} needs a decimal number or 0x hexadecimal value.')
            details=self.model.write(updates)
            if details:self.rom.save_original('Event commands: '+self.model.entry['label'],details)
        except (ValueError,OSError,OverflowError) as error:
            self.rom.data[:]=before;messagebox.showerror('Cannot save event commands',str(error),parent=self);return False
        self.app.refresh_after_history();self.load(self.current);self.status.set('Saved to the original ROM with automatic backup and undo history.');return True
    def reload(self):
        if self.pending() and not messagebox.askyesno('Reload script','Discard the current command draft?',parent=self):return
        self.load(self.current)
    def history(self,redo):
        if not self.settle():return
        try:self.rom.redo() if redo else self.rom.undo()
        except (ValueError,OSError) as error:messagebox.showerror('History unavailable',str(error),parent=self);return
        self.app.refresh_after_history();self.load(self.current)
    def launch(self):return self.app.save_and_launch(save_callback=self.save,parent=self)
    def open_viewer(self):
        if not self.settle():return
        if self.pending():self.load(self.current)
        window=self.app.view_events()
        if window:
            self.grab_release();window.transient(self)
            window.bind('<Destroy>',lambda event:self.grab_set() if event.widget is window and self.winfo_exists() else None,add='+')
            window.chapter.current(0);window.search.set('');window.populate()
            match=next((i for i,(trigger,e) in enumerate(window.visible) if not trigger and e['id']==self.model.entry['id']),None) if self.model else None
            if match is not None:window.list.selection_clear(0,'end');window.list.selection_set(match);window.select()
    def destroy(self):
        if self._parameter_reset is not None:
            self.after_cancel(self._parameter_reset);self._parameter_reset=None
        super().destroy()
    def close(self):
        if self.settle():self.destroy()

def open_event_command_window(app,event_id=None):
    if not app.rom:messagebox.showinfo('Open a ROM','Open a FE4 ROM first.',parent=app);return
    if app.settle():return EventCommandWindow(app,event_id)
