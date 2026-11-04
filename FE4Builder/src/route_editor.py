"""Private movement-route copies with catalogued caller discovery and atomic saves."""
import hashlib,json
from portraits import pc_address,pointer_for
from event_commands import EventCommands,catalogue
from movement_routes import DIRECTIONS
ARENA=0x5f0000
SIZE=0x10000
MAGIC=b'FE4BROUTESv1'.ljust(16,b'\0')
ROUTE_POINTERS={0x27:7,0x3f:1}
SIMPLE={0x80:'End',0x81:'Halt',0x85:'Face left',0x86:'Face right',0x87:'Face up',0x88:'Face down'}

def read_route(rom,pointer):
    at=pc_address(pointer)+rom.header;start=at;end=min(len(rom.data),at+0x10000-(pointer&65535));steps=[]
    for _ in range(256):
        if at>=end:raise ValueError('Truncated route or bank boundary.')
        op=rom.data[at];at+=1
        if 1<=op<=8:steps.append((DIRECTIONS[op-1],1))
        elif 10<=op<=18 or op==0x84:
            if at>=end:raise ValueError('Truncated route operand.')
            value=rom.data[at];at+=1
            steps.append((DIRECTIONS[op-10] if op<=17 else 'Wait' if op==18 else 'Speed',value))
        elif op in SIMPLE:
            steps.append((SIMPLE[op],0))
            if op==0x80:return steps,bytes(rom.data[start:at])
        else:raise ValueError(f'Unsupported route command ${op:02X}. This route remains read-only.')
    raise ValueError('Route exceeds 256 steps; editing disabled.')

def encode_steps(steps):
    if not steps or steps[-1][0]!='End' or any(name=='End' for name,_ in steps[:-1]):raise ValueError('Use exactly one End as the last step.')
    if len(steps)>256:raise ValueError('Maximum 256 steps.')
    result=bytearray();reverse={name:op for op,name in SIMPLE.items()}
    for name,value in steps:
        if name in reverse:result.append(reverse[name])
        else:
            if type(value) is not int or not 1<=value<=255:raise ValueError('Step amounts must be 1-255 (speed 1-5).')
            if name in DIRECTIONS:result.extend((10+DIRECTIONS.index(name),value))
            elif name=='Wait':result.extend((18,value))
            elif name=='Speed' and value<=5:result.extend((0x84,value))
            else:raise ValueError('Unsupported movement step or speed.')
    return bytes(result)

def callers(rom,pointer):
    result=[];unavailable=[];target=pc_address(pointer)
    for i,entry in enumerate(catalogue()['entries']):
        if not any(c['opcode'] in ROUTE_POINTERS for c in entry['commands']):continue
        try:model=EventCommands(rom,i)
        except ValueError:unavailable.append(entry['label']);continue
        for n,c in enumerate(model.commands):
            if c['opcode'] not in ROUTE_POINTERS:continue
            offset=ROUTE_POINTERS[c['opcode']]
            raw=model.snapshot[c['offset']+offset:c['offset']+offset+3];p=int.from_bytes(raw,'little')
            try:match=pc_address(p)==target
            except ValueError:match=False
            if match:result.append((i,n,f"{entry['label']} - command {n+1} (event {entry['id']:03X})"))
    return result,unavailable

class RouteDraft:
    opcode=0x27
    pointer_offset=7
    route_name='movement'
    decode=staticmethod(read_route)
    def encode(self,steps):return encode_steps(steps)
    def __init__(self,rom,event,command):
        self.rom=rom;self.event=event;self.command=command;self.snapshot=bytes(rom.data)
        model=EventCommands(rom,event);c=model.commands[command]
        if c['opcode']!=self.opcode:raise ValueError('Choose a matching '+self.route_name+' route command.')
        self.address=model.profile['start']+c['offset']+self.pointer_offset+rom.header
        self.pointer=int.from_bytes(rom.data[self.address:self.address+3],'little')
        self.steps,self.original=self.decode(rom,self.pointer)
        self.users,self.unavailable=callers(rom,self.pointer)
    def write(self,steps):
        if bytes(self.rom.data)!=self.snapshot:raise ValueError('ROM changed. Reopen the route editor before saving.')
        payload=self.encode(steps)
        if steps==self.steps:return []
        if len(self.rom.data)-self.rom.header!=0x800000:raise ValueError('Private routes require an 8 MiB ROM.')
        base=ARENA+self.rom.header;block=bytearray(self.rom.data[base:base+SIZE])
        if block[:16]==MAGIC:
            used=int.from_bytes(block[16:20],'little')
            if not 64<=used<=SIZE or block[20:52]!=hashlib.sha256(block[:20]+block[52:]).digest():raise ValueError('Route storage is damaged or was changed by another tool.')
        else:
            if len(set(block))!=1 or block[0] not in (0,255):raise ValueError('Private route storage is occupied. No data was changed.')
            # Existing catalogued references into the proposed arena prohibit claiming it.
            for i,e in enumerate(catalogue()['entries']):
                if not any(c['opcode'] in ROUTE_POINTERS for c in e['commands']):continue
                model=EventCommands(self.rom,i)
                for c in model.commands:
                    if c['opcode'] in ROUTE_POINTERS:
                        offset=ROUTE_POINTERS[c['opcode']]
                        p=int.from_bytes(model.snapshot[c['offset']+offset:c['offset']+offset+3],'little')
                        if ARENA<=pc_address(p)<ARENA+SIZE:raise ValueError('An existing route already references the proposed storage.')
            used=64;block[:64]=bytes(64);block[:16]=MAGIC
        if used+len(payload)>SIZE:raise ValueError('Private route storage is full. No data was changed.')
        pointer=pointer_for(ARENA+used);block[used:used+len(payload)]=payload
        block[16:20]=(used+len(payload)).to_bytes(4,'little');block[20:52]=hashlib.sha256(block[:20]+block[52:]).digest()
        data=bytearray(self.rom.data);data[base:base+SIZE]=block;data[self.address:self.address+3]=pointer.to_bytes(3,'little')
        details=[f'Private {self.route_name} route ${self.pointer:06X} -> ${pointer:06X}; only selected event command changed.']
        self.rom.data[:]=data
        return details
