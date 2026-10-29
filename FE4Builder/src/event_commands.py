"""Fixed-length Prologue event operand editing with shared layout and stale-draft guards."""
import json
from functools import lru_cache
from rom import DATA_DIR
from portraits import pc_address
from event_layouts import checked

# (Label, operand offset, bytes, minimum, maximum)
BACKGROUNDS={0:'Fountain',1:'Gate',2:'Alley',3:'Throne',4:'Hallway',5:'Cloister'}
FIELDS={0x4b:[('Chapter',1,1,0,11),('Event flag',2,1,0,79)],0x4c:[('Chapter',1,1,0,11),('Event flag',2,1,0,79)],0x27:[('Character',1,2,1,696),('Start X',3,1,0,63),('Start Y',4,1,0,63),('Movement speed',5,1,1,5),('Sprite color',6,1,2,8),('Disappear offscreen',5,1,0,1)],0x14:[('Dialogue scene',1,3,0,0xffffff),('Background',4,1,0,5),('Fade timing',6,1,1,255)],0x0c:[('Dialogue scene',1,3,0,0xffffff)],0x0e:[('Music track',1,1,0,255)],0x11:[('Byte sound effect',1,1,0,255)],0x12:[('Word sound command',1,2,0,65535)],0x34:[('Pause ticks',1,2,1,65535)],0x3a:[('Camera X',1,1,0,63),('Camera Y',2,1,0,63)],
        0x23:[('Unit group',1,1,0,57),('Entry in group',2,2,1,65535),('Start X',4,1,0,63),('Start Y',5,1,0,63),('Movement speed',6,1,0,7)],
        0x24:[('Character',1,2,1,696),('Faction slot',3,1,0,3),('Start X',4,1,0,63),('Start Y',5,1,0,63),('Destination X',6,1,0,63),('Destination Y',7,1,0,63),('Movement speed',8,1,0,7),('Sprite color',9,1,2,6),('Group leader',10,1,0,1),('AI setting',10,1,0,15)],
        0x42:[('Character',1,2,1,696),('Slot',3,1,0,1)],
        0x40:[('Camera X',1,1,0,63),('Camera Y',2,1,0,63),('Scroll speed',3,1,1,255)],
        0x46:[('Fade timing',1,1,1,255)],0x47:[('Fade timing',1,1,1,255)],
        'talk_target':[('Initiator',2,1,1,255),('Target',3,1,0,255)],
        'character_sprite':[('Prepare map sprite for',2,2,1,696)]}
def schema(command):
    if command['opcode']==0x4a:return {0x49:'character_sprite',0x68:'talk_target'}.get(command.get('condition'),command['opcode'])
    return command['opcode']

def audio_kind(command):return {0x0e:'music',0x11:'byte',0x12:'word'}.get(command['opcode'])

def audio_options(command):
    from audio_preview import catalogue as audio_catalogue
    kind=audio_kind(command)
    return {e['value']:e['label'] for e in audio_catalogue()['entries'] if e['kind']==kind}

def character_options(rom):
    from conversations import character_names
    from map_sprites import MapSprites
    sprites=MapSprites(rom);result={}
    for value,name in character_names(rom).items():
        if not 1<=value<=696:continue
        try:sprites.character(value)
        except (ValueError,IndexError):continue
        result[value]=name
    return result

