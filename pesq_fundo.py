import sys

import requests
from bs4 import BeautifulSoup


def executar(fundo):
    print('Pesquisando dados do fundo {}...'.format(fundo))

    url = 'https://www.fundsexplorer.com.br/funds/{}/'.format(fundo.lower())
    page = requests.get(url, headers={'User-Agent': 'Mozzila/5.0'})
    if page.status_code != 200:
        raise ValueError('Não foi possível encontrar o fundo!')

    soup = BeautifulSoup(page.text, 'html.parser')

    nome_do_fundo = soup.find(class_='basicInformation__grid__box').find_all('p')[1].string
    print(f'\n{nome_do_fundo}\n')

    comunicacoes = soup.find_all(class_='communicated__grid__row')
    for comunicacao in comunicacoes:
        if 'communicated__grid__rend' in comunicacao.get('class'):
            texto = comunicacao.find('p').text.replace('\n', ' ')
            link = ''
            data = comunicacao.find_all('li')[0].find('b').text
        else:
            texto = comunicacao.find('a').text
            link = comunicacao.find('a', href=True)['href']
            data = comunicacao.find('p').text.replace('.', '/')

        texto = ' '.join(texto.split())
        data = ' '.join(data.split())

        print(texto)
        print(link)
        print(data)


FUNDO = None
if len(sys.argv) > 1:
    FUNDO = sys.argv[1]
if FUNDO is not None:
    executar(FUNDO)
