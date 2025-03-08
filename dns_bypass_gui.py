import tkinter as tk
from tkinter import ttk, messagebox
import threading
import sys
from dns_bypass import DNSBypass, is_admin
from PIL import Image, ImageTk
import os

class DNSBypassGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DNS代理服务器")
        self.root.geometry("600x400")
        
        self.dns_proxy = None
        self.is_running = False
        
        # 修改加载赞助码图片的代码
        self.sponsor_image = None
        image_path = "zanzhuma.jpg"
        
        # 如果是打包后的程序，需要调整路径
        if getattr(sys, 'frozen', False):
            image_path = os.path.join(sys._MEIPASS, "zanzhuma.jpg")
        
        if os.path.exists(image_path):
            try:
                img = Image.open(image_path)
                img = img.resize((456, 434), Image.Resampling.LANCZOS)
                self.sponsor_image = ImageTk.PhotoImage(img)
            except Exception as e:
                print(f"加载赞助码图片失败: {e}")
        
        self._create_widgets()
        self._create_layout()
        
    def _create_widgets(self):
        # 创建设置框架
        self.settings_frame = ttk.LabelFrame(self.root, text="服务器设置", padding=10)
        
        # IP地址设置
        self.ip_label = ttk.Label(self.settings_frame, text="监听IP:")
        self.ip_var = tk.StringVar(value="127.0.0.1")
        self.ip_entry = ttk.Entry(self.settings_frame, textvariable=self.ip_var)
        
        # 端口设置
        self.port_label = ttk.Label(self.settings_frame, text="端口:")
        self.port_var = tk.StringVar(value="53")
        self.port_entry = ttk.Entry(self.settings_frame, textvariable=self.port_var)
        
        # 代理设置
        self.proxy_label = ttk.Label(self.settings_frame, text="代理地址:")
        self.proxy_var = tk.StringVar()
        self.proxy_entry = ttk.Entry(self.settings_frame, textvariable=self.proxy_var)
        
        # DoH服务器选择
        self.doh_label = ttk.Label(self.settings_frame, text="DoH服务器:")
        self.doh_var = tk.StringVar(value="cloudflare")
        self.doh_combo = ttk.Combobox(self.settings_frame, textvariable=self.doh_var)
        self.doh_combo['values'] = ['cloudflare', 'google', 'quad9']
        self.doh_combo['state'] = 'readonly'
        
        # 控制按钮
        self.control_frame = ttk.Frame(self.root)
        self.start_button = ttk.Button(self.control_frame, text="启动服务", command=self.start_server)
        self.stop_button = ttk.Button(self.control_frame, text="停止服务", command=self.stop_server)
        self.stop_button['state'] = 'disabled'
        
        # 添加赞助按钮
        self.sponsor_button = ttk.Button(
            self.control_frame, 
            text="赞助作者", 
            command=self.show_sponsor_code
        )
        
        # 状态显示
        self.status_frame = ttk.LabelFrame(self.root, text="运行状态", padding=10)
        self.status_text = tk.Text(self.status_frame, height=10, width=50)
        self.status_text.config(state='disabled')
        
        # 统计信息显示
        self.stats_frame = ttk.LabelFrame(self.root, text="统计信息", padding=10)
        self.stats_text = tk.Text(self.stats_frame, height=6, width=50)
        self.stats_text.config(state='disabled')
        
    def _create_layout(self):
        # 设置框架布局
        self.settings_frame.pack(fill='x', padx=10, pady=5)
        
        # 网格布局设置项
        self.ip_label.grid(row=0, column=0, sticky='e', padx=5, pady=2)
        self.ip_entry.grid(row=0, column=1, sticky='w', padx=5, pady=2)
        
        self.port_label.grid(row=0, column=2, sticky='e', padx=5, pady=2)
        self.port_entry.grid(row=0, column=3, sticky='w', padx=5, pady=2)
        
        self.proxy_label.grid(row=1, column=0, sticky='e', padx=5, pady=2)
        self.proxy_entry.grid(row=1, column=1, columnspan=3, sticky='ew', padx=5, pady=2)
        
        self.doh_label.grid(row=2, column=0, sticky='e', padx=5, pady=2)
        self.doh_combo.grid(row=2, column=1, columnspan=3, sticky='ew', padx=5, pady=2)
        
        # 控制按钮布局
        self.control_frame.pack(fill='x', padx=10, pady=5)
        self.start_button.pack(side='left', padx=5)
        self.stop_button.pack(side='left', padx=5)
        self.sponsor_button.pack(side='right', padx=5)
        
        # 状态显示布局
        self.status_frame.pack(fill='both', expand=True, padx=10, pady=5)
        self.status_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # 统计信息布局
        self.stats_frame.pack(fill='x', padx=10, pady=5)
        self.stats_text.pack(fill='both', expand=True, padx=5, pady=5)
        
    def update_status(self, message):
        """更新状态显示"""
        self.status_text.config(state='normal')
        self.status_text.insert('end', message + '\n')
        self.status_text.see('end')
        self.status_text.config(state='disabled')
        
    def update_stats(self):
        """更新统计信息"""
        if self.dns_proxy and self.is_running:
            stats = self.dns_proxy.stats
            stats_text = (
                f"缓存命中: {stats['cache_hits']}\n"
                f"缓存未命中: {stats['cache_misses']}\n"
                f"成功查询: {stats['successful_queries']}\n"
                f"失败查询: {stats['failed_queries']}\n"
                f"错误数: {stats['errors']}\n"
                f"缓存记录数: {len(self.dns_proxy.cache.cache)}"
            )
            self.stats_text.config(state='normal')
            self.stats_text.delete('1.0', 'end')
            self.stats_text.insert('1.0', stats_text)
            self.stats_text.config(state='disabled')
            
            if self.is_running:
                self.root.after(1000, self.update_stats)
        
    def start_server(self):
        """启动服务器"""
        if sys.platform == "win32" and not is_admin():
            messagebox.showerror("错误", "请以管理员权限运行此程序")
            return
            
        try:
            port = int(self.port_var.get())
            self.dns_proxy = DNSBypass(
                listen_ip=self.ip_var.get(),
                listen_port=port,
                proxy=self.proxy_var.get() or None,
                preferred_doh=self.doh_var.get()
            )
            
            # 在新线程中启动服务器
            self.server_thread = threading.Thread(target=self.dns_proxy.start, daemon=True)
            self.server_thread.start()
            
            self.is_running = True
            self.update_status("DNS代理服务器已启动")
            self.update_stats()
            
            # 更新按钮状态
            self.start_button['state'] = 'disabled'
            self.stop_button['state'] = 'normal'
            
            # 禁用设置
            self._toggle_settings(False)
            
        except Exception as e:
            messagebox.showerror("错误", f"启动服务器失败: {str(e)}")
            
    def stop_server(self):
        """停止服务器"""
        if self.dns_proxy:
            self.dns_proxy.stop()
            self.is_running = False
            self.update_status("DNS代理服务器已停止")
            
            # 更新按钮状态
            self.start_button['state'] = 'normal'
            self.stop_button['state'] = 'disabled'
            
            # 启用设置
            self._toggle_settings(True)
            
    def _toggle_settings(self, enabled: bool):
        """切换设置的启用状态"""
        state = 'normal' if enabled else 'disabled'
        self.ip_entry['state'] = state
        self.port_entry['state'] = state
        self.proxy_entry['state'] = state
        self.doh_combo['state'] = 'readonly' if enabled else 'disabled'
        
    def show_sponsor_code(self):
        """显示赞助码"""
        if self.sponsor_image:
            sponsor_window = tk.Toplevel(self.root)
            sponsor_window.title("赞助作者")
            sponsor_window.resizable(False, False)
            
            # 显示图片
            label = ttk.Label(sponsor_window, image=self.sponsor_image)
            label.pack(padx=10, pady=10)
            
            # 添加说明文字
            text_label = ttk.Label(
                sponsor_window, 
                text="感谢您的支持！",
                font=('微软雅黑', 12)
            )
            text_label.pack(pady=5)
            
            # 使窗口居中显示
            sponsor_window.update_idletasks()
            width = sponsor_window.winfo_width()
            height = sponsor_window.winfo_height()
            x = (sponsor_window.winfo_screenwidth() // 2) - (width // 2)
            y = (sponsor_window.winfo_screenheight() // 2) - (height // 2)
            sponsor_window.geometry(f'+{x}+{y}')
        else:
            messagebox.showerror("错误", "赞助码图片未找到")
        
    def run(self):
        """运行GUI程序"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
        
    def on_closing(self):
        """窗口关闭处理"""
        if self.is_running:
            self.stop_server()
        self.root.destroy()

def main():
    app = DNSBypassGUI()
    app.run()

if __name__ == "__main__":
    main() 