import json
import base64
import uuid
import time
import socket
import requests
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse, parse_qs

class ConfigToSingbox:
    def __init__(self):
        self.output_file = 'configs/singbox_configs.json'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def get_location_from_ip_api(self, ip: str) -> Tuple[str, str]:
        try:
            response = requests.get(f'http://ip-api.com/json/{ip}', headers=self.headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success' and data.get('countryCode'):
                    return data['countryCode'].lower(), data['country']
        except Exception:
            pass
        return '', ''

    def get_location_from_ipapi_co(self, ip: str) -> Tuple[str, str]:
        try:
            response = requests.get(f'https://ipapi.co/{ip}/json/', headers=self.headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('country_code') and data.get('country_name'):
                    return data['country_code'].lower(), data['country_name']
        except Exception:
            pass
        return '', ''

    def get_location_from_ipwhois(self, ip: str) -> Tuple[str, str]:
        try:
            response = requests.get(f'https://ipwhois.app/json/{ip}', headers=self.headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('country_code') and data.get('country'):
                    return data['country_code'].lower(), data['country']
        except Exception:
            pass
        return '', ''

    def get_location(self, address: str) -> tuple:
        try:
            ip = socket.gethostbyname(address)
            apis = [
                self.get_location_from_ip_api,
                self.get_location_from_ipapi_co,
                self.get_location_from_ipwhois,
            ]
            for api_func in apis:
                country_code, country = api_func(ip)
                if country_code and country and len(country_code) == 2:
                    flag = ''.join(chr(ord('🇦') + ord(c.upper()) - ord('A')) for c in country_code)
                    time.sleep(1)
                    return flag, country
            time.sleep(1)
        except Exception:
            pass
        return "🏳️", "Unknown"

    def decode_vmess(self, config: str) -> Optional[Dict]:
        try:
            encoded = config.replace('vmess://', '')
            decoded = base64.b64decode(encoded).decode('utf-8')
            return json.loads(decoded)
        except Exception:
            return None

    def parse_vless(self, config: str) -> Optional[Dict]:
        try:
            url = urlparse(config)
            if url.scheme.lower() != 'vless' or not url.hostname:
                return None
            netloc = url.netloc.split('@')[-1]
            address, port = netloc.split(':') if ':' in netloc else (netloc, '443')
            params = parse_qs(url.query)
            return {
                'uuid': url.username,
                'address': address,
                'port': int(port),
                'flow': params.get('flow', [''])[0],
                'sni': params.get('sni', [address])[0],
                'type': params.get('type', ['tcp'])[0],
                'path': params.get('path', [''])[0],
                'host': params.get('host', [address])[0],
                'security': params.get('security', ['none'])[0]
            }
        except Exception:
            return None

    def parse_trojan(self, config: str) -> Optional[Dict]:
        try:
            url = urlparse(config)
            if url.scheme.lower() != 'trojan' or not url.hostname:
                return None
            port = url.port or 443
            params = parse_qs(url.query)
            return {
                'password': url.username,
                'address': url.hostname,
                'port': port,
                'sni': params.get('sni', [url.hostname])[0],
                'alpn': params.get('alpn', [''])[0],
                'type': params.get('type', ['tcp'])[0],
                'path': params.get('path', [''])[0],
                'host': params.get('host', [url.hostname])[0]
            }
        except Exception:
            return None

    def parse_hysteria2(self, config: str) -> Optional[Dict]:
        try:
            url = urlparse(config)
            if url.scheme.lower() not in ['hysteria2', 'hy2'] or not url.hostname or not url.port:
                return None
            query = dict(pair.split('=') for pair in url.query.split('&')) if url.query else {}
            return {
                'address': url.hostname,
                'port': url.port,
                'password': url.username or query.get('password', ''),
                'sni': query.get('sni', url.hostname)
            }
        except Exception:
            return None

    def parse_shadowsocks(self, config: str) -> Optional[Dict]:
        try:
            parts = config.replace('ss://', '').split('@')
            if len(parts) != 2:
                return None
            method_pass = base64.b64decode(parts[0]).decode('utf-8')
            method, password = method_pass.split(':')
            server_parts = parts[1].split('#')[0]
            host, port = server_parts.split(':')
            return {
                'method': method,
                'password': password,
                'address': host,
                'port': int(port)
            }
        except Exception:
            return None

    def convert_to_singbox(self, config: str, index: int, protocol_type: str) -> Optional[Dict]:
        try:
            config_lower = config.lower()
            if config_lower.startswith('vmess://'):
                data = self.decode_vmess(config)
                if not data or not all(k in data for k in ['add', 'port', 'id']):
                    return None
                flag, country = self.get_location(data['add'])
                tag = f"{flag} {index} - {protocol_type} - {country} : {data['port']}"
                transport = {}
                if data.get('net') == 'ws':
                    transport = {"type": "ws", "path": data.get('path', '/'), "headers": {"Host": data.get('host', data['add'])}}
                tls = {}
                if data.get('tls') == 'tls':
                    tls = {"enabled": True, "server_name": data.get('sni', data['add']), "insecure": False, "alpn": ["http/1.1"], "record_fragment": False, "utls": {"enabled": True, "fingerprint": "chrome"}}
                else:
                    tls = {"enabled": False}
                return {"type": "vmess", "tag": tag, "server": data['add'], "server_port": int(data['port']), "uuid": data['id'], "security": data.get('scy', 'auto'), "alter_id": int(data.get('aid', 0)), "transport": transport, "tls": tls}
            elif config_lower.startswith('vless://'):
                data = self.parse_vless(config)
                if not data: return None
                flag, country = self.get_location(data['address'])
                tag = f"{flag} {index} - {protocol_type} - {country} : {data['port']}"
                transport = {}
                if data['type'] == 'ws':
                    transport = {"type": "ws", "path": data.get('path', '/'), "headers": {"Host": data.get('host', data['address'])}}
                tls_enabled = data['security'] == 'tls' or data['port'] in [443, 2053, 2083, 2087, 2096, 8443]
                tls = {}
                if tls_enabled:
                    tls = {"enabled": True, "server_name": data['sni'], "insecure": False, "alpn": ["http/1.1"], "record_fragment": False, "utls": {"enabled": True, "fingerprint": "chrome"}}
                else:
                    tls = {"enabled": False}
                return {"type": "vless", "tag": tag, "server": data['address'], "server_port": data['port'], "uuid": data['uuid'], "flow": data.get('flow', ''), "tls": tls, "transport": transport}
            elif config_lower.startswith('trojan://'):
                data = self.parse_trojan(config)
                if not data: return None
                flag, country = self.get_location(data['address'])
                tag = f"{flag} {index} - {protocol_type} - {country} : {data['port']}"
                transport = {}
                if data['type'] == 'ws':
                    transport = {"type": "ws", "path": data.get('path', '/'), "headers": {"Host": data.get('host', data['address'])}}
                tls = {"enabled": True, "server_name": data['sni'], "insecure": False, "alpn": ["http/1.1"], "record_fragment": False, "utls": {"enabled": True, "fingerprint": "chrome"}}
                return {"type": "trojan", "tag": tag, "server": data['address'], "server_port": data['port'], "password": data['password'], "tls": tls, "transport": transport}
            elif config_lower.startswith(('hysteria2://', 'hy2://')):
                data = self.parse_hysteria2(config)
                if not data: return None
                flag, country = self.get_location(data['address'])
                tag = f"{flag} {index} - {protocol_type} - {country} : {data['port']}"
                return {"type": "hysteria2", "tag": tag, "server": data['address'], "server_port": data['port'], "password": data['password'], "tls": {"enabled": True, "insecure": True, "server_name": data['sni']}}
            elif config_lower.startswith('ss://'):
                data = self.parse_shadowsocks(config)
                if not data: return None
                flag, country = self.get_location(data['address'])
                tag = f"{flag} {index} - {protocol_type} - {country} : {data['port']}"
                return {"type": "shadowsocks", "tag": tag, "server": data['address'], "server_port": data['port'], "method": data['method'], "password": data['password']}
            return None
        except Exception:
            return None

    def process_configs(self):
        try:
            with open('configs/proxy_configs.txt', 'r', encoding='utf-8') as f:
                configs = [line for line in f.read().strip().split('\n') if line.strip() and not line.strip().startswith('//')]

            outbounds, valid_tags = [], []
            counters = {"VLESS": 1, "Trojan": 1, "VMess": 1, "SS": 1, "Hysteria2": 1}
            protocol_map = {'vless': 'VLESS', 'trojan': 'Trojan', 'vmess': 'VMess', 'ss': 'SS', 'hysteria2': 'Hysteria2', 'hy2': 'Hysteria2'}

            for config in configs:
                protocol_key = config.split('://')[0].lower()
                protocol_name = protocol_map.get(protocol_key)
                if protocol_name:
                    converted = self.convert_to_singbox(config, counters[protocol_name], protocol_name)
                    if converted:
                        outbounds.append(converted)
                        valid_tags.append(converted['tag'])
                        counters[protocol_name] += 1
            if not outbounds:
                print("No valid configurations found.")
                return

            final_config = {
                "log": {"level": "warn", "timestamp": True},
                "dns": {
                    "servers": [
                        {"type": "https", "server": "8.8.8.8", "detour": "🌐 Anonymous Multi", "tag": "dns-remote"},
                        {"type": "udp", "server": "8.8.8.8", "server_port": 53, "tag": "dns-direct"},
                        {"type": "fakeip", "tag": "dns-fake", "inet4_range": "198.18.0.0/15", "inet6_range": "fc00::/18"}
                    ],
                    "rules": [
                        {"domain": ["raw.githubusercontent.com"], "server": "dns-direct"},
                        {"clash_mode": "Direct", "server": "dns-direct"},
                        {"clash_mode": "Global", "server": "dns-remote"},
                        {"type": "logical", "mode": "and", "rules": [{"rule_set": "geosite-ir"}, {"rule_set": "geoip-ir"}], "action": "route", "server": "dns-direct"},
                        {"rule_set": ["geosite-malware", "geosite-phishing", "geosite-cryptominers", "geosite-category-ads-all"], "action": "reject"},
                        {"disable_cache": True, "inbound": "tun-in", "query_type": ["A", "AAAA"], "server": "dns-fake"}
                    ],
                    "strategy": "ipv4_only",
                    "independent_cache": True
                },
                "inbounds": [
                    {"type": "tun", "tag": "tun-in", "address": ["172.18.0.1/30", "fdfe:dcba:9876::1/126"], "mtu": 9000, "auto_route": True, "strict_route": True, "endpoint_independent_nat": True, "stack": "mixed"},
                    {"type": "mixed", "tag": "mixed-in", "listen": "0.0.0.0", "listen_port": 2080}
                ],
                "outbounds": [
                    {"type": "selector", "tag": "🌐 Anonymous Multi", "outbounds": ["👽 Best Ping 🚀"] + valid_tags + ["direct"]},
                    {"type": "direct", "tag": "direct"},
                    {"type": "urltest", "tag": "👽 Best Ping 🚀", "outbounds": valid_tags, "url": "https://www.gstatic.com/generate_204", "interrupt_exist_connections": False, "interval": "30s"}
                ] + outbounds,
                "route": {
                    "rules": [
                        {"ip_cidr": "172.18.0.2", "action": "hijack-dns"},
                        {"clash_mode": "Direct", "outbound": "direct"},
                        {"clash_mode": "Global", "outbound": "🌐 Anonymous Multi"},
                        {"action": "sniff"},
                        {"protocol": "dns", "action": "hijack-dns"},
                        {"network": "udp", "action": "reject"},
                        {"rule_set": ["geosite-malware", "geosite-phishing", "geosite-cryptominers", "geosite-category-ads-all"], "action": "reject"},
                        {"rule_set": ["geoip-malware", "geoip-phishing"], "action": "reject"},
                        {"rule_set": ["geosite-ir"], "action": "route", "outbound": "direct"},
                        {"rule_set": ["geoip-ir"], "action": "route", "outbound": "direct"}
                    ],
                    "rule_set": [
                        {"type": "remote", "tag": "geosite-malware", "format": "binary", "url": "https://raw.githubusercontent.com/Chocolate4U/Iran-sing-box-rules/rule-set/geosite-malware.srs", "download_detour": "direct"},
                        {"type": "remote", "tag": "geoip-malware", "format": "binary", "url": "https://raw.githubusercontent.com/Chocolate4U/Iran-sing-box-rules/rule-set/geoip-malware.srs", "download_detour": "direct"},
                        {"type": "remote", "tag": "geosite-phishing", "format": "binary", "url": "https://raw.githubusercontent.com/Chocolate4U/Iran-sing-box-rules/rule-set/geosite-phishing.srs", "download_detour": "direct"},
                        {"type": "remote", "tag": "geoip-phishing", "format": "binary", "url": "https://raw.githubusercontent.com/Chocolate4U/Iran-sing-box-rules/rule-set/geoip-phishing.srs", "download_detour": "direct"},
                        {"type": "remote", "tag": "geosite-cryptominers", "format": "binary", "url": "https://raw.githubusercontent.com/Chocolate4U/Iran-sing-box-rules/rule-set/geosite-cryptominers.srs", "download_detour": "direct"},
                        {"type": "remote", "tag": "geosite-category-ads-all", "format": "binary", "url": "https://raw.githubusercontent.com/Chocolate4U/Iran-sing-box-rules/rule-set/geosite-category-ads-all.srs", "download_detour": "direct"},
                        {"type": "remote", "tag": "geosite-ir", "format": "binary", "url": "https://raw.githubusercontent.com/Chocolate4U/Iran-sing-box-rules/rule-set/geosite-ir.srs", "download_detour": "direct"},
                        {"type": "remote", "tag": "geoip-ir", "format": "binary", "url": "https://raw.githubusercontent.com/Chocolate4U/Iran-sing-box-rules/rule-set/geoip-ir.srs", "download_detour": "direct"}
                    ],
                    "auto_detect_interface": True,
                    "default_domain_resolver": {"server": "dns-direct", "strategy": "prefer_ipv4", "rewrite_ttl": 60},
                    "final": "🌐 Anonymous Multi"
                },
                "ntp": {"enabled": True, "server": "time.cloudflare.com", "server_port": 123, "domain_resolver": "dns-direct", "interval": "30m", "write_to_system": False},
                "experimental": {
                    "clash_api": {"external_controller": "127.0.0.1:9090", "default_mode": "Rule"}
                }
            }

            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(final_config, f, indent=4, ensure_ascii=False)
            
            print(f"Configuration successfully generated at: {self.output_file}")

        except Exception as e:
            print(f"Error processing configs: {str(e)}")

def main():
    converter = ConfigToSingbox()
    converter.process_configs()

if __name__ == '__main__':
    main()