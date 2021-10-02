CMD_LIST = """00 Fight Works correctly
01 Item Says Dirk, but casts Fire
02 Magic Casts Fire
03 Morph Works correctly, but causes monster to move forward a step each time
04 Revert Works correctly, but causes monster to move forward a step each time
05 Steal Works correctly - Monster steals gold from party
06 Capture Works correctly - Monster steals gold, and does damage
07 Swdtech Casts Fire with messed up name, and no animation
08 Throw Throws a Dirk
09 Tools Says Dirk but has strange results
0A Blitz Casts Fire with messed up animation
0B Runic Works correctly
0C Lore Casts Fire
0D Sketch Works correctly, but fails against characters, so must target monster
0E Control Fails if used on characters, causes strange glitches if used on monsters
0F Slots Casts Fire, with messed up name, and no animation
10 Rage Casts Fire
11 Leap Ends battle, Gau leaves party and can't be gotten back
12 Mimic Works correctly (mimics party's last attack)
13 Dance Tries to dance Wind Song, Always casts fire once successful
14 Row Works correctly
15 Def. Works correctly
16 Jump Works correctly
17 X-Magic Casts Fire (only once)
18 GPRain Works correctly
19 Summon Casts Fire, with messed up name, and no animation
1A Health Works correctly
1B Shock Works correctly
1C Possess Works correctly, but fails against characters, so must target monster
1D Magitek Casts Fire""".split("\n")

CMD_LIST = [s.split(" ") for s in CMD_LIST]
CMD_LIST = {int(idx, 16): f"({cmd})" if 'Works' in descr else f"{{{cmd}}}"
            for idx, cmd, *descr in CMD_LIST}
CMD_LIST[0xFE] = "Nothing"

