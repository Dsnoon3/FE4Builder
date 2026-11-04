import unittest
from copy import copy
from rom import ROOT,Rom
from event_commands import EventCommands,catalogue
from movement_routes import route_preview

class TemporaryMovementTests(unittest.TestCase):
    def test_all_commands_exact_bytes_flags_pointers_and_stale_guards(self):
        rom=Rom(next(ROOT.glob('*.sfc')));original=bytes(rom.data);count=0
        for index,entry in enumerate(catalogue()['entries'][:18]):
            for command,c in enumerate(entry['commands']):
                if c['opcode']!=0x27:continue
                count+=1;rom.data[:]=original;model=EventCommands(rom,index)
                values=model.values(command);values[:]=[1,12,13,4,8,1]
                at=entry['profile']['start']+c['offset']
                # Unexposed speed/flag bits must survive both edits to the shared byte.
                rom.data[at+5]|=0xe8;model=EventCommands(rom,index);before=bytes(rom.data)
                model.write({command:values});updated=EventCommands(rom,index)
                self.assertEqual(updated.values(command),values)
                self.assertEqual(rom.data[at+5],0xfc)
                allowed=set(range(at+1,at+7))
                self.assertTrue(all(a==b or i in allowed for i,(a,b) in enumerate(zip(before,rom.data))))
                self.assertEqual(rom.data[at+7:at+10],before[at+7:at+10])
                stale=updated;rom.data[at+3]^=1;state=bytes(rom.data)
                with self.assertRaises(ValueError):stale.write({command:values})
                self.assertEqual(bytes(rom.data),state)
        self.assertEqual(count,8)
        rom.data[:]=original
        index=next(i for i,e in enumerate(catalogue()['entries'][:18]) if any(c['opcode']==0x27 for c in e['commands']))
        model=EventCommands(rom,index);command=next(i for i,c in enumerate(model.commands) if c['opcode']==0x27)
        for field,value in ((0,0),(1,64),(3,6),(4,3),(5,2)):
            draft=model.values(command);draft[field]=value
            with self.assertRaises(ValueError):model.write({command:draft})
            self.assertEqual(bytes(rom.data),original)
        headered=copy(rom);headered.header=512;headered.data=bytearray(512)+rom.data
        EventCommands(headered,index).write({command:[1,12,13,4,2,0]})
        self.assertEqual(EventCommands(headered,index).values(command),[1,12,13,4,2,0])

    def test_route_decoding_bounds_and_gui(self):
        from types import SimpleNamespace
        fake=SimpleNamespace(header=0,data=bytearray(0x10010))
        fake.data[:10]=bytes([13,2,0x87,18,100,0x84,3,0x81,0x80,0])
        text=route_preview(fake,0xc00000)
        for phrase in ('Down 2','Face up','Wait 100','Set speed 3','Halt','End route'):self.assertIn(phrase,text)
        fake.data[0]=0x82;self.assertIn('Unknown',route_preview(fake,0xc00000))
        fake.data[0xffff]=13;self.assertIn('truncated',route_preview(fake,0xc0ffff))
        self.assertIn('limit reached',route_preview(fake,0xc00001,limit=1))
        from FE4Builder import App
        app=App();app.withdraw();app.rom=Rom(next(ROOT.glob('*.sfc')))
        try:
            entry=next(e for e in catalogue()['entries'] if any(c['opcode']==0x27 for c in e['commands']))
            window=app.edit_events(entry['id'])
            command=next(i for i,c in enumerate(window.model.commands) if c['opcode']==0x27)
            window.commands.selection_set(str(command));window.select_command()
            self.assertEqual(len(window.variables),6)
            self.assertIn('Movement route $',window.help.get())
            self.assertEqual(set(window.field_options[4].values()),{2,4,6,8})
            self.assertFalse(window.pending());window.destroy()
        finally:app.destroy()
