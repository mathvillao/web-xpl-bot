import discord
import os
from dotenv import load_dotenv
import nmap
import aiohttp
import asyncio
import subprocess

load_dotenv()  # Carrega variáveis de ambiente do .env

intents = discord.Intents.default()
# Removido message_content intent para evitar erro de privilégios
client = discord.Client(intents=intents)

# Função para enviar mensagens grandes
async def send_large_message(channel, content):
    MAX_MESSAGE_LENGTH = 2000
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
    
    try:
        if message.content.startswith('/nmap'):
            parts = message.content.split(' ')
            if len(parts) < 2:
                await message.channel.send("Usage: /nmap <host>")
                return
            host = parts[1]
            await message.channel.send(f"Scanning {host}... This may take a moment.")
            result = await nmap_scan_async(host)
            await send_large_message(message.channel, result)
            
        elif message.content.startswith('/gau'):
            parts = message.content.split(' ')
            if len(parts) < 2:
                await message.channel.send("Usage: /gau <domain>")
                return
            domain = parts[1]
            await message.channel.send(f"Searching URLs for {domain}... This may take a moment.")
            result = await wayback_scan_async(domain)
            await send_large_message(message.channel, result)
            
        elif message.content.startswith('/crt'):
            parts = message.content.split(' ')
            if len(parts) < 2:
                await message.channel.send("Usage: /crt <domain>")
                return
            domain = parts[1]
            await message.channel.send(f"Searching certificates for {domain}...")
            result = await crt_scan_async(domain)
            await send_large_message(message.channel, result)
            
        elif message.content.startswith('/curl'):
            parts = message.content.split(' ', 1)
            if len(parts) < 2:
                await message.channel.send("Usage: /curl <url>")
                return
            url = parts[1]
            await message.channel.send(f"Executing curl for {url}...")
            result = await execute_curl_async(url)
            await send_large_message(message.channel, result)
            
    except Exception as e:
        await message.channel.send(f"An error occurred: {str(e)}")

# Função de scan nmap assíncrona
async def nmap_scan_async(host):
    def run_nmap():
        try:
            nm = nmap.PortScanner()
            nm.scan(host, '22-443')
            result = f'Host {host} scan results:\n'
            for host_ip in nm.all_hosts():
                result += f'\nHost: {host_ip} ({nm[host_ip].hostname()})\n'
                result += f'State: {nm[host_ip].state()}\n'
                for protocol in nm[host_ip].all_protocols():
                    ports = nm[host_ip][protocol].keys()
                    for port in ports:
                        state = nm[host_ip][protocol][port]['state']
                        result += f'Port {port}/{protocol}: {state}\n'
            return result
        except Exception as e:
            return f"Nmap Error: {str(e)}"
    
    # Executa nmap em thread separada para não bloquear o event loop
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run_nmap)

# Função para buscar URLs com a Wayback Machine de forma assíncrona
async def wayback_scan_async(domain):
    url = f'http://web.archive.org/cdx/search/cdx?url={domain}/*&output=json&limit=100'
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if not data or len(data) <= 1:  # Primeiro item é o cabeçalho
                        return f"No URLs found for {domain}."
                    
                    # Pula o cabeçalho e extrai URLs únicos
                    urls = list(set([entry[2] for entry in data[1:] if len(entry) > 2]))
                    urls = urls[:50]  # Limita a 50 URLs para evitar mensagens muito longas
                    
                    return f"URLs found for {domain} (showing first 50):\n" + "\n".join(urls)
                else:
                    return f"Error: Unable to fetch URLs for {domain}. Status code: {response.status}"
    except asyncio.TimeoutError:
        return f"Error: Timeout while fetching URLs for {domain}"
    except Exception as e:
        return f"Error: {str(e)}"

# Função de consulta a certificados assíncrona
async def crt_scan_async(domain):
    url = f'https://crt.sh/?q={domain}&output=json'
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if not data:
                        return f"No certificates found for {domain}."
                    
                    result = f"Certificates for {domain}:\n"
                    for i, cert in enumerate(data[:10]):  # Limita a 10 certificados
                        result += f"\n{i+1}. Common Name: {cert.get('common_name', 'N/A')}\n"
                        result += f"   Issuer: {cert.get('issuer_name', 'N/A')}\n"
                        result += f"   Valid From: {cert.get('not_before', 'N/A')}\n"
                        result += f"   Valid To: {cert.get('not_after', 'N/A')}\n"
                    
                    if len(data) > 10:
                        result += f"\n... and {len(data) - 10} more certificates"
                    
                    return result
                else:
                    return f"Error: Unable to fetch certificates for {domain}. Status code: {response.status}"
    except asyncio.TimeoutError:
        return f"Error: Timeout while fetching certificates for {domain}"
    except Exception as e:
        return f"Error: {str(e)}"

# Função para executar o comando curl de forma assíncrona
async def execute_curl_async(url):
    def run_curl():
        try:
            result = subprocess.run(
                ['curl', '-L', '--max-time', '30', '--max-redirs', '5', url], 
                capture_output=True, 
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                output = result.stdout[:1500]  # Limita a saída
                if len(result.stdout) > 1500:
                    output += "\n... (output truncated)"
                return f"Response from {url}:\n```\n{output}\n```"
            else:
                return f"Curl Error: {result.stderr}"
        except subprocess.TimeoutExpired:
            return f"Error: Curl command timed out for {url}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    # Executa curl em thread separada
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run_curl)

if __name__ == "__main__":
    client.run(os.getenv('DISCORD_TOKEN'))