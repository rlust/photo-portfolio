import time
import requests

def annotate_all_batches(api_url, batch_size=10, interval_sec=60):
    offset = 0
    total = None
    while True:
        resp = requests.post(f"{api_url}?batch_size={batch_size}&offset={offset}")
        if resp.status_code != 200:
            print(f"Error: {resp.status_code}: {resp.text}")
            break
        data = resp.json()
        print(f"Batch offset {offset}: updated {data.get('updated_this_batch', 0)}, remaining: {data.get('remaining_untagged', '?')}")
        if total is None:
            total = data.get('total_untagged', 0)
        remaining = data.get('remaining_untagged', 0)
        if remaining == 0:
            print("All images have been annotated.")
            break
        offset += batch_size
        # If we hit the end, reset offset to 0 to catch any new images
        if offset >= total:
            offset = 0
            total = remaining
        time.sleep(interval_sec)

if __name__ == "__main__":
    annotate_all_batches(
        api_url="https://photoportfolio-backend-839093975626.us-central1.run.app/api/annotate-locations",
        batch_size=10,
        interval_sec=60
    )
