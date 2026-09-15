# CreateJS Graphics base64 path decoder
# --- work directory (all scratch data lives here; CW_WORK overrides) ---------
import os as _os
WORK = _os.environ.get('CW_WORK', '/tmp')
def wpath(*parts):
    return _os.path.join(WORK, *parts)


BASE64 = {"A":0,"B":1,"C":2,"D":3,"E":4,"F":5,"G":6,"H":7,"I":8,"J":9,
           "K":10,"L":11,"M":12,"N":13,"O":14,"P":15,"Q":16,"R":17,"S":18,"T":19,
           "U":20,"V":21,"W":22,"X":23,"Y":24,"Z":25,"a":26,"b":27,"c":28,"d":29,
           "e":30,"f":31,"g":32,"h":33,"i":34,"j":35,"k":36,"l":37,"m":38,"n":39,
           "o":40,"p":41,"q":42,"r":43,"s":44,"t":45,"u":46,"v":47,"w":48,"x":49,
           "y":50,"z":51,"0":52,"1":53,"2":54,"3":55,"4":56,"5":57,"6":58,"7":59,
           "8":60,"9":61,"+":62,"/":63}

CMD_NAMES = ['M','L','Q','C','Z']
PARAM_COUNT = [2,2,4,6,0]

def decode_createjs_path(s):
    """Decode CreateJS compact base64 path to SVG path commands list."""
    i = 0
    x, y = 0.0, 0.0
    commands = []
    
    while i < len(s):
        c = s[i]
        n = BASE64.get(c)
        if n is None:
            i += 1
            continue
        
        fi = n >> 3  # operation type
        if fi >= len(CMD_NAMES) or (n & 3):  # invalid command or unused bits not empty
            i += 1
            continue
        
        cmd = CMD_NAMES[fi]
        pl = PARAM_COUNT[fi]
        if fi == 0:  # moveTo resets position
            x, y = 0.0, 0.0
        
        i += 1
        charCount = (n >> 2 & 1) + 2  # 4th bit: 0=2chars, 1=3chars
        params = []
        
        for p_idx in range(pl):
            if i + charCount > len(s):
                break
            num = 0
            for j in range(charCount):
                nc = BASE64.get(s[i+j])
                if nc is None: nc = 0
                if j == 0:
                    sign = -1 if (nc >> 5) else 1
                    num = nc & 31
                else:
                    num = (num << 6) | nc
            i += charCount
            
            val = sign * num / 10.0
            if p_idx % 2 == 0:  # x
                val += x
                x = val
            else:  # y
                val += y
                y = val
            params.append(round(val, 2))
        
        if cmd == 'Z':
            commands.append(('Z',))
        else:
            commands.append((cmd,) + tuple(params))
    
    return commands

def commands_to_svg_path(commands):
    """Convert command list to SVG path d string."""
    parts = []
    for cmd in commands:
        if cmd[0] == 'Z':
            parts.append('Z')
        else:
            coords = ','.join(f'{v:.1f}' for v in cmd[1:])
            parts.append(f'{cmd[0]}{coords}')
    return ' '.join(parts)

# Test on 你 shape_1 (stroke 1)
test_path = "AD7KkQjHjtigkHQkHmelBmTQi+iygwhZQgmhXBZgCQCogbIvETQIrEeFWFyQEUFJhvIMQg6DNi7AiQgJACgKAAQh9AAkOlFg"
cmds = decode_createjs_path(test_path)
print("test (你 stroke1):", len(cmds), "commands")
print("first 5:", cmds[:5])
svg = commands_to_svg_path(cmds)
print("SVG:", svg[:120])
