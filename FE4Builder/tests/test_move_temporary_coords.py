import unittest,tempfile
from pathlib import Path
from copy import copy
from unittest.mock import patch
from rom import ROOT,Rom
from event_commands import EventCommands,catalogue

class MoveTemporaryCoordsTests(unittest.TestCase):
    def test_headers_modes_packed_flags_exact_changes_invalid_and_stale(self):
        rom=Rom(next(ROOT.glob('*.sfc')));original=bytes(rom.data);count=0
        for i,e in enumerate(catalogue()['entries'][:18]):
            for n,c in enumerate(e['commands']):
                if c['opcode']!=0x22:continue
                count+=1
                for header in (0,512):
                    for mode in (0,1,2):
                        r=copy(rom);r.header=header;r.data=bytearray(header)+original
                        at=e['profile']['start']+c['offset']+header
                        r.data[at+7]|=128
                        m=EventCommands(r,i);before=bytes(r.data)
                        values=[1,10,11,12,13,3,mode,2,1]
                        for field,bad in ((0,697),(1,64),(3,-1),(5,0),(5,6),(6,3),(7,3),(8,2),(5,True)):
                            invalid=values.copy();invalid[field]=bad
                            with self.assertRaises(ValueError):m.write({n:invalid})
                            self.assertEqual(bytes(r.data),before)
                        m.write({n:values})
                        self.assertEqual(r.data[at+7],128|16|(mode<<5)|3)
                        self.assertEqual(EventCommands(r,i).values(n),values)
                        self.assertEqual(r.data[:at+1],before[:at+1]);self.assertEqual(r.data[at+9:],before[at+9:])
                        with self.assertRaises(ValueError):m.write({n:[1,1,2,3,4,2,0,2,0]})
                r=copy(rom);r.data=bytearray(original);m=EventCommands(r,i)
                values=m.values(n);self.assertEqual(values[1:3],[255,255])
                values[6]=0;before=bytes(r.data)
                with self.assertRaises(ValueError):m.write({n:values})
                self.assertEqual(bytes(r.data),before)
        self.assertEqual(count,1)

    def test_gui_slot_sources_save_failure_backup_undo_redo(self):
        from FE4Builder import App
        rom=Rom(next(ROOT.glob('*.sfc')))
        with tempfile.TemporaryDirectory(dir=ROOT/'FE4Builder/research') as folder:
            path=Path(folder)/'move.sfc';path.write_bytes(rom.data);before=path.read_bytes()
            app=App();app.withdraw();app.rom=Rom(path)
            try:
                i=next(i for i,e in enumerate(catalogue()['entries'][:18]) if any(c['opcode']==0x22 for c in e['commands']))
                w=app.edit_events(catalogue()['entries'][i]['id']);n=next(n for n,c in enumerate(w.model.commands) if c['opcode']==0x22)
                w.commands.selection_set(str(n));w.select_command();self.assertEqual(len(w.variables),9)
                self.assertEqual(w.field_options[0][w.variables[0].get()],260)
                self.assertEqual(str(w.fields.grid_slaves(row=1,column=1)[0]['state']),'disabled')
                w.variables[6].set(next(k for k,v in w.field_options[6].items() if v==2))
                self.assertEqual(str(w.fields.grid_slaves(row=1,column=1)[0]['state']),'normal')
                self.assertEqual(str(w.fields.grid_slaves(row=3,column=1)[0]['state']),'disabled')
                w.variables[1].set('10');w.variables[2].set('11')
                w.variables[0].set(next(k for k,v in w.field_options[0].items() if v==1))
                self.assertTrue(w.pending());self.assertEqual(path.read_bytes(),before)
                with patch.object(app.rom,'save_original',side_effect=OSError('test')),patch('event_command_window.messagebox.showerror'):
                    self.assertFalse(w.save());self.assertEqual(bytes(app.rom.data),before)
                self.assertTrue(w.save());self.assertEqual(app.rom.last_backup.read_bytes(),before)
                self.assertEqual(EventCommands(app.rom,i).values(n)[6],2)
                w.history(False);self.assertEqual(path.read_bytes(),before)
                w.history(True);self.assertEqual(EventCommands(app.rom,i).values(n)[6],2);w.destroy()
            finally:app.destroy()
