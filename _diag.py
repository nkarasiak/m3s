import m3s
def n(g, box, p):
    try: return len(g.from_geometry(box, precision=p))
    except Exception as e: return f"ERR {type(e).__name__}: {e}"
small=(2.30,48.84,2.40,48.94)
for p in [4,5,6,7]:
    print("PlusCode 0.10 p"+str(p), n(m3s.PlusCode, small, p))
print("Maidenhead big p2", n(m3s.Maidenhead,(-4.0,44.0,12.0,52.0),2))
