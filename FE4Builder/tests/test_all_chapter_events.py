import unittest,tempfile
from copy import copy
from pathlib import Path
from unittest.mock import patch
from rom import Rom,ROOT
from event_commands import catalogue,EventCommands,audio_options,deployment_options

class AllChapterEventsTests(unittest.TestCase):
    def setUp(self):self.rom=Rom(next(ROOT.glob('*.sfc')))

    def test_every_catalogue_layout_and_original_drafts_validate(self):
        data=catalogue();self.assertEqual(len(data['entries']),557)
        self.assertEqual({e['chapter'] for e in data['entries']},set(range(12)))
        self.assertEqual(sum(bool(e['commands']) for e in data['entries']),554)
        original=bytes(self.rom.data)
        for i,e in enumerate(data['entries']):
            model=EventCommands(self.rom,i)
            self.assertEqual(model.write({n:model.values(n) for n,c in enumerate(model.commands) if c['editable']}),[])
            occupied=set()
            for c in model.commands:
                locations=set(range(c['offset'],c['offset']+c['size']))
                self.assertFalse(occupied&locations);occupied|=locations
                self.assertLessEqual(c['offset']+c['size'],e['profile']['length'])
        self.assertEqual(bytes(self.rom.data),original)

    def test_write_one_event_each_chapter_both_header_formats_and_unknown_layouts(self):
        data=catalogue()['entries'];original=bytes(self.rom.data)
        for header in (0,512):
            rom=copy(self.rom);rom.header=header;rom.data=bytearray(header)+original
            for chapter in range(12):
                i,n=next((i,n) for i,e in enumerate(data) if e['chapter']==chapter for n,c in enumerate(e['commands']) if c['opcode']==0x0e and c['editable'])
                model=EventCommands(rom,i);c=model.commands[n];old=model.values(n)[0]
                value=next(v for v in audio_options(c) if v!=old);before=bytes(rom.data)
                model.write({n:[value]});self.assertEqual(EventCommands(rom,i).values(n),[value])
                at=model.profile['start']+c['offset']+1+header
                self.assertEqual(rom.data[:at],before[:at]);self.assertEqual(rom.data[at+1:],before[at+1:])
                rom.data[:]=before
            for i,e in enumerate(data):
                if e.get('unsupported'):
                    with self.assertRaises(ValueError):EventCommands(rom,i).write({0:[1]})
        self.assertEqual(set(deployment_options(self.rom,1,7)),set(range(7)))
        self.assertEqual(deployment_options(self.rom,1,7)[1],'Faction slot 1')

    def test_chapter_search_cancel_readonly_fallback_and_no_viewer_menu(self):
        from FE4Builder import App
        app=App();app.withdraw();app.rom=self.rom
        try:
            app.show_menu();names=[row[1] for row in app.home_tools]
            self.assertIn('Event Editor',names);self.assertNotIn('Chapter Event Viewer',names)
            w=app.edit_events();app.update_idletasks()
            for chapter in range(12):
                w.chapter.current(chapter);w.change_chapter()
                self.assertEqual(w.model.entry['chapter'],chapter)
                self.assertTrue(w.visible)
                self.assertTrue(w.triggers_text.get('1.0','end').strip())
            w.focus_event(1)
            n=next(n for n,c in enumerate(w.model.commands) if c['opcode']==0x3a)
            w.commands.selection_set(str(n));w.select_command();w.variables[0].set('20')
            current=w.current;w.search.set('no matching script at all')
            self.assertEqual(w.current,current);self.assertTrue(w.pending());self.assertEqual(w.visible,[])
            w.search.set('')
            with patch('event_command_window.ask_unsaved',return_value=None):
                w.chapter.current(1);w.change_chapter()
            self.assertEqual(w.chapter.current(),0);self.assertTrue(w.pending())
            with patch('event_command_window.ask_unsaved',return_value=False):self.assertTrue(w.focus_event(2))
            self.assertEqual(w.variables,[]);self.assertIn('Read-only',w.status.get())
            self.assertTrue(w.reference_text.get('1.0','end').strip());w.destroy()
        finally:app.destroy()

    def test_non_prologue_gui_save_backup_undo_and_link_focus(self):
        from FE4Builder import App
        from route_window import RouteWindow
        with tempfile.TemporaryDirectory(dir=ROOT/'FE4Builder/research') as folder:
            path=Path(folder)/'chapter.sfc';path.write_bytes(self.rom.data);before=path.read_bytes()
            app=App();app.withdraw();app.rom=Rom(path)
            try:
                i,n=next((i,n) for i,e in enumerate(catalogue()['entries']) if e['chapter']==6 for n,c in enumerate(e['commands']) if c['opcode']==0x0e)
                entry=catalogue()['entries'][i];w=app.edit_events(entry['id'])
                self.assertEqual(w.chapter.current(),6)
                w.commands.selection_set(str(n));w.select_command()
                old=w.model.values(n)[0];value=next(v for v in w.field_options[0].values() if v!=old)
                w.variables[0].set(next(k for k,v in w.field_options[0].items() if v==value))
                self.assertTrue(w.save());self.assertEqual(app.rom.last_backup.read_bytes(),before)
                w.history(False);self.assertEqual(path.read_bytes(),before)
                w.history(True);self.assertEqual(EventCommands(app.rom,i).values(n),[value])
                self.assertTrue(w.focus_event(entry['id'],entry['profile']['start']+entry['commands'][n]['offset']))
                self.assertTrue(w.reference_text.tag_ranges('item-slot-reference'));w.destroy()
            finally:app.destroy()

    def test_linked_tools_open_the_matching_event_editor(self):
        from FE4Builder import App
        from event_command_window import EventCommandWindow
        import conversations,objectives,reinforcements
        app=App();app.withdraw();app.rom=self.rom
        try:
            for name,module in (('conversations',conversations),('objectives',objectives),('reinforcements',reinforcements)):
                rows=module.catalogue()['entries']
                index=next(i for i,e in enumerate(rows) if e['chapter']==1 and (e.get('events') if name!='reinforcements' else True))
                entry=rows[index];expected=entry['events'][0] if name!='reinforcements' else entry['id']
                window=getattr(app,'edit_'+name)();window.chapter.current(1);window.populate();window.load(index)
                window.view_event()
                editor=next(w for w in app.winfo_children() if isinstance(w,EventCommandWindow))
                self.assertEqual(catalogue()['entries'][editor.current]['id'],expected)
                self.assertEqual(editor.chapter.current(),1)
                editor.destroy();window.destroy()
        finally:app.destroy()

    def test_route_allocation_after_relocated_village_does_not_require_unrelated_scripts(self):
        from villages import Village
        from camera_routes import CameraRouteDraft
        Village(self.rom,0).write(123,0)
        i,n=next((i,n) for i,e in enumerate(catalogue()['entries']) for n,c in enumerate(e['commands']) if c['opcode']==0x3f)
        draft=CameraRouteDraft(self.rom,i,n)
        draft.write([('Left',2),('Speed',3),('End',0)])
        self.assertEqual(CameraRouteDraft(self.rom,i,n).steps,[('Left',2),('Speed',3),('End',0)])
