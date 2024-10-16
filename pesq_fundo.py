import datetime
import re
import smtplib
import sys
from email.message import EmailMessage

import requests
from bs4 import BeautifulSoup
from environs import Env

EMAIL_LIST = ["maickel.hubner@gmail.com", "deboramals@gmail.com"]
# EMAIL_LIST = ["maickel.hubner@gmail.com"]

LISTA_DE_FUNDOS = [
    "RNGO11",
    "BBFI11B",
    "HGPO11",
    "HFOF11",
    "RECR11",
    "HABT11",
    "XPLG11",
    "HGRU11",
]

env = Env()
env.read_env(".env")


def hoje():
    return datetime.date.today()


def texto_para_data(texto):
    return datetime.datetime.strptime(texto, "%d/%m/%Y").date()


def adiciona_dias(numero_dias=0, data=hoje()):
    return data + datetime.timedelta(days=numero_dias)


def converter_data_dmy(data):
    return data.strftime("%d/%m/%Y")


def get_row_info(comunicacao):
    rendimento = False
    if "communicated__grid__rend" in comunicacao.get("class"):
        texto = comunicacao.find("p").text.replace("\n", " ")
        link = ""
        data = comunicacao.find_all("b")[1].text
        rendimento = True
    else:
        texto = comunicacao.find("a").text
        link = comunicacao.find("a", href=True)["href"]
        data = comunicacao.find("p").text.replace(".", "/")

    texto = " ".join(texto.split())
    data = " ".join(data.split())

    data = texto_para_data(data)

    return {
        "data": data,
        "texto": texto,
        "link": link,
        "rendimento": rendimento,
    }


def executar(fundo):
    dados = {}
    delta_dias = -4 if hoje().weekday() == 0 else -2

    url = "https://www.fundsexplorer.com.br/funds/{}/".format(fundo.lower())
    page = requests.get(url, headers={"User-Agent": "Mozzila/5.0"})
    if page.status_code != 200:
        raise ValueError("Não foi possível encontrar o fundo!")

    soup = BeautifulSoup(page.text, "html.parser")

    nome_do_fundo = (
        soup.find(class_="basicInformation__grid__box").find_all("p")[1].string
    )

    dados["nome"] = nome_do_fundo

    comunicacoes = soup.find_all(class_="communicated__grid__row")
    notas = []
    for comunicacao in comunicacoes:
        info = get_row_info(comunicacao)

        # Se for uma comunicação de rendimento, procura a anterior para calcular a variação
        if info["rendimento"]:
            ant = procura_rend_ant(comunicacoes, info["data"])
            if ant is not None:
                val_atu = float(
                    re.findall(r"R\$\s*([\d,]+)", info["texto"])[0].replace(",", ".")
                )
                val_ant = float(
                    re.findall(r"R\$\s*([\d,]+)", ant["texto"])[0].replace(",", ".")
                )
                dif = val_atu - val_ant
                perc = dif * 100 / val_ant
                info[
                    "texto"
                ] += f" (valor anterior R$ {val_ant:.2f}, diferença de R$ {dif:.2f} ou {perc:.4f} %)"

        if info["data"] < adiciona_dias(delta_dias):
            break

        notas.append(info)

    dados["notas"] = notas

    return dados


def procura_rend_ant(comunicacoes, data):
    ant = None
    for comunicacao in comunicacoes:
        info = get_row_info(comunicacao)

        if info["data"] >= data:
            continue

        if info["rendimento"]:
            ant = info
            break

    return ant


def _send_mail(
    to_email,
    subject,
    message,
    server="smtp.zoho.com",
    from_email=None,
):
    from_email = from_email or env("EMAIL_FIIS", "")
    senha_email = env("SENHA_EMAIL_FIIS", "")

    if not from_email or not senha_email:
        raise ValueError("Email and password environment variables must be set")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = ", ".join(to_email)
    msg.add_alternative(message, subtype="html")

    with smtplib.SMTP(server, 587) as server:
        server.starttls()
        server.login(from_email, senha_email)
        server.send_message(msg)


def _load_mail_template():
    with open("mail.html", "r") as html_file:
        html = html_file.read()
    return html


def _treat_html(lista):
    texto = ""
    for fundo in lista.keys():
        if len(lista[fundo]["notas"]) > 0:
            texto_fundo = f"""
                <div class="container-fluid bg-3" style="margin-top: 50px">
                <p style="font-size: 130%; font-weight: bold; margin-bottom: 30px">
                    {fundo} - {lista[fundo]['nome']}
                </p>
            """
            for noticia in lista[fundo]["notas"]:
                if noticia["link"] == "":
                    texto_fundo += f"<p>{converter_data_dmy(noticia['data'])} - {noticia['texto']}</p>"
                else:
                    texto_fundo += f"""
                        <p><a
                            href='{noticia['link']}'
                            target='_blank'
                            style='color: #03a9f4'
                        >{converter_data_dmy(noticia['data'])} - {noticia['texto']}</a></p>
                    """
            texto_fundo += "</div>"
            texto += texto_fundo
    return texto


def enviar(lista):
    lista_emails = EMAIL_LIST
    assunto = "Atualização de FIIs"
    mensagem = _load_mail_template()

    mensagem = mensagem.replace("[[DATA]]", converter_data_dmy(hoje()))
    noticias = _treat_html(lista)
    if noticias == "":
        noticias = """
            <div class="container-fluid bg-3" style="margin-top: 50px">
            <p><b>Nenhuma notícia dos seus fundos no período.</b></p>
            </div>
        """
    mensagem = mensagem.replace("[[INFOS]]", noticias)
    mensagem = mensagem.replace("[[LISTA_FUNDOS]]", ", ".join(lista.keys()))

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
    for fundo in LISTA_DE_FUNDOS:
        f = executar(fundo)
        lista[fundo] = f
    enviar(lista)
