import logging
log = logging.getLogger("ai_scribe")

from .scripting import Script
def package_rom(romfile, outf="test.smc"):
    pass

DEFAULT_BLOCK = [(0xF8700, 0xFC050)]
# TODO: Have it use a unique message
DEFAULT_SCRIPT = b'\xf3\x00\00\xff\xff'
# Make a dict of the name -> script length
# then write scripts in the order you want
# construct pointers as the previous step happens
# replace script length with cumulative offset
def pack_scripts(export, orig_ptrs, script_blocks=DEFAULT_BLOCK,
                write_first=set(), use_default_script=True):
    # FIXME: do Dummies last
    # TODO: assert s.name == n

    # Get largest block (probably vanilla block)
    block = sorted(script_blocks, key=lambda t: t[1] - t[0])[-1]
    min_block = sorted(script_blocks, key=lambda t: t[0])[0]

    block_scrs = {blk: [] for blk in script_blocks}
    # Make all offsets relative to the games' expected start address
    block_offsets = {blk: blk[0] - 0xF8700 for blk in script_blocks}
    # Set the current pointer to the lowest block
    last = block_offsets[min_block]

    ptrs, scr = [], []

    # Start with 'error' script
    error_script_ptr = None
    if use_default_script:
        scr.append(DEFAULT_SCRIPT)
        block_scrs[block].append(DEFAULT_SCRIPT)
        error_script_ptr = last

        last += len(DEFAULT_SCRIPT)
        block_offsets[block] = last

    _ptrs = {}
    for n in write_first:
        _ptrs[n] = last
        scr.append(export[n]._bytes)
        block_scrs[block].append(export[n]._bytes)
        slen = len(export[n])
        # FIXME: restore pointer rewriting
        #log.debug(f">{n}: {hex(names[n])} -> {hex(0xF8700 + last)} +{hex(slen)}")
        log.debug(f">{n}: -> {hex(0xF8700 + last)} +{hex(slen)}")
        last += slen
        block_offsets[block] = last

    # TODO: remap pointers in actual dictionary
    #for n in names:
    for n in range(len(export)):
        if n in write_first:
            ptrs.append(_ptrs[n])
            continue

        for block, last in block_offsets.items():
            # block start offset relative to reference address
            if last + len(export[n]) >= block[1] - block[0]:
                continue

            ptrs.append(last)

            scr.append(export[n]._bytes)
            block_scrs[block].append(export[n]._bytes)

            slen = len(export[n])
            log.debug(f"{n}: -> [{hex(block[0])} {hex(block[1])}] | {hex(block[0] + last)} +{hex(slen)}")
            last += slen

            block_offsets[block] = last
            break
        else:
            # Uh oh --- without a default script, we can't do anything
            if error_script_ptr is None:
                raise ValueError("Cannot write additional scripts to block, out of space.")
            ptrs.append(error_script_ptr)
            log.warning(f"{n}: -> {hex(len(export[n]))} [OVERRUN]")
    assert None not in set(ptrs)

    # Rewrite to address space
    ptrs = construct_ptr_block(ptrs)
    for block, scr in block_scrs.items():
        block_scrs[block] = construct_scr_block(scr)
        print(f"({hex(block[0])}, {hex(block[1])}): {hex(block[1] - block[0])} -> {hex(len(block_scrs[block]))}")

    return block_scrs, ptrs

def construct_ptr_block(ptrs):
    low = b""
    for ptr in ptrs:
        low += int.to_bytes(ptr, 2, byteorder="little")
    return low

def construct_scr_block(scr):
    low = b""
    for s in scr:
        low += bytes(s)
    return low

def write_script_blocks(romfile, blocks):
    for (low, hi), data in blocks.items():
        block_diff = (hi - low) - len(data)

        if block_diff > 0:
            log.debug(f"Script block underrun, buffering {block_diff} bytes")
            data += bytes([255] * block_diff)
        elif block_diff < 0:
            log.error(f"Script block overrun.")
            raise ValueError(f"Script block overruns block bounds: {hex(low)} + {hex(len(data))} > {hex(hi)}")

        log.debug(f"Writing data block length {hex(len(data))} to ({hex(low)}, {hex(hi)})")
        romfile = romfile[:low] + data + romfile[hi:]

    return romfile


SCRIPT_BLOCK_LEN = 0xFC050 - 0xF8700
def randomize_scripts(g, n=384, ptr_off=0, total_len=SCRIPT_BLOCK_LEN, **kwargs):
    scripts = []
    _n = n
    while len(scripts) < _n:
        scripts += [g.generate_from_graph(**kwargs) for _ in range(_n - len(scripts))]
        scripts = [script for script in scripts if Script.validate(bytes(script))][:n]

    # Pair down longest scripts until we arrive at something we can fit in the ROM space
    while sum(map(len, scripts)) > total_len:
        scripts = sorted(scripts, key=len)
        try:
            scripts[-1] = g.generate_from_graph(**kwargs)
        except SyntaxError as e:
            print(e)
            raise ValueError("Encountered problem generating script with args: " +
                              str(kwargs))

    # FIXME: separate to pack function
    ptrs = [ptr_off] + [*map(len, scripts)][:-1]
    s = ptr_off
    for _ in range(len(ptrs)):
        s += ptrs.pop(0)
        ptrs.append(s)
    return scripts, ptrs