HELP={0x4b:'Turn ON the selected chapter-local event flag only if that chapter is active; otherwise continue without changing flags. Flags are switches read by other events, not direct terrain or unit actions. A later map-update command may be needed. IDs 0-79 are implemented by the native handler. Names describe reference-ROM uses, not guaranteed behavior in a custom ROM.',0x4c:'Turn OFF the selected chapter-local event flag only if that chapter is active; otherwise continue without changing flags. Clearing a flag does not directly replay events or change terrain. IDs 0-79 are implemented by the native handler. Names describe reference-ROM uses, not guaranteed behavior in a custom ROM.',0x27:'Animate a temporary character map sprite along the existing movement script. This is visual only: it does not deploy or recruit a unit. Start X/Y are map tiles; sprite color does not change allegiance. Initial speed can be changed by the route. Basic parameter edits preserve the route. Edit movement route creates a private copy and updates only this command pointer. Prepare matching sprite graphics and keep later waits aligned. Unknown route commands stop the preview; no route data is changed.',0x23:'Load one unit from an Army Editor deployment group and animate its entrance from Start X/Y to the record’s destination. Group entries are numbered from 1. Character, destination, faction, AI, commander and formation come from the selected Army record. The stored sprite-color byte is preserved: the native handler chooses the displayed color from allegiance. Movement speed changes the entrance animation only; other movement flags are preserved. Reusing a deployment can affect an already-loaded unit. Keep sprite preparation and later scene commands aligned.',0x28:'Read-only. Load the selected Army group entry hidden, without the normal entrance animation. This native command has a group ID and a one-based entry number.',0x42:'Look up an existing character and store its unit reference and current map coordinates in Event Unit Slot 1 or 2. This replaces the previous contents of that slot; it does not spawn or move the character. A failed lookup clears its reference and marks the coordinates invalid. Coordinates are captured when this command runs, so fill the slot again after movement if later commands need an updated position.',0x39:'Read-only, no parameters. Use Event Unit Slot 1’s stored coordinates as the map cursor/camera focus. The native handler updates cursor offsets relative to the current view, rather than directly writing camera scroll coordinates. If either stored coordinate is invalid, nothing happens. Fill Slot 1 first. There is no separate Slot 2 counterpart in the standard event command set.',0x41:'Read-only. Smoothly scroll the camera toward Event Unit Slot 1’s stored coordinates. This command has one native scroll-speed parameter. Invalid stored coordinates leave the view unchanged. Fill Slot 1 before using it; this does not track a unit’s later movement automatically. There is no separate Slot 2 counterpart in the standard event command set.',0x14:'Play a dialogue scene against the selected background. Find dialogue searches scene names and text; Open in Dialogue Editor edits this command’s text reference. Fade timing is the native transition parameter, not seconds. Dialogue Type is shown read-only and preserved because its presentation modes are not fully verified. Test the complete scene in-game.',0xffff:'Read-only, no parameters. End this event script and return control to the event engine. This is the two-byte terminator FF FF; it does not by itself end the chapter or choose an objective, dialogue or music track.',0x13:'Read-only, no parameters. Restore the map music stored for the current phase after an event temporarily plays another song. The stored phase track can reflect the chapter, active faction or victory situation; this does not simply restore the last song played. Use Play Song to select a specific track.', 'talk_target':'Set the initiator’s talk-target information. This replaces their previous target and is directional: A → B does not also set B → A. Target None clears the stored target. Both IDs are one byte. This does not create a conversation, recruit a character or select dialogue; keep the separate chapter talk trigger aligned using Recruitment & Conversations. The initiator must exist when this event executes.',0x0c:'Choose a dialogue by chapter, scene name or text using Find dialogue. This replaces only the existing command’s 3-byte pointer. Open in Dialogue Editor edits the text used by this command; settle pending event changes first. Dialogue controls portraits, speakers and pauses inside its own script.',0x29:'Read-only, no parameters. Wait until sprite decompression has finished and the unit movement setup engine is idle. This allows pending graphics/loading setup to complete; it does not guarantee that all units have finished walking. Use Wait Until Map Sprites Halting to synchronize scripted movement.',
      0xfd:'Read-only, no parameters. Yield ends the current event-processing pass and resumes at the following command on a later update, normally the next frame when the event engine is ready. It gives other game systems time to update. It is not a fixed-duration pause or a wait for a particular animation, movement or dialogue to finish.',
      0x2a:'Read-only, no parameters. Wait until every active scripted moving map sprite has finished moving or reached a halt point in its movement script. This covers event-controlled sprites, not every unit on the map. If no scripted sprites are active, continue immediately. A halt can be temporary: Continue From Map Sprite Halt resumes halted movement scripts. This command waits for movement readiness; it does not stop sprites itself.',
      0x0e:'Choose the music played by this existing command. Preview audio auditions the selected draft without saving it.',
      0x11:'Choose an observed byte sound effect. Preview audio auditions the selected draft using the same sound-driver queue.',
      0x12:'Choose an observed full word sound-driver command. Some control fading/volume rather than play an effect; preview can include background music. The full 16-bit word is preserved.',
      'character_sprite':'Prepare the selected character’s map-sprite graphics. This does not spawn, move or recruit that character. Match the graphics required by the later deployment/movement commands.',0x34:'Delay before the next command, in event timer ticks. This does not change dialogue waits or movement timing.',
      0x3a:'Move the camera to these map coordinates (0–63). This changes the camera only; units and terrain stay in place.',
      0x24:'Deploy an existing character and animate their entrance from Start to Destination. Faction slots here are Prologue groups; sprite color does not change allegiance. Group leader marks the commander. AI setting is the native 0–15 value, whose behavior depends on the faction AI. Movement speed changes only the entrance animation; other movement flags are preserved. Prepare the matching map sprite earlier in the event. Avoid deploying the same character twice, and review later dialogue and movement commands after replacing a character.',
      0x40:'Pan the camera smoothly to X/Y (0–63), measured in map tiles at the upper-left of the screen. Scroll speed accepts 1–255; larger values move faster. Zero is rejected because it cannot advance the scroll. Units and terrain stay in place. Keep the destination within the chapter camera area and test the scene in-game.',
      0x46:'Native fade-in timing parameter (1–255). This is not a duration in seconds; test the transition in-game.',
      0x47:'Native fade-out timing parameter (1–255). This is not a duration in seconds; test the transition in-game.'}

