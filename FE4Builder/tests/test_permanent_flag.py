import unittest,tempfile
from pathlib import Path
from copy import copy
from unittest.mock import patch
from rom import ROOT,Rom
from event_commands import EventCommands,catalogue,schema,permanent_flag_options

class PermanentFlagTests(unittest.TestCase):
    def test_operand_only_headers_validation_unknown_and_stale(self):
        rom=Rom(next(ROOT.glob('*.sfc')));original=bytes(rom.data);count=0
        self.assertEqual(permanent_flag_options()[2],'Finn Died')
        for index,e in enumerate(catalogue()['entries']):
            for n,c in enumerate(e['commands']):
                if schema(c)!='set_permanent_flag':continue
                count+=1
                for header in (0,512):
                    r=copy(rom);r.header=header;r.data=bytearray(header)+original;model=EventCommands(r,index);before=bytes(r.data)
                    for value in (-1,256,True,1.5,255):
                        with self.assertRaises(ValueError):model.write({n:[value]})
                        self.assertEqual(bytes(r.data),before)
                    old=model.values(n)[0];value=next(v for v in permanent_flag_options() if v!=old)
                    model.write({n:[value]});self.assertEqual(EventCommands(r,index).values(n),[value])
                    at=e['profile']['start']+c['offset']+2+header
                    self.assertTrue(all(a==b or i==at for i,(a,b) in enumerate(zip(before,r.data))))
                    with self.assertRaises(ValueError):model.write({n:[old]})
                    r.data[at]=255;model=EventCommands(r,index);self.assertEqual(model.write({n:[255]}),[])
        self.assertEqual(count,3)
    def test_selector_explanation_failed_save_backup_undo(self):
        from FE4Builder import App
        rom=Rom(next(ROOT.glob('*.sfc')))
        with tempfile.TemporaryDirectory(dir=ROOT/'FE4Builder/research') as folder:
            path=Path(folder)/'flag.sfc';path.write_bytes(rom.data);before=path.read_bytes();app=App();app.withdraw();app.rom=Rom(path)
            try:
                index=next(i for i,e in enumerate(catalogue()['entries']) if any(schema(c)=='set_permanent_flag' for c in e['commands']))
                w=app.edit_events(catalogue()['entries'][index]['id']);n=next(i for i,c in enumerate(w.model.commands) if schema(c)=='set_permanent_flag')
                w.commands.selection_set(str(n));w.select_command();self.assertEqual(len(w.variables),1)
                old=w.model.values(n)[0];value=2 if old!=2 else 1
                w.variables[0].set(next(k for k,v in w.field_options[0].items() if v==value))
                self.assertIn(permanent_flag_options()[value],w.help.get());self.assertIn('global flag',w.help.get())
                self.assertTrue(w.pending());self.assertEqual(path.read_bytes(),before)
                with patch.object(app.rom,'save_original',side_effect=OSError('test')),patch('event_command_window.messagebox.showerror'):
                    self.assertFalse(w.save());self.assertEqual(bytes(app.rom.data),before)
                self.assertTrue(w.save());self.assertEqual(app.rom.last_backup.read_bytes(),before)
                self.assertEqual(EventCommands(app.rom,index).values(n),[value]);w.history(False);self.assertEqual(path.read_bytes(),before)
                w.history(True);self.assertEqual(EventCommands(app.rom,index).values(n),[value]);w.destroy()
            finally:app.destroy()
