import dns.message
import dns.query
import dns.rdatatype
import socket
import threading
import requests
import json
import time
from typing import Union, Tuple, Dict
from collections import defaultdict

class DNSCache:
    def __init__(self, ttl: int = 300):
        self.cache: Dict[tuple, tuple] = {}
        self.default_ttl = ttl
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    def get(self, key: tuple) -> Union[bytes, None]:
        if key in self.cache:
            record, expire_time = self.cache[key]
            if time.time() < expire_time:
                return record
            del self.cache[key]
        return None

    def set(self, key: tuple, value: bytes, ttl: int = None):
        if ttl is None:
            ttl = self.default_ttl
        self.cache[key] = (value, time.time() + ttl)

    def _cleanup_loop(self):
        while True:
            time.sleep(60)
            current_time = time.time()
            expired_keys = [k for k, v in self.cache.items() if current_time > v[1]]
            for k in expired_keys:
                del self.cache[k]

class DNSBypass:
    DOH_SERVERS = {
        "cloudflare": "https://cloudflare-dns.com/dns-query",
        "google": "https://dns.google/dns-query",
        "quad9": "https://dns.quad9.net/dns-query"
    }

    def __init__(self, listen_ip: str = "127.0.0.1", listen_port: int = 53,
                 proxy: str = None, preferred_doh: str = "cloudflare"):
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        self.proxy = proxy
        self.doh_url = self.DOH_SERVERS.get(preferred_doh, self.DOH_SERVERS["cloudflare"])
        self.running = False
        self.cache = DNSCache()
        self.stats = defaultdict(int)
        
    def start(self):
        """启动DNS代理服务器"""
        self.running = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock.bind((self.listen_ip, self.listen_port))
            print(f"DNS代理服务器正在监听 {self.listen_ip}:{self.listen_port}")
            if self.proxy:
                print(f"使用代理: {self.proxy}")
            self._handle_requests()
        except PermissionError:
            print("错误：需要管理员权限才能监听53端口")
            return
        except Exception as e:
            print(f"启动失败: {e}")
            return

    def _handle_requests(self):
        """处理DNS请求"""
        while self.running:
            try:
                data, addr = self.sock.recvfrom(512)
                thread = threading.Thread(
                    target=self._process_dns_query,
                    args=(data, addr)
                )
                thread.start()
            except Exception as e:
                print(f"处理请求时出错: {e}")

    def _process_dns_query(self, data: bytes, addr: Tuple[str, int]):
        """处理单个DNS查询"""
        try:
            query = dns.message.from_wire(data)
            question = query.question[0]
            qname = str(question.name)
            qtype = question.rdtype

            # 检查缓存
            cache_key = (qname, qtype)
            cached_response = self.cache.get(cache_key)
            if cached_response:
                self.stats["cache_hits"] += 1
                self.sock.sendto(cached_response, addr)
                return

            self.stats["cache_misses"] += 1
            response = self._doh_query(qname, qtype)
            
            if response:
                self.cache.set(cache_key, response)
                self.sock.sendto(response, addr)
                self.stats["successful_queries"] += 1
            else:
                self.stats["failed_queries"] += 1
            
        except Exception as e:
            print(f"处理DNS查询时出错: {e}")
            self.stats["errors"] += 1

    def _doh_query(self, domain: str, rdtype: int) -> Union[bytes, None]:
        """发送DoH请求"""
        try:
            headers = {
                "Accept": "application/dns-message",
                "Content-Type": "application/dns-message",
            }
            
            query = dns.message.make_query(domain, rdtype)
            dns_req = query.to_wire()
            
            proxies = {"https": self.proxy} if self.proxy else None
            
            # 尝试所有DoH服务器
            for doh_url in self.DOH_SERVERS.values():
                try:
                    response = requests.post(
                        doh_url,
                        headers=headers,
                        data=dns_req,
                        verify=True,
                        proxies=proxies,
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        return response.content
                except:
                    continue
                    
        except Exception as e:
            print(f"DoH查询失败: {e}")
        return None

    def print_stats(self):
        """打印统计信息"""
        print("\n=== DNS代理统计 ===")
        print(f"缓存命中: {self.stats['cache_hits']}")
        print(f"缓存未命中: {self.stats['cache_misses']}")
        print(f"成功查询: {self.stats['successful_queries']}")
        print(f"失败查询: {self.stats['failed_queries']}")
        print(f"错误数: {self.stats['errors']}")
        print(f"缓存记录数: {len(self.cache.cache)}")

    def stop(self):
        """停止DNS代理服务器"""
        self.running = False
        self.print_stats()
        self.sock.close()

def main():
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='DNS代理服务器')
    parser.add_argument('--ip', default='127.0.0.1', help='监听IP地址')
    parser.add_argument('--port', type=int, default=53, help='监听端口')
    parser.add_argument('--proxy', help='代理服务器地址 (例如: socks5://127.0.0.1:1080)')
    parser.add_argument('--doh', default='cloudflare', 
                      choices=['cloudflare', 'google', 'quad9'],
                      help='首选DoH服务器')
    
    args = parser.parse_args()
    
    if sys.platform == "win32" and not is_admin():
        print("请以管理员权限运行此程序")
        return
        
    dns_proxy = DNSBypass(
        listen_ip=args.ip,
        listen_port=args.port,
        proxy=args.proxy,
        preferred_doh=args.doh
    )
    
    try:
        dns_proxy.start()
    except KeyboardInterrupt:
        print("\n正在停止服务...")
        dns_proxy.stop()

def is_admin():
    """检查是否具有管理员权限"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if __name__ == "__main__":
    main() 