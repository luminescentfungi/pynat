import requests, json, re, httpx
from bs4 import BeautifulSoup
from settings import COLOR_RESET, COLOR_LOG, COLOR_DEB, MAP_FILE, ID_MEMBER_URL, HEADERS

   
# Logging function with color and level
def log_message(msg, level="LOG"):
  if level == "LOG":
    print(f"{COLOR_LOG}[LOG] {msg}{COLOR_RESET}")
  elif level == "DEB":
    print(f"{COLOR_DEB}[DEB] {msg}{COLOR_RESET}")
  elif level == "ERR":
    print(f"\033[91m[ERR] {msg}{COLOR_RESET}")  # Red for errors
  else:
    print(f"[UNK] {msg}")


with open(MAP_FILE, 'r', encoding='utf-8', errors='ignore') as f:
  map_content = f.read()
map_match = re.search(r'(\[\s*\{.*?KeyWho.*?\}\s*\])', map_content, re.DOTALL)
user_mapdata = json.loads(map_match.group(1))
log_message(f"Total users in map data: {len(user_mapdata)}", "LOG")


def get_coords(city):
  url = "https://nominatim.openstreetmap.org/search"
  params = {
    'q': city,
    'format': 'json',
    'limit': 1
  }
  HEADERS = {'User-Agent': 'MyPythonScript/1.0'} # Nominatim requires User-Agent
  
  resp = requests.get(url, params=params, headers=HEADERS)
  data = resp.json()
  
  if data:
    lat = float(data[0]['lat'])
    lon = float(data[0]['lon'])
    return lat, lon
  log_message("No results found for city: " + city, "ERR")
  return None, None


def get_ids_from_city(city, location_threshold = 1.0):
  if not user_mapdata:
    log_message("No user map data available.", "ERR")
    return []
  lat, lon = get_coords(city)
  ids = []
  for user in user_mapdata:
    try:
      lat_ = float(user['latitude'])
      lon_ = float(user['longitude'])
      
      # Filtramos los que caen cerca de Barcelona
      if (lat - location_threshold < lat_ < lat + location_threshold) and \
         (lon - location_threshold < lon_ < lon + location_threshold):
        ids.append(str(user['KeyWho']))
    except:
      return []
  log_message(f"Found {len(ids)} users near {city}", "LOG")
  return ids

def get_member_soup_and_text(member_id):
    member_url = ID_MEMBER_URL + member_id
    try:
        with httpx.Client(timeout=10) as client:
            with client.stream("GET", member_url, headers=HEADERS) as response:
                html_chunks = []
                for chunk in response.iter_text():
                    html_chunks.append(chunk)
                    partial_html = ''.join(html_chunks)
                    soup_partial = BeautifulSoup(partial_html, 'html.parser')
                    text = soup_partial.get_text()
                    # Return as soon as we have some text (can be improved for streaming)
                    if text:
                        return soup_partial, text
    except Exception as e:
        log_message(f"Error fetching member page for {member_id}: {e}", "ERR")
        return None, None
    return None, None