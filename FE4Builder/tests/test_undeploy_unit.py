import unittest,tempfile
from pathlib import Path
from copy import copy
from unittest.mock import patch
from rom import ROOT,Rom
from event_commands import EventCommands,catalogue,schema

class UndeployTests(unittest.TestCase):
    def test_operand_only_headers_invalid_stale(self):
        rom=Rom(next(ROOT.glob('*.sfc')));original=bytes(rom.data);count=0
        for index,e in enumerate(catalogue()['entries'][:18]):
            for n,c in enumerate(e['commands']):
                if schema(c)!='undeploy_unit':continue
                count+=1
                for header in (0,512):
                    r=copy(rom);r.header=header;r.data=bytearray(header)+original;model=EventCommands(r,index);before=bytes(r.data)
                    for value in (0,-1,697,65535,True,1.5):
                        with self.assertRaises(ValueError):model.write({n:[value]})
                        self.assertEqual(bytes(r.data),before)
                    model.write({n:[1]});self.assertEqual(EventCommands(r,index).values(n),[1])
                    at=e['profile']['start']+c['offset']+2+header
                    self.assertTrue(all(a==b or i in (at,at+1) for i,(a,b) in enumerate(zip(before,r.data))))
                    self.assertEqual(r.data[at:at+2],b'\x01\x00')
                    with self.assertRaises(ValueError):model.write({n:[2]})
        self.assertEqual(count,5)
    def test_selector_portrait_save_failure_history(self):
        from FE4Builder import App
        rom=Rom(next(ROOT.glob('*.sfc')))
        with tempfile.TemporaryDirectory(dir=ROOT/'FE4Builder/research') as folder:
            path=Path(folder)/'undeploy.sfc';path.write_bytes(rom.data);before=path.read_bytes();app=App();app.withdraw();app.rom=Rom(path)
            try:
                index=next(i for i,e in enumerate(catalogue()['entries'][:18]) if any(schema(c)=='undeploy_unit' for c in e['commands']))
                w=app.edit_events(catalogue()['entries'][index]['id']);n=next(i for i,c in enumerate(w.model.commands) if schema(c)=='undeploy_unit')
                w.commands.selection_set(str(n));w.select_command();self.assertEqual(len(w.variables),1)
                w.variables[0].set(next(k for k,v in w.field_options[0].items() if v==1));self.assertIn('Sigurd',w.variables[0].get())
                face=w.fields.grid_slaves(row=1,column=0)[0];self.assertIsNotNone(face.photo)
                self.assertTrue(w.pending());self.assertEqual(path.read_bytes(),before)
                with patch.object(app.rom,'save_original',side_effect=OSError('test')),patch('event_command_window.messagebox.showerror'):
                    self.assertFalse(w.save());self.assertEqual(bytes(app.rom.data),before)
                self.assertTrue(w.save());self.assertEqual(app.rom.last_backup.read_bytes(),before)
                self.assertEqual(EventCommands(app.rom,index).values(n),[1]);w.history(False);self.assertEqual(path.read_bytes(),before)
                w.history(True);self.assertEqual(EventCommands(app.rom,index).values(n),[1]);w.destroy()
            finally:app.destroy()
