#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Factorio MOD 汉化工具 - 图形界面版
基于 DeepSeek API，参考 ElyTranslator 设计
功能：选择源文件目录、旧汉化参考目录，批量翻译 cfg 文件
"""

import os
import re
import time
import threading
import configparser
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
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
    @staticmethod
    def parse_file(filepath: str) -> Dict[str, Dict[str, str]]:
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
    def __init__(self, api_key: str, simulate: bool = False):
        self.api_key = api_key
        self.simulate = simulate
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

    def translate_batch(self, texts: List[str], reference: str = "") -> List[str]:
        if self.simulate:
            return [f"[模拟] {text}" for text in texts]

        results = []
        total = len(texts)
        for i in range(0, total, BATCH_SIZE):
            batch = texts[i:i+BATCH_SIZE]
            system_prompt = (
                "你是一位资深的游戏本地化专家，精通中英文游戏术语翻译，尤其擅长 Factorio（异星工厂）模组内容的本地化。\n"
                "你的任务是：将给定的英文游戏文本翻译为自然、准确的中文，同时严格遵守以下规则：\n"
                "1. **保留所有格式标记**：如 `__数字__`（占位符）、`[item=...]`、`[technology=...]`、`[entity=...]` 等，原样不动。\n"
                "2. **术语统一**：若提供了参考翻译，必须遵循其中的术语和风格；无参考时，使用 Factorio 官方中文版常见译法（如 \"iron plate\" → \"铁板\"、\"assembling machine\" → \"组装机\"）。\n"
                "3. **语言风格**：保持科技感、工业感，简洁直接，避免过度修饰或口语化。\n"
                "4. **输出规范**：只返回翻译后的文本，每行一条，不加序号、括号或任何额外注释。"
            )
            user_content = "请将以下英文游戏文本翻译为中文，严格遵循上述要求。\n"
            if reference:
                user_content += f"参考翻译（请保持术语一致）：\n{reference}\n\n"
            user_content += "待翻译条目（按顺序逐行输出翻译结果）：\n"
            for idx, text in enumerate(batch):
                user_content += f"{idx+1}. {text}\n"

            payload = {
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                "max_tokens": MAX_TOKENS,
                "temperature": TEMPERATURE
            }
            try:
                response = requests.post(DEEPSEEK_API_URL, headers=self.headers, json=payload, timeout=60)
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
                results.extend(batch)
        return results


class TranslatorGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Factorio MOD 汉化工具 - DeepSeek 版")
        self.root.geometry("800x650")
        self.root.resizable(True, True)

        self.source_dir = tk.StringVar()
        self.old_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.api_key = tk.StringVar()
        self.test_mode = tk.BooleanVar(value=False)
        self.is_running = False
        self.client = None

        self.load_config()
        self.create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_config(self):
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
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # API 配置
        api_frame = ttk.LabelFrame(main_frame, text="API 配置", padding="10")
        api_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(api_frame, text="DeepSeek API Key:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.api_entry = ttk.Entry(api_frame, textvariable=self.api_key, width=50, show="*")
        self.api_entry.grid(row=0, column=1, sticky=tk.W)
        ttk.Button(api_frame, text="显示", command=self.toggle_api_visibility, width=6).grid(row=0, column=2, padx=(5, 0))
        ttk.Label(api_frame, text="获取: platform.deepseek.com", foreground="gray").grid(row=0, column=3, padx=(10, 0))

        # 目录设置
        dir_frame = ttk.LabelFrame(main_frame, text="目录设置", padding="10")
        dir_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(dir_frame, text="英文源文件:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=3)
        ttk.Entry(dir_frame, textvariable=self.source_dir, width=60).grid(row=0, column=1, sticky=tk.W+tk.E, pady=3)
        ttk.Button(dir_frame, text="浏览", command=lambda: self.browse_folder(self.source_dir)).grid(row=0, column=2, padx=(5, 0), pady=3)
        ttk.Label(dir_frame, text="旧汉化参考:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=3)
        ttk.Entry(dir_frame, textvariable=self.old_dir, width=60).grid(row=1, column=1, sticky=tk.W+tk.E, pady=3)
        ttk.Button(dir_frame, text="浏览", command=lambda: self.browse_folder(self.old_dir)).grid(row=1, column=2, padx=(5, 0), pady=3)
        ttk.Label(dir_frame, text="输出目录:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=3)
        ttk.Entry(dir_frame, textvariable=self.output_dir, width=60).grid(row=2, column=1, sticky=tk.W+tk.E, pady=3)
        ttk.Button(dir_frame, text="浏览", command=lambda: self.browse_folder(self.output_dir)).grid(row=2, column=2, padx=(5, 0), pady=3)
        dir_frame.columnconfigure(1, weight=1)

        # 操作按钮 + 测试模式
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Checkbutton(btn_frame, text="测试模式（模拟翻译，不调用API）", variable=self.test_mode).pack(side=tk.LEFT, padx=(0, 10))

        self.start_btn = ttk.Button(btn_frame, text="开始翻译", command=self.start_translation, width=15)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_btn = ttk.Button(btn_frame, text="停止", command=self.stop_translation, width=10, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT)

        ttk.Button(btn_frame, text="保存配置", command=self.save_config, width=10).pack(side=tk.RIGHT, padx=(0, 5))
        ttk.Button(btn_frame, text="清空日志", command=self.clear_log, width=10).pack(side=tk.RIGHT)

        # 进度条
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X)
        self.status_label = ttk.Label(progress_frame, text="就绪", anchor=tk.W)
        self.status_label.pack(fill=tk.X, pady=(5, 0))

        # 日志
        log_frame = ttk.LabelFrame(main_frame, text="日志", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.tag_config("info", foreground="black")
        self.log_text.tag_config("success", foreground="green")
        self.log_text.tag_config("warning", foreground="orange")
        self.log_text.tag_config("error", foreground="red")
        self.log("欢迎使用 Factorio MOD 汉化工具！", "info")

    def browse_folder(self, var):
        folder = filedialog.askdirectory()
        if folder:
            var.set(folder)

    def toggle_api_visibility(self):
        current = self.api_entry.cget("show")
        self.api_entry.config(show="" if current == "*" else "*")

    def log(self, message: str, level: str = "info"):
        self.log_text.insert(tk.END, f"{message}\n", level)
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def clear_log(self):
        self.log_text.delete(1.0, tk.END)
        self.log("日志已清空", "info")

    def set_status(self, text: str):
        self.status_label.config(text=text)
        self.root.update_idletasks()

    def set_progress(self, value: float):
        self.progress_var.set(value)
        self.root.update_idletasks()

    # ===== 工具方法 =====
    def extract_mod_info(self, filename: str) -> Tuple[str, Optional[str]]:
        m = re.match(r'^(.*)_(\d+\.\d+\.\d+)(?:-.*)?\.cfg$', filename)
        if m:
            return m.group(1), m.group(2)
        return filename.replace('.cfg', ''), None

    def extract_mod_name(self, filename: str) -> str:
        return self.extract_mod_info(filename)[0]

    # ===== 加载旧汉化 =====
    def load_old_translations(self, old_dir: str):
        old_groups = {}
        old_by_mod_version = {}
        old_cache = {}
        if os.path.exists(old_dir):
            for cfg_file in Path(old_dir).glob("*.cfg"):
                mod_name, version = self.extract_mod_info(cfg_file.name)
                old_groups.setdefault(mod_name, []).append(cfg_file)
                if version is not None:
                    old_by_mod_version[(mod_name, version)] = str(cfg_file)
                try:
                    old_cache[str(cfg_file)] = CfgParser.parse_file(str(cfg_file))
                except Exception as e:
                    self.log(f"  加载失败 {cfg_file.name}: {e}", "warning")
            self.log(f"  加载了 {len(old_groups)} 个模组的旧翻译", "success")
            self.log(f"  可精确匹配版本的文件数: {len(old_by_mod_version)}", "info")
        else:
            self.log("  未找到旧汉化目录，将直接翻译", "warning")
        return old_groups, old_by_mod_version, old_cache

    # ===== 对比选择对话框（区分复制/翻译计数） =====
    def compare_and_select(self, source_files: List[Path], old_by_mod_version: Dict, old_groups: Dict) -> List[Tuple[Path, str]]:
        file_info = []
        for src_file in source_files:
            mod, ver = self.extract_mod_info(src_file.name)
            match_key = (mod, ver) if ver is not None else None
            has_exact_match = match_key is not None and match_key in old_by_mod_version
            has_ref = mod in old_groups
            status = "已匹配（可复制）" if has_exact_match else "需要翻译"
            default_copy = has_exact_match
            default_translate = not has_exact_match
            file_info.append((src_file, status, has_ref, default_copy, default_translate))

        dialog = tk.Toplevel(self.root)
        dialog.title("对比结果 - 请选择处理方式")
        dialog.geometry("780x480")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="对于每个文件，选择“复制”或“翻译”（互斥），可都不选以跳过。",
                  foreground="blue").pack(pady=2)
        ttk.Label(dialog, text="“复制”表示直接使用旧汉化，“翻译”表示调用 API 重新翻译。").pack(pady=2)

        frame = ttk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        columns = ("复制", "翻译", "文件名", "状态", "有参考")
        tree = ttk.Treeview(frame, columns=columns, show="headings", yscrollcommand=scrollbar.set)
        tree.heading("复制", text="复制")
        tree.heading("翻译", text="翻译")
        tree.heading("文件名", text="文件名")
        tree.heading("状态", text="状态")
        tree.heading("有参考", text="有参考")
        tree.column("复制", width=60, anchor=tk.CENTER)
        tree.column("翻译", width=60, anchor=tk.CENTER)
        tree.column("文件名", width=280, anchor=tk.W)
        tree.column("状态", width=160, anchor=tk.W)
        tree.column("有参考", width=80, anchor=tk.CENTER)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=tree.yview)

        copy_flags = {}
        translate_flags = {}
        for i, (src_file, status, has_ref, default_copy, default_translate) in enumerate(file_info):
            item = tree.insert("", tk.END, values=("", "", src_file.name, status, "是" if has_ref else "否"), iid=str(i))
            copy_flags[item] = tk.BooleanVar(value=default_copy)
            translate_flags[item] = tk.BooleanVar(value=default_translate)
            if default_copy:
                tree.set(item, "复制", "✔")
            if default_translate:
                tree.set(item, "翻译", "✔")

        # 计数标签（区分复制和翻译）
        count_label = ttk.Label(dialog, text="已选择: 复制 0 个，翻译 0 个 (共 0 个)")
        count_label.pack(pady=5)

        def update_selected_count():
            copy_count = sum(1 for item in copy_flags if copy_flags[item].get())
            trans_count = sum(1 for item in translate_flags if translate_flags[item].get())
            total = copy_count + trans_count
            count_label.config(text=f"已选择: 复制 {copy_count} 个，翻译 {trans_count} 个 (共 {total} 个)")

        def toggle_copy(item):
            new_val = not copy_flags[item].get()
            copy_flags[item].set(new_val)
            tree.set(item, "复制", "✔" if new_val else "")
            if new_val:
                translate_flags[item].set(False)
                tree.set(item, "翻译", "")
            update_selected_count()

        def toggle_translate(item):
            new_val = not translate_flags[item].get()
            translate_flags[item].set(new_val)
            tree.set(item, "翻译", "✔" if new_val else "")
            if new_val:
                copy_flags[item].set(False)
                tree.set(item, "复制", "")
            update_selected_count()

        def on_tree_click(event):
            region = tree.identify_region(event.x, event.y)
            if region == "cell":
                column = tree.identify_column(event.x)
                item = tree.identify_row(event.y)
                if not item:
                    return
                if column == "#1":  # 复制列
                    toggle_copy(item)
                elif column == "#2":  # 翻译列
                    toggle_translate(item)

        tree.bind("<Button-1>", on_tree_click)

        def select_all():
            for i, (_, _, _, default_copy, default_translate) in enumerate(file_info):
                item = str(i)
                copy_flags[item].set(default_copy)
                translate_flags[item].set(default_translate)
                tree.set(item, "复制", "✔" if default_copy else "")
                tree.set(item, "翻译", "✔" if default_translate else "")
            update_selected_count()

        def select_none():
            for item in copy_flags:
                copy_flags[item].set(False)
                translate_flags[item].set(False)
                tree.set(item, "复制", "")
                tree.set(item, "翻译", "")
            update_selected_count()

        result = []

        def on_ok():
            nonlocal result
            result = []
            for i, (src_file, _, _, _, _) in enumerate(file_info):
                item = str(i)
                if copy_flags[item].get():
                    result.append((src_file, "copy"))
                elif translate_flags[item].get():
                    result.append((src_file, "translate"))
            dialog.destroy()

        def on_cancel():
            nonlocal result
            result = []
            dialog.destroy()

        # 按钮布局：全选、全不选在左，确认、取消在右
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, pady=10, padx=10)

        left_btn_frame = ttk.Frame(button_frame)
        left_btn_frame.pack(side=tk.LEFT)
        ttk.Button(left_btn_frame, text="全选", command=select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(left_btn_frame, text="全不选", command=select_none).pack(side=tk.LEFT, padx=5)

        right_btn_frame = ttk.Frame(button_frame)
        right_btn_frame.pack(side=tk.RIGHT)
        ttk.Button(right_btn_frame, text="确认", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(right_btn_frame, text="取消", command=on_cancel).pack(side=tk.LEFT, padx=5)

        update_selected_count()  # 初始化计数
        self.root.wait_window(dialog)
        return result

    # ===== 开始翻译 =====
    def start_translation(self):
        if not self.test_mode.get() and not self.api_key.get().strip():
            messagebox.showerror("错误", "请输入 DeepSeek API Key（测试模式下可留空）")
            return
        if not os.path.exists(self.source_dir.get()):
            messagebox.showerror("错误", "英文源文件目录不存在")
            return
        if not self.output_dir.get():
            messagebox.showerror("错误", "请选择输出目录")
            return

        Path(self.output_dir.get()).mkdir(parents=True, exist_ok=True)
        self.save_config()

        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.set_progress(0)
        self.log("=" * 60, "info")
        self.log("开始翻译任务", "info")
        if self.test_mode.get():
            self.log("⚠ 测试模式已启用，不会调用真实 API，将使用模拟翻译", "warning")

        thread = threading.Thread(target=self.translation_worker, daemon=True)
        thread.start()

    def stop_translation(self):
        self.is_running = False
        self.log("正在停止...", "warning")
        self.stop_btn.config(state=tk.DISABLED)

    # ===== 翻译工作线程 =====
    def translation_worker(self):
        try:
            source_dir = self.source_dir.get()
            old_dir = self.old_dir.get()
            output_dir = self.output_dir.get()

            self.log("加载旧汉化参考...", "info")
            old_groups, old_by_mod_version, old_cache = self.load_old_translations(old_dir)

            source_files = list(Path(source_dir).glob("*.cfg"))
            if not source_files:
                self.log("错误：源目录中没有 cfg 文件", "error")
                return
            self.log(f"找到 {len(source_files)} 个源文件", "info")

            selected_items = self.compare_and_select(source_files, old_by_mod_version, old_groups)
            if not selected_items:
                self.log("未选择任何文件，任务结束", "warning")
                return
            self.log(f"用户选择了 {len(selected_items)} 个文件进行处理", "info")

            api_key = self.api_key.get().strip() if not self.test_mode.get() else "dummy"
            self.client = DeepSeekAPIClient(api_key, simulate=self.test_mode.get())

            total = len(selected_items)
            for idx, (src_file, operation) in enumerate(selected_items):
                if not self.is_running:
                    self.log("用户已停止", "warning")
                    break

                self.set_status(f"处理: {src_file.name} ({operation})")
                self.set_progress((idx / total) * 100)

                if operation == "copy":
                    src_mod, src_version = self.extract_mod_info(src_file.name)
                    match_key = (src_mod, src_version) if src_version is not None else None
                    if match_key and match_key in old_by_mod_version:
                        ref_file_path = old_by_mod_version[match_key]
                        out_path = Path(output_dir) / src_file.name
                        self.log(f"  准备复制：{ref_file_path} -> {out_path}", "info")
                        try:
                            shutil.copy2(ref_file_path, out_path)
                            self.log(f"[{idx+1}/{total}] {src_file.name} 复制成功", "success")
                        except Exception as e:
                            self.log(f"[{idx+1}/{total}] {src_file.name} 复制失败: {e}", "error")
                    else:
                        self.log(f"[{idx+1}/{total}] {src_file.name} 选择复制但未找到精确匹配，跳过", "error")

                elif operation == "translate":
                    src_mod, _ = self.extract_mod_info(src_file.name)
                    ref_text = ""
                    if src_mod in old_groups:
                        ref_text = self.build_reference_text(old_groups[src_mod], old_cache)
                        self.log(f"[{idx+1}/{total}] {src_file.name} (有参考: {src_mod})", "info")
                    else:
                        self.log(f"[{idx+1}/{total}] {src_file.name} (无参考)", "info")
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
