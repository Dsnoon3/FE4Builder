"""Camera-specific route grammar; legacy no-direction records are preserve-only."""
from collections import Counter
from portraits import pc_address
from route_editor import RouteDraft,DIRECTIONS
LEGACY='Legacy no-direction step ($12; preserve only)'

def read_camera_route(rom,pointer):
    at=pc_address(pointer)+rom.header;start=at
    end=min(len(rom.data),at+0x10000-(pointer&65535));steps=[]
    for _ in range(256):
        if at>=end:raise ValueError('Camera route is truncated or crosses its bank.')
        op=rom.data[at];at+=1
        if op==0x80:
            steps.append(('End',0));return steps,bytes(rom.data[start:at])
        if 1<=op<=8:steps.append((DIRECTIONS[op-1],1))
        elif 10<=op<=18 or op==0x84:
            if at>=end:raise ValueError('Camera route operand is truncated.')
            amount=rom.data[at];at+=1
            name=DIRECTIONS[op-10] if op<=17 else LEGACY if op==18 else 'Speed'
            if amount==0:raise ValueError('Camera route contains an unsupported zero amount/speed.')
            steps.append((name,amount))
        else:raise ValueError(f'Unsupported camera route byte ${op:02X}; editing disabled.')
    raise ValueError('Camera route exceeds 256 steps.')

def encode_camera_steps(steps,original=()):
    if not steps or len(steps)>256 or steps[-1]!=('End',0) or any(k=='End' for k,v in steps[:-1]):
        raise ValueError('Use exactly one End as the last step; maximum 256 steps.')
    legacy=Counter(step for step in original if step[0]==LEGACY);result=bytearray()
    for name,amount in steps:
        if name=='End':result.append(0x80);continue
        if type(amount) is not int or not 1<=amount<=255:raise ValueError('Camera distances and speeds must be 1-255.')
        if name in DIRECTIONS:result.extend((10+DIRECTIONS.index(name),amount))
        elif name=='Speed':result.extend((0x84,amount))
        elif name==LEGACY and legacy[(name,amount)]:
            legacy[(name,amount)]-=1;result.extend((18,amount))
        else:raise ValueError('Unsupported camera step. Legacy $12 can only be preserved or removed; it is not a normal timed pause.')
    return bytes(result)

class CameraRouteDraft(RouteDraft):
    opcode=0x3f
    pointer_offset=1
    route_name='camera'
    decode=staticmethod(read_camera_route)
    def encode(self,steps):return encode_camera_steps(steps,self.steps)

def camera_preview(rom,pointer):
    try:
        steps,_=read_camera_route(rom,pointer)
        return f'Camera route ${pointer:06X}:\n'+'\n'.join(f'{k} {v}' if v else k for k,v in steps)
    except ValueError as error:return f'Camera route ${pointer:06X}: '+str(error)
