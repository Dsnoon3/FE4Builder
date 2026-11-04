import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from rom import ROOT,Rom
from event_commands import catalogue,EventCommands
from route_editor import callers,ARENA,SIZE
from camera_routes import CameraRouteDraft as RouteDraft,read_camera_route as read_route,encode_camera_steps as encode_steps,LEGACY

class CameraRouteEditorTests(unittest.TestCase):
    def setUp(self):
        self.rom=Rom(next(ROOT.glob('*.sfc')))
        self.event=next(i for i,e in enumerate(catalogue()['entries']) if any(c['opcode']==0x3f for c in e['commands']))
        self.command=next(i for i,c in enumerate(catalogue()['entries'][self.event]['commands']) if c['opcode']==0x3f)
    def test_copy_preserves_original_callers_and_reopen_header(self):
        from copy import copy
        for header in (0,512):
            rom=copy(self.rom);rom.header=header;rom.data=bytearray(header)+self.rom.data
            draft=RouteDraft(rom,self.event,self.command)
            # Create another verified caller sharing this route.
            other=next((i,n) for i,e in enumerate(catalogue()['entries']) for n,c in enumerate(e['commands']) if c['opcode']==0x3f and (i,n)!=(self.event,self.command))
            m=EventCommands(rom,other[0]);c=m.commands[other[1]];at=m.profile['start']+c['offset']+1+header
            rom.data[at:at+3]=draft.pointer.to_bytes(3,'little')
            draft=RouteDraft(rom,self.event,self.command);self.assertGreaterEqual(len(draft.users),2)
            original=bytes(rom.data);steps=[('Down',2),('Speed',255),('Right',1),('End',0)]
            draft.write(steps);new=RouteDraft(rom,self.event,self.command)
            self.assertEqual(new.steps,steps);self.assertNotEqual(new.pointer,draft.pointer)
            self.assertEqual(read_route(rom,draft.pointer)[1],draft.original)
            self.assertEqual(rom.data[at:at+3],original[at:at+3])
            allowed=set(range(ARENA+header,ARENA+header+SIZE))|set(range(draft.address,draft.address+3))
            self.assertTrue(all(a==b or i in allowed for i,(a,b) in enumerate(zip(original,rom.data))))
            with self.assertRaises(ValueError):draft.write(steps)
            new.write([('Left',1),('End',0)]);self.assertEqual(RouteDraft(rom,self.event,self.command).steps,[('Left',1),('End',0)])
    def test_invalid_occupied_and_corrupt_are_atomic(self):
        draft=RouteDraft(self.rom,self.event,self.command);before=bytes(self.rom.data)
        for steps in ([],[('Right',1)],[('End',0),('Left',1)],[('Speed',256),('End',0)],[('Wait',256),('End',0)]):
            with self.assertRaises(ValueError):draft.write(steps)
            self.assertEqual(bytes(self.rom.data),before)
        self.rom.data[ARENA+100]^=3;draft=RouteDraft(self.rom,self.event,self.command);before=bytes(self.rom.data)
        with self.assertRaises(ValueError):draft.write([('Right',3),('End',0)])
        self.assertEqual(bytes(self.rom.data),before)
    def test_unknown_route_and_corrupt_storage_rejected(self):
        draft=RouteDraft(self.rom,self.event,self.command)
        draft.write([('Right',2),('End',0)])
        self.rom.data[ARENA+16]^=1
        draft=RouteDraft(self.rom,self.event,self.command);before=bytes(self.rom.data)
        with self.assertRaises(ValueError):draft.write([('Left',1),('End',0)])
        self.assertEqual(bytes(self.rom.data),before)
        from portraits import pc_address
        self.rom.data[pc_address(draft.pointer)]=0x82
        with self.assertRaises(ValueError):RouteDraft(self.rom,self.event,self.command)

    def test_gui_failed_save_rollback_backup_undo(self):
        from FE4Builder import App
        from route_window import RouteWindow
        with tempfile.TemporaryDirectory(dir=ROOT/'FE4Builder/research') as folder:
            path=Path(folder)/'route.sfc';path.write_bytes(self.rom.data);original=path.read_bytes()
            app=App();app.withdraw();app.rom=Rom(path)
            try:
                parent=app.edit_events(catalogue()['entries'][self.event]['id']);window=RouteWindow(parent,self.event,self.command,camera=True)
                window.steps=[('Down',3),('End',0)]
                with patch.object(app.rom,'save_original',side_effect=OSError('test')),patch('route_window.messagebox.showerror'):
                    self.assertFalse(window.save());self.assertEqual(bytes(app.rom.data),original)
                with patch('route_window.messagebox.showerror') as errors:
                    self.assertTrue(window.save(),str(errors.call_args))
                self.assertEqual(app.rom.last_backup.read_bytes(),original)
                saved=path.read_bytes();app.rom.undo();self.assertEqual(path.read_bytes(),original)
                app.rom.redo();self.assertEqual(path.read_bytes(),saved)
                self.assertEqual(RouteDraft(app.rom,self.event,self.command).steps,[('Down',3),('End',0)])
                parent.destroy()
            finally:app.destroy()

    def test_legacy_no_direction_preserved_but_not_created(self):
        i,n=next((i,n) for i,e in enumerate(catalogue()['entries']) for n,c in enumerate(e['commands']) if c['opcode']==0x3f and i!=self.event)
        draft=RouteDraft(self.rom,i,n);self.assertIn((LEGACY,120),draft.steps)
        changed=list(draft.steps);changed[0]=('Left',2)
        draft.write(changed)
        self.assertEqual(RouteDraft(self.rom,i,n).steps,changed)
        with self.assertRaises(ValueError):encode_steps([(LEGACY,120),('End',0)])
        with self.assertRaises(ValueError):encode_steps([('Wait',120),('End',0)])
        with self.assertRaises(ValueError):encode_steps([('Halt',0),('End',0)])

    def test_camera_and_unit_routes_share_pool_without_overwriting(self):
        from route_editor import RouteDraft as UnitRouteDraft
        camera=RouteDraft(self.rom,self.event,self.command)
        camera.write([('Down',3),('End',0)])
        camera=RouteDraft(self.rom,self.event,self.command);original=camera.original
        i,n=next((i,n) for i,e in enumerate(catalogue()['entries']) for n,c in enumerate(e['commands']) if c['opcode']==0x27)
        UnitRouteDraft(self.rom,i,n).write([('Right',4),('End',0)])
        self.assertEqual(read_route(self.rom,camera.pointer)[1],original)
        self.assertNotEqual(UnitRouteDraft(self.rom,i,n).pointer,camera.pointer)
