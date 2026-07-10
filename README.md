TranslateFactorioMod —— 异星工厂翻译模组工具
A complete toolchain for translating Factorio mods into Chinese

项目简介 | Introduction
TranslateFactorioMod 是一套完整的 Factorio（异星工厂）模组汉化工具链，帮助模组作者和汉化爱好者快速将模组翻译为中文。

本工具链覆盖从文本提取 → AI 翻译 → 打包发布的完整流程，支持旧版汉化作为翻译参考，保持术语和风格的一致性。

A complete toolchain for translating Factorio mods into Chinese. Covers the entire workflow from text extraction → AI translation → packaging for release. Supports using existing translations as reference to maintain consistent terminology and style.

功能特性 | Features
功能	说明
🔧 自动提取英文文本	从 %APPDATA%\Factorio\mods 目录自动扫描所有模组压缩包，提取 locale/en 下的 cfg 文件
📋 模组信息聚合	自动读取每个模组的 info.json，汇总生成 #AAA-modlist.cfg 模组信息列表
🤖 AI 智能翻译	基于 DeepSeek API 进行翻译，支持以旧版汉化作为风格和术语参考
📦 一键打包发布	将翻译后的文件与 info.json 等打包为可直接发布的 Factorio 模组压缩包
🖥️ 图形界面	翻译工具提供 GUI 界面，操作简单，无需命令行基础
🔄 版本兼容	自动识别模组名（忽略版本号和后缀），支持新旧版本之间的翻译复用
Feature	Description
🔧 Auto-extract English texts	Scan all mod packages in %APPDATA%\Factorio\mods and extract cfg files from locale/en
📋 Mod info aggregation	Read info.json from each mod and generate #AAA-modlist.cfg
🤖 AI-powered translation	DeepSeek API based translation with optional reference to existing translations
📦 One-click packaging	Package translated files with info.json into a ready-to-publish Factorio mod zip
🖥️ GUI interface	Easy to use, no command-line knowledge required
🔄 Version compatibility	Auto-detect mod names (ignoring version numbers and suffixes) for translation reuse
工具链概览 | Toolchain Overview
步骤	工具	功能	输入 → 输出
1	ExtractFactorioModCFG	提取英文 cfg 文件	%APPDATA%\Factorio\mods\*.zip → FactorioModCFG\*.cfg
2	ExtractFactorioModInfo	生成模组信息列表	%APPDATA%\Factorio\mods\*.zip → FactorioModCFG\#AAA-modlist.cfg
3	DeepSeekTranslator	AI 翻译（GUI）	FactorioModCFG\*.cfg + 旧汉化参考 → FactorioModCFG_zh\*.cfg
4	PackFactorioChineseMod	打包发布	FactorioModCFG_zh\*.cfg + FactorioModInfo\* → 模组名_版本.zip
系统要求 | Requirements
运行 ExtractFactorioModCFG / ExtractFactorioModInfo / PackFactorioChineseMod
Windows 操作系统（PowerShell 5.0+）

无需额外安装依赖

运行 DeepSeekTranslator (GUI)
Windows 10/11 操作系统

Python 3.8 或更高版本

依赖库：requests

bash
pip install requests
DeepSeek API 密钥
访问 DeepSeek 平台 注册并获取 API Key

API 按 Token 计费，参考价格见下方说明

