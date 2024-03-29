import networkx
import random
from . import _NAME_ALIASES
from . import flags

#
# Areas
#
# FIXME: reverse the order of this so the later repeats are simpler
AREA_SETS = [
    # World of Balance

    # Narshe incursion
    {"Guard", "Lobo", "Vomammoth", "Marshal", "Whelk", "Head"},
    # Narshe mines
    {"Repo Man", "Vaporite", "Were-Rat"},
    # Narshe to Figaro WoB
    {"Areneid", "Dark Wind", "Leafer", "Sand Ray", "M-TekArmor"},
    # SF Cave
    {"Crawly", "Hornet", "Bleary"},
    # SF WoB:
    {"GreaseMonk", "Rhinotaur", "Rhodox"},
    # Kolts
    {"Brawler", "Trilium", "Cirpius", "Tusker", "Vaporite", "Ipooh", "Vargas"},
    # Lete River
    {"Exocite", "Nautiloid", "Pterodon"},
    # Terra's Scenario / Narshe
    {"Dark Side", "1st Class", "Repo Man", "Rinn", "Spectre", "Vaporite", "Were-Rat", "Wild Rat", "Ultros"},
    # Locke's Scenario / SF
    {"HeavyArmor", "Merchant", "Officer", "Commander", "Vector Pup"},
    # Locke's Scenario / SF Cave
    {"Gold Bear", "Primordite", "Trilobiter", "TunnelArmr"},
    # Sabin's Scenario WoB
    {"Beakor", "CrassHoppr", "Rhobite", "Stray Cat", "WeedFeeder", "Grenade"},
    # Sabin's Scenario / Imperial Camp
    # 3 = Cyan's AI during IC escape
    {"Cadet", "Doberman", "Leader", "M-TekArmor", "Soldier", "Telstar", "Templar", "3"},
    # Sabin's Scenario / Phantom Forest
    {"Ghost", "Poplium"},
    # Sabin's Scenario / Ghost Train
    {"Bomb", "Ghost", "Hazer", "Over-Mind", "StillGoing", "Whisper", "Siegfried2", "Specter", "GhostTrain"},
    # Sabin's Scenario / Barren Falls
    {"Piranha", "Rizopas"},
    # Sabin's Scenario / Serpent Trench
    {"Actaneon", "Anguiform", "Aspik"},
    # Kefka @ Narshe
    {"Bounty Man", "Fidor", "HeavyArmor", "Trooper", "Rider", "Kefka3"},
    # Kohligen, Southern Deserts
    {"FossilFang"},
    # Jidoor, Kohligen Map
    {"Iron Fist", "Mind Candy", "Over Grunk", "Red Fang", "Vulture"},
    # Zozo
    {"Gabbldegak", "HadesGigas", "Harvester", "SlamDancer", "Dadaluma"},
    # Opera House
    {"Sewer Rat", "Ultros2", "Vermin"},
    # Southern Continent
    {"Bug", "ChickenLip", "Joker", "Ralph", "Wyvern"},
    # Vector
    {"Mega Armor", "Sp Forces", "Guardian"},
    # Magitek Research Facility
    {"Chaser", "Commando", "Flan", "Garm", "General", "Gobbler", "Rhinox", "Trapper",
     "Pipsqueak", "ProtoArmor", "Mag Roader", "Mag Roader2",
     "Ifrit", "Shiva", "Number 024", "Number 128", "Left Blade", "RightBlade"},
    # Escape from Vector
    {"Crane", "Crane2"},
    # Terra's Flashback
    #{"Soldier"?},
    # Cave to the Sealed Gate
    {"Apparite", "Coelecite", "Ing", "Lich", "Zombone", "Ninja"},
    # Sealed Gate
    #{"Kefka [Sealed Gate]"}
    # Thamasa Island Map
    {"Baskervor", "Cephaler", "Chimera"},
    # Thamasa Island Cave
    {"Abolisher", "Adamanchyt", "Insecare", "Mandrake", "Slurm", "Ultros3"},
    # Burning House in Thamasa
    {"Balloon", "FlameEater"},
    # Thamasa
    #{"Kefka [Thamasa]", "(Red?Esper)"},
    # Battle With Imperial Air Force
    {"Sky Armor", "Spit Fire", "Air Force", "Laser Gun", "MissileBay", "Speck", "Ultros4", "Chupon2"},
    # Floating Continent
    {"Apokryphos", "Behemoth", "Brainpan", "Dragon", "Gigantos", "Misfit", "Wirey Drgn", "AtmaWeapon"},
    # Floating Continent (Escape)
    {"Naughty", "Nerapa"},

    # World of Ruin

    # Solitary Island
    {"Peepers", "EarthGuard"},
    # general WoR
    {"Crawler", "Black Drgn"},
    # Albrook, Tzen Area Map
    {"Mesosaur", "Chitonid", "Gigan Toad", "Gilomantis", "Lunaris", "Osprey"},
    # Collapsing House
    {"HermitCrab", "Pm Stalker", "Scorpion"},
    # Raised Serpent Trench
    {"Bloompire", "Buffalax", "Delta Bug", "Lizard"},
    # WoR Figaro Cave, Figaro Castle
    {"Cruller", "Dante", "Humpty", "NeckHunter"},
    # Figaro Castle
    {"Drop", "Tentacle", "Tentacle2", "Tentacle3", "Tentacle4"},
    # Figaro Area Map
    {"Maliga", "Nohrabbit", "Sand Horse"},
    # Daryl's Tomb
    {"Exoray", "Mad Oscar", "Orog", "Osteosaur", "PowerDemon", "Presenter", "Whelk Head", "Dullahan"},
    # Mt. Zozo
    {"Borras", "Luridan", "Punisher", "Scrapper", "Ursus", "Storm Drgn"},
    # Southwest Continent
    {"Mantodea", "Spek Tor", "Sprinter"},
    # Doma Island
    {"TumbleWeed"},
    # Northwest Continent
    {"Bogy", "Deep Eye", "Harpiai", "Muus"},
    # Narshe
    {"Nastidon", "Red Wolf", "Test Rider", "Woolly"},
    # Narshe Caves, Hills
    {"Psychot", "Wizard", "Mag Roader3", "Mag Roader4", "Warlock"},
    # Narshe, Zozo Area Maps
    {"Geckorex", "Reach Frog"},
    # Jidoor / Owzer's House
    {"Still Life", "Crusher", "Dahling", "Nightshade", "SoulDancer", "Vindr",
     "Wild Cat", "Chadarnook", "Chadarnook2"},
    # Maranda Area Desert
    {"Cactrot", "Hoover"},
    # Thamasa Island
    {"GloomShell", "Harpy", "Prussian"},
    # Cave in the Veldt
    {"Rhyos", "Toe Cutter", "Allo Ver", "SrBehemoth", "SrBehemoth2"},
    # Triangle Island
    {"Zone Eater"},
    # Ebot's Rock
    {"Slatter", "Cluck", "Displayer", "Eland", "Hipocampus", "Opinicus",
     "Hidon", "Hidonite", "Hidonite2", "Hidonite3", "Hidonite4"},
    # Gogo's Lair
    {"Covert", "Karkass", "Ogor", "Tap Dancer", "Wart Puck"},
    # Ancient Underground Castle
    {"Boxed Set", "Enuo", "Figaliz", "Goblin", "Lethal Wpn", "KatanaSoul", "Master Pug", "Blue Drgn"},
    # Underground Narshe Caves
    {"Kiwok", "Anemone", "Ceritops", "Tomb Thumb", "Poppers", "Pug", "Pugs", "Umaro2"},
    # Phoenix Cave
    {"Aquila", "Chaos Drgn", "Necromancr", "Parasoul", "Phase", "Rain Man",
     "Trixter", "Uroburos", "Sea Flower", "Red Dragon"},
    # Cyan's Dream
    {"Allosaurus", "Barb-e", "Critic", "Samurai", "Sky Cap",
     "Suriander", "Io", "Pan Dora", "Parasite", "PlutoArmor",
     "Curley", "Larry", "Moe", "SoulSaver", "Wrexsoul"},
    
    # Triangle Island (here to scale up the optional battle)
    {"Intangir"},

    # Fanatic's Tower
    {"L.10 Magic", "L.20 Magic", "L.30 Magic", "L.40 Magic", "L.50 Magic",
     "L.60 Magic", "L.70 Magic", "L.80 Magic", "L.90 Magic", "Magic Urn",
     "MagiMaster", "White Drgn"},
    # Forest On Northwest Continent
    {"Brachosaur", "Tyranosaur"},
    # WoR Bosses (indp.)
    {"Doom Gaze",
     # Narshe Cliffs
     "Tritoch2",
     "Ice Dragon",
     # WoR Opera House
     "Dirt Drgn",
     # Mobliz
     "Phunbaba", "Phunbaba2", "Phunbaba3", "Phunbaba4",
     # Colloseum
     # need Shadow battle id
     "Chupon", "Siegfried"},#, "Shadow"},
    # Kefka's Tower
    # FIXME: need mappings
    {"Brontaur", "Dark Force", "Didalos", "Dueller", "Evil Oscar",
     "Fortis", "GtBehemoth", "Hemophyte", "Innoc", "IronHitman", "Junk",
     "Land Worm", "Madam", "Mover", "Outsider", "Prometheus", "Retainer",
     "Scullion", "Sky Base", "Steroidite", "Vectagoyle", "Vectaur", "Veteran",
     "Skull Drgn",
     "Inferno", "Rough", "Striker", "Atma",
     "Doom Drgn", "Gold Drgn",
     "Guardian2", "Doom", "Goddess", "Poltrgeist",
     "Face", "Long Arm", "Short Arm",
     "Hit", "Magic", "Tiger", "Tools",
     "Girl", "Sleep",
     "Kefka2"},

    # Superboss in BC + high level Colosseum fights
    {"Umaro"}
]
#AREA_SETS = [{_NAME_ALIASES.get(n, n) for n in s} for s in AREA_SETS]

