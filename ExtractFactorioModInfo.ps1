# ================= 配置 =================
$SourceDir = "$env:APPDATA\Factorio\mods"
$JsonFileName = "info.json"
$LocaleSubPath = "locale\en"

# 目标文件夹和输出文件
$TargetFolder = Join-Path $PSScriptRoot "FactorioModCFG"
$OutputFile = Join-Path $TargetFolder "#AAA-modlist.cfg"
# ========================================

# 转义函数：将特殊字符转换为字面转义序列
function Escape-String {
    param([string]$inputString)
    if (-not $inputString) { return "" }
    $result = $inputString -replace "\\", "\\"
    $result = $result -replace "`r`n", "\n"
    $result = $result -replace "`n", "\n"
    $result = $result -replace "`r", "\r"
    $result = $result -replace "`t", "\t"
    return $result
}

# 从 cfg 文件中提取指定段落的内容（返回哈希表）
function Get-CfgSection {
    param(
        [string]$cfgFilePath,
        [string]$sectionName
    )
    if (-not (Test-Path $cfgFilePath)) { return $null }

    $content = Get-Content -Path $cfgFilePath -Raw -Encoding UTF8
    # 使用 (?s) 让 . 匹配换行符，同时忽略大小写
    $pattern = "(?s)(?i)\[$sectionName\](.*?)(?=\[|\Z)"
    $match = [regex]::Match($content, $pattern)
    if (-not $match.Success) { return $null }

    $sectionText = $match.Groups[1].Value.Trim()
    # 解析键值对：按任意换行符分割，忽略空行和注释行
    $hash = @{}
    $sectionText -split "\r?\n" | ForEach-Object {
        $line = $_.Trim()
        if ($line -and $line -notmatch '^#') {
            $parts = $line -split '=', 2
            if ($parts.Count -eq 2) {
                $hash[$parts[0].Trim()] = $parts[1].Trim()
            }
        }
    }
    return $hash
}

$modList = @()
$zipFiles = Get-ChildItem -Path $SourceDir -Filter "*.zip" -File

if ($zipFiles.Count -eq 0) {
    Write-Warning "在 $SourceDir 中没有找到 .zip 文件，请检查路径是否正确。"
    exit
}

