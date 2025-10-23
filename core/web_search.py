import webbrowser
from duckduckgo_search import DDGS

def search(query):
    results = DDGS().text("python programming", max_results=10)
    print(results)