# Bosses
BOSSES = {"Whelk", "Head", "Marshal", "M-TekArmor", "Ipooh", "Vargas", "Ultros",
          "TunnelArmr", "Leader", "GhostTrain", "Piranha", "Rizopas",
          "Kefka3", "Dadaluma", "Ultros2", "Ifrit", "Shiva",
          "Number 024", "Number 128", "Left Blade", "RightBlade",
          "Crane", "Crane2", "Ultros3", "FlameEater", "Air Force",
          "Laser Gun", "MissileBay", "Speck", "Ultros4", "Chupon2",
          "AtmaWeapon", "Nerapa"}
BOSSES |= {"Tentacle", "Tentacle2", "Tentacle3", "Tentacle4",
           # FIXME: sort out this
           "Presenter", "Whelk Head", "Dullahan", "SrBehemoth",
           "SrBehemoth2", "Hidon", "Hidonite", "Hidonite2", "Hidonite3",
           "Hidonite4", "KatanaSoul", "Master Pug", "Pug", "Pugs", "Umaro2",
           "SoulSaver", "Wrexsoul", "MagiMaster", "Chadarnook", "Chadarnook2",
           "Phunbaba", "Phunbaba2", "Phunbaba3", "Phunbaba4",
           "Doom Gaze", "Tritoch3", "Chupon", "Umaro",
           "Inferno", "Rough", "Striker", "Atma", "Guardian2",
           "Doom", "Goddess", "Poltrgeist",
           "Face", "Long Arm", "Short Arm", "Hit", "Magic", "Tiger", "Tools",
           "Girl", "Sleep", "Kefka2"}
