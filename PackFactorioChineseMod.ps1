# ================= 配置 =================
$ScriptDir = $PSScriptRoot
$ModInfoFolder = Join-Path $ScriptDir "FactorioModInfo"
$InfoJsonPath = Join-Path $ModInfoFolder "info.json"
$CfgSrcFolder = Join-Path $ScriptDir "FactorioModCFG_zh"
$FilesToCopy = @("changelog.txt", "info.json", "LICENSE", "README.md", "thumbnail.png")
$BackupFolder = Join-Path $ScriptDir "模组备份"
# ==========================================

# 检查必要文件/文件夹是否存在
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

# 读取 info.json 获取 name 和 version
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

$targetFolderName = "$name`_$version"
$targetPath = Join-Path $ScriptDir $targetFolderName
$targetLocalePath = Join-Path $targetPath "locale\zh-CN"

# 如果目标文件夹已存在，先删除
if (Test-Path $targetPath) {
    Write-Host "目标文件夹已存在，正在删除旧版本..."
    Remove-Item -Path $targetPath -Recurse -Force
}

# 创建目标文件夹及其 locale\zh-CN 子目录
New-Item -ItemType Directory -Path $targetLocalePath -Force | Out-Null

# 复制 FactorioModCFG_zh 的全部内容到 locale\zh-CN（内部文件平铺）
$cfgItems = Get-ChildItem -Path $CfgSrcFolder -Force
foreach ($item in $cfgItems) {
    if ($item.PSIsContainer) {
        Copy-Item -Path $item.FullName -Destination $targetLocalePath -Recurse -Force
    } else {
        Copy-Item -Path $item.FullName -Destination $targetLocalePath -Force
    }
}
Write-Host "已复制 FactorioModCFG_zh 内容到 $targetLocalePath"

# 从 FactorioModInfo 文件夹复制指定文件到目标根目录
foreach ($file in $FilesToCopy) {
    $srcFile = Join-Path $ModInfoFolder $file
    if (Test-Path $srcFile) {
        Copy-Item -Path $srcFile -Destination $targetPath -Force
        Write-Host "已复制 $file"
    } else {
        Write-Warning "在 FactorioModInfo 中未找到 $file，跳过复制"
    }
}

# 打包为 zip
$zipPath = Join-Path $ScriptDir "$targetFolderName.zip"
if (Test-Path $zipPath) {
    Remove-Item -Path $zipPath -Force
}
Compress-Archive -Path $targetPath -DestinationPath $zipPath -CompressionLevel Optimal
Write-Host "已打包：$zipPath"

# 创建备份文件夹（如果不存在）
if (-not (Test-Path $BackupFolder)) {
    New-Item -ItemType Directory -Path $BackupFolder -Force | Out-Null
}

# 将目标文件夹移动到备份文件夹
$backupTargetPath = Join-Path $BackupFolder $targetFolderName
if (Test-Path $backupTargetPath) {
    Remove-Item -Path $backupTargetPath -Recurse -Force
}
Move-Item -Path $targetPath -Destination $BackupFolder -Force
Write-Host "已将 $targetFolderName 移动到 $BackupFolder"

Write-Host "全部完成！"
