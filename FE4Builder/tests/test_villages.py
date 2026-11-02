import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from rom import ROOT,Rom
from villages import Village,entries,ARENA,SIZE,slot,resolve_dialogue_ref
from dialogue import Dialogue,catalogue


class VillageTests(unittest.TestCase):
    def setUp(self):self.rom=Rom(next(ROOT.glob('*.sfc')))

    def test_all_variants_add_remove_restore_rewards_and_branches(self):
        self.assertEqual(len(entries()),78)
        baseline=bytes(self.rom.data)
        for i,entry in enumerate(entries()):
            original=Village(self.rom,i)
            original.write(123,1000,original.stat,original.amount)
            changed=Village(self.rom,i)
            self.assertEqual((changed.item,changed.gold),(123,1000))
            self.assertEqual(self.rom.data[entry['ref']+2],0x2f)
            changed.write(0,0,changed.stat,changed.amount)
            removed=Village(self.rom,i)
            self.assertEqual((removed.item,removed.gold),(0,0))
            removed.write(*original.original_values)
            restored=Village(self.rom,i)
            self.assertEqual(restored.original_values,original.original_values)
            start=entry['start'];size=entry['length']
            self.assertEqual(bytes(self.rom.data[start:start+size]),baseline[start:start+size])
        self.assertEqual(len(self.rom.data),len(baseline))
        # Only the private reserve and the selected event pointer operands differ.
        expected=bytearray(baseline)
        expected[ARENA:ARENA+SIZE]=self.rom.data[ARENA:ARENA+SIZE]
        for entry in entries():
            at=entry['ref'];expected[at:at+3]=self.rom.data[at:at+3]
        self.assertEqual(self.rom.data,expected)

    def test_reward_type_conversion_all_villages_headers_and_dialogue(self):
        for header in (0,512):
            rom=Rom(next(ROOT.glob('*.sfc')))
            if header:rom.data=bytearray(512)+rom.data;rom.header=512
            size=len(rom.data)
            for i,entry in enumerate(entries()):
                original=Village(rom,i)
                for kind in ('stat','item','item+stat','none','stat'):
                    model=Village(rom,i)
                    model.write(123,750,4,3,reward_type=kind)
                    fresh=Village(rom,i)
                    self.assertEqual(fresh.reward_type,kind)
                    self.assertEqual(fresh.item,123 if kind in ('item','item+stat') else 0)
                    self.assertEqual(fresh.stat,4 if kind in ('stat','item+stat') else None)
                    self.assertEqual(fresh.recipient,original.recipient)
                    self.assertEqual(len(rom.data),size)
                    for offset,opcode,length in original.nodes:
                        if opcode==0x0c:
                            ref=resolve_dialogue_ref(rom,entry['start']+offset+1)
                            self.assertEqual(rom.data[ref+header:ref+header+3],original.body[offset+1:offset+4])

    def test_dialogue_edits_before_and_after_reward_edits_follow_private_script(self):
        i=next(i for i,e in enumerate(entries()) if e['chapter']==0 and e['reward'] is not None)
        village=Village(self.rom,i);entry=village.entry
        scene=next(e for e in catalogue()['entries'] if entry['start']<=e['address']<entry['start']+entry['length'])
        old=Dialogue(self.rom,scene)
        first=old.text.replace('[End]',' Before.[End]')
        old.write(first)
        stale=Dialogue(self.rom,scene)
        village=Village(self.rom,i);village.write(0,1000)
        moved=Dialogue(self.rom,scene)
        self.assertEqual(moved.text,first)
        self.assertEqual(moved.ref,resolve_dialogue_ref(self.rom,scene['address']))
        with self.assertRaises(ValueError):stale.write(first.replace('Before','Stale'))
        second=first.replace('Before','After')
        moved.write(second)
        village=Village(self.rom,i);village.write(125,2000)
        self.assertEqual(Dialogue(self.rom,scene).text,second)
        self.assertEqual(Village(self.rom,i).original_values,(125,2000,None,None))

    def test_stats_recipients_conflicts_stale_and_invalid_are_atomic(self):
        i=next(i for i,e in enumerate(entries()) if Village(self.rom,i).kind=='stat')
        model=Village(self.rom,i);recipient=model.recipient
        model.write(123,500,5,2)
        fresh=Village(self.rom,i)
        self.assertEqual((fresh.stat,fresh.amount),(5,2));self.assertEqual(fresh.recipient,recipient)
        before=bytes(self.rom.data)
        with self.assertRaises(ValueError):model.write(124,500,5,3)
        for args in ((143,0,5,1),(123,-1,5,1),(123,0,8,1),(123,0,5,31)):
            with self.assertRaises(ValueError):fresh.write(*args)
        self.assertEqual(bytes(self.rom.data),before)
        self.rom.data[ARENA+100]^=1;before=bytes(self.rom.data)
        with self.assertRaises(ValueError):fresh.write(124,500,5,2)
        self.assertEqual(bytes(self.rom.data),before)
        self.rom=Rom(next(ROOT.glob('*.sfc')));model=Village(self.rom,0)
        self.rom.data[ARENA]=7;before=bytes(self.rom.data)
        with self.assertRaises(ValueError):model.write(123,0,model.stat,model.amount)
        self.assertEqual(bytes(self.rom.data),before)

    def test_headered_save_backup_undo_redo_and_other_reserves(self):
        from growth_patch import install,ARENA as GROWTH,SIZE as GROWTH_SIZE
        install(self.rom)
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            path=Path(folder)/'village.smc';path.write_bytes(bytes(512)+self.rom.data)
            rom=Rom(path);before=path.read_bytes();model=Village(rom,0)
            rom.save_original('Village rewards',model.write(123,1000,model.stat,model.amount))
            self.assertEqual(rom.last_backup.read_bytes(),before)
            self.assertEqual(Village(Rom(path),0).gold,1000)
            self.assertEqual(rom.data[GROWTH+512:GROWTH+512+GROWTH_SIZE],before[GROWTH+512:GROWTH+512+GROWTH_SIZE])
            self.assertEqual(rom.data[:512],bytes(512))
            rom.undo();self.assertEqual(path.read_bytes(),before)
            rom.redo();self.assertEqual(Village(rom,0).item,123)

    def test_gui_type_switch_and_expansion_confirmation_rollback(self):
        from FE4Builder import App
        app=App();app.withdraw();app.rom=self.rom
        try:
            window=app.edit_villages()
            window.reward_type.set('Stat increase');window.change_reward_type()
            self.assertEqual(str(window.stat_box['state']),'readonly')
            window.stat.set('Speed');window.amount.set('3')
            before=bytes(self.rom.data)
            with patch.object(self.rom,'save_original'):
                self.assertTrue(window.save())
            self.assertEqual(Village(self.rom,window.current).reward_type,'stat')
            self.assertEqual(len(self.rom.data),len(before))
            before=bytes(self.rom.data)
            def expand(*args,**kwargs):
                self.rom.data.extend(bytes(16));return ['test expansion']
            with patch.object(window.model,'write',side_effect=expand),patch('village_window.messagebox.askyesno',return_value=False) as confirm,patch.object(self.rom,'save_original') as save:
                self.assertFalse(window.save());confirm.assert_called_once();save.assert_not_called()
            self.assertEqual(bytes(self.rom.data),before)
            window.destroy()
        finally:app.destroy()

    def test_menu_categories_search_and_editor_save_failure(self):
        from FE4Builder import App
        app=App();app.withdraw();app.update_idletasks();app.rom=self.rom
        try:
            app.show_menu()
            self.assertEqual([app.home_tabs.tab(tab,'text') for tab in app.home_tabs.tabs()],
                             ['Characters','Items','Maps & Events','Graphics & Text','Advanced'])
            labels=[tool[1] for tool in app.home_tools]
            for name in ('Village Rewards','Dialogue Editor','Character Editor','Patches'):self.assertIn(name,labels)
            app.home_search.set('village')
            self.assertEqual(app.home_tabs.tab(app.home_tabs.select(),'text'),'Search results')
            app.home_search.set('');self.assertEqual(len(app.home_tabs.tabs()),5)
            window=app.edit_villages();window.item.set(next(name for name,value in window.item_options.items() if value==123));window.gold.set('1000')
            self.assertTrue(window.pending());before=bytes(self.rom.data)
            with patch.object(self.rom,'save_original',side_effect=OSError('Read only')),patch('village_window.messagebox.showerror'):
                self.assertFalse(window.save())
            self.assertEqual(bytes(self.rom.data),before);self.assertTrue(window.pending())
            with patch('village_window.ask_unsaved',return_value=None):self.assertFalse(window.settle())
            with patch('village_window.messagebox.askyesno',return_value=True):window.reload()
            self.assertFalse(window.pending());window.close()
        finally:app.destroy()
