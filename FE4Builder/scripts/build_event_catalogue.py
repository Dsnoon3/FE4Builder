"""Expand verified event commands for every chapter. Requires a user-owned reference ROM and disassembly."""
import argparse,hashlib,json,re,sys
from pathlib import Path
B=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(B/'src'))
from event_commands import FIELDS,schema
from portraits import pc_address

def definitions(path):
    result={}
    for name,body in re.findall(r'(\w+)\s+\.segment[^\n]*\n(.*?)\.endsegment',path.read_text(),re.S):
        lines=[line.split(';')[0].strip() for line in body.splitlines() if line.split(';')[0].strip()]
        if not lines or not re.fullmatch(r'\.byte \$[\dA-Fa-f]{2}',lines[0]):continue
        size=0
        for line in lines:
            m=re.fullmatch(r'\.(byte|char|word|sint|addr|long)\s+(.+)',line)
            if not m:break
            size+=dict(byte=1,char=1,word=2,sint=2,addr=2,long=3)[m[1]]
        else:result[int(lines[0][-2:],16)]=(name,size)
    return result

def build(rom,source):
    existing=json.loads((B/'data/event_commands.json').read_text(encoding='utf-8'))
    events=json.loads((B/'data/events.json').read_text(encoding='utf-8'))
    if len(rom)!=0x800000:raise ValueError('Catalogue generation requires the 8 MiB reference ROM.')
    for event in events['events']:
        raw=rom[event['start']:event['start']+event['length']]
        if hashlib.sha256(raw).hexdigest()!=event['hash']:raise ValueError('Reference ROM mismatch at '+event['label'])
    companions=[]
    for filename in ('event_commands','conversations','objectives'):
        companions+=json.loads((B/f'data/{filename}.json').read_text(encoding='utf-8'))['profiles']
    main=definitions(source/'SAFEGUARD/EVENTS/Main.h');conditions=definitions(source/'SAFEGUARD/EVENTS/Conditions.h')
    conditions[0x69]=('SET_TALK_TARGET_IF_UNMARRIED',5)
    old={e['id']:e for e in existing['entries']};entries=[];skipped=[]
    renamed={2:'GO_TO',3:'JUMP_IF_TRUE',4:'JUMP_IF_FALSE',8:'CHECK_CHAPTER_FLAG',0x3b:'MAP_TRANSITION'}
    for event in events['events']:
        if event['id'] in old:
            row=old[event['id']];row['source']=event['source'];entries.append(row);continue
        start=event['start'];limit=start+event['length'];nodes={};occupied={};pending=[start]
        try:
            while pending:
                at=pending.pop()
                while start<=at<limit:
                    if at in nodes:break
                    if at in occupied:raise ValueError('Branch points inside a command.')
                    offset=at-start;op=rom[at];child=None
                    if rom[at:at+2] in (b'\xff\xff',b'\xfe\xfe'):
                        opcode=65535 if rom[at]==255 else 65534
                        nodes[at]=dict(offset=offset,opcode=opcode,size=2,name='END_EVENT' if opcode==65535 else 'EVENT_DUMMY',condition=None,editable=False)
                        break
                    name,size=main[op]
                    if op in (0x4a,0x4d):
                        child=rom[at+1];child_name,child_size=conditions[child]
                        if child in (0x2c,0x2d):child_size=rom.index(255,at+2,limit)-(at+1)+1
                        size+=child_size;name+=' / '+child_name
                    if at+size>limit:raise ValueError('Truncated command.')
                    if any(pos in occupied for pos in range(at,at+size)):raise ValueError('Overlapping commands.')
                    c=dict(offset=offset,opcode=op,size=size,name=renamed.get(op,name),condition=child,editable=False)
                    if op in renamed:c['legacy_name']=name
                    # Unskippable wrappers have distinct execution semantics and stay read-only.
                    c['editable']=schema(c) in FIELDS and op!=0x4d
                    nodes[at]=c
                    for pos in range(at,at+size):occupied[pos]=at
                    if op in (2,3,4,5,6):
                        word=int.from_bytes(rom[at+1:at+3],'little',signed=op in (5,6))
                        target=at+word if op in (5,6) else (start&~65535)|word
                        if not start<=target<limit:raise ValueError('Branch leaves this verified script span.')
                        pending.append(target)
                        if op==2:break
                    at+=size
                else:raise ValueError('No terminator before end of verified span.')
            commands=sorted(nodes.values(),key=lambda c:c['offset'])
            if not any(c['opcode'] in (65535,65534) for c in commands):raise ValueError('No reachable event terminator.')
            row=dict(id=event['id'],chapter=event['chapter'],label=event['label'],commands=commands,source=event['source'],profile=dict(start=start,length=event['length'],masks=[]))
        except (KeyError,ValueError,IndexError) as error:
            reason=f'Unknown command or condition ${error.args[0]:02X}.' if isinstance(error,KeyError) else str(error);skipped.append(dict(id=event['id'],label=event['label'],reason=reason))
            row=dict(id=event['id'],chapter=event['chapter'],label=event['label'],commands=[],source=event['source'],unsupported=reason,profile=dict(start=start,length=event['length'],masks=[]))
        entries.append(row)
    # Preserve Prologue entry indices for existing callers; append the other scripts.
    entries=existing['entries']+[e for e in entries if e['id'] not in old]
    absolute=set()
    for p in companions:
        absolute.update((p['start']+at,n) for at,n in p['masks'])
    for e in entries:
        start=e['profile']['start']
        for c in e['commands']:
            if c['editable']:
                absolute.update((start+c['offset']+offset,size) for _,offset,size,_,_ in FIELDS[schema(c)])
            if c['opcode'] in (0x27,0x3f):absolute.add((start+c['offset']+(7 if c['opcode']==0x27 else 1),3))
    base={(p['start'],p['length']):p for p in companions}
    profiles=[]
    for e in entries:
        start=e['profile']['start'];length=e['profile']['length'];end=start+length
        profile=dict(base.get((start,length),{}),start=start,length=length)
        masks=sorted({(max(at,start)-start,min(at+n,end)-max(at,start)) for at,n in absolute if at<end and at+n>start})
        profile['masks']=masks;raw=bytearray(rom[start:end])
        for at,n in masks:raw[at:at+n]=bytes(n)
        profile['hash']=hashlib.sha256(raw).hexdigest();e['profile']=profile;profiles.append(profile)
    existing.update(version=2,entries=entries,profiles=profiles,skipped=skipped)
    (B/'data/event_commands.json').write_text(json.dumps(existing,indent=2)+'\n',encoding='utf-8')
    print(len(entries),'scripts;',sum(bool(e['commands']) for e in entries),'decoded;',sum(c['editable'] for e in entries for c in e['commands']),'editable commands;',len(skipped),'read-only layouts')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('rom',type=Path);parser.add_argument('source',type=Path);args=parser.parse_args()
    rom=args.rom.read_bytes()
    if len(rom)%0x8000==512:rom=rom[512:]
    build(rom,args.source)
