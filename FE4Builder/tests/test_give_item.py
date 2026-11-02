import unittest,tempfile
from pathlib import Path
from copy import copy
from unittest.mock import patch
from rom import ROOT,Rom
from event_commands import EventCommands,catalogue,schema,player_item_options
from player_items import SlotLocations

class GiveItemTests(unittest.TestCase):
    def test_parameter_bytes_headers_context_validation_stale_and_appearances(self):
        rom=Rom(next(ROOT.glob('*.sfc')));original=bytes(rom.data);count=0
        for i,e in enumerate(catalogue()['entries']):
            for n,c in enumerate(e['commands']):
                if schema(c)!='give_item':continue
                count+=1
                for header in (0,512):
                    for actor,slot in ((2,1),(65535,142)):
                        r=copy(rom);r.header=header;r.data=bytearray(header)+original;model=EventCommands(r,i);before=bytes(r.data)
                        for values in ([0,1],[697,1],[32768,1],[1,0],[1,143],[1,255],[True,1],[1,1.5]):
                            with self.assertRaises(ValueError):model.write({n:values})
                            self.assertEqual(bytes(r.data),before)
                        model.write({n:[actor,slot]});self.assertEqual(EventCommands(r,i).values(n),[actor,slot])
                        at=e['profile']['start']+c['offset']+2+header
                        self.assertEqual(r.data[at:at+3],actor.to_bytes(2,'little')+bytes([slot]))
                        self.assertTrue(all(a==b or k in (at,at+1,at+2) for k,(a,b) in enumerate(zip(before,r.data))))
                        with self.assertRaises(ValueError):model.write({n:[1,2]})
                        current=EventCommands(r,i);r.data[0x3f489+header]^=1;before=bytes(r.data)
                        with self.assertRaises(ValueError):current.write({n:[1,2]})
                        self.assertEqual(bytes(r.data),before)
                r=copy(rom);r.data=bytearray(original);m=EventCommands(r,i);m.write({n:[65535,2]})
                at=e['profile']['start']+c['offset'];references=SlotLocations(r).rows[2]
                self.assertTrue(any(row.address==at for row in references))
        self.assertEqual(count,1)
        before=player_item_options(rom)[1];rom.data[0x3f489]=0x40
        self.assertNotEqual(player_item_options(rom)[1],before)
    def test_gui_names_slot_context_appearances_failed_save_undo(self):
        from FE4Builder import App
        rom=Rom(next(ROOT.glob('*.sfc')))
        with tempfile.TemporaryDirectory(dir=ROOT/'FE4Builder/research') as folder:
            path=Path(folder)/'give.sfc';path.write_bytes(rom.data);original=path.read_bytes();app=App();app.withdraw();app.rom=Rom(path)
            try:
                i=next(i for i,e in enumerate(catalogue()['entries']) if any(schema(c)=='give_item' for c in e['commands']))
                w=app.edit_events(catalogue()['entries'][i]['id']);n=next(n for n,c in enumerate(w.model.commands) if schema(c)=='give_item')
                w.commands.selection_set(str(n));w.select_command();self.assertEqual(len(w.variables),2)
                self.assertIn('Sigurd',w.variables[0].get());self.assertIn('indexed appearances',w.help.get())
                w.variables[0].set(next(k for k,v in w.field_options[0].items() if v==65535));self.assertIn('Event Unit Slot 1',w.variables[0].get())
                w.variables[1].set(next(k for k,v in w.field_options[1].items() if v==2));self.assertIn('Selected PID $02',w.help.get())
                self.assertTrue(w.pending());self.assertEqual(path.read_bytes(),original)
                with patch.object(app.rom,'save_original',side_effect=OSError('test')),patch('event_command_window.messagebox.showerror'):
                    self.assertFalse(w.save());self.assertEqual(bytes(app.rom.data),original)
                self.assertTrue(w.save());self.assertEqual(app.rom.last_backup.read_bytes(),original)
                self.assertEqual(EventCommands(app.rom,i).values(n),[65535,2]);w.history(False);self.assertEqual(path.read_bytes(),original)
                w.history(True);self.assertEqual(EventCommands(app.rom,i).values(n),[65535,2]);w.destroy()
            finally:app.destroy()
