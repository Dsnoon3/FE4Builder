"""Generated ROM fixtures for slot identity, occurrence readers and navigation."""
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch
from rom import Rom, MODULES, load_module, character_modules, category_modules, DATA_DIR
from player_items import SlotLocations, PLAYER_MODULE
import village_window
import event_command_window # Import before patching source catalogues in fixture setup.
from item_slot_events import decode
from portraits import pointer_for
from village_scripts import signature


def set_fields(rom,table,index,**values):
    at=rom.address(table,index)
    for field in table.fields:
        if field.name in values:
            rom.data[at+field.offset:at+field.offset+field.size]=values[field.name].to_bytes(field.size,'little')


class PlayerItemsTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.path=Path(self.folder.name)/'generated.sfc'
        data=bytearray(b'\xff')*0x800000
        data[0xffc0:0xffcb]=b'FIREEMBLEM4';self.path.write_bytes(data);self.rom=Rom(self.path)
        self.tables=character_modules();self.player=next(t for t in category_modules('Item Editor') if t.name==PLAYER_MODULE)
        set_fields(self.rom,self.player,6,Item=0);set_fields(self.rom,self.player,7,Item=0)
        for table in category_modules('Item Editor'):
            if table.name=='FE4 Weapon/Staff Editor 1':
                self.weapon=table
                for i in (0,1):set_fields(self.rom,table,i,Name=i,Type=0,Rank=2)
        set_fields(self.rom,self.tables[0],0,**{'Char no.':1,'Equipment 1':7})
        set_fields(self.rom,self.tables[0],1,**{'Char no.':2,'Equipment 1':8})
        set_fields(self.rom,self.tables[1],0,**{'Char no.':30,'Equipment 1':7})
        self.enemy=category_modules('Enemy Editor')[0]
        character=next(f.name for f in self.enemy.fields if 'Number' in f.name or 'no.' in f.name)
        set_fields(self.rom,self.enemy,0,**{character:300,'Dropable Equipment':7})
        set_fields(self.rom,self.enemy,1,**{character:301,'Dropable Equipment':8})
        # 58 live deployment groups, independently terminated and editable.
        for group in range(58):
            offset=116+group*16
            self.rom.data[0x1c000+group*2:0x1c002+group*2]=offset.to_bytes(2,'little')
        self.rom.data[0x1c000+116:0x1c002+116]=(1).to_bytes(2,'little')
        self.rom.data[0x1c000+116+13*16:0x1c002+116+13*16]=(300).to_bytes(2,'little')
        self.shop=category_modules('Shop Editor')[0]
        set_fields(self.rom,self.shop,0,**{'Equipment 1':7})
        set_fields(self.rom,self.shop,1,**{'Equipment 1':8})
        self.shop7=next(t for t in category_modules('Shop Editor') if 'Chapter 7' in t.name)
        set_fields(self.rom,self.shop7,0,**{'Equipment 1':7})
        for address,value in zip((0x7ab55,0x7ab5a,0x7ab5f),(0x4b,0x62,0x36)):
            self.rom.data[address:address+4]=b'\xc9'+value.to_bytes(2,'little')+b'\xf0'
        self.event={'id':1,'chapter':4,'label':'Generated item grant','start':0x110000,'length':7,'source':'Historical slot 99 is NOT evidence','hash':'unused'}
        self.rom.data[0x110000:0x110007]=b'\x4a\x57\x01\x00\x07\xff\xff'
        self.pointer(1,0x110000)
        raw=b'\x4a\x57\xff\xff\x07\xff\xff'
        self.rom.data[0x100000:0x100007]=raw;self.pointer(2,0x100000)
        self.village={'chapter':2,'label':'Generated village','event_id':2,'ref':0xfe8bf+6,'start':0x100000,'length':7,'reward':0,'signature':signature(raw)}
        self.villages=patch('villages.entries',return_value=[self.village]);self.villages.start()
        self.village_ui=patch('village_window.entries',return_value=[self.village]);self.village_ui.start()
        self.events=patch('events.catalogue',return_value={'events':[self.event],'chapters':[]});self.events.start()
        # Icon bytes need not contain actual game graphics for widget checks.
        self.rom.data[0xd1ae:0xd1b2]=bytes(4)
        self.rom.original=bytes(self.rom.data);self.path.write_bytes(self.rom.data)

    def tearDown(self):
        self.events.stop();self.villages.stop();self.village_ui.stop();self.folder.cleanup()

    def pointer(self,event,address):
        at=0xfe8bf+event*3
        self.rom.data[at:at+3]=pointer_for(address).to_bytes(3,'little')

    def test_independent_slot_records_preserve_exact_byte_addresses_and_padding(self):
        raw=load_module(MODULES/'Item Editors/FE4 Player Weapon Editor.nmm')
        self.assertEqual(self.player.count,142);self.assertEqual(self.player.stride,1)
        self.assertEqual(len(self.player.fields),1)
        self.assertEqual(self.rom.address(self.player,6),self.rom.address(raw,0)+6)
        before=bytes(self.rom.data);self.rom.write(self.player,141,[0x46])
        changed=[i for i,(a,b) in enumerate(zip(before,self.rom.data)) if a!=b]
        self.assertEqual(changed,[self.rom.address(raw,0)+141])
        self.assertEqual(self.rom.data[self.rom.address(raw,0)+142:self.rom.address(raw,0)+144],b'\xff\xff')

    def test_every_source_is_keyed_to_slot_instead_of_duplicate_item_type(self):
        index=SlotLocations(self.rom);rows=index.rows[7]
        self.assertEqual({r.kind for r in rows},{'starting','drop','shop','event','village','inheritance'})
        self.assertTrue(any(r.kind=='starting' and r.generation==1 and r.target[-1]==0 for r in rows))
        self.assertFalse(any(r.kind=='starting' and r.generation==1 and r.target[-1]==1 for r in rows))
        self.assertTrue(any(r.kind=='drop' and r.chapter==3 and r.target[-1]==0 for r in rows))
        self.assertFalse(any(r.kind=='drop' and r.target[-1]==1 for r in rows))
        self.assertTrue(any(r.kind=='event' and r.address==0x110000 for r in rows))
        self.assertTrue(any(r.kind=='village' and r.chapter==2 for r in rows))
        gen2=[r for r in rows if r.generation==2]
        self.assertEqual(gen2[0].kind,'inheritance')
        self.assertIn('fallback',index.summary(7))
        self.assertEqual(index.warnings,[])

    def test_rom_changes_move_each_reference_between_slots(self):
        first=SlotLocations(self.rom)
        set_fields(self.rom,self.tables[0],0,**{'Equipment 1':8})
        set_fields(self.rom,self.shop,0,**{'Equipment 1':8})
        set_fields(self.rom,self.enemy,0,**{'Dropable Equipment':8})
        self.rom.data[0x110004]=8;self.rom.data[0x100004]=8
        second=SlotLocations(self.rom)
        self.assertGreater(len(first.rows[7]),len(second.rows[7]))
        self.assertFalse(any(r.kind in ('event','village','drop') for r in second.rows[7]))
        self.assertTrue(any(r.kind=='event' for r in second.rows[8]))
        self.assertTrue(any(r.kind=='village' for r in second.rows[8]))
        self.assertTrue(any(r.kind=='drop' and r.target[-1]==0 for r in second.rows[8]))

    def test_private_village_rewards_follow_live_pointer_and_added_rewards(self):
        from villages import Village
        model=Village(self.rom,0);model.write(8,0)
        index=SlotLocations(self.rom)
        self.assertFalse(any(r.kind=='village' for r in index.rows[7]))
        self.assertTrue(any(r.kind=='village' for r in index.rows[8]))
        model=Village(self.rom,0);model.write(0,0)
        self.assertFalse(any(r.kind=='village' for r in SlotLocations(self.rom).rows[8]))
        # Gold-only source gains a new private prefix containing a slot grant.
        self.village.update(length=2,reward=None,signature=signature(b'\xff\xff'))
        from villages import ARENA,SIZE
        self.rom.data[ARENA:ARENA+SIZE]=b'\xff'*SIZE
        self.rom.data[0x100000:0x100002]=b'\xff\xff';self.pointer(2,0x100000)
        Village(self.rom,0).write(7,0)
        self.assertTrue(any(r.kind=='village' for r in SlotLocations(self.rom).rows[7]))

    def test_inheritance_eligibility_reads_current_item_rank_and_code_exceptions(self):
        set_fields(self.rom,self.weapon,0,Rank=255)
        self.assertFalse(any(r.kind=='inheritance' for r in SlotLocations(self.rom).rows[7]))
        # Editing the routine's explicit holy exception to item 0 changes the rule.
        self.rom.data[0x7ab56:0x7ab58]=bytes(2)
        self.assertTrue(any(r.kind=='inheritance' for r in SlotLocations(self.rom).rows[7]))
        set_fields(self.rom,self.player,6,Item=255)
        self.assertFalse(any(r.kind=='inheritance' for r in SlotLocations(self.rom).rows[7]))

    def test_live_event_parser_rejects_operands_and_follows_branches_and_relocation(self):
        start=0x120000
        # Slot-looking bytes occur in a dialogue pointer; they are not commands.
        script=b'\x0c\x4a\x57\x07'+b'\x03'+(start+12 & 0xffff).to_bytes(2,'little')+b'\x4a\x57\x01\x00\x08'+b'\x4a\x58\x01\x00\x07\xff\xff'
        self.rom.data[start:start+len(script)]=script
        grants,_,errors=decode(self.rom,start,len(script))
        self.assertEqual([g[1] for g in grants],[7,8]);self.assertEqual(errors,[])
        self.pointer(1,start) # Retain the old catalogue length; follow live pointers.
        self.assertEqual({r.address for r in SlotLocations(self.rom).rows[7] if r.kind=='event'},{start+12})
        self.rom.data[start+4:start+7]=b'\x02'+(start+1 & 0xffff).to_bytes(2,'little')
        grants,_,errors=decode(self.rom,start,len(script));self.assertEqual(grants,[]);self.assertTrue(errors)
        self.rom.data[start]=0x18
        _,_,errors=decode(self.rom,start,len(script));self.assertTrue(errors)

    def test_gui_slot_names_icon_live_rename_and_record_navigation(self):
        from FE4Builder import App
        app=App();app.withdraw();app.rom=self.rom
        try:
            app.item_preview_view.current(1)
            self.assertTrue(app.go_to_record('Item Editor',PLAYER_MODULE,6))
            self.assertEqual(app.item_preview_view.current(),0)
            self.assertIn('07  Iron Sword',app.list.get(0,'end'))
            self.assertEqual(len(app.editors),1)
            self.assertTrue(app.item_picture.cget('image'))
            self.assertEqual(app.heading.cget('text'),'07 Iron Sword')
            row=next(r for r in app.slot_appearance_rows if r.kind=='starting' and r.generation==1)
            self.assertTrue(app.open_item_slot_location(row))
            self.assertEqual(app.mode,'Character Editor');self.assertEqual(app.record[1],0)
            self.assertEqual(app.navigation[-1][1],PLAYER_MODULE)
            self.assertTrue(app.go_to_record('Item Editor',PLAYER_MODULE,6))
            set_fields(self.rom,self.weapon,0,Name=1)
            app.populate();self.assertIn('07  Steel Sword',app.list.get(0,'end'))
            set_fields(self.rom,self.shop,0,**{'Equipment 1':8})
            app.render()
            self.assertFalse(any(r.kind=='shop' and r.chapter==1 for r in app.slot_appearance_rows))
        finally:app.destroy()

    def test_links_open_the_exact_shop_village_and_live_event_operand(self):
        from FE4Builder import App
        app=App();app.withdraw();app.rom=self.rom
        chapters=[{'start':0x120000+i*16,'length':2,'hash':'unknown','source':'Generated chapter overview'} for i in range(12)]
        try:
            app.go_to_record('Item Editor',PLAYER_MODULE,6)
            row=next(r for r in app.slot_appearance_rows if r.kind=='shop' and r.chapter==1)
            self.assertTrue(app.open_item_slot_location(row))
            self.assertEqual(app.mode,'Shop Editor');self.assertEqual(app.modules[app.record[0]].name,self.shop.name)
            app.go_to_record('Item Editor',PLAYER_MODULE,6)
            row=next(r for r in app.slot_appearance_rows if r.kind=='village')
            self.assertTrue(app.open_item_slot_location(row))
            village=next(w for w in app.winfo_children() if w.winfo_class()=='Toplevel')
            self.assertEqual(village.current,0);self.assertEqual(village.model.item,7);village.destroy()
            row=next(r for r in app.slot_appearance_rows if r.kind=='event')
            from event_commands import catalogue as commands
            custom=dict(commands()['entries'][0],chapter=4)
            with patch('events.catalogue',return_value={'events':[self.event],'chapters':chapters}),patch('event_command_window.catalogue',return_value={'entries':[custom]}):
                self.assertTrue(app.open_item_slot_location(row))
                viewer=next(w for w in app.winfo_children() if w.winfo_class()=='Toplevel')
                self.assertEqual(viewer.chapter.current(),4)
                self.assertEqual(viewer.model,None)  # Generated custom bytes stay read-only.
                self.assertEqual(viewer.current,0)
                self.assertTrue(viewer.reference_text.tag_ranges('item-slot-reference'))
                self.assertIn('4A 57 01 00 07',viewer.reference_text.get('1.0','end'))
                viewer.destroy()
        finally:app.destroy()

    def test_slot_form_writes_only_one_slot_and_preserves_backup_undo_redo(self):
        from FE4Builder import App
        app=App();app.withdraw();app.rom=self.rom
        try:
            app.go_to_record('Item Editor',PLAYER_MODULE,6)
            before=self.path.read_bytes()
            variable,options=app.editors[0]
            variable.set(next(label for label,value in options.items() if value==1))
            self.assertTrue(app.write_original())
            after=self.path.read_bytes()
            self.assertEqual([i for i,(a,b) in enumerate(zip(before,after)) if a!=b],[self.rom.address(self.player,6)])
            self.assertEqual(self.rom.last_backup.read_bytes(),before)
            self.assertIn('07  Steel Sword',app.list.get(0,'end'))
            self.assertIn('08  Iron Sword',app.list.get(0,'end'))
            app.history_step(False);self.assertEqual(self.path.read_bytes(),before)
            app.history_step(True);self.assertEqual(self.path.read_bytes(),after)
        finally:app.destroy()

    def test_enemy_equipped_item_id_does_not_count_as_a_player_slot_drop(self):
        set_fields(self.rom,self.enemy,0,**{'Dropable Equipment':255,'Equipment 1':7})
        self.assertFalse(any(row.kind=='drop' for row in SlotLocations(self.rom).rows[7]))

    def test_live_deployment_group_replacement_and_variable_flag_lists(self):
        # DEPLOY_UNIT_GROUP_CHILD carries a flag and two words after its group.
        # Flag lists carry a variable count terminated by FF, not fixed operands.
        script=b'\x4a\x4f\x0d\xff'+(300).to_bytes(2,'little')+(301).to_bytes(2,'little')+b'\x4a\x2c\x01\x02\x03\xff'+b'\x4a\x57\x01\x00\x07\xff\xff'
        self.rom.data[0x110000:0x110000+len(script)]=script;self.event['length']=len(script)
        grants,loads,errors=decode(self.rom,0x110000,len(script))
        self.assertEqual([g[1] for g in grants],[7]);self.assertEqual(errors,[])
        self.assertIn((None,13),loads);self.assertIn((301,None),loads)
        rows=SlotLocations(self.rom).rows[7]
        self.assertEqual({r.chapter for r in rows if r.kind=='drop'},{4})
        self.event['chapter']=9
        rows=SlotLocations(self.rom).rows[7]
        self.assertEqual({(r.generation,r.chapter) for r in rows if r.kind=='drop'},{(2,9)})

    def test_silent_group_member_load_and_two_slot_event_grant(self):
        script=b'\x28\x0d\x01\x00'+b'\x4a\x52\x01\x00\x00\x07\x08\xff\xff'
        self.rom.data[0x110000:0x110000+len(script)]=script;self.event['length']=len(script)
        grants,loads,errors=decode(self.rom,0x110000,len(script))
        self.assertEqual([g[1] for g in grants],[7,8]);self.assertEqual(errors,[])
        self.assertIn((1,13),loads)
        index=SlotLocations(self.rom)
        self.assertTrue(any(r.kind=='event' for r in index.rows[8]))
        self.assertEqual({r.chapter for r in index.rows[7] if r.kind=='drop'},{4})

    def test_headered_addresses_and_sources_match_headerless(self):
        rows=SlotLocations(self.rom).rows[7]
        headered=self.path.with_suffix('.smc');headered.write_bytes(b'H'*512+self.rom.data)
        rom=Rom(headered);result=SlotLocations(rom).rows[7]
        self.assertEqual([(r.kind,r.target) for r in rows],[(r.kind,r.target) for r in result])
        self.assertEqual(rom.address(self.player,6)-self.rom.address(self.player,6),512)

if __name__=='__main__':unittest.main()
