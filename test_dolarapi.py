import requests
try:
    print("Fetching from dolarapi...")
    r = requests.get("https://dolarapi.com/v1/dolares/oficial")
    data = r.json()
    print(data)
    print(f"Venta: {data['venta']}")
except Exception as e:
    print(f"Error: {e}")
