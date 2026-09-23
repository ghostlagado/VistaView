from requests import get
from os import getenv

API_KEY = getenv("ACTION_API")
ACTION_NAME = 'GGPS3'

def getPrice(act:str = ACTION_NAME):
    response = get(
        f"https://brapi.dev/api/v2/stocks/quote?symbols={act}",
        headers={
            "Authorization": f"Bearer {API_KEY}"
        }
    )

    data = response.json()
    return data['results'][0]['regularMarketPrice']