def field_bits(command,index):
    if command['opcode']==0x27:return {3:(7,0),5:(16,4)}.get(index,(65535 if index==0 else 255,0))
    if command['opcode']==0x23 and index==4:return (7,0)
    if command['opcode']==0x24:
        return {6:(7,0),8:(128,7),9:(15,0)}.get(index,(255 if index!=0 else 65535,0))
    return ((1 << (FIELDS.get(schema(command),[('',0,2,0,0)])[index][2]*8))-1,0)

def chapter_flag_options(chapter):
    known=catalogue().get('chapter_flags',{}).get(str(chapter),{})
    return {i:known.get(str(i),'Unnamed flag') for i in range(80)}

def temporary_options(rom,index):
    if index==0:return character_options(rom)
    return {4:{2:'Blue',4:'Red',6:'Green',8:'Yellow'},5:{0:'No',1:'Yes'}}.get(index,{})

def deployment_options(rom,index):
    if index==0:return character_options(rom)
    return {1:{0:'Player',1:'Evans',2:'Yngvi',3:'Arvis'},7:{2:'Blue',4:'Red',6:'Green'},8:{0:'No',1:'Yes'}}.get(index,{})

@lru_cache(maxsize=1)
def catalogue():return json.loads((DATA_DIR/'event_commands.json').read_text(encoding='utf-8'))

