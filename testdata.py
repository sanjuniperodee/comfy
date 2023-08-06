import csv
from bs4 import BeautifulSoup
from requests import get
writer = csv.writer(open("Mika.csv", "w", encoding='utf-16',newline=''), delimiter='\t')
writer.writerow(["NAMING", "YEAR", "CITY", "PRICE", "INFO", "LINK"])
href = 'https://www.loftit.ru/catalog/?sp='
for i in range(1, 999):
    url = href  + str(i)
    soup = BeautifulSoup(get(url).text, 'html.parser')
    responses = soup.find_all('div', class_='items')
    for item in responses:
        print(item)
        # name = item.find('a', class_='list-link ddl_product_link').text.strip()
        # price = item.find('span', class_='price').text.strip()
        # city = item.find('div', class_='list-region').text.strip()
        # info = item.find('div', class_='a-search-description').text.strip()
        # year = info[0:4]
        # link = "https://kolesa.kz" + item.find('a', class_='list-link ddl_product_link')['href']
        # row = [name, year, city, price.replace(u'\xa0', u'').replace(u'₸', u''), info, link]
        # writer.writerow(row)
