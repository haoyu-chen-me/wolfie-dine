import requests
import json
import datetime

# Scrape Dental Cafe website
TARGET_URL_TEMPLATE = "https://stonybrook.api.nutrislice.com/menu/api/weeks/school/sbu-eats-events/menu-type/dental-cafe/{year}/{month}/{day}/?format=json"

def fetch_dental_cafe_menu():
    # Get today's date in Eastern Time (UTC - 5 hours)
    eastern_time = datetime.datetime.utcnow() - datetime.timedelta(hours=5)
    
    # Format URL with zero-padded dates
    url = TARGET_URL_TEMPLATE.format(
        year=eastern_time.year,
        month=f"{eastern_time.month:02d}",
        day=f"{eastern_time.day:02d}"
    )
    print(f"Fetching from: {url}")
    
    headers = {"User-Agent": "Mozilla/5.0 (SBU Student Project)"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        todays_menu = []
        date_str = eastern_time.strftime("%Y-%m-%d")
        
        found_today = False
        # Find today's menu
        for day_data in data.get('days', []):
            if day_data.get('date') == date_str:
                found_today = True
                menu_items = day_data.get('menu_items', [])
                
                print(f"Found date {date_str} with {len(menu_items)} items.")
                for item in menu_items:
                    food_obj = item.get('food')
                    
                    if food_obj is None:
                        continue 
                    food_name = food_obj.get('name', 'Unknown Name')
                    price = item.get('price', '')
                    todays_menu.append({
                        "name": food_name,
                        "price": price,
                    })
                break 
        
        # No data for today?
        is_weekend = eastern_time.weekday() >= 5  # 5=Sat, 6=Sun

        if is_weekend and (not found_today or len(todays_menu) == 0):
            print("happy weekends")
        elif not found_today:
            print(f"API data does not contain {date_str}.")
        else:
            print(f"Valid menu items: {len(todays_menu)}.")
        
        # Write to JSON file - FIXED: Use eastern_time instead of datetime.now()
        output = {
            "date": date_str,
            "location": "Dental Cafe",
            "menu": todays_menu,
            "updated_at": eastern_time.strftime("%Y-%m-%d %H:%M:%S EST")  # Changed this line
        }
        with open('dental_cafe.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=4, ensure_ascii=False)
        
        print(f"Successfully updated dental_cafe.json with {len(todays_menu)} items!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fetch_dental_cafe_menu()

