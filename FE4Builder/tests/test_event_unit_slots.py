import tempfile,unittest
from copy import copy
from pathlib import Path
from rom import ROOT,Rom
from event_commands import EventCommands,catalogue,HELP

class EventUnitSlotTests(unittest.TestCase):
    def setUp(self):
        self.rom=Rom(next(ROOT.glob('*.sfc')))
        self.index=next(i for i,e in enumerate(catalogue()['entries'][:18]) if any(c['opcode']==0x42 for c in e['commands']))
    def test_exact_character_slot_bytes_validation_and_header(self):
        original=bytes(self.rom.data);count=0
        for index,entry in enumerate(catalogue()['entries'][:18]):
            for command,node in enumerate(entry['commands']):
                if node['opcode']!=0x42:continue
                count+=1;model=EventCommands(self.rom,index);at=model.profile['start']+node['offset']
                for bad in ([0,0],[697,0],[1,-1],[1,2],[1],[1,1.5]):
                    with self.assertRaises(ValueError):model.write({command:bad})
                    self.assertEqual(bytes(self.rom.data),original)
                model.write({command:[260,1]})
                self.assertEqual(self.rom.data[at:at+4],bytes([0x42,4,1,1]))
                self.assertEqual(EventCommands(self.rom,index).values(command),[260,1])
                self.assertEqual(self.rom.data[:at],original[:at]);self.assertEqual(self.rom.data[at+4:],original[at+4:])
                self.rom.data[:]=original
                headered=copy(self.rom);headered.header=512;headered.data=bytearray(512)+self.rom.data
                EventCommands(headered,index).write({command:[1,0]})
                self.assertEqual(EventCommands(headered,index).values(command),[1,0])
        self.assertEqual(count,2)
    def test_ui_slots_save_undo_and_camera_help(self):
        from FE4Builder import App
        original=bytes(self.rom.data)
        with tempfile.TemporaryDirectory(dir=ROOT/'FE4Builder/research') as folder:
            path=Path(folder)/'slot.sfc';path.write_bytes(original)
            app=App();app.withdraw();app.rom=Rom(path)
            try:
                w=app.edit_events(catalogue()['entries'][self.index]['id'])
                command=next(i for i,c in enumerate(w.model.commands) if c['opcode']==0x42)
                w.commands.selection_set(str(command));w.select_command()
                self.assertEqual(w.field_options[1],{'Slot 1':0,'Slot 2':1})
                w.variables[0].set(next(k for k,v in w.field_options[0].items() if v==260));w.variables[1].set('Slot 2')
                self.assertTrue(w.pending());self.assertEqual(path.read_bytes(),original)
                self.assertTrue(w.save());self.assertEqual(EventCommands(app.rom,self.index).values(command),[260,1])
                self.assertEqual(app.rom.last_backup.read_bytes(),original)
                w.history(False);self.assertEqual(path.read_bytes(),original)
                w.history(True);self.assertEqual(EventCommands(app.rom,self.index).values(command),[260,1])
                for opcode in (0x39,0x41):
                    matches=[(i,e) for i,e in enumerate(catalogue()['entries'][:18]) if any(c['opcode']==opcode for c in e['commands'])]
                    self.assertIn(opcode,HELP)
                    if not matches:continue  # Scroll-to-slot is not present in the supported Prologue scripts.
                    entry=matches[0]
                    w.load(entry[0]);selected=next(i for i,c in enumerate(w.model.commands) if c['opcode']==opcode)
                    w.commands.selection_set(str(selected));w.select_command();app.update()
                    self.assertEqual(w.help.get(),HELP[opcode]);self.assertFalse(w.variables)
                    self.assertFalse(w.model.commands[selected]['editable'])
                w.destroy()
            finally:app.destroy()
