import tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from rom import ROOT,Rom
from event_commands import catalogue,EventCommands,FIELDS,schema,character_options,audio_kind,audio_options,deployment_options,group_units,temporary_options

class EventCommandTests(unittest.TestCase):
    def setUp(self):self.rom=Rom(next(ROOT.glob('*.sfc')))
    def test_all_catalogued_commands_roundtrip_exact_operands(self):
        original=bytes(self.rom.data);count=0
        self.assertEqual(len(catalogue()['entries']),18)
        for index,e in enumerate(catalogue()['entries']):
            model=EventCommands(self.rom,index);start=model.profile['start'];baseline=model.snapshot
            self.assertEqual(model.write({}),[])
            for command,c in enumerate(model.commands):
                if not c['editable']:continue
                model=EventCommands(self.rom,index);values=model.values(command)
                values=[next(value for value in audio_options(c) if value!=values[0])] if audio_kind(c) else [low if value==high else value+1 for value,(_,_,_,low,high) in zip(values,FIELDS[schema(c)])]
                if c['opcode'] in (0x0c,0x14):values[0]=next(o['pointer'] for o in model.dialogues() if o['pointer']!=model.values(command)[0])
                if c['opcode']==0x23:
                    values[0]=model.values(command)[0];values[1]=next(k for k in group_units(self.rom,values[0]) if k!=model.values(command)[1])
                if c['opcode']==0x27:
                    values=[next((v for v in temporary_options(self.rom,i) if v!=old),value) if temporary_options(self.rom,i) else value for i,(old,value) in enumerate(zip(model.values(command),values))]
                if c['opcode']==0x24:
                    values=[next((v for v in deployment_options(self.rom,i) if v!=old),value) if deployment_options(self.rom,i) else value for i,(old,value) in enumerate(zip(model.values(command),values))]
                details=model.write({command:values});self.assertTrue(details)
                changed={i for i,(a,b) in enumerate(zip(baseline,self.rom.data[start:start+len(baseline)])) if a!=b}
                allowed={c['offset']+offset+j for _,offset,size,_,_ in FIELDS[schema(c)] for j in range(size)}
                self.assertTrue(changed);self.assertTrue(changed<=allowed)
                self.assertEqual(EventCommands(self.rom,index).values(command),values)
                self.rom.data[start:start+len(baseline)]=baseline;count+=1
        self.assertEqual(count,219);self.assertEqual(bytes(self.rom.data),original)
    def test_direct_deployment_packed_fields_and_ui(self):
        from FE4Builder import App
        original=bytes(self.rom.data)
        index=next(i for i,e in enumerate(catalogue()['entries']) if any(c['opcode']==0x24 for c in e['commands']))
        model=EventCommands(self.rom,index)
        command=next(i for i,c in enumerate(model.commands) if c['opcode']==0x24)
        at=model.profile['start']+model.commands[command]['offset']
        # Simulate existing movement flags and reserved AI bits.
        self.rom.data[at+8]|=0x60;self.rom.data[at+10]|=0x50
        model=EventCommands(self.rom,index)
        values=[6,0,10,11,12,13,4,6,1,9]
        model.write({command:values})
        self.assertEqual(EventCommands(self.rom,index).values(command),values)
        self.assertEqual(self.rom.data[at+8],0x64)
        self.assertEqual(self.rom.data[at+10],0xd9)
        baseline=bytes(self.rom.data)
        for field,value in ((0,697),(1,4),(2,64),(6,8),(7,3),(8,2),(9,16)):
            invalid=values.copy();invalid[field]=value
            with self.assertRaises(ValueError):EventCommands(self.rom,index).write({command:invalid})
            self.assertEqual(bytes(self.rom.data),baseline)
        self.rom.data[:]=original
        app=App();app.withdraw();app.rom=self.rom
        try:
            window=app.edit_events(model.entry['id'])
            window.commands.selection_set(str(command));window.select_command()
            self.assertEqual(len(window.variables),10)
            for i in (0,1,7,8):self.assertTrue(window.field_options[i])
            window.variables[8].set(next(k for k,v in window.field_options[8].items() if v==1))
            window.variables[9].set('9');window.remember_command()
            self.assertEqual(window.drafts[command][-2:],('1','9'))
            self.assertEqual(bytes(self.rom.data),original)
            window.destroy()
        finally:app.destroy()

    def test_map_scroll_parameters_validation_and_ui(self):
        from FE4Builder import App
        original=bytes(self.rom.data)
        index=next(i for i,e in enumerate(catalogue()['entries']) if any(c['opcode']==0x40 for c in e['commands']))
        model=EventCommands(self.rom,index)
        command=next(i for i,c in enumerate(model.commands) if c['opcode']==0x40)
        for values in ([64,0,1],[0,-1,1],[0,0,0],[0,0,256],[0,0]):
            with self.assertRaises(ValueError):model.write({command:values})
            self.assertEqual(bytes(self.rom.data),original)
        model.write({command:[12,8,3]})
        self.assertEqual(EventCommands(self.rom,index).values(command),[12,8,3])
        self.rom.data[:]=original
        app=App();app.withdraw();app.rom=self.rom
        try:
            window=app.edit_events(model.entry['id'])
            window.commands.selection_set(str(command));window.select_command()
            self.assertEqual(len(window.variables),3)
            for variable,value in zip(window.variables,('12','8','3')):variable.set(value)
            window.remember_command()
            self.assertEqual(window.drafts[command],('12','8','3'))
            self.assertTrue(window.pending())
            self.assertEqual(bytes(self.rom.data),original)
            window.destroy()
        finally:app.destroy()

    def test_invalid_atomic_stale_layout_and_relocated_rejected(self):
        model=EventCommands(self.rom,0);original=bytes(self.rom.data)
        camera=next(i for i,c in enumerate(model.commands) if c['opcode']==0x3a)
        pause=next(i for i,c in enumerate(model.commands) if c['opcode']==0x34)
        for values in ([-1,0],[64,0],[1.0,2],[1],['1',2]):
            with self.assertRaises(ValueError):model.write({pause:[10],camera:values})
            self.assertEqual(bytes(self.rom.data),original)
        readonly=next(i for i,c in enumerate(model.commands) if not c['editable'])
        with self.assertRaises(ValueError):model.write({readonly:[]})
        model.write({pause:[11]})
        with self.assertRaises(ValueError):model.write({pause:[12]})
        self.rom.data[:]=original;self.rom.data[model.profile['start']]^=1
        with self.assertRaises(ValueError):EventCommands(self.rom,0)
        self.rom.data[:]=original;at=0xfe8bf+model.entry['id']*3;self.rom.data[at:at+3]=(0x2f8020).to_bytes(3,'little')
        with self.assertRaises(ValueError):EventCommands(self.rom,0)
    def test_copier_header_and_other_editor_compatibility(self):
        from reinforcements import Reinforcement,catalogue as reinforcements
        from conversations import Conversation,catalogue as conversations
        original=bytes(self.rom.data)
        for index,e in enumerate(catalogue()['entries']):
            from copy import copy
            headered=copy(self.rom);headered.data=bytearray(512)+self.rom.data;headered.header=512
            model=EventCommands(headered,index)
            for command,c in enumerate(model.commands):
                if c['editable']:
                    values=model.values(command);values[0]=next(v for v in audio_options(c) if v!=values[0]) if audio_kind(c) else values[0]+1
                    if c['opcode'] in (0x0c,0x14):values[0]=next(o['pointer'] for o in model.dialogues() if o['pointer']!=model.values(command)[0])
                    if c['opcode']==0x23:values[0]=model.values(command)[0];values[1]=next(k for k in group_units(self.rom,values[0]) if k!=model.values(command)[1])
                    model.write({command:values})
                    self.assertEqual(EventCommands(headered,index).values(command),values);break
        for index,e in enumerate(catalogue()['entries']):
            model=EventCommands(self.rom,index);command=next(i for i,c in enumerate(model.commands) if c['editable'])
            c=model.commands[command]
            values=model.values(command);values[0]=next(v for v in audio_options(c) if v!=values[0]) if audio_kind(c) else values[0]+1
            if c['opcode'] in (0x0c,0x14):values[0]=next(o['pointer'] for o in model.dialogues() if o['pointer']!=model.values(command)[0])
            if c['opcode']==0x23:values[0]=model.values(command)[0];values[1]=next(k for k in group_units(self.rom,values[0]) if k!=model.values(command)[1])
            model.write({command:values})
            for j,entry in enumerate(reinforcements()['entries']):
                if entry['id']==e['id']:
                    other=Reinforcement(self.rom,j);other.write([u['values'] for u in other.units],[t['turn'] for t in other.triggers])
            for j,entry in enumerate(conversations()['entries']):
                if e['id'] in entry['events']:Conversation(self.rom,j)
        self.assertNotEqual(bytes(self.rom.data),original)
    def test_window_save_failure_history_navigation_and_readonly(self):
        from FE4Builder import App
        with tempfile.TemporaryDirectory(dir=ROOT/'FE4Builder/research') as folder:
            path=Path(folder)/'events.sfc';original=bytes(self.rom.data);path.write_bytes(original)
            app=App();app.withdraw();app.rom=Rom(path)
            try:
                window=app.edit_events(1);app.update();self.assertEqual(window.model.entry['id'],1)
                self.assertTrue(window.bind('<Control-s>'))
                command=next(i for i,c in enumerate(window.model.commands) if c['opcode']==0x3a)
                window.commands.selection_set(str(command));window.select_command();window.variables[0].set('20')
                sprite=next(i for i,c in enumerate(window.model.commands) if schema(c)=='character_sprite')
                window.commands.selection_set(str(sprite));window.select_command()
                window.variables[0].set(next(label for label,key in window.field_options[0].items() if key==6))
                self.assertTrue(window.pending())
                with patch('event_command_window.ask_unsaved',return_value=None):self.assertFalse(window.settle())
                readonly=next(i for i,c in enumerate(window.model.commands) if not c['editable'])
                window.commands.selection_set(str(readonly));window.select_command();self.assertFalse(window.variables);self.assertTrue(window.pending())
                with patch.object(app.rom,'save_original',side_effect=OSError('test failure')),patch('event_command_window.messagebox.showerror'):
                    self.assertFalse(window.save())
                self.assertEqual(bytes(app.rom.data),original);self.assertTrue(window.pending());self.assertEqual(path.read_bytes(),original)
                self.assertTrue(window.save());self.assertFalse(window.pending());self.assertEqual(len(path.read_bytes()),len(original))
                self.assertEqual(app.rom.last_backup.read_bytes(),original)
                self.assertEqual(EventCommands(app.rom,0).values(command)[0],20)
                self.assertEqual(EventCommands(app.rom,0).values(sprite),[6])
                window.history(False);self.assertEqual(path.read_bytes(),original)
                window.history(True);self.assertEqual(EventCommands(app.rom,0).values(command)[0],20)
                self.assertEqual(EventCommands(app.rom,0).values(sprite),[6])
                window.destroy()
                viewer=app.view_events();viewer.list.selection_clear(0,'end');viewer.list.selection_set(1);viewer.select()
                self.assertEqual(viewer.command_event_id,1);self.assertEqual(str(viewer.commands_button['state']),'normal');viewer.destroy()
            finally:app.destroy()

    def test_character_sprite_dropdown_exact_bytes_and_protected_subcommand(self):
        from FE4Builder import App
        from tkinter import ttk
        original=bytes(self.rom.data);model=EventCommands(self.rom,0)
        command=next(i for i,c in enumerate(model.commands) if schema(c)=='character_sprite')
        node=model.commands[command];start=model.profile['start']+node['offset']
        self.assertEqual(original[start:start+2],bytes([0x4a,0x49]))
        self.assertIn(6,character_options(self.rom))
        model.write({command:[6]})
        self.assertEqual(self.rom.data[start:start+4],bytes([0x4a,0x49,6,0]))
        self.assertEqual(self.rom.data[:start],original[:start]);self.assertEqual(self.rom.data[start+4:],original[start+4:])
        self.assertEqual(EventCommands(self.rom,0).values(command),[6])
        for value in (0,697,65535,-1):
            with self.assertRaises(ValueError):EventCommands(self.rom,0).write({command:[value]})
        self.rom.data[start+1]=0x4a
        with self.assertRaises(ValueError):EventCommands(self.rom,0)
        self.rom.data[:]=original
        app=App();app.withdraw();app.rom=self.rom
        try:
            window=app.edit_events(1);window.commands.selection_set(str(command));window.select_command()
            self.assertTrue(any(isinstance(w,ttk.Combobox) for w in window.fields.winfo_children()))
            label=next(label for label,key in window.field_options[0].items() if key==6)
            window.variables[0].set(label);self.assertTrue(window.pending())
            self.assertEqual(window.drafts[command],('6',))
            other=next(i for i,c in enumerate(window.model.commands) if c['opcode']==0x34)
            window.commands.selection_set(str(other));window.select_command()
            window.commands.selection_set(str(command));window.select_command()
            self.assertEqual(window.variables[0].get(),label)
            self.assertEqual(bytes(app.rom.data),original);window.destroy()
        finally:app.destroy()

    def test_audio_draft_preview_and_full_word_save(self):
        from FE4Builder import App
        original=bytes(self.rom.data)
        with tempfile.TemporaryDirectory(dir=ROOT/'FE4Builder/research') as folder:
            path=Path(folder)/'audio-events.sfc';path.write_bytes(original)
            app=App();app.withdraw();app.rom=Rom(path)
            try:
                window=app.edit_events(1)
                command=next(i for i,c in enumerate(window.model.commands) if c['opcode']==0x12)
                node=window.model.commands[command];at=window.model.profile['start']+node['offset']
                window.commands.selection_set(str(command));window.select_command()
                window.variables[0].set(next(label for label,value in window.field_options[0].items() if value==0x7ff7))
                with patch.object(app,'open_audio') as opened:
                    window.preview_audio();opened.assert_called_once_with('word',0x7ff7,autoplay=True)
                self.assertTrue(window.pending());self.assertFalse(app.rom.dirty);self.assertEqual(path.read_bytes(),original)
                self.assertTrue(window.save());self.assertEqual(path.read_bytes()[at:at+3],bytes([0x12,0xf7,0x7f]))
                self.assertEqual(app.rom.last_backup.read_bytes(),original)
                window.history(False);self.assertEqual(path.read_bytes(),original)
                window.history(True);self.assertEqual(path.read_bytes()[at:at+3],bytes([0x12,0xf7,0x7f]))
                window.destroy()
            finally:app.destroy()
    def test_audio_unknown_ids_preserved_but_new_unknown_values_rejected(self):
        for opcode in (0x0e,0x11,0x12):
            index=next(i for i,e in enumerate(catalogue()['entries']) if any(c['opcode']==opcode for c in e['commands']))
            model=EventCommands(self.rom,index);command=next(i for i,c in enumerate(model.commands) if c['opcode']==opcode)
            before=bytes(self.rom.data);unknown=255 if opcode!=0x12 else 65535
            with self.assertRaises(ValueError):model.write({command:[unknown]})
            self.assertEqual(bytes(self.rom.data),before)
            node=model.commands[command];at=model.profile['start']+node['offset']+1;size=2 if opcode==0x12 else 1
            self.rom.data[at:at+size]=unknown.to_bytes(size,'little')
            modified=EventCommands(self.rom,index);self.assertEqual(modified.write({command:[unknown]}),[])
            valid=next(iter(audio_options(node)));modified.write({command:[valid]})
            self.assertEqual(EventCommands(self.rom,index).values(command),[valid])
            self.rom.data[:]=before