SPELL_LIST = """00:ºFire**
01:ºIce***
02:ºBolt**
03:ºPoison
04:ºDrain*
05:ºFire 2
06:ºIce 2*
07:ºBolt 2
08:ºBio***
09:ºFire 3
0A:ºIce 3*
0B:ºBolt 3
0C:ºBreak*
0D:ºDoom**
0E:ºPearl*
0F:ºFlare*
10:ºDemi**
11:ºQuartr
12:ºX-Zone
13:ºMeteor
14:ºUltima
15:ºQuake*
16:ºW Wind
17:ºMerton
18:öScan**
19:öSlow**
1A:öRasp**
1B:öMute**
1C:öSafe**
1D:öSleep*
1E:öMuddle
1F:öHaste*
20:öStop**
21:öBserk*
22:öFloat*
23:öImp***
24:öRflect
25:öShell*
26:öVanish
27:öHaste2
28:öSlow 2
29:öOsmose
2A:öWarp**
2B:öQuick*
2C:öDispel
2D:•Cure**
2E:•Cure 2
2F:•Cure 3
30:•Life**
31:•Life 2
32:•Antdot
33:•Remedy
34:•Regen*
35:•Life 3
36:Ramuh***
37:Ifrit***
38:Shiva***
39:Siren***
3A:Terrato*
3B:Shoat***
3C:Maduin**
3D:Bismark*
3E:Stray***
3F:Palidor*
40:Tritoch*
41:Odin****
42:Raiden**
43:Bahamut*
44:Alexandr
45:Crusader
46:Ragnarok
47:Kirin***
48:ZoneSeek
49:Carbunkl
4A:Phantom*
4B:Sraphim*
4C:Golem***
4D:Unicorn*
4E:Fenrir**
4F:Starlet*
50:Phoenix*
51:Fire Skean
52:Water Edge
53:Bolt Edge*
54:Storm*****
55:Joker Doom(really Dispatch)
56:**********(really Retort)
57:**********(really Slash)
58:**********(really Quadra Slam)
59:**********(really Empowerer)
5A:**********(really Stunner)
5B:**********(really Quadra Slice)
5C:**********(really Cleave)
5D:Pummel****
5E:AuraBolt**
5F:Suplex****
60:Fire Dance
61:Mantra****
62:Air Blade*
63:Spiraler**
64:Bum Rush**
65:Wind Slash
66:Sun Bath**
67:Rage******
68:Harvester*
69:Sand Storm
6A:Antlion***
6B:Elf Fire**
6C:Specter***
6D:Land Slide
6E:Sonic Boom
6F:El Nino***
70:Plasma****
71:Snare*****
72:Cave In***
73:Snowball**
74:Surge*****
75:Cokatrice*
76:Wombat****
77:Kitty*****
78:Tapir*****
79:Whump*****
7A:Wild Bear*
7B:Pois. Frog
7C:Ice Rabbit
7D:Bio Blast*(Super Ball)
7E:Flash*****
7F:Chocobop**
80:H-Bomb****
81:7-Flush***
82:Megahit***(Leo's Shock)
83:Fire Beam*
84:Bolt Beam*
85:Ice Beam**
86:Bio Blast*
87:Heal Force
88:Confuser**
89:X-fer*****
8A:TekMissile
8B:Condemned*
8C:Roulette**
8D:CleanSweep
8E:Aqua Rake*
8F:Aero******
90:Blow Fish*
91:Big Guard*
92:Revenge***
93:Pearl Wind
94:L.5 Doom**
95:L.4 Flare*
96:L.3 Muddle
97:Reflect???
98:L? Pearl**
99:Step Mine*
9A:ForceField
9B:Dischord**
9C:Sour Mouth
9D:Pep Up****
9E:Rippler***
9F:Stone*****
A0:Quasar****
A1:GrandTrain
A2:Exploder**
A3:Imp Song**
A4:Clear*****
A5:Virite****
A6:ChokeSmoke
A7:Schiller**
A8:Lullaby***
A9:Acid Rain*
AA:Confusion*
AB:Megazerk**
AC:Mute******
AD:Net*******
AE:Slimer****
AF:Delta Hit*
B0:Entwine***
B1:Blaster***
B2:Cyclonic**
B3:Fire Ball*
B4:Atomic Ray
B5:Tek Laser*
B6:Diffuser**
B7:WaveCannon
B8:Mega Volt*
B9:Giga Volt*
BA:Blizzard**
BB:Absolute 0
BC:Magnitude8
BD:Raid******
BE:Flash Rain
BF:TekBarrier
C0:Fallen One
C1:WallChange
C2:Escape****
C3:50 Gs*****
C4:Mind Blast
C5:N. Cross**
C6:Flare Star
C7:Love Token
C8:Seize*****
C9:R.Polarity
CA:Targeting
CB:Sneeze****
CC:S. Cross**
CD:Launcher**
CE:Charm*****
CF:Cold Dust*
D0:Tentacle**
D1:HyperDrive
D2:Train*****
D3:Evil Toot*
D4:Grav Bomb*
D5:Engulf****
D6:Disaster**
D7:Shrapnel**
D8:Bomblet***
D9:Heart Burn
DA:Zinger****
DB:Discard***
DC:Overcast**
DD:Missile***
DE:Goner*****
DF:Meteo*****
E0:Revenger**
E1:Phantasm**
E2:Dread*****
E3:Shock Wave
E4:Blaze*****
E5:Soul Out**
E6:Gale Cut**
E7:Shimsham**
E8:Lode Stone
E9:Scar Beam*
EA:BabaBreath
EB:Lifeshaver
EC:Fire Wall*
ED:Slide*****
EE:Battle****
EF:Special***
F0:Riot Blade
F1:Mirager***
F2:Back Blade
F3:ShadowFang
F4:RoyalShock
F5:TigerBreak
F6:Spin Edge*
F7:SabreSoul*
F8:Star Prism
F9:Red Card**
FA:MoogleRush
FB:X-Meteo***
FC:Takedown**
FD:Wild Fang*
FE:Lagomorph*
FF:??????????""".replace("Lagomorph*", "Nothing").split("\n")

SPELL_LIST = [s.split(":")[-1].replace("*", "") for s in SPELL_LIST]

ESPERS = {k: v for k, v in enumerate(SPELL_LIST) if k in range(0x36, 0x50)}
DESPERATIONS = {k: v for k, v in enumerate(SPELL_LIST) if k in range(0xF0, 0xFE)}

