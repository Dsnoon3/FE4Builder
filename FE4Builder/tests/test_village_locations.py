"""Village interaction coordinates, variant links, and map selection."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from rom import ROOT,Rom
from villages import Village,VillageLocation,entries

class VillageLocationTests(unittest.TestCase):
    def test_all_links_headers_exact_bytes_and_shared_variants(self):
        baseline=Rom(next(ROOT.glob('*.sfc')))
        shared=False
        for header in (0,512):
            rom=Rom(baseline.path)
            if header:rom.data=bytearray(512)+rom.data;rom.header=512
            for i,entry in enumerate(entries()):
                model=VillageLocation(rom,i);before=bytes(rom.data)
                x,y=model.position
                for target in ((x-2,y),(x+2,y),(x,y+2),(x,y-2)):
                    try:model.validate(*target)
                    except ValueError:continue
                    break
                else:self.fail('No valid nearby tile')
                model.write(*target)
                at=model.address+header+3
                self.assertEqual(rom.data[:at],before[:at])
                self.assertEqual(rom.data[at:at+2],bytes(target))
                self.assertEqual(rom.data[at+2:],before[at+2:])
                self.assertEqual(Village(rom,i).original_values,Village(baseline,i).original_values)
                for j,other in enumerate(entries()):
                    if other['chapter']==entry['chapter'] and other['location']['address']==model.address:
                        self.assertEqual(VillageLocation(rom,j).position,target)
                shared|=len(model.variants)>1
                with self.assertRaises(ValueError):model.write(x,y)
                VillageLocation(rom,i).write(x,y)
        self.assertTrue(shared)

    def test_invalid_collisions_guards_and_stale_leave_memory_unchanged(self):
        rom=Rom(next(ROOT.glob('*.sfc')));model=VillageLocation(rom,0);before=bytes(rom.data)
        for x,y in ((-1,0),(64,0),(0,64),(True,1),(1.5,2)):
            with self.assertRaises(ValueError):model.write(x,y)
            self.assertEqual(bytes(rom.data),before)
        other=next(VillageLocation(rom,j) for j,e in enumerate(entries()) if e['chapter']==model.entry['chapter'] and e['location']['address']!=model.address)
        with self.assertRaises(ValueError):model.write(*other.position)
        rom.data[model.address+3]^=1;before=bytes(rom.data)
        with self.assertRaises(ValueError):model.write(*model.position)
        self.assertEqual(bytes(rom.data),before)
        rom.data[model.address+2]=0
        with self.assertRaises(ValueError):VillageLocation(rom,0)

    def test_picker_single_click_cancel_save_rollback_backup_history(self):
        from FE4Builder import App
        rom=Rom(next(ROOT.glob('*.sfc')))
        with tempfile.TemporaryDirectory(dir=ROOT/'FE4Builder/research') as folder:
            path=Path(folder)/'locations.sfc';path.write_bytes(rom.data)
            app=App();app.withdraw();app.rom=Rom(path)
            try:
                w=app.edit_villages();index=w.current;old=w.location_position
                picker=w.pick_location();app.update_idletasks()
                self.assertIsNotNone(picker)
                x,y=old;target=(x-2,y)
                w.location_model.validate(*target)
                left,top,right,bottom=picker.model.bounds
                self.assertEqual((picker.image.width(),picker.image.height()),((right-left)*16,(bottom-top)*16))
                picker.canvas.xview_moveto(0.2);picker.canvas.yview_moveto(0.2)
                event=SimpleNamespace(x=(target[0]-left)*16+8-picker.canvas.canvasx(0),y=(target[1]-top)*16+8-picker.canvas.canvasy(0))
                self.assertEqual(picker.point(event),target)
                picker.choose(event)
                self.assertFalse(picker.winfo_exists());self.assertEqual(w.location_position,target)
                self.assertTrue(w.pending());self.assertEqual(path.read_bytes(),bytes(rom.data))
                picker=w.pick_location();picker.close();self.assertEqual(w.location_position,target)
                before=path.read_bytes()
                with patch.object(app.rom,'save_original',side_effect=OSError('test failure')),patch('village_window.messagebox.showerror'):
                    self.assertFalse(w.save())
                self.assertEqual(bytes(app.rom.data),before);self.assertEqual(w.location_position,target)
                self.assertTrue(w.save());self.assertEqual(app.rom.last_backup.read_bytes(),before)
                self.assertEqual(VillageLocation(Rom(path),index).position,target)
                w.history(False);self.assertEqual(path.read_bytes(),before);self.assertEqual(w.location_position,old)
                w.history(True);self.assertEqual(w.location_position,target)
                w.destroy()
            finally:app.destroy()
