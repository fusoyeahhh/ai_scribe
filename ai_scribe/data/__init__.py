
ENEMY_DATA_OFFSET = 0xF0000
ENEMY_DATA_SIZE = 0x20
ENEMY_DATA_BLOCKS = 0x180
ENEMY_MP_REL_OFFSET = 0x0A
def give_base_mp(romfile):

    ptr = ENEMY_DATA_OFFSET + ENEMY_MP_REL_OFFSET
    for i in range(ENEMY_DATA_BLOCKS):
        mp = max(20, int.from_bytes(romfile[ptr:ptr + 2], "little"))
        romfile = romfile[:ptr] + mp.to_bytes(2, "little") + romfile[ptr + 2:]
        ptr += ENEMY_DATA_SIZE

    return romfile

_ESPER_TARGET_PATCH_LEN = 22
def apply_esper_target_patch(romfile, patch_dst=0xF8700):
    """
    Cancel on Party -> Cancel if no Opposition
    (Makes enemy use of espers not fizzle)
    Original patch written by AnubianCDude

    C2/5905: 22 00 20 F0            JSL Freespace            [Tested at C0D620, BC Code goes to F07000ish]

    [18 bytes used  (0x13)]

    By default, it will be placed in the very beginning of the allocated space for scripts, so writers will have to account for this.
    """
    # So if you move it to say  0x2F789A (EF/789A),
    # then the write to address 0x025905 [C2/5905]
    # would have to change to little-endian JSL command 22 9A 78 EF.
    # C2/5905: 22 00 20 F0            JSL Freespace            [Tested at C0D620, BC Code goes to F07000ish]
    #          EA EA                  NOPx2
    jsl_patch_data = [0x22] + list(patch_dst.to_bytes(3, "little")) + [0xEA, 0xEA]

    romfile = romfile[:0x25905] + bytes(jsl_patch_data) + romfile[0x25905 + len(jsl_patch_data):]

    # F0/7000:
    patch_data = [
        # A5 BA        LDA $BA
        0xA5, 0xBA,
        # 10 0B        BPL $590 B(branch if not abort on characters)
        0x10, 0x0B,
        # A5 BA        LDA $BA
        0xA5, 0xBA,
        # 10 0B        BPL $590B      (branch if not abort on characters)
        0x20, 0x0B,
        # 7B           TDC            (Accumulator = 0)
        0x7B,
        # E0 08        CPX #$08       (set Carry if caster is monster.  note that "caster" can
        #                               also mean "reflector", in which
        #                               case a good part of this function will
        #                               be skipped.)
        0xE0, 0x08,
        # B0 04        BCS    0x04            [If monster, skip]
        0xB0, 0x04,

        # 64 B8        STZ $B8        (clear character targets)
        0x64, 0xB8,
        # 80 02            BRA    0x02            [Skip to exit]
        0x80, 0x02,
        # 64 B9        STZ $B9        (clear enemy targets)
        0x64, 0xB9,
        # A5 BA        LDA $BA            [Load the flags again, because normal execution needs to use them]
        0xA5, 0xBA,
        # 6B            RTL        [Return to normal execution]
        0x6B
    ]
    romfile = romfile[:patch_dst] + bytes(patch_data) + romfile[patch_dst + len(patch_data):]

    return romfile