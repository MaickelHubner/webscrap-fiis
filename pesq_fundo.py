import datetime
import os
import smtplib
import sys
from email.message import EmailMessage

import requests
from bs4 import BeautifulSoup


def hoje():
    return datetime.date.today()


def texto_para_data(texto):
    return datetime.datetime.strptime(texto, '%d/%m/%Y').date()


def adiciona_dias(numero_dias=0, data=hoje()):
    return data + datetime.timedelta(days=numero_dias)


def convDateToDMY(data):
    return data.strftime('%d/%m/%Y')


def executar(fundo):
    dados = {}
    delta_dias = -3 if hoje().weekday == 0 else -1

    url = 'https://www.fundsexplorer.com.br/funds/{}/'.format(fundo.lower())
    page = requests.get(url, headers={'User-Agent': 'Mozzila/5.0'})
    if page.status_code != 200:
        raise ValueError('Não foi possível encontrar o fundo!')

    soup = BeautifulSoup(page.text, 'html.parser')

    nome_do_fundo = soup.find(class_='basicInformation__grid__box').find_all('p')[1].string

    dados['nome'] = nome_do_fundo

    comunicacoes = soup.find_all(class_='communicated__grid__row')
    notas = []
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

        data = texto_para_data(data)

        if data < adiciona_dias(delta_dias):
            continue

        notas.append(
            {
                'data': data,
                'texto': texto,
                'link': link,
            }
        )

    dados['notas'] = notas

    return dados


def _send_mail(to_email, subject, message, server='smtp.zoho.com', from_email=os.getenv('EMAIL_FIIS', '')):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = ', '.join(to_email)
    # msg.set_content(message)
    msg.add_alternative(message, subtype='html')
    server = smtplib.SMTP(server, 587)
    # server.set_debuglevel(1)
    server.starttls()
    server.login(os.getenv('EMAIL_FIIS', ''), os.getenv('SENHA_EMAIL_FIIS', ''))
    server.send_message(msg)
    server.quit()


def _load_mail_template():
    with open('mail.html', 'r') as html_file:
        html = html_file.read()
    return html


def _treat_html(lista):
    texto = ''
    for fundo in lista.keys():
        if len(lista[fundo]['notas']) > 0:
            texto_fundo = f'''
                <div class="container-fluid bg-3" style="margin-top: 50px">
                <p style="font-size: 130%; font-weight: bold; margin-bottom: 30px">
                    {fundo} - {lista[fundo]['nome']}
                </p>
            '''
            for noticia in lista[fundo]['notas']:
                if noticia['link'] == '':
                    texto_fundo += f"<p>{convDateToDMY(noticia['data'])} - {noticia['texto']}</p>"
                else:
                    texto_fundo += f"""
                        <p><a
                            href='{noticia['link']}'
                            target='_blank'
                            style='color: #03a9f4'
                        >{convDateToDMY(noticia['data'])} - {noticia['texto']}</a></p>
                    """
            texto_fundo += '</div>'
            texto += texto_fundo
    return texto


def enviar(lista):
    lista_emails = ['maickel.hubner@gmail.com']  # , 'deboramals@gmail.com']
    assunto = 'Atualização de FIIs'
    mensagem = _load_mail_template()

    mensagem = mensagem.replace('[[DATA]]', convDateToDMY(hoje()))
    noticias = _treat_html(lista)
    if noticias == '':
        noticias = '''
            <div class="container-fluid bg-3" style="margin-top: 50px">
            <p><b>Nenhuma notícia dos seus fundos no período.</b></p>
            </div>
        '''
    mensagem = mensagem.replace('[[INFOS]]', noticias)
    mensagem = mensagem.replace('[[LISTA_FUNDOS]]', ', '.join(lista.keys()))

    _send_mail(lista_emails, assunto, mensagem)


FUNDO = None
if len(sys.argv) > 1:
    FUNDO = sys.argv[1]
if FUNDO is not None:
    lista = {}
    f = executar(FUNDO)
    lista[FUNDO] = f
    enviar(lista)
else:
    lista = {}
    for fundo in ['RNGO11', 'BBFI11B', 'FAMB11B', 'HGPO11', 'HFOF11', 'RECR11', 'HABT11', 'XPLG11', 'HGRU11']:
        f = executar(fundo)
        lista[fundo] = f
    enviar(lista)
