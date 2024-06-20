import concurrent.futures
import json
import random
import time
import requests
from colorama import Fore, Style, init
from tenacity import retry, wait_fixed, stop_after_attempt
from urllib.parse import parse_qs, unquote

init(autoreset=True)

def print_welcome():
    print(f"{Fore.CYAN}{Style.BRIGHT}{'WELCOME':^50}")
    print(f"{'SCRIPT BY : JUAN GUSTAVO':^50}{Style.RESET_ALL}\n")

print_welcome()

def load_accounts(file_path='query.txt'):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    accounts = []
    for line in lines:
        if line.strip():
            parsed = parse_qs(line.strip())
            user_info = json.loads(unquote(parsed['user'][0]))
            query_string = f"query_id={parsed.get('query_id', [''])[0]}&user={unquote(parsed['user'][0])}&auth_date={parsed['auth_date'][0]}&hash={parsed['hash'][0]}"
            accounts.append({
                "query_string": query_string,
                "user_info": user_info
            })
    return accounts

def get_headers(query_string):
    return {
        "Authorization": query_string,
        "Content-Type": "application/octet-stream",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15A372 Safari/604.1",
        "Referer": "https://game.chickcoop.io/"
    }

@retry(wait=wait_fixed(5), stop=stop_after_attempt(3), retry_error_callback=lambda retry_state: print(f"Mencoba lagi setelah {retry_state.outcome.exception()}..."))
def post_request_with_retry(url, headers, data=None):
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", 60))
        print(f"Rate limit tercapai. Menunggu {retry_after} detik...")
        time.sleep(retry_after)
        raise requests.exceptions.RequestException("Rate Limited")
    response.raise_for_status()
    return response

def refresh_token(query_string):
    url = "https://api.chickcoop.io/auth/refresh"
    headers = get_headers(query_string)
    try:
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        new_token = response.json().get("token")
        return new_token
    except Exception as e:
        print(f"Gagal memperbarui token: {e}")
        return None

def auto_hatch(query_string, wait_seconds):
    url = "https://api.chickcoop.io/hatch/manual"
    headers = get_headers(query_string)
    hatched_count = 0
    max_eggs = 10000

    while True:
        try:
            response = post_request_with_retry(url, headers=headers)
            data = response.json()
        except (requests.RequestException, json.JSONDecodeError) as e:
            print(f"Terjadi kesalahan: {e}")
            if response.status_code == 401:
                new_token = refresh_token(query_string)
                if new_token:
                    query_string = new_token
                    headers = get_headers(query_string)
                    continue
            break

        if response.status_code == 429:
            retry_after = response.headers.get('Retry-After', 60)
            print(f"Rate limit tercapai. Menunggu {retry_after} detik...")
            time.sleep(int(retry_after))
            continue

        if data['ok']:
            hatched_count += 1
            profile = data['data']['profile']
            eggs = data['data']['eggs']
            farm_value = data['data']['farmValue']
            gem = data['data'].get('gem', 'N/A')
            colors = [Fore.RED, Fore.GREEN, Fore.YELLOW, Fore.BLUE, Fore.MAGENTA, Fore.CYAN, Fore.WHITE]
            print(f"{Style.BRIGHT}---------LOGIN INFORMASI---------")
            print(f"{colors[0]}{Style.BRIGHT}User: {profile['username']}")
            print(f"{colors[1]}{Style.BRIGHT}Jumlah Telur: {eggs['quantity']}")
            print(f"{colors[2]}{Style.BRIGHT}Farm Value: {farm_value}")
            print(f"{colors[3]}{Style.BRIGHT}Gems: {gem}")
            print(f"{colors[4]}{Style.BRIGHT}Laying Rate: {data['data']['chickens']['layingRate']['combine']}")
            print(f"{colors[5]}{Style.BRIGHT}Telur Berhasil Dipecahkan: {hatched_count}")
            print(Style.RESET_ALL + "---------------------------------")
            if eggs['quantity'] >= max_eggs:
                print(f"{Fore.GREEN}Menunggu {wait_seconds} detik Untuk Lanjut...")
                time.sleep(wait_seconds)
        else:
            print(f"[{query_string}] Gagal menetaskan telur. Kesalahan: {data['error']}")
            break

        time.sleep(random.uniform(0.5, 2))

def run_for_all_accounts(wait_seconds):
    accounts = load_accounts()

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for account in accounts:
            executor.submit(auto_hatch, account['query_string'], wait_seconds)

if __name__ == "__main__":
    wait_seconds = int(input(f"{Fore.YELLOW}Menunggu Telur Yang Akan Di Pecah Berapa Detik: ").strip())

    run_for_all_accounts(wait_seconds)