#BOSSES = {_NAME_ALIASES.get(n, n) for n in BOSSES}

# Add Cyan's Imperial Camp AI as a "boss" so that it is randomized
# but templated
BOSSES |= {"3"}
BOSSES |= {"Siegfried2"}

# FIXME
DRAGON = {"Blue Drgn", "Red Dragon", "Ice Dragon", "Dirt Drgn",
          "Gold Drgn", "Skull Drgn", "Storm Drgn", "White Drgn"}
BOSSES |= DRAGON

# Kefka's various managers: Imperial Camp, Thamasa, Bridge, Final
# FIXME: 5 isn't a script manager, it's 282 (False Kefka) in BC
SCRIPT_MANAGERS = {"2", "5", "6", "10", "Kefka"}

# Merchant, Guardian are included to preserve special event activation
EVENT_BATTLES = {"Merchant", "B.Day Suit", "Officer", "Guardian",
                 # Terra and Soldiers in flashback battle
                 "", "Soldier",
                 # Imperial camp
                 "Kefka",
                 # Special events (Ifrit clone)
                 # FIXME: this is the Kefka script manager in BC
                 "9",
                 # Tritoch Scenes
                 "Tritoch", "Tritoch2",
                 # Don't mess with variable setting to preserve magicite receipt
                 # FIXME: Do this by variable identification
                 "Doom Gaze",
                 # don't interfere with Gau recruit and BC reuses this
                 # for Final/False Kefka related things
                 # FIXME: This is the Kefka / Leo battle in BC
                 "4",
                 # Ensure engulf is available
                 "Zone Eater"}#, "Shadow"}

# FIXME: temporary
BOSSES |= EVENT_BATTLES

# TODO: By type
HUMAN = []
MTEK = []
LEVEL_BASED = []

