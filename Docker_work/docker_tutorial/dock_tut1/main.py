import requests
from bs4 import BeautifulSoup

URL = "https://www.tutorialspoint.com/index.htm"

def main():    
    req = requests.get(URL)
    soup = BeautifulSoup(req.content, "html.parser")
    print(soup.title)
    print("##############")
    for link in soup.find_all('a'):
        print("link=",link.get('href'))
        break #print only one
        
if __name__ == '__main__':
    main()