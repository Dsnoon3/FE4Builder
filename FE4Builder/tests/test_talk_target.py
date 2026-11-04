import tempfile,unittest
from pathlib import Path
from copy import copy
from tkinter import ttk
from rom import ROOT,Rom
from event_commands import catalogue,EventCommands,schema,talk_options

class TalkTargetTests(unittest.TestCase):
    def setUp(self):
        self.rom=Rom(next(ROOT.glob('*.sfc')))
        self.index=next(i for i,e in enumerate(catalogue()['entries'][:18]) if any(schema(c)=='talk_target' for c in e['commands']))
    def test_exact_operands_atomic_validation_header_and_opcodes(self):
        original=bytes(self.rom.data);count=0
        for index,e in enumerate(catalogue()['entries'][:18]):
            for command,c in enumerate(e['commands']):
                if schema(c)!='talk_target':continue
                count+=1;model=EventCommands(self.rom,index);at=model.profile['start']+c['offset']
                self.assertEqual(self.rom.data[at:at+2],bytes([0x4a,0x68]))
                for bad in ([256,1],[0,1],[1,256],[-1,1],[1],[1,1.5]):
                    with self.assertRaises(ValueError):model.write({command:bad})
                    self.assertEqual(bytes(self.rom.data),original)
                model.write({command:[2,0]})
                self.assertEqual(self.rom.data[at:at+4],bytes([0x4a,0x68,2,0]))
                self.assertEqual(self.rom.data[:at],original[:at]);self.assertEqual(self.rom.data[at+4:],original[at+4:])
                self.assertEqual(EventCommands(self.rom,index).values(command),[2,0])
                self.rom.data[:]=original
                headered=copy(self.rom);headered.data=bytearray(512)+self.rom.data;headered.header=512
                EventCommands(headered,index).write({command:[2,3]})
                self.assertEqual(EventCommands(headered,index).values(command),[2,3])
                self.rom.data[at+1]^=1
                with self.assertRaises(ValueError):EventCommands(self.rom,index)
                self.rom.data[:]=original
        self.assertEqual(count,4)
    def test_named_dropdown_draft_save_undo_and_other_editor_compatibility(self):
        from FE4Builder import App
        from conversations import Conversation,catalogue as conversations
        original=bytes(self.rom.data)
        with tempfile.TemporaryDirectory(dir=ROOT/'FE4Builder/research') as folder:
            path=Path(folder)/'talk.sfc';path.write_bytes(original)
            app=App();app.withdraw();app.rom=Rom(path)
            try:
                window=app.edit_events(catalogue()['entries'][self.index]['id'])
                command=next(i for i,c in enumerate(window.model.commands) if schema(c)=='talk_target')
                window.commands.selection_set(str(command));window.select_command()
                self.assertEqual(len(window.variables),2)
                self.assertEqual(sum(isinstance(w,ttk.Combobox) for w in window.fields.winfo_children()),2)
                self.assertTrue(all(0<=v<=255 for options in window.field_options for v in options.values()))
                for i,value in enumerate((2,3)):window.variables[i].set(next(k for k,v in window.field_options[i].items() if v==value))
                self.assertTrue(window.pending());self.assertEqual(path.read_bytes(),original)
                other=next(i for i,c in enumerate(window.model.commands) if i!=command)
                window.commands.selection_set(str(other));window.select_command()
                window.commands.selection_set(str(command));window.select_command()
                self.assertEqual(window.drafts[command],('2','3'))
                self.assertTrue(window.save());self.assertEqual(EventCommands(app.rom,self.index).values(command),[2,3])
                for index,entry in enumerate(conversations()['entries']):
                    if window.model.entry['id'] in entry['events']:Conversation(app.rom,index)
                self.assertEqual(app.rom.last_backup.read_bytes(),original)
                window.history(False);self.assertEqual(path.read_bytes(),original)
                window.history(True);self.assertEqual(EventCommands(app.rom,self.index).values(command),[2,3])
                window.destroy()
            finally:app.destroy()
