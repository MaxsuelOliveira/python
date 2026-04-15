import os
import requests
from db import Database, Controller


def get_google_maps_api_key():
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Defina GOOGLE_MAPS_API_KEY no ambiente antes de executar este script.")
    return api_key

class BusinessInfoApp:
    def __init__(self, api_key, api_base_url):
        self.api_key = api_key
        self.base_url = api_base_url
        self.api_key_header = {"Authorization": f"Bearer {api_key}"}
        self.session = requests.Session()
        self.session.headers.update(self.api_key_header)
        self.city = "Barreiras, Bahia"
        self.type = "lojas"
        self.Controller = Controller(Database())

    def get_data(self, endpoint):
        response = self.session.get(f"{self.base_url}/{endpoint}")
        response.raise_for_status()
        return response.json()
    
    def get_businesses(self, city):
        URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        query = f"businesses in {city}"
        params = {
            "query": query,
            "key": self.api_key
        }
        response = self.session.get(URL, params=params)
        businesses = response.json()["results"]

        # Defina o local e o tipo de empresa que você deseja consultar
        location = "cidade,estado"
        type = "lojas"

        # Construa a URL da API
        url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={type}+in+{city}&key={self.api_key}"

        # Execute a consulta à API
        response = requests.get(url)

        # Verifique se a consulta foi bem-sucedida
        if response.status_code == 200:
            # Carregue o resultado da consulta em um objeto JSON
            result = response.json()

            # Imprima o nome e o endereço de cada empresa encontrada
            for business in result["results"]:
                print(business["name"])
                print(business["formatted_address"])
        else:
            print("A consulta à API falhou com o status code:", response.status_code)

        return businesses

    def get_business_details(self, place_id):
        URL = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": place_id,
            "key": self.api_key
        }
        response = requests.get(URL, params=params)
        details = response.json()["result"]
        return details

    def get_business_reviews(self, place_id):
        URL = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": place_id,
            "key": self.api_key,
            "fields": "reviews"
        }
        response = requests.get(URL, params=params)
        reviews = response.json()["result"].get("reviews", [])
        return reviews

    def get_business_photos(self, place_id):
        URL = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": place_id,
            "key": self.api_key,
            "fields": "photos"
        }
        response = self.session.get(URL, params=params)
        photos = response.json()["result"].get("photos", [])
        photo_urls = []
        for photo in photos:
            photo_reference = photo["photo_reference"]
            photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_reference}&key={self.api_key}"
            photo_urls.append(photo_url)
        return photo_urls

    def get_people_also_viewed(self, place_id):
        URL = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": place_id,
            "key": self.api_key,
            "fields": "similar_places"
        }
        response = requests.get(URL, params=params)
        similar_places = response.json()["result"].get("similar_places", [])
        return similar_places

    def init(self):
        city = "Barreiras, Bahia"
        self.Controller.run("create", "get" , city)
        
        businesses = self.get_businesses(city)
        
        for business in businesses:
            print(business["name"])
            print(business["formatted_address"])
            print("-" * 20)
            details = self.get_business_details(business["place_id"])
            print("Detalhes:")
            print("Telefone:", details.get("formatted_phone_number", "N/A"))
            print("Site:", details.get("website", "N/A"))
            print("Avaliação:", details.get("rating", "N/A"))
            print("-" * 20)
if __name__ == "__main__":
    app = BusinessInfoApp(get_google_maps_api_key(), "https://maps.googleapis.com/maps/api/place/textsearch/json")
    app.init()