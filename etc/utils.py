import pandas

if __name__ == "__main__":
    wob = pandas.read_html("http://shrines.rpgclassics.com/snes/ff6/wob2.shtml")[2]
    wob.columns = wob.iloc[0]
    wob = wob.drop(0)

    print("### World of Balance ###")
    for loc, grp in wob.groupby("Location"):
        print(f"    # {loc}")
        grp = [f"\"{e.replace(' ', '?')}\"" for e in grp["Name"]]
        print(f"    {{{', '.join(grp)}}}")

    wor = pandas.read_html("http://shrines.rpgclassics.com/snes/ff6/wor2.shtml")[2]
    wor.columns = wor.iloc[0]
    wor = wor.drop(0)

    print("### World of Ruin ###")
    for loc, grp in wor.groupby("Location"):
        print(f"    # {loc}")
        grp = [f"\"{e.replace(' ', '?')}\"" for e in grp["Name"]]
        print(f"    {{{', '.join(grp)}}}")
