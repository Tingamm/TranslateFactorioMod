# ================= 配置参数 =================
$SourceDir = "$env:APPDATA\Factorio\mods"          # 源目录：Factorio mods 文件夹
$DestDir   = "$PSScriptRoot\FactorioModCFG"        # 输出目录：脚本同级下的 FactorioModCFG 文件夹
$InnerSubPath = "locale\en"                         # 压缩包内目标子路径（相对于顶层文件夹）
$FileExtension = "*.cfg"                           # 要提取的文件类型
# =============================================

# 如果输出目录不存在，则创建它
if (-not (Test-Path $DestDir)) {
    New-Item -ItemType Directory -Path $DestDir -Force | Out-Null
}

# 获取源目录下所有的 .zip 压缩包
$zipFiles = Get-ChildItem -Path $SourceDir -Filter "*.zip" -File

# 遍历每一个压缩包
foreach ($zip in $zipFiles) {
    # 获取压缩包的基本名称（不含扩展名，例如 "aai-loaders_0.2.11"）
    $zipBaseName = [System.IO.Path]::GetFileNameWithoutExtension($zip.Name)
    # 创建一个临时解压目录（使用随机 GUID 避免冲突）
    $tempDir = Join-Path $env:TEMP "ModExtract_$([System.Guid]::NewGuid().ToString())"
    
    try {
        # 将压缩包解压到临时目录
        Expand-Archive -Path $zip.FullName -DestinationPath $tempDir -Force
        
        # 获取压缩包内的顶层文件夹（通常只有一个，如 "aai-loaders"）
        $topFolders = Get-ChildItem -Path $tempDir -Directory
        if ($topFolders.Count -eq 0) {
            Write-Warning "压缩包 $($zip.Name) 中没有顶层文件夹，跳过"
            continue
        }
        $topFolder = $topFolders[0].Name
        
        # 拼接目标子目录的完整路径：顶层文件夹 + 用户指定的子路径
        $targetSubDir = Join-Path $tempDir "$topFolder\$InnerSubPath"
        if (-not (Test-Path $targetSubDir)) {
            Write-Warning "压缩包 $($zip.Name) 中找不到路径 '$topFolder\$InnerSubPath'，跳过"
            continue
        }
        
        # 获取该子目录下所有匹配的 cfg 文件
        $cfgFiles = Get-ChildItem -Path $targetSubDir -Filter $FileExtension -File
        if ($cfgFiles.Count -eq 0) {
            Write-Warning "压缩包 $($zip.Name) 的目标路径中没有 cfg 文件，跳过"
            continue
        }
        
        # 遍历每个 cfg 文件，按规则重命名并复制到输出目录
        foreach ($cfg in $cfgFiles) {
            if ($cfgFiles.Count -eq 1) {
                # 只有一个 cfg 文件时，命名为：压缩包名称.cfg
                $newName = "$zipBaseName.cfg"
            } else {
                # 有多个 cfg 文件时，命名为：压缩包名称-原文件名.cfg
                $newName = "$zipBaseName-$($cfg.Name)"
            }
            $destFile = Join-Path $DestDir $newName
            Copy-Item -Path $cfg.FullName -Destination $destFile -Force
            Write-Host "已提取: $newName"
        }
    }
    catch {
        Write-Error "处理压缩包 $($zip.Name) 时出错: $_"
    }
    finally {
        # 清理临时解压目录（无论成功或失败）
        if (Test-Path $tempDir) {
            Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Host "全部完成！文件已保存到：$DestDir"