TARGET_LIST = """00	Terra
01	Locke
02	Cyan
03	Shadow
04	Edgar
04	Sabin
05	Celes
06	Strago
07	Setzer
08	Relm
09	Mog
0A	Gau
0B	Gogo
0C	Umaro
0D	Banon
0E	Leo
2B	Kefka (at Thamasa)
30	Monster #1
31	Monster #2
32	Monster #3
33	Monster #4
34	Monster #5
35	Monster #6
36	Self
37	All monsters except self
38	All monsters
39	Random monster excluding self
3A	Random monster
3B	All dead characters
3C	Random dead character
3D	All dead monsters
3E	All dead monsters
3F	All characters with wall status
40	Random character with wall status
41	All monsters with wall status
42	Random monster with wall status
43	All characters
44	Random character
45	Character who last attacked
46	All characters and all monsters
47	Use normal targetting
48	Character #1
49	Character #2
4A	Character #3
4B	Character #4
4C	50% chance all targets (except self), 50% one random target (not self)
4D	Target that was last targetted by Targetting""".split("\n")

TARGET_LIST = [s.split("\t") for s in TARGET_LIST]
TARGET_LIST = {int(i, 16): t.strip() for i, t in TARGET_LIST}

ITEM_LIST = """00 Dirk
01 MithrilKnife
02 Guardian
03 Air Lancet
04 ThiefKnife
05 Assassin
06 Man Eater
07 SwordBreaker
08 Graedus
09 ValiantKnife
0A MithrilBlade
0B RegalCutlass
0C Rune Edge
0D Flame Sabre
0E Blizzard
0F ThunderBlade
10 Epee
11 Break Blade
12 Drainer
13 Enhancer
14 Crystal
15 Falchion
16 Soul Sabre
17 Ogre Nix
18 Excalibur
19 Scimitar
1A Illumina
1B Ragnarok
1C Atma Weapon
1D Mithril Pike
1E Trident
1F Stout Spear
20 Partisan
21 Pearl Lance
22 Gold Lance
23 Aura Lance
24 Imp Halberd
25 Imperial
26 Kodachi
27 Blossom
28 Hardened
29 Striker
2A Stunner
2B Ashura
2C Kotetsu
2D Forged
2E Tempest
2F Murasame
30 Aura
31 Strato
32 Sky Render
33 Heal Rod
34 Mithril Rod
35 Fire Rod
36 Ice Rod
37 Thunder Rod
38 Poison Rod
39 Pearl Rod
3A Gravity Rod
3B Punisher
3C Magus Rod
3D Chocobo Brsh
3E DaVinci Brsh
3F Magical Brsh
40 Rainbow Brsh
41 Shuriken
42 Ninja Star
43 Tack Star
44 Flail
45 Full Moon
46 Morning Star
47 Boomerang
48 Rising Sun
49 Hawk Eye
4A Bone Club
4B Sniper
4C Wing Edge
4D Cards
4E Darts
4F Doom Darts
50 Trump
51 Dice
52 Fixed Dice
53 MetalKnuckle
54 Mithril Claw
55 Kaiser
56 Poison Claw
57 Fire Knuckle
58 Dragon Claw
59 Tiger Fangs
5A Buckler
5B Heavy Shld
5C Mithril Shld
5D Gold Shld
5E Aegis Shld
5F Diamond Shld
60 Flame Shld
61 Ice Shld
62 Thunder Shld
63 Crystal Shld
64 Genji Shld
65 TortoiseShld
66 Cursed Shld
67 Paladin Shld
68 Force Shield
69 Leather Hat
6A Hair Band
6B Plumed Hat
6C Beret
6D Magus Hat
6E Bandana
6F Iron Helmet
70 Coronet
71 Bard's Hat
72 Green Beret
73 Heaad Band
74 Mithril Helm
75 Tiara
76 Gold Helmet
77 Tiger Mask
78 Red Cap
79 Mystery Veil
7A Circlet
7B Regal Crown
7C Diamond Helm
7D Dark Hood
7E Crystal Helm
7F Oath Veil
80 Cat Hood
81 Genji Helmet
82 Thornlet
83 Titanium
84 LeatherArmor
85 Cotton Robe
86 Kung Fu Suit
87 Iron Armor
88 Silk Robe
89 Mithril Vest
8A Ninja Gear
8B White Dress
8C Mithril Mail
8D Gaia Gear
8E Mirage Vest
8F Gold Armor
90 Power Sash
91 Light Robe
92 Diamond Vest
93 Red Jacket
94 Force Armor
95 DiamondArmor
96 Dark Gear
97 Tao Robe
98 Crystal Mail
99 Czarina Gown
9A Genji Armor
9B Imp's Armor
9C Minerva
9D Tabby Suit
9E Chocobo Suit
9F Moogle Suit
A0 Nutkin Suit
A1 BehemothSuit
A2 Snow Muffler
A3 NoiseBlaster
A4 Bio Blaster
A5 Flash
A6 Chain Saw
A7 Debilitator
A8 Drill
A9 Air Anchor
AA AutoCrossbow
AB Fire Skean
AC Water Edge
AD Bolt Edge
AE Inviz Edge
AF Shadow Edge
B0 Goggles
B1 Star Pendant
B2 Peace Ring
B3 Amulet
B4 White Cape
B5 Jewel Ring
B6 Fairy Ring
B7 Barrier Ring
B8 MithrilGlove
B9 Guard Ring
BA RunningShoes
BB Wall Ring
BC Cherub Down
BD Cure Ring
BE True Knight
BF DragoonBoots
C0 Zephyr Cape
C1 Czarina Ring
C2 Cursed Ring
C3 Earrings
C4 Atlas Armlet
C5 Blizzard Orb
C6 Rage Ring
C7 Sneak Ring
C8 Pod Bracelet
C9 Hero Ring
CA Ribbon
CB Muscle Belt
CC Crystal Orb
CD Gold Hairpin
CE Economizer
CF Thief Glove
D0 Gauntlet
D1 Genji Glove
D2 Hyper Wrist
D3 Offering
D4 Beads
D5 Black Belt
D6 Coin Toss
D7 FakeMustache
D8 Gem Box
D9 Dragon Horn
DA Merit Award
DB Memento Ring
DC Safety Bit
DD Relic Ring
DE Moogle Charm
DF Charm Bangle
E0 Marvel Shoes
E1 Back Guard
E2 Gale Hairpin
E3 Sniper Sight
E4 Exp. Egg
E5 Tintinabar
E6 Sprint Shoes
E7 Rename Card
E8 Tonic
E9 Potion
EA X-Potion
EB Tincture
EC Ether
ED X-Ether
EE Elixer
EF Megalixer
F0 Fenix Down
F1 Revivify
F2 Antidote
F3 Eyedrop
F4 Soft
F5 Remedy
F6 Sleeping Bag
F7 Tent
F8 Green Cherry
F9 Magicite
FA Super Ball
FB Echo Screen
FC Smoke Bomb
FD Warp Stone
FE Dried Meat
FF -Blank-""".split("\n")

