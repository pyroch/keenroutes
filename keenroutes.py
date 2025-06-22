import dns.resolver
import paramiko
import argparse
import time
import signal
import sys

# Глобальные переменные
client = None
is_running = True

def signal_handler(sig, frame):
    global client
    global is_running
    print("Получен сигнал завершения. Завершаем работу...")
    is_running = False
    if client:
        client.close()
    sys.exit(0)

# Установка обработчиков сигналов
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def get_ip_addresses(domain):
    ip_addresses = []
    try:
        answers = dns.resolver.resolve(domain, 'A')
        for rdata in answers:
            ip_addresses.append(rdata.address)
    except dns.resolver.NoAnswer:
        print(f"[!] Нет IP-ответа для {domain}")
    except dns.resolver.NXDOMAIN:
        print(f"[!] Домен {domain} не существует")
    return ip_addresses

def get_ips(domains):
    domain_ip_map = {}
    for domain in domains:
        print(f"Резолвим {domain}...")
        ips = get_ip_addresses(domain)
        domain_ip_map[domain] = ips
    return domain_ip_map

def update_routes(domain_ip_map, gateway, vpn_name):
    global client
    add = 0
    update = 0

    for domain, ips in domain_ip_map.items():
        for ip in ips:
            if not is_running:
                return

            stdin, stdout, stderr = client.exec_command(f"ip route {ip} {vpn_name} auto")
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')

            if error:
                print(f"[Ошибка] {error.strip()}")

            if 'Added static route' in output:
                add += 1
            if 'Renewed static route' in output:
                update += 1

            time.sleep(0.5)

    client.exec_command("system configuration save")
    client.close()

    print(f"Добавлено маршрутов: {add}")
    print(f"Обновлено маршрутов: {update}")

def main():
    global client

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=22)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--vpn_name", required=True)
    parser.add_argument("--domains", required=True)
    parser.add_argument("--gateway", default="0.0.0.0")
    parser.add_argument("--interval", type=int, default=60, help="Интервал между проверками в секундах. 0 — один раз")

    args = parser.parse_args()
    domains = [d.strip() for d in args.domains.split(",")]

    while is_running:
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(hostname=args.host, port=args.port, username=args.username, password=args.password, banner_timeout=200)
            print("✅ SSH-соединение установлено.")
        except paramiko.ssh_exception.AuthenticationException:
            print("❌ Ошибка аутентификации SSH.")
            sys.exit(1)

        domain_ip_map = get_ips(domains)
        update_routes(domain_ip_map, gateway=args.gateway, vpn_name=args.vpn_name)

        if args.interval <= 0:
            break

        print(f"⏳ Ожидание {args.interval} секунд перед следующей проверкой...\n")
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
