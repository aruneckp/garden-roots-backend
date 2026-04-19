import requests
import csv
import time

# ─── CONFIG ───────────────────────────────────────────────
ACCESS_TOKEN    = "EAAVZAOBMhZCN8BRC43UxeyqoOQh1I9kVxprj8EWqZBqaLd7ZB6NMDXQZA9CUmkvBNjFGZCNpnNlMz23CIEbZB7FPoMVZABPcqCZAxxxq2q8eNqSRdeo8hR7y0rZALO6iZAjoT4WcmIqlQRTaW7UkH4fwjG1I6jwubYSz22GBvuImRTwOtHgrnz8w3NLIVxwDSsOTGUS3qLVkU7i2lmJoTAryen5j8OqU80Tmu0GiZCuWQUiKFFBbLZByFYsbGhSlmNivh6wLk2vZBHqriVZAkb28QBZB4xpZA8a5f"
PHONE_NUMBER_ID = "1129084516948141"
API_VERSION     = "v19.0"
BASE_URL        = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"


HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

IMAGE_URL = "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=800"

def clean_number(phone: str) -> str:
    return str(phone).replace("+", "").replace(" ", "").replace("-", "").strip()

def send_text(to: str, message: str):
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message}
    }
    response = requests.post(BASE_URL, headers=HEADERS, json=payload)
    return response.json(), response.status_code

def send_image(to: str, image_url: str, caption: str):
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "image",
        "image": {
            "link": image_url,
            "caption": caption
        }
    }
    response = requests.post(BASE_URL, headers=HEADERS, json=payload)
    return response.json(), response.status_code

def send_template(to: str, template_name: str, lang: str = "en_US"):
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": lang}
        }
    }
    response = requests.post(BASE_URL, headers=HEADERS, json=payload)
    return response.json(), response.status_code

# ─── LOAD FROM CSV AND SEND ───────────────────────────────
def send_bulk_from_csv(csv_file: str):
    success = 0
    failed  = 0
    failed_numbers = []

    with open(csv_file, newline='') as f:
        reader = csv.DictReader(f)
        numbers = list(reader)

    print(f"📋 Total numbers loaded: {len(numbers)}\n")

    for i, row in enumerate(numbers, 1):
        phone = clean_number(row['phone'])
        name  = row.get('name', 'there')

        print(f"[{i}/{len(numbers)}] Sending to {phone}...")

        # ✅ Use template for first contact (any number)
        result, status = send_template(phone, "hello_world")

        # ✅ OR use text if within 24hr window:
        # result, status = send_text(phone, "am coming")

        # ✅ Send image
        # result, status = send_image(phone, IMAGE_URL, "am coming 😊")

        if status == 200:
            print(f"   ✅ Success")
            success += 1
        else:
            error = result.get('error', {}).get('message', 'Unknown error')
            print(f"   ❌ Failed: {error}")
            failed += 1
            failed_numbers.append(phone)

        time.sleep(0.5)  # ⏱ small delay to avoid rate limits

    # ─── SUMMARY ──────────────────────────────────────────
    print(f"\n{'='*40}")
    print(f"📊 RESULTS SUMMARY")
    print(f"{'='*40}")
    print(f"✅ Success : {success}")
    print(f"❌ Failed  : {failed}")
    print(f"📦 Total   : {len(numbers)}")

    if failed_numbers:
        print(f"\n❌ Failed numbers:")
        for n in failed_numbers:
            print(f"   - {n}")

        # Save failed numbers to retry later
        with open("failed_numbers.csv", "w") as f:
            f.write("phone\n")
            for n in failed_numbers:
                f.write(f"{n}\n")
        print(f"\n💾 Failed numbers saved to failed_numbers.csv")


# ─── RUN ──────────────────────────────────────────────────
if __name__ == "__main__":
    send_bulk_from_csv("numbers.csv")