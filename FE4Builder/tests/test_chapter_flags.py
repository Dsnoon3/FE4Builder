import unittest,tempfile
from pathlib import Path
from copy import copy
from unittest.mock import patch
from rom import ROOT,Rom
from event_commands import EventCommands,catalogue,chapter_flag_options

class ChapterFlagTests(unittest.TestCase):
    def test_two_commands_masks_invalid_atomic_stale_and_headers(self):
        rom=Rom(next(ROOT.glob('*.sfc')));original=bytes(rom.data);count=0
        for index,e in enumerate(catalogue()['entries']):
            for n,c in enumerate(e['commands']):
                if c['opcode'] not in (0x4b,0x4c):continue
                count+=1
                for header in (0,512):
                    r=copy(rom);r.header=header;r.data=bytearray(header)+original
                    model=EventCommands(r,index);before=bytes(r.data);at=e['profile']['start']+c['offset']+header
                    for values in ([12,1],[0,80],[-1,1],[0,-1],[0,1.5],[True,1]):
                        with self.assertRaises(ValueError):model.write({n:values})
                        self.assertEqual(bytes(r.data),before)
                    model.write({n:[1,79]});self.assertEqual(EventCommands(r,index).values(n),[1,79])
                    self.assertTrue(all(a==b or i in (at+1,at+2) for i,(a,b) in enumerate(zip(before,r.data))))
                    with self.assertRaises(ValueError):model.write({n:[0,22]})
        self.assertEqual(count,2);self.assertEqual(chapter_flag_options(0)[23],'Bridge Raised')
        self.assertEqual(chapter_flag_options(1)[23],'Unnamed flag')
    def test_gui_chapter_refresh_backup_and_undo(self):
        from FE4Builder import App
        rom=Rom(next(ROOT.glob('*.sfc')))
        with tempfile.TemporaryDirectory(dir=ROOT/'FE4Builder/research') as folder:
            path=Path(folder)/'flags.sfc';path.write_bytes(rom.data);before=path.read_bytes()
            app=App();app.withdraw();app.rom=Rom(path)
            try:
                index=next(i for i,e in enumerate(catalogue()['entries']) if any(c['opcode']==0x4c for c in e['commands']))
                w=app.edit_events(catalogue()['entries'][index]['id']);n=next(i for i,c in enumerate(w.model.commands) if c['opcode']==0x4c)
                w.commands.selection_set(str(n));w.select_command();self.assertEqual(len(w.variables),2)
                self.assertIn('Bridge Raised',w.variables[1].get())
                w.variables[0].set(next(k for k,v in w.field_options[0].items() if v==1))
                self.assertIn('Unnamed flag',w.variables[1].get());self.assertEqual(w.field_options[1][w.variables[1].get()],23)
                w.variables[0].set(next(k for k,v in w.field_options[0].items() if v==0));self.assertIn('Bridge Raised',w.variables[1].get())
                w.variables[1].set(next(k for k,v in w.field_options[1].items() if v==22))
                with patch.object(app.rom,'save_original',side_effect=OSError('test')),patch('event_command_window.messagebox.showerror'):
                    self.assertFalse(w.save());self.assertEqual(bytes(app.rom.data),before)
                self.assertTrue(w.save());self.assertEqual(app.rom.last_backup.read_bytes(),before)
                self.assertEqual(EventCommands(app.rom,index).values(n),[0,22])
                w.history(False);self.assertEqual(path.read_bytes(),before)
                w.history(True);self.assertEqual(EventCommands(app.rom,index).values(n),[0,22]);w.destroy()
            finally:app.destroy()
