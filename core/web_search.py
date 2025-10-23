import webbrowser
import ddg

def search(query: str) -> None:
    """Performs a web search using the default browser.

    Args:
        query (str): The search query.
    """
    if not query:
        raise ValueError("Search query cannot be empty.")
    
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    webbrowser.open(url)