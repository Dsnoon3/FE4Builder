import unittest,tempfile
from pathlib import Path
from copy import copy
from unittest.mock import patch
from rom import ROOT,Rom
from event_commands import catalogue,EventCommands,schema

class DeployGroupTests(unittest.TestCase):
    def test_operand_only_headers_invalid_and_stale_army(self):
        rom=Rom(next(ROOT.glob('*.sfc')));original=bytes(rom.data);count=0
        for index,e in enumerate(catalogue()['entries'][:18]):
            for n,c in enumerate(e['commands']):
                if schema(c)!='deploy_group':continue
                count+=1
                for header in (0,512):
                    r=copy(rom);r.header=header;r.data=bytearray(header)+original
                    model=EventCommands(r,index);before=bytes(r.data)
                    for value in (-1,58,256,True,1.5):
                        with self.assertRaises(ValueError):model.write({n:[value]})
                        self.assertEqual(bytes(r.data),before)
                    value=1 if model.values(n)[0]!=1 else 0
                    model.write({n:[value]});self.assertEqual(EventCommands(r,index).values(n),[value])
                    address=e['profile']['start']+c['offset']+2+header
                    self.assertTrue(all(a==b or i==address for i,(a,b) in enumerate(zip(before,r.data))))
                    with self.assertRaises(ValueError):model.write({n:[value]})
                    model=EventCommands(r,index);r.data[0x1c000+header]^=8;before=bytes(r.data)
                    with self.assertRaises(ValueError):model.write({n:[value]})
                    self.assertEqual(bytes(r.data),before)
        self.assertEqual(count,3)
    def test_gui_preview_save_rollback_history(self):
        from FE4Builder import App
        rom=Rom(next(ROOT.glob('*.sfc')))
        with tempfile.TemporaryDirectory(dir=ROOT/'FE4Builder/research') as folder:
            path=Path(folder)/'deploy.sfc';path.write_bytes(rom.data);before=path.read_bytes()
            app=App();app.withdraw();app.rom=Rom(path)
            try:
                index=next(i for i,e in enumerate(catalogue()['entries'][:18]) if any(schema(c)=='deploy_group' for c in e['commands']))
                w=app.edit_events(catalogue()['entries'][index]['id']);n=next(i for i,c in enumerate(w.model.commands) if schema(c)=='deploy_group')
                w.commands.selection_set(str(n));w.select_command();self.assertEqual(len(w.variables),1)
                self.assertIn('Army group preview',w.help.get());self.assertIn('destination',w.help.get())
                value=1 if w.model.values(n)[0]!=1 else 0
                w.variables[0].set(next(k for k,v in w.field_options[0].items() if v==value))
                self.assertTrue(w.pending());self.assertIn('Army group preview',w.help.get());self.assertEqual(path.read_bytes(),before)
                with patch.object(app.rom,'save_original',side_effect=OSError('test')),patch('event_command_window.messagebox.showerror'):
                    self.assertFalse(w.save());self.assertEqual(bytes(app.rom.data),before)
                self.assertTrue(w.save());self.assertEqual(app.rom.last_backup.read_bytes(),before)
                self.assertEqual(EventCommands(app.rom,index).values(n),[value])
                w.history(False);self.assertEqual(path.read_bytes(),before)
                w.history(True);self.assertEqual(EventCommands(app.rom,index).values(n),[value]);w.destroy()
            finally:app.destroy()
