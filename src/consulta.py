import json
d = json.load(open("data/contornos.json", encoding="utf-8"))
e = d["estados"][0]
print({k: (v if k != "g" else f"<{len(v)} polígonos>") for k, v in e.items()})
print("primeiro ponto:", e["g"][0][0][:2] if e["t"] == 2 else e["g"][0][:2])
m = d["municipios"][0]
print({k: (v if k != "g" else f"<{len(v)}>") for k, v in m.items()})
print("exemplo visitada:", list(d["visitadas"].items())[0])