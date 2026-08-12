import tkinter as tk
from tkinter import scrolledtext, ttk, filedialog
from DrissionPage import ChromiumPage
import threading
import time
import sys
import datetime
from urllib.parse import urlparse
import pandas as pd
import os

class DouyinNicknameExtractor:
    def __init__(self, root):
        # 设置中文字体支持
        self.font_config = ('Microsoft YaHei', 10)
        
        # 初始化主窗口
        self.root = root
        self.root.title("抖音昵称提取器")
        self.root.geometry("700x550")
        self.root.resizable(True, True)
        
        # 设置窗口图标（可选）
        # self.root.iconbitmap("icon.ico")
        
        # 创建主框架
        self.main_frame = ttk.Frame(root, padding=(10, 10, 10, 10))
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建URL输入区域
        self.create_url_input_area()
        
        # 创建结果显示区域
        self.create_result_area()
        
        # 创建日志区域
        self.create_log_area()
        
        # 创建状态栏
        self.create_status_bar()
        
        # 初始化浏览器
        self.dp = None
        self.is_running = False
        self.stop_event = threading.Event()
    
    def create_url_input_area(self):
        """创建URL输入区域"""
        input_frame = ttk.LabelFrame(self.main_frame, text="抖音视频URL (每行一个)", padding=(10, 5, 10, 5))
        input_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.url_text = scrolledtext.ScrolledText(input_frame, font=self.font_config, wrap=tk.WORD, height=6)
        self.url_text.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=(0, 10), pady=(0, 5))
        self.url_text.insert(tk.END, "https://v.douyin.com/")  # 默认URL前缀
        
        # 创建按钮框架
        button_frame = ttk.Frame(input_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.start_button = ttk.Button(button_frame, text="开始批量抓取", command=self.start_extraction)
        self.start_button.pack(side=tk.RIGHT)
        
        self.export_button = ttk.Button(button_frame, text="导出到Excel", command=self.export_to_excel)
        self.export_button.pack(side=tk.RIGHT, padx=(0, 10))
        self.export_button.config(state=tk.DISABLED)
        
        self.stop_button = ttk.Button(button_frame, text="停止", command=self.stop_extraction)
        self.stop_button.pack(side=tk.RIGHT, padx=(0, 10))
        self.stop_button.config(state=tk.DISABLED)
    
    def create_result_area(self):
        """创建结果显示区域"""
        result_frame = ttk.LabelFrame(self.main_frame, text="提取结果", padding=(10, 5, 10, 5))
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 创建表格视图
        columns = ('index', 'url', 'nickname', 'status')
        self.result_tree = ttk.Treeview(result_frame, columns=columns, show='headings')
        
        # 定义列宽和标题
        self.result_tree.heading('index', text='序号')
        self.result_tree.column('index', width=50, anchor='center')
        
        self.result_tree.heading('url', text='抖音URL')
        self.result_tree.column('url', width=300, anchor='w')
        
        self.result_tree.heading('nickname', text='昵称')
        self.result_tree.column('nickname', width=150, anchor='w')
        
        self.result_tree.heading('status', text='状态')
        self.result_tree.column('status', width=100, anchor='center')
        
        # 添加垂直滚动条
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        self.result_tree.configure(yscroll=scrollbar.set)
        
        # 布局
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_tree.pack(fill=tk.BOTH, expand=True)
        
        # 存储结果数据
        self.results_data = []
    
    def create_log_area(self):
        """创建日志显示区域"""
        log_frame = ttk.LabelFrame(self.main_frame, text="抓取日志", padding=(10, 5, 10, 5))
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, font=self.font_config, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
    
    def create_status_bar(self):
        """创建状态栏"""
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def log(self, message):
        """向日志区域添加消息"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def update_result(self, index, url, nickname, status):
        """更新结果表格"""
        # 添加新行（不检查重复）
        self.result_tree.insert('', tk.END, values=(index, url, nickname, status))
        # 添加到数据列表
        self.results_data.append({'index': index, 'url': url, 'nickname': nickname, 'status': status})
        
        # 如果有结果，启用导出按钮
        if self.results_data and not self.is_running:
            self.export_button.config(state=tk.NORMAL)
    
    def update_status(self, status):
        """更新状态栏"""
        self.status_var.set(status)
    
    def start_extraction(self):
        """开始批量提取昵称"""
        if self.is_running:
            return
        
        # 获取所有URL
        urls_text = self.url_text.get(1.0, tk.END).strip()
        if not urls_text:
            self.log("错误：请输入至少一个URL")
            return
        
        # 解析URL列表
        raw_urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        
        # 提取并验证URL
        valid_urls = []
        for raw_url in raw_urls:
            # 提取HTTP地址
            import re
            # 匹配HTTP/HTTPS地址
            url_match = re.search(r'https?://[\w\-._~:/?#[\]@!$&\'()*+,;=.]+', raw_url)
            
            if url_match:
                extracted_url = url_match.group(0)
                valid_urls.append(extracted_url)
                if extracted_url != raw_url:
                    self.log(f"已从输入中提取URL: {extracted_url}")
            else:
                self.log(f"警告：无法从输入 '{raw_url}' 中提取有效URL，已跳过")
        
        if not valid_urls:
            self.log("错误：没有有效的URL")
            return
        
        # 存储原始输入顺序的URL列表
        self.original_urls = valid_urls
        
        # 检测重复URL，创建映射表
        seen_urls = set()
        unique_urls = []
        
        for url in valid_urls:
            if url not in seen_urls:
                seen_urls.add(url)
                unique_urls.append(url)
        
        # 记录重复URL信息
        duplicate_count = len(valid_urls) - len(unique_urls)
        if duplicate_count > 0:
            self.log(f"检测到 {duplicate_count} 个重复URL，将自动跳过抓取")
        
        # 禁用开始按钮，启用停止按钮
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.export_button.config(state=tk.DISABLED)
        
        # 清空结果和日志
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        self.results_data = []
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # 更新状态
        self.update_status(f"正在批量提取昵称... 共{len(unique_urls)}个唯一URL")
        self.log(f"开始批量处理，共{len(unique_urls)}个唯一URL")
        
        # 在新线程中执行批量提取操作
        self.is_running = True
        self.stop_event.clear()
        self.extraction_thread = threading.Thread(target=self.batch_extract_nickname, args=(unique_urls,))
        self.extraction_thread.daemon = True
        self.extraction_thread.start()
    
    def stop_extraction(self):
        """停止提取操作"""
        if not self.is_running:
            return
        
        self.log("正在停止提取操作...")
        self.stop_event.set()
        
        # 等待线程结束
        if self.extraction_thread.is_alive():
            self.extraction_thread.join(timeout=5.0)  # 等待最多5秒
        
        # 清理浏览器资源
        self.cleanup_browser()
        
        # 更新UI状态
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.update_status("已停止")
        self.log("提取操作已停止")
    
    def batch_extract_nickname(self, urls):
        """批量提取多个URL的昵称"""
        try:
            # 初始化浏览器
            self.dp = ChromiumPage()
            self.log("浏览器已启动")
            
            total_urls = len(urls)
            success_count = 0
            
            # 为每个URL提取昵称
            for index, url in enumerate(urls, 1):
                if self.stop_event.is_set():
                    break
                
                # 更新状态
                self.update_status(f"正在处理URL {index}/{total_urls}")
                self.log(f"开始处理URL {index}/{total_urls}: {url}")
                
                # 提取昵称（带超时控制）
                try:
                    # 记录开始时间
                    url_start_time = time.time()
                    max_url_time = 60  # 每个URL的最大处理时间（秒）
                    
                    # 创建一个线程来执行提取操作
                    import threading
                    result = [None]
                    error = [None]
                    
                    def extract_task():
                        try:
                            result[0] = self._extract_single_nickname(url)
                        except Exception as e:
                            error[0] = e
                    
                    thread = threading.Thread(target=extract_task)
                    thread.daemon = True
                    thread.start()
                    
                    # 等待线程完成或超时
                    thread.join(max_url_time)
                    
                    # 检查是否超时
                    if thread.is_alive():
                        # 超时，跳过该URL
                        self.log(f"URL {index}/{total_urls} 处理超时，跳过该地址")
                        self.root.after(0, lambda idx=index, u=url: 
                                      self.update_result(idx, u, "", "超时"))
                    else:
                        # 检查是否有错误
                        if error[0]:
                            error_msg = str(error[0])
                            self.log(f"URL {index}/{total_urls} 处理出错: {error_msg}")
                            self.root.after(0, lambda idx=index, u=url: 
                                          self.update_result(idx, u, "", "出错"))
                        else:
                            nickname = result[0]
                            if nickname:
                                success_count += 1
                                status = "成功"
                                self.log(f"URL {index}/{total_urls} 提取成功: {nickname}")
                            else:
                                status = "失败"
                                nickname = ""  # 未找到昵称时设为空
                                self.log(f"URL {index}/{total_urls} 提取失败: 未找到昵称")
                            
                            # 更新结果
                            self.root.after(0, lambda idx=index, u=url, n=nickname, s=status: 
                                          self.update_result(idx, u, n, s))
                    
                except Exception as e:
                    error_msg = str(e)
                    self.log(f"URL {index}/{total_urls} 处理出错: {error_msg}")
                    self.root.after(0, lambda idx=index, u=url: 
                                  self.update_result(idx, u, "", "出错"))
                
                # 处理完成后短暂休息
                if index < total_urls and not self.stop_event.is_set():
                    self.log(f"准备处理下一个URL，等待2秒...")
                    time.sleep(2)  # 避免请求过于频繁
            
            # 完成后更新状态
            if not self.stop_event.is_set():
                self.log(f"批量处理完成，共{total_urls}个URL，成功{success_count}个")
                self.update_status(f"批量处理完成，成功{success_count}/{total_urls}")
        except Exception as e:
            error_msg = f"批量提取过程中发生错误: {str(e)}"
            self.log(error_msg)
            self.update_status("批量处理出错")
        finally:
            # 清理资源
            self.cleanup_browser()
            
            # 更新UI状态
            self.root.after(0, self._finalize_extraction)
    
    def _extract_single_nickname(self, url):
        """提取单个URL的昵称"""
        start_time = time.time()
        max_time = 60  # 最大抓取时间（秒）
        
        try:
            # 重置监听
            if hasattr(self.dp, 'listen'):
                try:
                    self.dp.listen.stop()
                except:
                    pass
            
            # 开始监听所有请求
            self.dp.listen.start('')
            self.log("开始监听所有请求")
            
            # 访问目标URL
            self.dp.get(url)
            self.log(f"已访问URL: {url}")
            
            info_url = None
            nickname = None
            
            # 循环获取匹配的请求
            timeout_count = 0
            max_timeout = 5  # 最大超时次数
            
            while not self.stop_event.is_set() and timeout_count < max_timeout:
                # 检查是否超时
                if time.time() - start_time > max_time:
                    self.log("抓取超时，跳过该地址")
                    return None
                
                try:
                    resp = self.dp.listen.wait(timeout=5)
                    if resp:
                        tmp_url = resp.request.url
                        self.log(f"捕获到请求: {tmp_url}")
                        
                        # 尝试从响应中提取昵称
                        try:
                            resp_data = resp.response.body
                            if isinstance(resp_data, dict):
                                # 尝试从不同路径提取昵称
                                if 'aweme_detail' in resp_data:
                                    nickname = resp_data.get('aweme_detail', {}).get('author', {}).get('nickname', '')
                                elif 'author' in resp_data:
                                    nickname = resp_data.get('author', {}).get('nickname', '')
                                
                                if nickname:
                                    self.log(f"成功提取昵称: {nickname}")
                                    return nickname
                        except Exception as e:
                            self.log(f"解析响应数据时出错: {str(e)}")
                except TimeoutError:
                    timeout_count += 1
                    if self.stop_event.is_set():
                        break
                    self.log(f"等待请求中... ({timeout_count}/{max_timeout})")
                    continue
                except Exception as e:
                    self.log(f"监听请求时出错: {str(e)}")
                    if self.stop_event.is_set():
                        break
                    continue
            
            # 检查是否超时
            if time.time() - start_time > max_time:
                self.log("抓取超时，跳过该地址")
                return None
            
            # 如果没有获取到昵称，尝试从页面直接提取
            if not nickname and not self.stop_event.is_set():
                self.log("尝试从页面直接提取昵称")
                try:
                    # 尝试不同的选择器提取昵称
                    selectors = [
                        'h1.GMEdHsXq',  # 页面标题中的昵称
                        '.GMEdHsXq',    # 页面标题中的昵称
                        '.user-info .nickname',
                        '.author-info .nickname',
                        '.user-name',
                        '.nickname'
                    ]
                    
                    for selector in selectors:
                        self.log(f"尝试选择器: {selector}")
                        elements = self.dp.ele(selector, timeout=3)
                        if elements:
                            nickname = elements.text.strip()
                            if nickname:
                                self.log(f"从页面提取昵称成功: {nickname}")
                                return nickname
                    
                    # 如果所有选择器都失败，尝试从页面源码中提取
                    self.log("尝试从页面源码中提取昵称")
                    page_source = self.dp.page_source
                    import re
                    # 匹配h1标签中的昵称
                    h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', page_source, re.DOTALL)
                    if h1_match:
                        h1_content = h1_match.group(1)
                        # 去除HTML标签
                        clean_content = re.sub(r'<[^>]+>', '', h1_content).strip()
                        if clean_content:
                            self.log(f"从页面源码提取昵称成功: {clean_content}")
                            return clean_content
                except Exception as e:
                    self.log(f"从页面提取昵称时出错: {str(e)}")
            
            self.log("未提取到昵称或已超时")
            return None
        except Exception as e:
            self.log(f"提取昵称时出错: {str(e)}")
            return None
    

    
    def cleanup_browser(self):
        """清理浏览器资源"""
        try:
            if hasattr(self, 'dp') and self.dp:
                self.log("正在关闭浏览器...")
                try:
                    self.dp.listen.stop()
                except:
                    pass
                self.dp.quit()
                self.dp = None
                self.log("浏览器已关闭")
        except Exception as e:
            self.log(f"关闭浏览器时出错: {str(e)}")

    def export_to_excel(self):
        """将结果导出到Excel文件"""
        if not self.results_data:
            self.log("没有数据可导出")
            return
        
        try:
            # 创建DataFrame
            df = pd.DataFrame(self.results_data)
            
            # 选择需要导出的列
            df = df[['index', 'url', 'nickname', 'status']]
            
            # 重命名列名
            df.columns = ['序号', '抖音URL', '昵称', '状态']
            
            # 打开文件对话框让用户选择保存路径
            current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"抖音昵称提取结果_{current_time}.xlsx"
            
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                initialfile=default_filename
            )
            
            if not file_path:
                self.log("导出已取消")
                return
            
            # 导出到Excel
            df.to_excel(file_path, index=False)
            
            self.log(f"数据已成功导出到: {file_path}")
            self.update_status(f"导出成功: {os.path.basename(file_path)}")
        except Exception as e:
            error_msg = f"导出Excel时出错: {str(e)}"
            self.log(error_msg)
            self.update_status("导出失败")

    def _finalize_extraction(self):
        """提取完成后的UI清理工作"""
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.update_status("就绪")
        
        # 按照原始输入顺序重新构建结果
        if hasattr(self, 'original_urls') and self.original_urls:
            self.log("按照原始输入顺序重新构建结果...")
            
            # 创建URL到昵称的映射
            url_to_nickname = {item['url']: item['nickname'] for item in self.results_data}
            
            # 清空当前结果
            for item in self.result_tree.get_children():
                self.result_tree.delete(item)
            self.results_data = []
            
            # 按照原始顺序处理每个URL
            for index, url in enumerate(self.original_urls, 1):
                if url in url_to_nickname:
                    nickname = url_to_nickname[url]
                    # 检查是否为重复URL（在原始列表中出现次数大于1）
                    is_duplicate = self.original_urls.count(url) > 1
                    status = "重复" if (is_duplicate and nickname) else ("重复-无昵称" if is_duplicate else "成功")
                else:
                    nickname = ""
                    status = "失败"
                
                # 添加到结果
                self.results_data.append({'index': index, 'url': url, 'nickname': nickname, 'status': status})
                
                # 更新UI
                self.root.after(0, lambda idx=index, u=url, n=nickname, s=status: 
                              self.result_tree.insert('', tk.END, values=(idx, u, n, s)))
            
            self.log("已按照原始输入顺序重新构建结果")
        
        self.log("提取操作已完成")
        
        # 如果有结果，启用导出按钮
        if self.results_data:
            self.export_button.config(state=tk.NORMAL)

if __name__ == "__main__":
    # 创建主窗口
    root = tk.Tk()
    
    # 设置中文字体支持
    default_font = ('Microsoft YaHei', 10)
    text_font = ('Microsoft YaHei', 10)
    
    # 应用字体配置
    root.option_add("*Font", default_font)
    root.option_add("*Text.Font", text_font)
    root.option_add("*Entry.Font", text_font)
    root.option_add("*ScrolledText.Font", text_font)
    
    # 创建应用实例
    app = DouyinNicknameExtractor(root)
    
    # 处理窗口关闭事件
    def on_closing():
        app.stop_extraction()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # 启动主循环
    root.mainloop()
