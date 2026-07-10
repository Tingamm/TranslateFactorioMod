#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Factorio MOD 汉化工具 - 图形界面版
基于 DeepSeek API，参考 ElyTranslator 设计
功能：选择源文件目录、旧汉化参考目录，批量翻译 cfg 文件
"""

import os
import re
import json
import time
import threading
import configparser
from pathlib import Path
from typing import Dict, List, Optional
import requests

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# ==================== 配置 ====================
CONFIG_FILE = "translator_config.ini"
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"
MAX_TOKENS = 4096
TEMPERATURE = 0.3
BATCH_SIZE = 10
RATE_LIMIT_DELAY = 0.5
# ==============================================


class CfgParser:
    """CFG 文件解析器"""

    @staticmethod
    def parse_file(filepath: str) -> Dict[str, Dict[str, str]]:
        """返回 {段落: {键: 值}}"""
        result = {}
        current_section = ""
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                section_match = re.match(r'^\[(.+)\]$', line)
                if section_match:
                    current_section = section_match.group(1)
                    if current_section not in result:
                        result[current_section] = {}
                    continue
                kv_match = re.match(r'^([^=]+)=(.*)$', line)
                if kv_match:
                    key = kv_match.group(1).strip()
                    value = kv_match.group(2).strip()
                    if current_section:
                        result[current_section][key] = value
                    else:
                        if "_default" not in result:
                            result["_default"] = {}
                        result["_default"][key] = value
        return result

    @staticmethod
    def write_file(filepath: str, data: Dict[str, Dict[str, str]]):
        """将数据写回 cfg 文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            for section, kv_pairs in data.items():
                if section == "_default":
                    for key, value in kv_pairs.items():
                        f.write(f"{key}={value}\n")
                else:
                    f.write(f"[{section}]\n")
                    for key, value in kv_pairs.items():
                        f.write(f"{key}={value}\n")
                    f.write("\n")


