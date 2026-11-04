import unittest,tempfile
from pathlib import Path
from copy import copy
from unittest.mock import patch
from rom import Rom,ROOT
from event_commands import EventCommands,catalogue,schema,FIELDS,HELP

class ChapterCleanupTests(unittest.TestCase):
    def test_headers_exact_operand_validation_stale_and_readonly_help(self):
        rom=Rom(next(ROOT.glob('*.sfc')));original=bytes(rom.data);count=0;readonly=set()
        for i,e in enumerate(catalogue()['entries'][:18]):
            for n,c in enumerate(e['commands']):
                kind=schema(c)
                if kind in ('add_castle_money','save_chapter_turncount'):
                    readonly.add(kind);self.assertFalse(c['editable']);self.assertNotIn(kind,FIELDS)
                    self.assertIn('no parameters',HELP[kind]);self.assertIn('4A',HELP[kind])
                    with self.assertRaises(ValueError):EventCommands(rom,i).write({n:[]})
                if kind!='remove_chapter_struct':continue
                count+=1
                for header in (0,512):
                    r=copy(rom);r.header=header;r.data=bytearray(header)+original
                    for target in (1,11):
                        model=EventCommands(r,i);before=bytes(r.data)
                        for bad in (-1,12,255,True,1.5):
                            with self.assertRaises(ValueError):model.write({n:[bad]})
                            self.assertEqual(bytes(r.data),before)
                        model.write({n:[target]});self.assertEqual(EventCommands(r,i).values(n),[target])
                        at=e['profile']['start']+c['offset']+2+header
                        self.assertEqual(r.data[:at],before[:at]);self.assertEqual(r.data[at],target);self.assertEqual(r.data[at+1:],before[at+1:])
                        with self.assertRaises(ValueError):model.write({n:[0]})
        self.assertEqual(count,1);self.assertEqual(readonly,{'add_castle_money','save_chapter_turncount'})

    def test_gui_selector_descriptions_rollback_backup_undo(self):
        from FE4Builder import App
        rom=Rom(next(ROOT.glob('*.sfc')))
        with tempfile.TemporaryDirectory(dir=ROOT/'FE4Builder/research') as folder:
            path=Path(folder)/'cleanup.sfc';path.write_bytes(rom.data);before=path.read_bytes()
            app=App();app.withdraw();app.rom=Rom(path)
            try:
                i=next(i for i,e in enumerate(catalogue()['entries'][:18]) if any(schema(c)=='remove_chapter_struct' for c in e['commands']))
                w=app.edit_events(catalogue()['entries'][i]['id']);n=next(n for n,c in enumerate(w.model.commands) if schema(c)=='remove_chapter_struct')
                w.commands.selection_set(str(n));w.select_command();self.assertEqual(len(w.variables),1)
                self.assertIn('Prologue',w.variables[0].get());self.assertEqual(set(w.field_options[0].values()),set(range(12)))
                w.variables[0].set(next(k for k,v in w.field_options[0].items() if v==1))
                for j,c in enumerate(w.model.commands):
                    if schema(c) in ('add_castle_money','save_chapter_turncount'):
                        w.commands.selection_set(str(j));w.select_command();self.assertEqual(w.variables,[])
                        self.assertIn('no parameters',w.help.get())
                with patch.object(app.rom,'save_original',side_effect=OSError('test')),patch('event_command_window.messagebox.showerror'):
                    self.assertFalse(w.save());self.assertEqual(bytes(app.rom.data),before)
                self.assertTrue(w.save());self.assertEqual(app.rom.last_backup.read_bytes(),before)
                self.assertEqual(EventCommands(app.rom,i).values(n),[1])
                w.history(False);self.assertEqual(path.read_bytes(),before)
                w.history(True);self.assertEqual(EventCommands(app.rom,i).values(n),[1]);w.destroy()
            finally:app.destroy()
