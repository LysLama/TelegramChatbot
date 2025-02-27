import requests

GOOGLE_API_KEY = "AIzaSyBJHGGQqDjk_qDB1tX17LrT0ma4KahT7IM"
SEARCH_ENGINE_ID = "22d0f7f4aa3de4b1f"
query = "Thời tiết hôm nay"

url = f"https://www.googleapis.com/customsearch/v1?q={query}&cx={SEARCH_ENGINE_ID}&key={GOOGLE_API_KEY}"
response = requests.get(url)
data = response.json()

print(url)
for item in data.get("items", []):
    print(item["title"], "-", item["link"])
