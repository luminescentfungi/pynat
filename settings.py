# Cookies and Session Settings
COOKIE = '1765817615_cdrq1m4r'
PHPSESSID = 'f6b7ttvbetp3m6igf9adc7tm09'

# General variables and settings
COLOR_RESET = "\033[0m"
COLOR_LOG = "\033[92m"   # Green
COLOR_DEB = "\033[94m"   # Blue
DEBUG = True
# jnttkk07

# Base URLs for scraping
BASE_URL = "https://ohnaturist.com/"
NEWS_URL = BASE_URL + "NewMembersI.php"
MSGS_URL = BASE_URL + "Msg2I.php"
DIRS_URL = BASE_URL + "DirectoryI.php"
ID_MEMBER_URL = BASE_URL + "MemberI.php?KeyMember="
MSG_TO_URL = BASE_URL + "Msg2NewI.php?KeyWriteTo="

# Files
MAP_FILE = 'ohnat-map.js'

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": BASE_URL,
    "Cookie": f"Cookie={COOKIE}; PHPSESSID={PHPSESSID}"
}
