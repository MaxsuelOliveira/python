import requests

def get_data():
    response = requests.get('https://www.aliexpress.com/item/1005006616400469.html?spm=a2g0o.cart.0.0.4d5d7f06RQeLvf&mp=1')
    return response.text

def main():
    data = get_data()
    print(data)

main()