安装与目录结构 | Installation
1. 克隆仓库
bash
git clone https://github.com/your-username/TranslateFactorioMod.git
cd TranslateFactorioMod
2. 目录结构
text
TranslateFactorioMod/
│
├── 1、ExtractFactorioModCFG.bat          # 第一步启动器
├── ExtractFactorioModCFG.ps1              # 第一步脚本
│
├── 2、ExtractFactorioModInfo.bat          # 第二步启动器
├── ExtractFactorioModInfo.ps1              # 第二步脚本
│
├── 3、DeepSeekTranslator.py               # 第三步 GUI 工具
│
├── 4、PackFactorioChineseMod.bat          # 第四步启动器
├── PackFactorioChineseMod.ps1             # 第四步脚本
│
├── FactorioModCFG\                        # 第一步输出（英文源文件）
├── FactorioModCFG_zh\                     # 第三步输出（汉化后文件）
├── FactorioModInfo\                       # 用户创建（模组信息文件）
│   ├── info.json                         # 必须
│   ├── changelog.txt                     # 可选
│   ├── LICENSE                           # 可选
│   ├── README.md                         # 可选
│   └── thumbnail.png                     # 可选
├── OldChinese\                            # 用户创建（旧版汉化参考）
└── 模组备份\                              # 第四步自动生成
使用说明 | Usage
第一步：提取英文源文件
双击 1、ExtractFactorioModCFG.bat，自动从 %APPDATA%\Factorio\mods 提取所有模组的 locale/en/*.cfg 到 FactorioModCFG 文件夹。

命名规则：

单个 cfg 文件：模组名_版本.cfg

多个 cfg 文件：模组名_版本-原文件名.cfg

第二步：生成模组信息列表
双击 2、ExtractFactorioModInfo.bat，读取每个模组的 info.json，生成 FactorioModCFG\#AAA-modlist.cfg。

若 info.json 缺少 description，自动从 locale/en/*.cfg 的 [mod-description] 段落补充。

第三步：AI 翻译
双击 3、DeepSeekTranslator.py 启动 GUI：

输入 DeepSeek API Key

选择目录：

英文源文件：FactorioModCFG

旧汉化参考：OldChinese（可选）

输出目录：FactorioModCFG_zh

点击 “开始翻译”

程序会自动按模组名分组，将旧汉化作为翻译参考，调用 DeepSeek API 重新翻译所有条目。

第四步：打包发布
创建 FactorioModInfo 文件夹，放入 info.json（必须）及其他文件

双击 4、PackFactorioChineseMod.bat

自动生成 模组名_版本.zip 发布包

完整工作流示例 | Workflow Example
text
【准备阶段】
├── 创建工作目录
├── 将所有脚本放入该目录
├── 创建 FactorioModInfo 文件夹，放入 info.json
└── 创建 OldChinese 文件夹，放入旧版汉化文件（如有）

【第一步】提取英文源文件
└── 双击 1、ExtractFactorioModCFG.bat → 生成 FactorioModCFG\

【第二步】生成模组信息列表
└── 双击 2、ExtractFactorioModInfo.bat → 生成 #AAA-modlist.cfg

【第三步】AI 翻译
└── 双击 3、DeepSeekTranslator.py → 选择目录 → 开始翻译 → 生成 FactorioModCFG_zh\

【第四步】打包发布
└── 双击 4、PackFactorioChineseMod.bat → 生成 模组名_版本.zip
模组名识别规则 | Mod Name Detection
工具通过正则表达式 ^(.*)_(\d+\.\d+\.\d+)(?:-.*)?\.cfg$ 提取基础模组名（忽略版本号和后缀）：

文件名	提取结果
aai-loaders_0.2.11.cfg	aai-loaders
aai-vehicles-miner_0.7.1.cfg	aai-vehicles-miner
aai-programmable-vehicles_0.8.5-informatron.cfg	aai-programmable-vehicles
erm_unit_control_1.1.14-hotkeys.cfg	erm_unit_control
DeepSeek API 价格参考 | API Pricing
DeepSeek API 采用按 Token 计费模式，价格如下（截至 2026 年 7 月）：

模型	计费项	平时价格	高峰价格 (9:00-12:00, 14:00-18:00)
V4 Pro	输入（缓存命中）	0.025 元/百万 Tokens	0.05 元/百万 Tokens
V4 Pro	输入（缓存未命中）	3 元/百万 Tokens	6 元/百万 Tokens
V4 Pro	输出	6 元/百万 Tokens	12 元/百万 Tokens
V4 Flash	输入（缓存命中）	0.02 元/百万 Tokens	0.04 元/百万 Tokens
V4 Flash	输入（缓存未命中）	1 元/百万 Tokens	2 元/百万 Tokens
V4 Flash	输出	2 元/百万 Tokens	4 元/百万 Tokens
建议在非高峰时段（工作日 12:00-14:00 或 18:00 之后）进行大批量翻译以降低成本。

常见问题 | FAQ
Q1：双击 .bat 文件闪退怎么办？
打开 PowerShell，手动运行查看错误信息：

powershell
cd 脚本目录
powershell.exe -ExecutionPolicy Bypass -File "ExtractFactorioModCFG.ps1"
常见原因及解决：

错误	解决方法
ModuleNotFoundError: No module named 'requests'	执行 pip install requests
中文显示乱码	用记事本另存为 UTF-8 with BOM 编码
脚本无法执行	以管理员身份运行 PowerShell，执行 Set-ExecutionPolicy RemoteSigned
Q2：翻译工具提示“API Key 无效”？
检查 API Key 是否正确（格式：sk-xxxxx）

确认 DeepSeek 账户余额充足

检查网络是否能访问 api.deepseek.com

Q3：旧汉化文件没有匹配上？
确保旧文件命名符合 模组名_版本(-后缀).cfg 格式，工具会自动提取基础模组名进行匹配。

Q4：翻译结果中换行符显示异常？
这是正常行为，DeepSeek 的翻译输出保留了文本原始格式。如有特殊需要，可在后续手动调整。

许可证 | License
MIT License

贡献 | Contributing
欢迎提交 Issue 和 Pull Request！

Fork 本仓库

创建功能分支 (git checkout -b feature/AmazingFeature)

提交更改 (git commit -m 'Add some AmazingFeature')

推送到分支 (git push origin feature/AmazingFeature)

创建 Pull Request

相关项目 | Related Projects
FactorioModLToC — 异星工厂模组汉化工具

FactorioModTranslator — 多语言模组翻译工具

factorio-mods-localization — Crowdin 集成翻译工具

版本：v1.0 | 更新日期：2026-07-10 | 全部内容由AI生成
