import requests

def resolve_google_redirect(url):
    """
    Resolves a Google redirect URL to its final destination.

    Args:
        url (str): The Google redirect URL to resolve.

    Returns:
        str: The final destination URL after following the redirect.
    """
    try:
        # Send a GET request to the URL
        response = requests.get(url, allow_redirects=True)
        
        # Return the final URL after all redirects
        return response.url
    except requests.RequestException as e:
        print(f"An error occurred: {e}")
        return None