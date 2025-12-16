import requests, json, re, httpx
from bs4 import BeautifulSoup
from settings import COLOR_RESET, COLOR_LOG, COLOR_DEB, COOKIE, MAP_FILE, ID_MEMBER_URL, HEADERS, PHPSESSID, SEND_MSG_URL

   
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

def parse_conversation(html_data):
  soup = BeautifulSoup(html_data, 'html.parser')
  
  contact = soup.find('div', class_='TitleLeft').text.strip().replace('Conversación con ', '')
  subject = soup.find('div', class_='TitleRight').text.strip().replace('Sobre ', '')
  # Extract messages
  messages = []
  
  # Find all message containers indicating sender (MsgFromYou or MsgFromOther)
  message_containers = soup.find_all(['div', 'div'], class_=re.compile(r'MsgFrom(You|Other)'))
  
  for container in message_containers:
    message_data = {}
    
    # Determine if the message is 'MsgFromYou' (You) or 'MsgFromOther' (The other contact)
    if 'MsgFromYou' in container.get('class', []):
      message_data['sender'] = 'You'
      message_data['alignment'] = 'right'
    elif 'MsgFromOther' in container.get('class', []):
      message_data['sender'] = contact
      message_data['alignment'] = 'left'
    
    # log_message(f"Parsing message from: {message_data['sender']}", "DEB")
    # log_message(f"Message container HTML: {container}", "DEB")
    # log_message(f"Message container text: {container.get_text()}", "DEB")
    
    # Extract the message content (MsgLeft)
    body_msg_tag = container.find('div', class_='MsgLeft')
    if body_msg_tag:
      # Use .get_text(separator=' ', strip=True) to clean the text and replace <br> with spaces
      message_data['body'] = body_msg_tag.get_text(separator=' ', strip=True)

    # Extract the date/time (MsgFromInfos or MsgToInfos)
    info_tag = container.find(['div'], class_=re.compile(r'Msg(From|To)Infos'))
    if info_tag:
      # The time text is after the sender, separated by <br>
      # Remove the sender/recipient name before getting the text
      info_text = info_tag.get_text(separator='\n', strip=True)
      # Try to extract only the date/time part
      match_date = re.search(r'(Hace.*)', info_text)
      message_data['time'] = match_date.group(1) if match_date else 'Unknown Date/Time'
      
    messages.append(message_data)
    
  return {
    'contact': contact,
    'subject': subject,
    'messages': messages
  }

def send_message(key_contact, message, key_message, subject, key_conversation=None):
    """Send the POST request for a specific contact key"""
    referer = f"https://ohnaturist.com/Msg2ConvReceivedI.php?KeyConversation={key_conversation}" if key_conversation else "https://ohnaturist.com/"
    pheaders = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Cookie": f"PHPSESSID={PHPSESSID}; Cookie={COOKIE}",
        "Origin": "https://ohnaturist.com",
        "Referer": referer,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache"
    }
    log_message(f"Preparing to send message to KeyContact={key_contact} with KeyMessage={key_message} and Referer={referer}", "DEB")
    pdata = {
        "formMsg_New_Submit2": "Enviar mensaje",
        "formMsg_New_Subject": subject,
        "formMsg_New_KeyContact": key_contact,
        "formMsg_New_KeyMessage": key_message,
        "formMsg_New_Submit": "Enviar mensaje",
        "item": "undefined",
        "namedItem": "undefined",
        "formMsg_New_Body": message
    }
    response = httpx.post(SEND_MSG_URL, headers=pheaders, data=pdata)
    return response