class DeepSeekAPIClient:
    """DeepSeek API 客户端"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

    def translate_batch(self, texts: List[str], reference: str = "") -> List[str]:
        """批量翻译"""
        results = []
        total = len(texts)

        for i in range(0, total, BATCH_SIZE):
            batch = texts[i:i+BATCH_SIZE]
            user_content = ""
            if reference:
                user_content += f"以下是已有的翻译参考（请严格遵循其风格、术语和一致性）：\n\n{reference}\n\n"
            user_content += "请将以下英文条目翻译为中文，保持原有格式（如占位符 __1__、[item=...] 等），只返回翻译结果，每行一条，顺序不能乱：\n"
            for idx, text in enumerate(batch):
                user_content += f"{idx+1}. {text}\n"

            payload = {
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": "你是一个专业的游戏本地化翻译专家，擅长将英文游戏文本翻译为中文。要求保持格式标记，术语统一，语言自然。"},
                    {"role": "user", "content": user_content}
                ],
                "max_tokens": MAX_TOKENS,
                "temperature": TEMPERATURE
            }

            try:
                response = requests.post(
                    DEEPSEEK_API_URL,
                    headers=self.headers,
                    json=payload,
                    timeout=60
                )
                response.raise_for_status()
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                lines = content.split('\n')
                translations = []
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    cleaned = re.sub(r'^(\d+)[\.\s]+', '', line)
                    translations.append(cleaned)
                while len(translations) < len(batch):
                    translations.append(batch[len(translations)])
                results.extend(translations[:len(batch)])
                time.sleep(RATE_LIMIT_DELAY)
            except Exception as e:
                results.extend(batch)  # 失败时保留原文

        return results


class TranslatorGUI:
    """主界面"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Factorio MOD 汉化工具 - DeepSeek 版")
        self.root.geometry("800x650")
        self.root.resizable(True, True)

        # 状态变量
        self.source_dir = tk.StringVar()
        self.old_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.api_key = tk.StringVar()
        self.is_running = False

        # API 客户端
        self.client = None

        # 加载配置
        self.load_config()

        # 创建界面
        self.create_widgets()

        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_config(self):
        """加载配置文件"""
        config = configparser.ConfigParser()
        if os.path.exists(CONFIG_FILE):
            try:
                config.read(CONFIG_FILE, encoding='utf-8')
                if 'Settings' in config:
                    self.api_key.set(config['Settings'].get('api_key', ''))
                    self.source_dir.set(config['Settings'].get('source_dir', ''))
                    self.old_dir.set(config['Settings'].get('old_dir', ''))
                    self.output_dir.set(config['Settings'].get('output_dir', ''))
            except Exception:
                pass

    def save_config(self):
        """保存配置文件"""
        config = configparser.ConfigParser()
        config['Settings'] = {
            'api_key': self.api_key.get(),
            'source_dir': self.source_dir.get(),
            'old_dir': self.old_dir.get(),
            'output_dir': self.output_dir.get()
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            config.write(f)

    def create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ===== API 密钥 =====
        api_frame = ttk.LabelFrame(main_frame, text="API 配置", padding="10")
        api_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(api_frame, text="DeepSeek API Key:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        api_entry = ttk.Entry(api_frame, textvariable=self.api_key, width=50, show="*")
        api_entry.grid(row=0, column=1, sticky=tk.W)
        ttk.Button(api_frame, text="显示", command=self.toggle_api_visibility, width=6).grid(row=0, column=2, padx=(5, 0))
        ttk.Label(api_frame, text="获取: platform.deepseek.com", foreground="gray").grid(row=0, column=3, padx=(10, 0))

        # ===== 目录选择 =====
        dir_frame = ttk.LabelFrame(main_frame, text="目录设置", padding="10")
        dir_frame.pack(fill=tk.X, pady=(0, 10))

        # 源文件目录
        ttk.Label(dir_frame, text="英文源文件:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=3)
        ttk.Entry(dir_frame, textvariable=self.source_dir, width=60).grid(row=0, column=1, sticky=tk.W+tk.E, pady=3)
        ttk.Button(dir_frame, text="浏览", command=lambda: self.browse_folder(self.source_dir)).grid(row=0, column=2, padx=(5, 0), pady=3)

        # 旧汉化目录
        ttk.Label(dir_frame, text="旧汉化参考:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=3)
        ttk.Entry(dir_frame, textvariable=self.old_dir, width=60).grid(row=1, column=1, sticky=tk.W+tk.E, pady=3)
        ttk.Button(dir_frame, text="浏览", command=lambda: self.browse_folder(self.old_dir)).grid(row=1, column=2, padx=(5, 0), pady=3)

        # 输出目录
        ttk.Label(dir_frame, text="输出目录:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=3)
        ttk.Entry(dir_frame, textvariable=self.output_dir, width=60).grid(row=2, column=1, sticky=tk.W+tk.E, pady=3)
        ttk.Button(dir_frame, text="浏览", command=lambda: self.browse_folder(self.output_dir)).grid(row=2, column=2, padx=(5, 0), pady=3)

        dir_frame.columnconfigure(1, weight=1)

        # ===== 操作按钮 =====
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        self.start_btn = ttk.Button(btn_frame, text="开始翻译", command=self.start_translation, width=15)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_btn = ttk.Button(btn_frame, text="停止", command=self.stop_translation, width=10, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT)

        ttk.Button(btn_frame, text="保存配置", command=self.save_config, width=10).pack(side=tk.RIGHT, padx=(0, 5))
        ttk.Button(btn_frame, text="清空日志", command=self.clear_log, width=10).pack(side=tk.RIGHT)

        # ===== 进度条 =====
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X)

        self.status_label = ttk.Label(progress_frame, text="就绪", anchor=tk.W)
        self.status_label.pack(fill=tk.X, pady=(5, 0))

        # ===== 日志输出 =====
        log_frame = ttk.LabelFrame(main_frame, text="日志", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 配置日志颜色
        self.log_text.tag_config("info", foreground="black")
        self.log_text.tag_config("success", foreground="green")
        self.log_text.tag_config("warning", foreground="orange")
        self.log_text.tag_config("error", foreground="red")

        self.log("欢迎使用 Factorio MOD 汉化工具！", "info")

    def browse_folder(self, var):
        """浏览文件夹"""
        folder = filedialog.askdirectory()
        if folder:
            var.set(folder)

    def toggle_api_visibility(self):
        """切换 API Key 显示/隐藏"""
        current = self.api_entry.cget("show")
        self.api_entry.config(show="" if current == "*" else "*")

    def log(self, message: str, level: str = "info"):
        """添加日志"""
        self.log_text.insert(tk.END, f"{message}\n", level)
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        self.log("日志已清空", "info")

    def set_status(self, text: str):
        """设置状态栏"""
        self.status_label.config(text=text)
        self.root.update_idletasks()

    def set_progress(self, value: float):
        """设置进度"""
        self.progress_var.set(value)
        self.root.update_idletasks()

    def extract_mod_name(self, filename: str) -> str:
        """提取模组名（忽略版本号）"""
        m = re.match(r'^(.*)_(\d+\.\d+\.\d+)(?:-.*)?\.cfg$', filename)
        if m:
            return m.group(1)
        return filename.replace('.cfg', '')

    def start_translation(self):
        """开始翻译"""
        # 验证输入
        if not self.api_key.get().strip():
            messagebox.showerror("错误", "请输入 DeepSeek API Key")
            return
        if not os.path.exists(self.source_dir.get()):
            messagebox.showerror("错误", "英文源文件目录不存在")
            return
        if not self.output_dir.get():
            messagebox.showerror("错误", "请选择输出目录")
            return

        # 创建输出目录
        Path(self.output_dir.get()).mkdir(parents=True, exist_ok=True)

        # 保存配置
        self.save_config()

        # 禁用按钮
        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.set_progress(0)
        self.log("=" * 60, "info")
        self.log("开始翻译任务", "info")

        # 在新线程中执行
        thread = threading.Thread(target=self.translation_worker, daemon=True)
        thread.start()

    def stop_translation(self):
        """停止翻译"""
        self.is_running = False
        self.log("正在停止...", "warning")
        self.stop_btn.config(state=tk.DISABLED)

    def translation_worker(self):
        """翻译工作线程"""
        try:
            source_dir = self.source_dir.get()
            old_dir = self.old_dir.get()
            output_dir = self.output_dir.get()

            # 初始化 API 客户端
            self.client = DeepSeekAPIClient(self.api_key.get().strip())

            # 1. 加载旧汉化（按模组名分组）
            self.log("加载旧汉化参考...", "info")
            old_groups = {}
            old_cache = {}
            if os.path.exists(old_dir):
                for cfg_file in Path(old_dir).glob("*.cfg"):
                    mod_name = self.extract_mod_name(cfg_file.name)
                    old_groups.setdefault(mod_name, []).append(cfg_file)
                    try:
                        old_cache[str(cfg_file)] = CfgParser.parse_file(str(cfg_file))
                    except Exception as e:
                        self.log(f"  加载失败 {cfg_file.name}: {e}", "warning")
                self.log(f"  加载了 {len(old_groups)} 个模组的旧翻译", "success")
            else:
                self.log("  未找到旧汉化目录，将直接翻译", "warning")

            # 2. 获取源文件
            source_files = list(Path(source_dir).glob("*.cfg"))
            if not source_files:
                self.log("错误：源目录中没有 cfg 文件", "error")
                return

            self.log(f"找到 {len(source_files)} 个源文件", "info")

            # 3. 逐个处理
            total = len(source_files)
            for idx, src_file in enumerate(source_files):
                if not self.is_running:
                    self.log("用户已停止", "warning")
                    break

                mod_name = self.extract_mod_name(src_file.name)
                self.set_status(f"处理: {src_file.name}")
                self.set_progress((idx / total) * 100)

                # 构建参考文本
                ref_text = ""
                if mod_name in old_groups:
                    ref_text = self.build_reference_text(old_groups[mod_name], old_cache)
                    self.log(f"[{idx+1}/{total}] {src_file.name} (有参考: {mod_name})", "info")
                else:
                    self.log(f"[{idx+1}/{total}] {src_file.name} (无参考)", "info")

                # 处理文件
                self.process_file(src_file, output_dir, ref_text)

            self.set_progress(100)
            self.set_status("完成")
            self.log("=" * 60, "info")
            self.log("翻译任务完成！", "success")

        except Exception as e:
            self.log(f"发生错误: {e}", "error")
            import traceback
            self.log(traceback.format_exc(), "error")
        finally:
            self.is_running = False
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)

    def build_reference_text(self, file_paths: List[Path], cache: Dict) -> str:
        """合并参考文本"""
        lines = []
        for fp in file_paths:
            lines.append(f"# from: {fp.name}")
            data = cache.get(str(fp))
            if not data:
                continue
            for section, kv_pairs in data.items():
                if section != "_default":
                    lines.append(f"[{section}]")
                for key, value in kv_pairs.items():
                    lines.append(f"{key}={value}")
                if section != "_default":
                    lines.append("")
            lines.append("")
        return "\n".join(lines)

    def process_file(self, src_path: Path, output_dir: str, ref_text: str):
        """处理单个文件"""
        try:
            src_data = CfgParser.parse_file(str(src_path))
            entries = []
            for section, kv_pairs in src_data.items():
                for key, value in kv_pairs.items():
                    entries.append((section, key, value))

            if not entries:
                return

            english_texts = [entry[2] for entry in entries]
            translations = self.client.translate_batch(english_texts, ref_text)

            for i, (section, key, _) in enumerate(entries):
                if i < len(translations):
                    src_data[section][key] = translations[i]

            out_path = Path(output_dir) / src_path.name
            CfgParser.write_file(str(out_path), src_data)
            self.log(f"  已保存: {out_path.name}", "success")

        except Exception as e:
            self.log(f"  处理失败: {e}", "error")

    def on_closing(self):
        """关闭窗口"""
        if self.is_running:
            if not messagebox.askokcancel("确认", "翻译正在进行中，确定要退出吗？"):
                return
        self.save_config()
        self.root.destroy()


def main():
    app = TranslatorGUI()
    app.root.mainloop()


if __name__ == "__main__":
    main()