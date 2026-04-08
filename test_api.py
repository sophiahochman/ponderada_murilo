import requests, json

BASE = "http://localhost:5000"

print("=" * 55)
print("VALIDAÇÃO DE ENDPOINTS DA API")
print("=" * 55)

# GET /
r = requests.get(f"{BASE}/")
print(f"\nGET /  =>  {r.status_code}")
d = r.json()
print(f"  total_leituras : {d['total_leituras']}")
print(f"  ultimas leituras: {len(d['ultimas_leituras'])} registros")

# GET /leituras?limit=5
r = requests.get(f"{BASE}/leituras?limit=5")
print(f"\nGET /leituras?limit=5  =>  {r.status_code}")
d = r.json()
print(f"  paginacao: { {k: d['paginacao'][k] for k in ['total','limit','offset','pagina_atual','total_paginas']} }")

# GET /leituras/2
r = requests.get(f"{BASE}/leituras/2")
print(f"\nGET /leituras/2  =>  {r.status_code}")
print(f"  dados: {r.json()['dados']}")

# PUT /leituras/2
r = requests.put(f"{BASE}/leituras/2", json={"temperatura": 99.9, "localizacao": "Teste-PUT"})
print(f"\nPUT /leituras/2  =>  {r.status_code}")
print(f"  dados atualizados: {r.json()['dados']}")

# GET /api/estatisticas
r = requests.get(f"{BASE}/api/estatisticas")
print(f"\nGET /api/estatisticas  =>  {r.status_code}")
print(json.dumps(r.json(), indent=2, ensure_ascii=False))

# DELETE /leituras/2
r = requests.delete(f"{BASE}/leituras/2")
print(f"\nDELETE /leituras/2  =>  {r.status_code}")
print(f"  {r.json()}")

# GET /leituras/2 (deve retornar 404)
r = requests.get(f"{BASE}/leituras/2")
print(f"\nGET /leituras/2 (pós-delete)  =>  {r.status_code}  (esperado: 404)")
print(f"  {r.json()}")
