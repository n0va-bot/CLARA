import webbrowser
from core.headers import get_useragent

url = "http://frogfind.com/?q="

def search(query: str):
    headers = {
        "User-Agent": get_useragent()
    }