ITEM_LIST = [" ".join(descr) for idx, *descr in map(str.split, ITEM_LIST)]

FC_MODIFIERS = {
    # Next two bytes are CMD and unused
    0x1: "IF CMD USED",
    # Next two bytes are SPELL and unused
    0x2: "IF SPELL USED",
    # Next two bytes are ITEM and unused
    0x3: "IF ITEM USED",
    # Next two bytes are ELEM and unused
    0x4: "IF ELEM ATK",
    # Next two bytes ignored
    0x5: "IF DAMAGED",
    # Next two bytes are TARGET and HP / 128
    0x6: "IF HP <",
    # Next two bytes are TARGET and MP
    0x7: "IF MP <",
    # Next two bytes are TARGET and STATUS
    0x8: "IF HAS STATUS",
    # Next two bytes are TARGET and STATUS
    0x9: "IF NOT HAS STATUS",
    # Never executed
    0xA: "NOT EXE",
    # Next two bytes are TIME and unused
    0xB: "ETIMER >",
    # Next two bytes are VAR and VAL
    0xC: "VAR <",
    # Next two bytes are VAR and VAL
    0xD: "VAR >=",
    # Next two bytes are TARGET and LEVEL
    0xE: "IF LEVEL <",
    # Next two bytes are TARGET and LEVEL
    0xF: "IF LEVEL >=",
    # Next two bytes are unused(?)
    0x10: "IF SINGLE ETYPE",
    # Next two bytes are EPARTY (in bits?) and ignored
    0x11: "IS ALIVE",
    # Next two bytes are EPARTY (in bits?) and ignored
    0x12: "IS DEAD",
    # Next two bytes are PARTY / EPARTY and VAL
    0x13: "IF ANY ALIVE",
    # Next two bytes are VAR and BIT
    0x14: "IF VAR BIT",
    0x15: "IF NOT VAR BIT",
    # Next two bytes are TIME and unused
    0x16: "BAT TIMER >",
    # Next two bytes are TARGET and ignored
    0x17: "SET TARGET",
    # Next two bytes are unused
    0x18: "IF GAU JOINED",
    # Next two bytes are NUM and unused
    0x19: "IF FORM #",
    # Next two bytes are ELEM and TARGET
    0x1A: "IF WEAK TO",
    # Next two bytes are 16-bit NUM
    0x1B: "IS FORM # =",
    # Next two bytes are unused
    0x1C: "ALWAYS"
}

