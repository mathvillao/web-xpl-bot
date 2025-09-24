import discord
import os
from dotenv import load_dotenv
import nmap
import requests
import subprocess  # Para executar comandos curl

load_dotenv()  # Carrega variáveis de ambiente do .env

intents = discord.Intents.default()
client = discord.Client(intents=intents)

# Função para enviar mensagens grandes
async def send_large_message(channel, content):
    MAX_MESSAGE_LENGTH = 2000  # Limitando a mensagem a 2000 para garantir que não ultrapasse 4000
    while len(content) > MAX_MESSAGE_LENGTH:
        await channel.send(content[:MAX_MESSAGE_LENGTH])
        content = content[MAX_MESSAGE_LENGTH:]
    if content:
        await channel.send(content)

@client.event
async def on_ready():
    print(f'Bot conectado como {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('/nmap'):
        host = message.content.split(' ')[1]
        result = nmap_scan(host)
        await send_large_message(message.channel, result)

    elif message.content.startswith('/gau'):
        domain = message.content.split(' ')[1]
        result = wayback_scan(domain)
        await send_large_message(message.channel, result)

    elif message.content.startswith('/crt'):
        domain = message.content.split(' ')[1]
        result = crt_scan(domain)
        await send_large_message(message.channel, result)

    elif message.content.startswith('/curl'):
        url = message.content.split(' ', 1)[1]  # Captura a URL após o comando
        result = execute_curl(url)
        await send_large_message(message.channel, result)

# Função de scan nmap
def nmap_scan(host):
    try:
        nm = nmap.PortScanner()
        nm.scan(host, '22-443')
        return f'Host {host} scan:\n{nm.all_hosts()}'
    except Exception as e:
        return f"Error: {str(e)}"

# Função para buscar URLs com a Wayback Machine
def wayback_scan(domain):
    url = f'http://web.archive.org/cdx/search/cdx?url={domain}/*&output=json'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if not data:
                return f"No data found for {domain}."
            urls = [entry[2] for entry in data]  # Extrai os URLs
            return f"URLs found for {domain}:\n" + "\n".join(urls)
        else:
            return f"Error: Unable to fetch URLs for {domain}. Status code: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return f"Error: {str(e)}"

# Função de consulta a certificados
def crt_scan(domain):
    url = f'https://crt.sh/?q={domain}'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return f"Certificates for {domain}:\n{response.text[:2000]}"  # Limita a resposta
        else:
            return f"Error: Unable to fetch certificates for {domain}. Status code: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return f"Error: {str(e)}"

# Função para executar o comando curl
def execute_curl(url):
    try:
        result = subprocess.run(['curl', url], capture_output=True, text=True)
        if result.returncode == 0:
            return f"Response from {url}:\n{result.stdout}"
        else:
            return f"Error: {result.stderr}"
    except Exception as e:
        return f"Error: {str(e)}"

client.run(os.getenv('DISCORD_TOKEN'))
