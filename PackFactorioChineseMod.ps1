# ================= 配置 =================
$ScriptDir = $PSScriptRoot
$ModInfoFolder = Join-Path $ScriptDir "FactorioModInfo"
$InfoJsonPath = Join-Path $ModInfoFolder "info.json"
$CfgSrcFolder = Join-Path $ScriptDir "FactorioModCFG_zh"
$FilesToCopy = @("changelog.txt", "info.json", "LICENSE", "README.md", "thumbnail.png")
$BackupFolder = Join-Path $ScriptDir "模组备份"
# ==========================================

# ---------- 检查必要文件/文件夹 ----------
if (-not (Test-Path $ModInfoFolder)) {
    Write-Error "错误：在脚本目录下未找到 FactorioModInfo 文件夹"
    exit 1
}
if (-not (Test-Path $InfoJsonPath)) {
    Write-Error "错误：在 FactorioModInfo 文件夹中未找到 info.json"
    exit 1
}
if (-not (Test-Path $CfgSrcFolder)) {
    Write-Error "错误：在脚本目录下未找到 FactorioModCFG_zh 文件夹"
    exit 1
}

# ---------- 读取 info.json ----------
try {
    $jsonContent = Get-Content -Path $InfoJsonPath -Raw -Encoding UTF8
    $jsonObj = $jsonContent | ConvertFrom-Json
    $name = $jsonObj.name
    $version = $jsonObj.version
    if ([string]::IsNullOrEmpty($name)) {
        Write-Error "info.json 中缺少 'name' 字段"
        exit 1
    }
    if ([string]::IsNullOrEmpty($version)) {
        Write-Warning "info.json 中缺少 'version' 字段，将使用默认 1.0.0"
        $version = "1.0.0"
    }
} catch {
    Write-Error "读取或解析 info.json 失败：$_"
    exit 1
}

# ========== 新增：交互式版本号更新 ==========
Write-Host "当前版本号: $version"
$updateVersion = Read-Host "是否更新版本号？(Y/N)"
if ($updateVersion -eq 'Y' -or $updateVersion -eq 'y') {
    $newVersion = Read-Host "请输入新版本号 (格式如 1.2.3)"
    if (-not [string]::IsNullOrWhiteSpace($newVersion)) {
        $version = $newVersion
        # 写回 info.json
        $jsonObj.version = $version
        $jsonObj | ConvertTo-Json -Depth 10 | Set-Content -Path $InfoJsonPath -Encoding UTF8
        Write-Host "已更新 info.json 中的版本号为 $version"
    } else {
        Write-Warning "输入无效，保留原版本号 $version"
    }
} else {
    Write-Host "保持原版本号不变"
}
# ===========================================

# 使用最终版本号构建目标文件夹名
$targetFolderName = "$name`_$version"
$targetPath = Join-Path $ScriptDir $targetFolderName
$targetLocalePath = Join-Path $targetPath "locale\zh-CN"

# ---------- 清理并重建目标文件夹 ----------
if (Test-Path $targetPath) {
    Write-Host "目标文件夹已存在，正在删除旧版本..."
    Remove-Item -Path $targetPath -Recurse -Force
}
New-Item -ItemType Directory -Path $targetLocalePath -Force | Out-Null

# ---------- 复制语言文件 ----------
$cfgItems = Get-ChildItem -Path $CfgSrcFolder -Force
foreach ($item in $cfgItems) {
    if ($item.PSIsContainer) {
        Copy-Item -Path $item.FullName -Destination $targetLocalePath -Recurse -Force
    } else {
        Copy-Item -Path $item.FullName -Destination $targetLocalePath -Force
    }
}
Write-Host "已复制 FactorioModCFG_zh 内容到 $targetLocalePath"

# ---------- 复制其他文件 ----------
foreach ($file in $FilesToCopy) {
    $srcFile = Join-Path $ModInfoFolder $file
    if (Test-Path $srcFile) {
        Copy-Item -Path $srcFile -Destination $targetPath -Force
        Write-Host "已复制 $file"
    } else {
        Write-Warning "在 FactorioModInfo 中未找到 $file，跳过复制"
    }
}

# ================== 打包为 ZIP（强制正斜杠分隔 + 顶层文件夹） ==================
$zipPath = Join-Path $ScriptDir "$targetFolderName.zip"
if (Test-Path $zipPath) {
    Remove-Item -Path $zipPath -Force
}

# ---------- 加载 .NET 压缩程序集 ----------
try {
    Add-Type -AssemblyName System.IO.Compression -ErrorAction Stop
    Add-Type -AssemblyName System.IO.Compression.FileSystem -ErrorAction Stop
} catch {
    Write-Error "无法加载 System.IO.Compression 程序集。您的 PowerShell 版本可能过低（需要 5.0+）或系统缺少 .NET Framework。"
    Write-Error "建议安装 7-Zip 并改用以下命令打包："
    Write-Error "  7z a -tzip `"$zipPath`" `"$targetPath`" -mx=9"
    exit 1
}

# ---------- 创建 ZIP，每个条目添加顶层文件夹前缀 ----------
$zipStream = [System.IO.File]::OpenWrite($zipPath)
$zip = [System.IO.Compression.ZipArchive]::new($zipStream, [System.IO.Compression.ZipArchiveMode]::Create)

$sourceDir = $targetPath
$files = Get-ChildItem -Path $sourceDir -Recurse -File
foreach ($file in $files) {
    $relativePath = $file.FullName.Substring($sourceDir.Length + 1) -replace '\\', '/'
    $entryName = "$targetFolderName/$relativePath"
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
        $zip,
        $file.FullName,
        $entryName,
        [System.IO.Compression.CompressionLevel]::Optimal
    )
}
$zip.Dispose()
$zipStream.Dispose()
Write-Host "已打包（包含顶层文件夹，正斜杠分隔）：$zipPath"

# ================== 备份 ==================
if (-not (Test-Path $BackupFolder)) {
    New-Item -ItemType Directory -Path $BackupFolder -Force | Out-Null
}
$backupTargetPath = Join-Path $BackupFolder $targetFolderName
if (Test-Path $backupTargetPath) {
    Remove-Item -Path $backupTargetPath -Recurse -Force
}
Move-Item -Path $targetPath -Destination $BackupFolder -Force
Write-Host "已将 $targetFolderName 移动到 $BackupFolder"

Write-Host "全部完成！"