# skills
BLITZ = {"Pummel", "AuraBolt", "Suplex", "Fire Dance",
         "Mantra", "Air Blade", "Spiraler", "Bum Rush"}
BLITZ = {flags._SPELL_LIST.get(cmd, cmd) for cmd in BLITZ}

SWDTECH = {"Dispatch", "Retort", "Slash", "Empowerer", "Stunner"}
# Don't really work
#SWDTECH |= {"QuadraSlam", "QuadraSlice", "Cleave"}
SWDTECH = {flags._SPELL_LIST.get(cmd, cmd) for cmd in SWDTECH}

DANCES = {
    "Wind Rhapsody": {"Wind Slash", "Sun Bath", "Plasma", "Cokatrice"},
    "Forest Suite": {"Rage", "Harvester", "Elf Fire", "Wombat"},
    "Desert Aria": {"Sand Storm", "Antlion", "Wind Slash", "Kitty"},
    "Love Sonata": {"Specter", "Elf Fire", "Tapir", "Snare"},
    "Earth Blues": {"Sonic Boom", "Sun Bath", "Whump", "Land Slide"},
    "Water Harmony": {"El Nino", "Plasma", "Specter", "Wild Bear"},
    "Dusk Requiem": {"Pois. Frog", "Elf Fire", "Cave In", "Snare"},
    "Snowman Jazz": {"Snowball", "Surge", "Ice Rabbit", "Snare"}
}
DANCES = {k: {flags._SPELL_LIST.get(d, d) for d in v} for k, v in DANCES.items()}
DANCE = set.union(*DANCES.values())

# For use with 0xF6
SNGL_CMDS = {"Capture", "Steal", "Morph", "Revert", "Runic",
             "Mimic", "Jump", "GPRain", "Shock"}
SNGL_CMDS |= {"Row", "Def."}
# Will only work if preceded by a targeting cmd against enemy party
#SNGL_CMDS |= {"Sketch"}
# Will only be useful if preceded by a targeting cmd against enemy party
#SNGL_CMDS |= {"Health"}
SNGL_CMDS = {flags._CMD_LIST.get(cmd, cmd) for cmd in SNGL_CMDS}

def add_throw_or_use():
    pass

# FIXME: to data
import pandas
skills = pandas.read_csv("etc/skill_data.csv")
skills["Elements"] = skills["Elements"].fillna("")
skills["Statuses"] = skills["Statuses"].fillna("")
sort_by = {"Power", "MP Cost"}

# Sanitize
def _sanitize(pstr):
    pstr = pstr.replace("*", "")
    if "/" in pstr:
        pstr = pstr.split("/")[0]
    return pstr.replace("(", "").replace(")", "")

for prm in sort_by:
    skills[prm] = skills[prm].astype(str).apply(_sanitize).astype(int)

skills = skills.sort_values(by=list(sort_by))

#
# Elements
#
ELEM_THEMES = {}
for elem in {"ice", "fire", "lightning", "water", "wind", "earth", "pearl", "poison"}:
    _elem = skills.loc[skills["Elements"].str.contains(elem.capitalize())]["Spell Name"]

    g = networkx.generators.fast_gnp_random_graph(len(_elem), 3 / len(elem), directed=True)
    ELEM_THEMES[elem] = networkx.relabel_nodes(g, dict(enumerate(_elem.index)))

#
# Statuses
#
# FIXME: remove annoying skills
STATUS_THEMES = {}
for status in {'Poison', 'Petrify', 'Death', 'Slow', 'Mute', 'Safe',
               'Sleep', 'Confuse', 'Haste', 'Stop', 'Berserk', 'Float', 'Imp',
               'Rflect', 'Shell', 'Vanish', 'Quick'}:
    _status = skills.loc[skills["Statuses"].str.contains(status.capitalize())]["Spell Name"]

    g = networkx.generators.fast_gnp_random_graph(len(_status), 3 / len(status), directed=True)
    STATUS_THEMES[status.lower()] = networkx.relabel_nodes(g, dict(enumerate(_status.index)))

#
# Commands
#
FROM_COMMANDS = {
    "Dance": DANCE,
    "SwdTech": SWDTECH,
    "Blitz": BLITZ
}
for name, commands in FROM_COMMANDS.items():
    g = networkx.generators.fast_gnp_random_graph(len(commands), 3 / len(commands), directed=True)
    FROM_COMMANDS[name] = networkx.relabel_nodes(g, dict(enumerate(commands)))

#
# Special
#