class EventCommands:
    def __init__(self,rom,index):
        self.rom=rom;self.index=index;self.entry=catalogue()['entries'][index];self.profile=self.entry['profile']
        at=0xfe8bf+self.entry['id']*3+rom.header;self.pointer=bytes(rom.data[at:at+3])
        if len(self.pointer)!=3 or pc_address(int.from_bytes(self.pointer,'little'))!=self.profile['start']:
            raise ValueError('This event has moved. Editing requires its verified original location.')
        self.snapshot=checked(rom,self.profile);self.commands=self.entry['commands']
        self.group_snapshot=bytes(rom.data[0x1c000+rom.header:0x20000+rom.header])
    def dialogues(self):
        if not hasattr(self,'_dialogues'):
            try:self._dialogues=dialogue_options(self.rom)
            except ValueError:self._dialogues=[]
        return self._dialogues
    def values(self,index):
        command=self.commands[index];at=command['offset']
        return [(int.from_bytes(self.snapshot[at+offset:at+offset+size],'little') & field_bits(command,i)[0]) >> field_bits(command,i)[1] for i,(_,offset,size,_,_) in enumerate(FIELDS.get(schema(command),[]))]
    def describe(self,index):
        command=self.commands[index];fields=FIELDS.get(schema(command),[])
        values=self.values(index)
        if schema(command)=='character_sprite':
            return 'Prepare character map sprite · '+character_options(self.rom).get(values[0],f'Character 0x{values[0]:04X}')
        if command['opcode']==0x23:
            return 'Load Unit by Group · '+unit_groups(self.rom).get(values[0],str(values[0]))+' / '+group_units(self.rom,values[0]).get(values[1],{}).get('label',f'Entry {values[1]}')+f' · Start {values[2]}, {values[3]} · Speed {values[4]}'
        if command['opcode']==0x42:
            names=character_options(self.rom)
            return 'Fill Event Unit Slot · '+names.get(values[0],f'Character ${values[0]:04X}')+f' → Slot {1 if values[1]==0 else 2}'
        if schema(command)=='talk_target':
            names=talk_options(self.rom,0);targets=talk_options(self.rom,1)
            return 'Set Talk Target · '+names.get(values[0],f'Character ${values[0]:02X}')+' → '+targets.get(values[1],f'Character ${values[1]:02X}')
        if command['opcode'] in (0x0c,0x14):
            labels={o['pointer']:o['label'] for o in self.dialogues()}
            label=labels.get(values[0],f'Existing scene ${values[0]:06X}')
            if command['opcode']==0x14:
                mode=self.snapshot[command['offset']+5]
                return 'Dialogue with BG · '+label+' · '+BACKGROUNDS.get(values[1],f'Background {values[1]}')+f' · Type {mode} (read-only) · Fade {values[2]}'
            return 'Dialogue · '+label
        if audio_kind(command):
            return command['name'].replace('_',' ').title()+' · '+audio_options(command).get(values[0],f'Existing unknown ${values[0]:04X}')+f' (${values[0]:04X})'
        return command['name'].replace('_',' ').title()+(' · '+', '.join(f'{field[0]}: {value}' for field,value in zip(fields,values)) if fields else '')
    def write(self,updates):
        current=EventCommands(self.rom,self.index)
        if current.pointer!=self.pointer or current.snapshot!=self.snapshot:
            raise ValueError('Event bytes changed while this editor was open. Reload before writing.')
        if any(type(i) is int and 0<=i<len(self.commands) and self.commands[i]['opcode']==0x23 for i in updates) and current.group_snapshot!=self.group_snapshot:
            raise ValueError('Army deployment data changed. Reload before editing group loads.')
        edits={};details=[]
        for index,values in updates.items():
            if type(index) is not int or not 0<=index<len(self.commands):raise ValueError('Unknown command selection.')
            command=self.commands[index];fields=FIELDS.get(schema(command))
            if not command['editable'] or fields is None:raise ValueError('This command is read-only.')
            if schema(command)=='character_sprite' and (len(values)!=1 or type(values[0]) is not int or values[0] not in character_options(self.rom)):
                raise ValueError('Choose a character with a valid map-sprite assignment.')
            if len(values)!=len(fields):raise ValueError('Incorrect command parameter count.')
            if command['opcode']==0x23:
                if any(type(v) is not int for v in values):raise ValueError('Group load parameters must be whole numbers.')
                if values[0] not in unit_groups(self.rom) or values[1] not in group_units(self.rom,values[0]):raise ValueError('Choose a valid unit entry in the selected deployment group.')
            for field_index,((label,offset,size,low,high),value,old) in enumerate(zip(fields,values,self.values(index))):
                if type(value) is not int or (not low<=value<=high and value!=old):raise ValueError(f'{label} must be {low}–{high}.')
                if command['opcode']==0x27 and value!=old and temporary_options(self.rom,field_index) and value not in temporary_options(self.rom,field_index):
                    raise ValueError(f'{label}: choose a listed option.')
                if command['opcode']==0x42 and field_index==0 and value!=old and value not in character_options(self.rom):
                    raise ValueError('Choose a character with a valid unit assignment.')
                if command['opcode']==0x14 and field_index==1 and value!=old and value not in BACKGROUNDS:
                    raise ValueError('Choose a listed dialogue background.')
                if schema(command)=='talk_target' and value!=old and value not in talk_options(self.rom,field_index):
                    raise ValueError(f'{label}: choose a named character with a one-byte ID.')
                if command['opcode']==0x24 and deployment_options(self.rom,field_index) and value!=old and value not in deployment_options(self.rom,field_index):
                    raise ValueError(f'{label}: choose a listed option.')
                if command['opcode'] in (0x0c,0x14) and field_index==0 and value!=old and value not in {o['pointer'] for o in self.dialogues()}:
                    raise ValueError('Dialogue scene: choose a supported scene from Find dialogue.')
                if value!=old and audio_kind(command) and value not in audio_options(command):
                    raise ValueError(f'{label}: choose an ID from the audio catalogue. Existing unknown values may be kept unchanged.')
                if value!=old:
                    address=self.profile['start']+command['offset']+offset+self.rom.header
                    mask,shift=field_bits(command,field_index)
                    previous=int.from_bytes(edits.get(address,self.rom.data[address:address+size]),'little')
                    edits[address]=((previous & ~mask) | (value << shift)).to_bytes(size,'little')
                    details.append(f'Command {index+1}: {label} {old} → {value}')
        # Validate the entire draft before touching memory; preserve every opcode and pointer.
        for address,data in edits.items():self.rom.data[address:address+len(data)]=data
        return details


