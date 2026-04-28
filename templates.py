import requests

ACCESS_TOKEN = "EAAVZAOBMhZCN8BRWvKweTD1JT2ZBOZCbncEqAZAqkNRIBaEG1u2GNwkWobZBTxa3UkijLEZCf46EjivRV8pfCHHRVZAcMUoEX9DrtE7J4e1axFxGzWqrm92IAzweVrGuEXAgM0teKKIUCdORtSMhbPGmDb4lraLO1ZAZAfphP985IubWT027vZCKZBnLIT45gEPT4uvxlFJsmgQonH1kGyF1gT0m5R2LHBa4zmKR0oWNXksIqd1ZBwgB2PrpcRGqVmVEgPgP3Vq2rmNNWRisFXFNh8NNF"
WABA_ID = "2793899564293703"   # NOT phone number id
API_VERSION = "v19.0"

url = f"https://graph.facebook.com/{API_VERSION}/{WABA_ID}/message_templates"

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

params = {
    "limit": 50
}

response = requests.get(url, headers=headers, params=params)

data = response.json()

# Pretty print results
for template in data.get("data", []):
    print("="*40)
    print("Name      :", template.get("name"))
    print("Status    :", template.get("status"))
    print("Language  :", template.get("language"))
    print("Category  :", template.get("category"))
