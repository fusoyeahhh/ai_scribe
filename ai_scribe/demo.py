import command_graph
import flags
from extract import translate, extract

if __name__ == "__main__":
    scripts = extract()

    combos = [
        ("Harvester", "TunnelArmr"),
        ("KatanaSoul", "Rizopas"),
        ("Atma", "Kefka3"),
        ("ChickenLip", "Leader"),
        ("Madam", "Balloon"),
        ("Pug", "Outsider"),
        ("Larry", "Moe", "Curly"),
        ("Outsider", "Harvester", "Tap?Dancer", "KatanaSoul"), # + dadaluma
        ('Red?Drgn', 'Blue?Drgn', 'Dirt?Drgn', 'White?Drgn',
         'Gold?Drgn', 'Skull?Drgn', 'Storm?Drgn', 'White?Drgn'),
        ("Aspik", "SlamDancer"),
    ]
    for combo in combos:
        graph = command_graph.CommandGraph()
        graph.from_scripts({k: v for k, v in scripts.items() if k in combo})

        print(f"Fusion: {combo}")
        print(translate(graph.generate_from_graph()))