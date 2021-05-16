import flags

#
# Areas
#
# FIXME: reverse the order of this so the later repeats are simpler
AREA_SETS = [
    # Narshe incursion
    {"Guard", "Lobo", "Vomammoth", "Marshal", "Whelk"},
    # Narshe mines
    {"Repo?Man", "Vaporite", "Were?Rat"},
    # Narshe to Figaro WoB
    {"Areneid", "Dark?Wind", "Leafer", "Sand?Ray", "M?TekArmor"},
    # SF Cave
    {"Crawly", "Hornet", "Bleary"},
    # SF WoB:
    {"GreaseMonk", "Rhinotaur", "Rhodox"},
    # Kolts
    {"Brawler", "Trilium", "Cirpius", "Tusker", "Vaporite", "Ipooh", "Vargas"},
    # Lete River
    {"Exocite", "Nautiloid", "Pterodon"},
    # Terra's Scenario / Narshe
    {"Dark?Side", "1st?Class", "Repo?Man", "Rinn", "Spectre", "Vaporite", "Were?Rat", "Wild?Rat", "Ultros"},
    # Locke's Scenario / SF
    {"HeavyArmor", "Merchant", "Officer", "Commander", "Vector?Pup"},
    # Locke's Scenario / SF Cave
    {"Gold?Bear", "Primordite", "Trilobiter", "TunnelArmr"},
    # Sabin's Scenario WoB
    {"Beakor", "CrassHoppr", "Rhobite", "Stray?Cat"},
    # Sabin's Scenario / Imperial Camp
    # 3 = Cyan's AI during IC escape
    {"Cadet", "Doberman", "Leader", "M?TekArmor", "Soldier", "Telstar", "Templar", "3"},
    # Sabin's Scenario / Phantom Forest
    {"Ghost", "Poplium"},
    # Sabin's Scenario / Ghost Train
    {"Bomb", "Ghost", "Hazer", "Over?Mind", "StillGoing", "Whisper", "Siegfried", "Specter", "GhostTrain"},
    # Sabin's Scenario / Barren Falls
    {"Piranha", "Rizopas"},
    # Sabin's Scenario / Serpent Trench
    {"Actaneon", "Anguiform", "Aspik"},
    # Kefka @ Narshe
    {"Bounty?Man", "Fidor", "HeavyArmor", "Trooper", "Rider", "Kefka3"},
]

# Some bosses
# Merchant is included to preserve special event activation
BOSSES = {"Whelk", "Marshal", "M?TekArmor", "Ipooh", "Vargas", "Ultros",
          "Merchant", "TunnelArmr", "GhostTrain", "Piranha", "Rizopas", "Kefka3"}

# By type
HUMAN = []
MTEK = []

#
# Elements
#
import pandas
skills = pandas.read_csv("skill_data.csv").sort_values(by=["Power", "MP Cost"])
import networkx

ELEM_THEMES = {}
for elem in {"ice", "fire", "lightning", "water", "wind", "earth", "pearl", "poison"}:
    _elem = skills.loc[skills["Elements"].str.contains(elem.capitalize())]["Spell Name"]
    g = networkx.generators.fast_gnp_random_graph(len(_elem), 3 / len(elem), directed=True)
    ELEM_THEMES[elem] = networkx.relabel_nodes(g, dict(enumerate(_elem.index)))

#
# Statuses
#
STATUS_THEMES = {}
for status in {'Poison', 'Petrify', 'Death', 'Slow', 'Mute', 'Safe',
               'Sleep', 'Confuse', 'Haste', 'Stop', 'Berserk', 'Float', 'Imp',
               'Rflect', 'Shell', 'Vanish', 'Quick'}:
    _status = skills.loc[skills["Statuses"].str.contains(status.capitalize())]["Spell Name"]
    g = networkx.generators.fast_gnp_random_graph(len(_status), 3 / len(status), directed=True)
    STATUS_THEMES[status.lower()] = networkx.relabel_nodes(g, dict(enumerate(_status.index)))

#
# Special
#