foreach ($zip in $zipFiles) {
    $tempDir = Join-Path $env:TEMP "ModInfo_$([System.Guid]::NewGuid().ToString())"
    try {
        Expand-Archive -Path $zip.FullName -DestinationPath $tempDir -Force

        $topFolders = Get-ChildItem -Path $tempDir -Directory
        if ($topFolders.Count -eq 0) {
            Write-Warning "压缩包 $($zip.Name) 没有顶层文件夹，跳过"
            continue
        }
        $topFolder = $topFolders[0].Name
        $jsonPath = Join-Path $tempDir "$topFolder\$JsonFileName"

        if (-not (Test-Path $jsonPath)) {
            Write-Warning "压缩包 $($zip.Name) 中未找到 $JsonFileName，跳过"
            continue
        }

        $jsonContent = Get-Content -Path $jsonPath -Raw -Encoding UTF8
        try {
            $jsonObj = $jsonContent | ConvertFrom-Json
        } catch {
            Write-Warning "压缩包 $($zip.Name) 的 $JsonFileName 格式无效，跳过"
            continue
        }

        # 读取字段（可能缺失）
        $name = $jsonObj.name
        $title = $jsonObj.title
        $description = $jsonObj.description

        # 检查哪些字段缺失
        $missingFields = @()
        if ([string]::IsNullOrEmpty($name)) { $missingFields += "name" }
        if ([string]::IsNullOrEmpty($title)) { $missingFields += "title" }
        if ([string]::IsNullOrEmpty($description)) { $missingFields += "description" }

        if ($missingFields.Count -gt 0) {
            Write-Host "压缩包 $($zip.Name) 缺少字段: $($missingFields -join ', ')，尝试从 locale/en/*.cfg 补充"

            # 定位 locale/en 目录
            $localeDir = Join-Path $tempDir "$topFolder\$LocaleSubPath"
            if (Test-Path $localeDir) {
                $cfgFiles = Get-ChildItem -Path $localeDir -Filter "*.cfg" -File
                $cfgNameHash = $null
                $cfgDescHash = $null

                # 遍历所有 cfg 文件，直到找到所有需要的补充信息
                foreach ($cfgFile in $cfgFiles) {
                    # 如果 name 或 title 缺失，尝试读取 mod-name 段落
                    if ([string]::IsNullOrEmpty($name) -or [string]::IsNullOrEmpty($title)) {
                        if ($null -eq $cfgNameHash) {
                            $cfgNameHash = Get-CfgSection -cfgFilePath $cfgFile.FullName -sectionName "mod-name"
                        }
                    }
                    # 如果 description 缺失，尝试读取 mod-description 段落
                    if ([string]::IsNullOrEmpty($description)) {
                        if ($null -eq $cfgDescHash) {
                            $cfgDescHash = Get-CfgSection -cfgFilePath $cfgFile.FullName -sectionName "mod-description"
                        }
                    }
                    # 如果都已经找到，提前退出循环
                    if ((-not [string]::IsNullOrEmpty($name) -or -not [string]::IsNullOrEmpty($title)) -and -not [string]::IsNullOrEmpty($description)) {
                        break
                    }
                }

                # 补充 name（如果缺失，尝试从 mod-name 段取第一个键，否则用压缩包基本名称）
                if ([string]::IsNullOrEmpty($name)) {
                    if ($cfgNameHash -and $cfgNameHash.Count -gt 0) {
                        $name = $cfgNameHash.Keys | Select-Object -First 1
                    }
                    if ([string]::IsNullOrEmpty($name)) {
                        $name = [System.IO.Path]::GetFileNameWithoutExtension($zip.Name)
                    }
                }

                # 补充 title（如果缺失，从 mod-name 段取第一个键的值）
                if ([string]::IsNullOrEmpty($title)) {
                    if ($cfgNameHash -and $cfgNameHash.Count -gt 0) {
                        $firstKey = $cfgNameHash.Keys | Select-Object -First 1
                        $title = $cfgNameHash[$firstKey]
                    }
                }

                # 补充 description（如果缺失，从 mod-description 段取第一个键的值）
                if ([string]::IsNullOrEmpty($description)) {
                    if ($cfgDescHash -and $cfgDescHash.Count -gt 0) {
                        $firstKey = $cfgDescHash.Keys | Select-Object -First 1
                        $description = $cfgDescHash[$firstKey]
                    }
                }

                Write-Host "  补充后 - name: '$name', title: '$title', description 长度: $($description.Length)"
            } else {
                Write-Warning "压缩包 $($zip.Name) 中未找到 locale/en 目录，无法补充缺失字段"
            }

            # 再次检查是否仍然缺失
            $stillMissing = @()
            if ([string]::IsNullOrEmpty($name)) { $stillMissing += "name" }
            if ([string]::IsNullOrEmpty($title)) { $stillMissing += "title" }
            if ([string]::IsNullOrEmpty($description)) { $stillMissing += "description" }
            if ($stillMissing.Count -gt 0) {
                Write-Warning "压缩包 $($zip.Name) 补充后仍缺失字段: $($stillMissing -join ', ')，跳过"
                continue
            }
        }

        # 加入有效 mod
        $modList += [PSCustomObject]@{
            Name = $name
            Title = $title
            Description = $description
        }
        Write-Host "已读取: $($zip.Name) -> $name"
    }
    catch {
        Write-Error "处理 $($zip.Name) 时出错: $_"
    }
    finally {
        if (Test-Path $tempDir) {
            Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

if ($modList.Count -eq 0) {
    Write-Warning "没有成功读取任何 mod 信息，输出文件将不会被创建。"
    exit
}

# 确保目标文件夹存在
if (-not (Test-Path $TargetFolder)) {
    New-Item -ItemType Directory -Path $TargetFolder -Force | Out-Null
}

# 生成输出内容（两个大块）
$outputLines = @()
$outputLines += "[mod-name]"
foreach ($mod in $modList) {
    $outputLines += "$($mod.Name)=$($mod.Title)"
}
$outputLines += ""
$outputLines += "[mod-description]"
foreach ($mod in $modList) {
    $escapedDescription = Escape-String $mod.Description
    $outputLines += "$($mod.Name)=$escapedDescription"
}

# 直接写入目标文件
$outputLines | Out-File -FilePath $OutputFile -Encoding UTF8 -Force
Write-Host "所有 mod 信息已提取完成！输出文件：$OutputFile"
Write-Host "共处理 $($modList.Count) 个 mod。"
