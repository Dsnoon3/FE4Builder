import unittest,tempfile
from pathlib import Path
from copy import copy
from unittest.mock import patch
from rom import Rom,ROOT
from event_commands import EventCommands,catalogue,schema,castle_context

class SetUnitCastleTests(unittest.TestCase):
    def test_parameters_headers_masks_invalid_stale_and_castle_guards(self):
        rom=Rom(next(ROOT.glob('*.sfc')));original=bytes(rom.data);count=0
        for i,e in enumerate(catalogue()['entries'][:18]):
            for n,c in enumerate(e['commands']):
                if schema(c)!='set_unit_castle':continue
                count+=1
                for header in (0,512):
                    r=copy(rom);r.header=header;r.data=bytearray(header)+original
                    model=EventCommands(r,i);before=bytes(r.data)
                    for values in ([0,1],[697,1],[1,255],[1,3],[True,1],[1,1.5]):
                        with self.assertRaises(ValueError):model.write({n:values})
                        self.assertEqual(bytes(r.data),before)
                    model.write({n:[2,1]});self.assertEqual(EventCommands(r,i).values(n),[2,1])
                    at=e['profile']['start']+c['offset']+2+header
                    self.assertEqual(r.data[at:at+3],bytes([2,0,1]))
                    self.assertEqual(r.data[:at],before[:at]);self.assertEqual(r.data[at+3:],before[at+3:])
                    with self.assertRaises(ValueError):model.write({n:[1,0]})
        self.assertEqual(count,10)
        i=next(i for i,e in enumerate(catalogue()['entries'][:18]) if any(schema(c)=='set_unit_castle' for c in e['commands']))
        model=EventCommands(rom,i);n=next(n for n,c in enumerate(model.commands) if schema(c)=='set_unit_castle')
        from objectives import catalogue as objectives
        address=objectives()['chapters'][0]['castles'][0]['address']
        rom.data[address+3]^=1;before=bytes(rom.data)
        with self.assertRaises(ValueError):model.write({n:[2,1]})
        self.assertEqual(bytes(rom.data),before)

    def test_gui_named_castles_rollback_backup_undo_redo(self):
        from FE4Builder import App
        rom=Rom(next(ROOT.glob('*.sfc')))
        with tempfile.TemporaryDirectory(dir=ROOT/'FE4Builder/research') as folder:
            path=Path(folder)/'castle.sfc';path.write_bytes(rom.data);before=path.read_bytes()
            app=App();app.withdraw();app.rom=Rom(path)
            try:
                i=next(i for i,e in enumerate(catalogue()['entries'][:18]) if any(schema(c)=='set_unit_castle' for c in e['commands']))
                w=app.edit_events(catalogue()['entries'][i]['id']);n=next(n for n,c in enumerate(w.model.commands) if schema(c)=='set_unit_castle')
                w.commands.selection_set(str(n));w.select_command();self.assertEqual(len(w.variables),2)
                self.assertIn('Chalphy',w.variables[1].get());self.assertEqual(set(w.field_options[1].values()),{0,1,2})
                w.variables[1].set(next(k for k,v in w.field_options[1].items() if v==1))
                with patch.object(app.rom,'save_original',side_effect=OSError('test')),patch('event_command_window.messagebox.showerror'):
                    self.assertFalse(w.save());self.assertEqual(bytes(app.rom.data),before)
                self.assertTrue(w.save());self.assertEqual(app.rom.last_backup.read_bytes(),before)
                self.assertEqual(EventCommands(app.rom,i).values(n)[1],1)
                w.history(False);self.assertEqual(path.read_bytes(),before)
                w.history(True);self.assertEqual(EventCommands(app.rom,i).values(n)[1],1);w.destroy()
            finally:app.destroy()
