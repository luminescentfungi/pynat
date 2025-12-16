# Cookies and Session Settings
COOKIE = '1765817615_cdrq1m4r'
PHPSESSID = 'f6b7ttvbetp3m6igf9adc7tm09'


# General variables and settings
COLOR_RESET = "\033[0m"
COLOR_LOG = "\033[92m"   # Green
COLOR_DEB = "\033[94m"   # Blue
DEBUG = True
# Maximum number of results to emit in news, search, etc.
MAX_RESULTS = 1
# jnttkk07

# Base URLs for scraping
BASE_URL = "https://ohnaturist.com/"
NEWS_URL = BASE_URL + "NewMembersI.php"
MSGS_URL = BASE_URL + "Msg2I.php"
DIRS_URL = BASE_URL + "DirectoryI.php"
ID_MEMBER_URL = BASE_URL + "MemberI.php?KeyMember="
CONVERSATION_URL = BASE_URL + "Msg2ConvReceivedI.php?KeyConversation="
SEND_MSG_URL = BASE_URL + "Services/Msg2Send_beta.php"

# Files
MAP_FILE = 'ohnat-map.js'

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": BASE_URL,
    "Cookie": f"Cookie={COOKIE}; PHPSESSID={PHPSESSID}"
}

# POST_HEADERS = {
#     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
#     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
#     "Accept-Encoding": "gzip, deflate, br, zstd",
#     "Accept-Language": "en-US,en;q=0.9,es-ES,es;q=0.8,fr-FR,fr;q=0.7,de-DE,de;q=0.6,it-IT,it;q=0.5,pt-PT,pt;q=0.4,ru-RU,ru;q=0.3,zh-CN,zh;q=0.2,ja-JP,ja;q=0.1",
#     "Cookie": f"PHPSESSID={PHPSESSID}; Cookie={COOKIE}"
# }