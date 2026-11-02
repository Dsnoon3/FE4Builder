import unittest,tempfile
from pathlib import Path
from copy import copy
from unittest.mock import patch
from rom import ROOT,Rom
from event_commands import EventCommands,catalogue,HELP,TRANSITION_MODES

class MapTransitionTests(unittest.TestCase):
    def test_all_operands_modes_headers_preservation_and_stale(self):
        rom=Rom(next(ROOT.glob('*.sfc')));original=bytes(rom.data);count=0
        for i,e in enumerate(catalogue()['entries']):
            for n,c in enumerate(e['commands']):
                if c['opcode']!=0x3b:continue
                count+=1;self.assertEqual(c['name'],'MAP_TRANSITION');self.assertTrue(c['editable'])
                for header in (0,512):
                    for timing,mode in ((1,0),(2,1),(63,2)):
                        r=copy(rom);r.header=header;r.data=bytearray(header)+original;model=EventCommands(r,i)
                        before=bytes(r.data);model.write({n:[timing,mode]});at=e['profile']['start']+c['offset']+1+header
                        self.assertEqual(r.data[at],timing|(mode<<6));self.assertEqual(EventCommands(r,i).values(n),[timing,mode])
                        self.assertTrue(all(a==b or k==at for k,(a,b) in enumerate(zip(before,r.data))))
                        if before!=bytes(r.data):
                            with self.assertRaises(ValueError):model.write({n:[timing,mode]})
                r=copy(rom);r.data=bytearray(original);at=e['profile']['start']+c['offset']+1
                r.data[at]=0xc1;model=EventCommands(r,i);model.write({n:[4,3]});self.assertEqual(r.data[at],0xc4)
                r.data[at]=0x80;model=EventCommands(r,i);self.assertEqual(model.write({n:[0,2]}),[])
                model.write({n:[0,1]});self.assertEqual(r.data[at],0x40)
                r.data[at]=0x41;model=EventCommands(r,i);before=bytes(r.data)
                for values in ([0,1],[64,1],[-1,1],[1,3],[1,4],[True,1],[1,False],[1.5,1]):
                    with self.assertRaises(ValueError):model.write({n:values})
                    self.assertEqual(bytes(r.data),before)
        self.assertEqual(count,4);self.assertIn('64 seconds',HELP[0x3b]);self.assertIn('End',HELP[0x3b])
    def test_gui_draft_warning_failed_save_backup_history(self):
        from FE4Builder import App
        rom=Rom(next(ROOT.glob('*.sfc')))
        with tempfile.TemporaryDirectory(dir=ROOT/'FE4Builder/research') as folder:
            path=Path(folder)/'transition.sfc';path.write_bytes(rom.data);original=path.read_bytes();app=App();app.withdraw();app.rom=Rom(path)
            try:
                i=next(i for i,e in enumerate(catalogue()['entries']) if any(c['opcode']==0x3b for c in e['commands']))
                w=app.edit_events(catalogue()['entries'][i]['id']);n=next(n for n,c in enumerate(w.model.commands) if c['opcode']==0x3b)
                w.commands.selection_set(str(n));w.select_command();self.assertEqual(len(w.variables),2);self.assertIn('Map Transition',w.command_heading.get())
                w.variables[0].set('1');w.variables[1].set(TRANSITION_MODES[1]);self.assertIn('Draft parameter: $41',w.help.get())
                w.variables[1].set(TRANSITION_MODES[2]);self.assertIn('separate Fade In',w.help.get());self.assertIn('Halt alone',w.help.get())
                self.assertTrue(w.pending());self.assertEqual(path.read_bytes(),original)
                with patch.object(app.rom,'save_original',side_effect=OSError('test')),patch('event_command_window.messagebox.showerror'):
                    self.assertFalse(w.save());self.assertEqual(bytes(app.rom.data),original)
                self.assertTrue(w.save());self.assertEqual(app.rom.last_backup.read_bytes(),original)
                self.assertEqual(EventCommands(app.rom,i).values(n),[1,2]);w.history(False);self.assertEqual(path.read_bytes(),original)
                w.history(True);self.assertEqual(EventCommands(app.rom,i).values(n),[1,2]);w.destroy()
            finally:app.destroy()