def dialogue_options(rom):
    from dialogue import catalogue as scenes,Dialogue,readable,check_profile
    check_profile(rom)
    result=[]
    for entry in scenes()['entries']:
        try:model=Dialogue(rom,entry)
        except ValueError:continue
        result.append(dict(entry=entry,pointer=int.from_bytes(model.pointer,'little'),label=entry['group']+' · '+entry['label'],text=readable(model.text)))
    return result


def talk_options(rom,index):
    from conversations import character_names
    result={value:name for value,name in character_names(rom).items() if 1<=value<=255}
    if index==1:result={0:'None (clear talk target)',**result}
    return result


def unit_groups(rom):
    metadata=json.loads((DATA_DIR/'army_groups.json').read_text(encoding='utf-8'))
    return {i:('Prologue' if e['chapter']==0 else 'Final Chapter' if e['chapter']==11 else f"Chapter {e['chapter']}")+' / '+e['group'] for i,e in enumerate(metadata)}

def group_units(rom,group):
    from conversations import character_names
    groups=unit_groups(rom)
    if type(group) is not int or group not in groups:raise ValueError('Unknown deployment group.')
    base=0x1c000+rom.header
    offsets=[int.from_bytes(rom.data[base+i*2:base+i*2+2],'little') for i in groups]
    offset=offsets[group]
    if offset<len(groups)*2 or offset>=0x4000 or (offset-116)%8:raise ValueError('Invalid army deployment pointer.')
    end=min([v for v in offsets if v>offset]+[0x4000])
    if group==57:end=min(end,offset+13*8)
    names=character_names(rom);result={};terminated=False
    for pos in range(offset,end-7,8):
        raw=rom.data[base+pos:base+pos+8];character=int.from_bytes(raw[:2],'little')
        if character==65535:terminated=True;break
        entry=len(result)+1
        result[entry]=dict(label=f"{entry}: "+names.get(character,f'Character ${character:04X}'),character=character,x=raw[2],y=raw[3],leader=bool(raw[4]),ai=raw[5],faction=raw[6],formation=raw[7])
    if not terminated and group!=57:raise ValueError('Army deployment group has no valid end marker.')
    return result
