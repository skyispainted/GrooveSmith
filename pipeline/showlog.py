import json, sys
d = json.load(open(sys.argv[1]))
print("status:", d.get("status"), "stage:", d.get("stage"))
for l in d.get("logs", []):
    print(l)