SPECIAL_EVENTS = {
    # 0x0->0x3 are not used directly by enemy scripts
    0x0: "Prebattle character animations (?)",
    0x1: "Victory animations (?)",
    0x2: "[UNUSED]",
    0x3: "[UNUSED]",

    0x4: "Biggs, Wedge, and Terra: Tritoch scene",
    0x5: "Biggs, Wedge, and Terra: Whelk introduction",
    0x6: "Terra, Locke, and Edgar: M-M-M-MAGIC!?",
    0x7: "Sabin enters the Vargas battle",
    0x8: "Vargas hits Sabin with Doom Fist",
    0x9: "Vargas dies from Pummel",
    0xA: "post-Ultros Lete River party separation",

    # Next two not used by enemy scripts
    0xB: "Shadow leaves the party",
    0xC: "[UNUSED]",

    0xD: "Gau joins the party on the Veldt",
    0xE: "Locke steals the officer's clothes",
    0xF: "Locke steals the merchant's clothes",
    0x10: "Locke and Celes: TunnelArmr introduction",
    0x11: "Terra and Kefka: flashback scene",
    0x12: "Esper Terra: Tritoch scene",
    0x13: "Battle on the Small Bridge (pt 1: vs. Kefka)",
    0x14: "Battle on the Small Bridge (pt 2: Espers rampage)",
    0x15: "Battle on the Small Bridge (pt 3: Espers attack airship)",
    0x16: "Relm enters the Ultros battle",
    0x17: "Kefka kills Leo",
    0x18: "Battle of Thamasa: Espers emerge to defend",
    0x19: "Kefka w/ soldiers at Sealed Gate: Dummied Scene",
    0x1A: "Kefka transforms fake Ifrit into magicite",
    0x1B: "[UNUSED]",
    0x1C: "YOU SCARE MONSTERS. GO AWAY.",
    0x1D: "Kefka at Imperial Camp(?)",
    0x1E: "Kefka vs Gestahl",
    0x1F: "Wrexsoul: Possession cutscene",
    0x20: "Final Kefka: ???",
}

MISC = {
    # 0	Sets the target(s) battle timer to 0
    0x0: "TARG BAT TIME RESET",
    # 1	Target(s) becomes invincible
    0x1: "TARGET SET INVC.",
    # 2	Ends the combat
    0x2: "END BATTLE",
    # 3	Gau is added as a party member
    0x3: "ADD GAU",
    # 4	Sets global battle timer to 0
    0x4: "BAT TIME RESET",
    # 5	Target(s) loses invincibility
    0x5: "TARGET UNSET INVC.",
    # 6	Target(s) becomes targettable
    0x6: "SET TARG",
    # 7	makes target(s) untargettable
    0x7: "UNSET TARG",
    # 8	Unknown
    0x8: "UNK.",
    # 9	End the combat
    0x9: "END BATTLE",
    # A	Does nothing
    0xA: "NOTHING",
    # B	Monster gains an unremovable status.
    0xB: "GAIN STATUS",
    # C	Monster loses a status gained by FB 0B
    0xC: "LOSE STATUS"
}

ANIMATIONS = """0	Monster(s) flashes red
1	Monster(s) moves back 1 step slowly
2	Monster(s) moves forward 1 step slowly
3	Monster(s) moves back 1 step quickly
4	Monster(s) moves forward 1 step quickly
5	Characters run to the right
6	Characters run to the left
7	Monster(s) steps back 3 steps quickly
8	Monster(s) steps forward 3 steps quickly
9	Unknown
A	Causes head to appear, screen to shake (used by Kefka)
B	All monsters flash for a long time
C	Monsters(s) flashes for a long time
D	Screen flashes like boss death""".split("\n")

ANIMATIONS = [anim.split("\t")[-1] for anim in ANIMATIONS]