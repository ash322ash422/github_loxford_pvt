import random
import requests
from bs4 import BeautifulSoup

URL = "https://www.tutorialspoint.com/index.htm"

def main():    
    req = requests.get(URL)
    soup = BeautifulSoup(req.content, "html.parser")
    links = soup.find_all('a')
    
    while(True):
        idx = random.randrange(0, len(links))
        print(f'link={links[idx]}')

        user_input = input('Do you want another random link (y/[n])? ')
        if user_input != 'y':
            break    
#end def
    
if __name__ == '__main__':
    main()