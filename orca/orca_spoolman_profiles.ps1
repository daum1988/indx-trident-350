<#
.SYNOPSIS
  Creates standalone OrcaSlicer filament profiles from the filaments in Spoolman.

.DESCRIPTION
  For each Spoolman filament a profile "<Vendor> <Name> (SM<id>)" is created with
  filament ID "PSM<id>". The printer (orca_lanes.py) writes the same ID into
  Moonraker's lane_data, so Orca picks exactly this profile when syncing filaments.

  Templates: for each material, create your own filament in Orca once
  ("Create filament", compatible with your printer) and name it
  "<TemplatePrefix> <Material>", e.g. "SM-Vorlage PLA", "SM-Vorlage PETG"
  (default prefix "SM-Vorlage", change it with -TemplatePrefix "SM-Template").
  All settings of the template are kept; Spoolman provides name, vendor,
  colour, nozzle and bed temperature, density, diameter and price.
  A Spoolman spool's material is matched to the template with the longest matching
  type ("PLA+" -> "SM-Vorlage PLA" if there is no "PLA+" template).

  Close OrcaSlicer before running and restart it afterwards.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\orca_spoolman_profiles.ps1 -WhatIf
  powershell -ExecutionPolicy Bypass -File .\orca_spoolman_profiles.ps1
  powershell -ExecutionPolicy Bypass -File .\orca_spoolman_profiles.ps1 -Prune
#>
[CmdletBinding()]
param(
  [string]$SpoolmanUrl = "http://spoolman.local:7912",
  # Orca folder for standalone user filament profiles. Default: the folder
  # Orca currently uses (preset_folder in OrcaSlicer.conf; signed in =
  # user\<account ID>, otherwise user\default).
  [string]$OrcaDir = "",
  # Where the templates are (default: the same folder)
  [string]$TemplateDir = "",
  # Where to write (default: OrcaDir). Pass an empty folder for testing.
  [string]$OutDir = "",
  [string]$TemplatePrefix = "SM-Vorlage",
  # Only show, write nothing
  [switch]$WhatIf,
  # Delete "PSM..." profiles whose filament no longer exists in Spoolman
  [switch]$Prune,
  # Also create archived Spoolman filaments and those without a spool
  [switch]$All
)

$ErrorActionPreference = "Stop"
if (-not $WhatIf -and -not $OutDir -and (Get-Process -Name OrcaSlicer -ErrorAction SilentlyContinue)) {
  Write-Host "OrcaSlicer is still running. Close Orca and start the script again." -ForegroundColor Red
  exit 1
}
if (-not $OrcaDir) {
  $folder = "default"
  $conf = Join-Path $env:APPDATA "OrcaSlicer\OrcaSlicer.conf"
  if (Test-Path $conf) {
    $m = [regex]::Match([IO.File]::ReadAllText($conf), '"preset_folder"\s*:\s*"([^"]+)"')
    if ($m.Success) { $folder = $m.Groups[1].Value }
  }
  $OrcaDir = Join-Path $env:APPDATA "OrcaSlicer\user\$folder\filament\base"
  Write-Host "Orca profile folder: user\$folder" -ForegroundColor Cyan
}
if (-not $TemplateDir) { $TemplateDir = $OrcaDir }
if (-not $OutDir) { $OutDir = $OrcaDir }
$utf8 = New-Object System.Text.UTF8Encoding($false)
$inv = [Globalization.CultureInfo]::InvariantCulture

function Read-Json([string]$path) {
  [IO.File]::ReadAllText($path, $utf8) | ConvertFrom-Json
}

function Set-Prop($obj, [string]$name, $value, [switch]$OnlyIfExists) {
  if ($obj.PSObject.Properties[$name]) {
    # Orca 2.5 keeps some values as a list per extruder variant (e.g. 6 entries).
    # A single new value then applies to all entries of the template.
    $old = @($obj.$name)
    if ($value -is [array] -and @($value).Count -eq 1 -and $old.Count -gt 1) {
      $v = @($value)[0]
      $value = @(for ($i = 0; $i -lt $old.Count; $i++) { $v })
    }
    $obj.$name = $value
  }
  elseif (-not $OnlyIfExists) { $obj | Add-Member -NotePropertyName $name -NotePropertyValue $value }
}

function Get-First($obj, [string]$name) {
  if ($obj.PSObject.Properties[$name] -and $obj.$name -ne $null) { return @($obj.$name)[0] }
  return $null
}

function Num([double]$v) { $v.ToString("0.###", $inv) }

# "@Voron Trident 350 0.4 nozzle" -> "d04", "0.25" -> "d025", none -> ""
function Get-NozzleKey([string]$suffix) {
  $m = [regex]::Match($suffix, '(\d+(?:\.\d+)?)\s*nozzle')
  if (-not $m.Success) { return "" }
  "d" + ([double]::Parse($m.Groups[1].Value, $inv).ToString("0.###", $inv) -replace '\.', '')
}

# Spoolman stores extra fields as JSON text ("0.98"). Returns key -> value as
# Orca text; a field with a matching nozzle suffix overrides the generic one.
function Get-ExtraValues($extra, [string]$nz) {
  $out = @{}
  if (-not $extra) { return $out }
  $props = @($extra.PSObject.Properties)
  foreach ($pass in 0, 1) {
    foreach ($e in $props) {
      $k = $e.Name
      $m = [regex]::Match($k, '^(.+)_(d\d+)$')
      $isNozzle = $m.Success
      if (($pass -eq 0 -and $isNozzle) -or ($pass -eq 1 -and -not $isNozzle)) { continue }
      if ($isNozzle) { if ($m.Groups[2].Value -ne $nz) { continue }; $k = $m.Groups[1].Value }
      $raw = [string]$e.Value
      if ($raw -eq "" -or $raw -eq "null") { continue }
      try { $v = $raw | ConvertFrom-Json } catch { $v = $raw }
      if ($v -eq $null -or "$v" -eq "") { continue }
      if ($v -is [double] -or $v -is [decimal] -or $v -is [single]) { $v = ([double]$v).ToString("0.#####", $inv) }
      $out[$k] = "$v"
    }
  }
  $out
}
$warnedKeys = @{}

function Safe-FileName([string]$s) {
  $bad = [IO.Path]::GetInvalidFileNameChars() -join ''
  ($s -replace "[$([regex]::Escape($bad))]", '-').Trim()
}

# ---------------------------------------------------------------- Templates
if (-not (Test-Path $TemplateDir)) { throw "Template folder not found: $TemplateDir" }
$templates = @{}
foreach ($f in Get-ChildItem -Path $TemplateDir -Filter *.json) {
  try { $j = Read-Json $f.FullName } catch { continue }
  if ($j.name -notlike "$TemplatePrefix *") { continue }
  if ($j.inherits) { Write-Warning "Template '$($j.name)' inherits from '$($j.inherits)' - create it as a standalone filament. Skipped."; continue }
  $type = [string](Get-First $j "filament_type")
  if (-not $type) { $type = $j.name.Substring($TemplatePrefix.Length).Trim() }
  $gc = (@($j.filament_start_gcode) -join "`n")
  if ($gc -match "SET_ACTIVE_SPOOL") { Write-Warning "Template '$($j.name)' sets SET_ACTIVE_SPOOL in the filament start G-code. That breaks the per-tool spool assignment - please remove it." }
  # Orca creates a separate profile per nozzle variant ("... @Voron Trident 350 0.4 nozzle").
  # All variants of a type are collected; each gets its own Spoolman profile.
  $suffix = ""
  $at = $j.name.LastIndexOf(" @")
  if ($at -ge 0) { $suffix = $j.name.Substring($at) }
  $key = $type.ToUpperInvariant()
  if (-not $templates.ContainsKey($key)) { $templates[$key] = @() }
  $templates[$key] += [pscustomobject]@{ Type = $type; Path = $f.FullName; Name = $j.name; Suffix = $suffix }
}
if ($templates.Count -eq 0) {
  throw "No template found. In Orca create a filament '$TemplatePrefix <Material>' per material (e.g. '$TemplatePrefix PLA'). Searched in: $TemplateDir"
}
Write-Host ("Templates: " + (($templates.Values | ForEach-Object { $_ } | ForEach-Object { $_.Name }) -join ", "))

function Find-Template([string]$material) {
  $m = ($material + "").Trim().ToUpperInvariant()
  if ($templates.ContainsKey($m)) { return $templates[$m] }
  # longest template type the material starts with (PLA+ -> PLA, PETG-CF -> PETG)
  $best = $null
  foreach ($k in $templates.Keys) {
    if ($m.StartsWith($k) -and ($best -eq $null -or $k.Length -gt $best.Length)) { $best = $k }
  }
  if ($best) { return $templates[$best] }
  return $null
}

# ---------------------------------------------------------------- Spoolman
$api = $SpoolmanUrl.TrimEnd('/') + "/api/v1"
# PowerShell 5.1 returns a JSON array as one object: unpack it via the pipeline
$filaments = @(Invoke-RestMethod -Uri "$api/filament" -Method Get -TimeoutSec 15 | ForEach-Object { $_ })
$spools = @(Invoke-RestMethod -Uri "$api/spool" -Method Get -TimeoutSec 15 | ForEach-Object { $_ })
$activeFil = @{}
foreach ($s in $spools) { if (-not $s.archived -and $s.filament) { $activeFil[[int]$s.filament.id] = $true } }
Write-Host ("Spoolman: {0} filaments, {1} of them with a non-archived spool" -f $filaments.Count, $activeFil.Count)

if (-not $WhatIf -and -not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }

$written = 0; $same = 0; $skipped = 0
$keepIds = @{}
foreach ($fil in $filaments) {
  $fid = [int]$fil.id
  if (-not $All -and -not $activeFil.ContainsKey($fid)) { continue }
  $id = "PSM$fid"
  $keepIds[$id] = $true
  $tplList = Find-Template $fil.material
  if (-not $tplList) { Write-Warning "SM$fid '$($fil.name)': no template for material '$($fil.material)'"; $skipped++; continue }

  $vendor = if ($fil.vendor -and $fil.vendor.name) { [string]$fil.vendor.name } else { "" }
  $label = (@($vendor, [string]$fil.name) | Where-Object { $_ }) -join " "
  if (-not $label) { $label = [string]$fil.material }

  # One profile per nozzle variant of the template, all with the same filament ID
  foreach ($tpl in @($tplList)) {
  $p = Read-Json $tpl.Path
  $name = "$label (SM$fid)$($tpl.Suffix)"

  Set-Prop $p "name" $name
  Set-Prop $p "inherits" ""
  Set-Prop $p "from" "User"
  Set-Prop $p "filament_id" $id
  Set-Prop $p "filament_settings_id" @($name)
  Set-Prop $p "filament_vendor" @($(if ($vendor) { $vendor } else { "Generic" }))

  $hex = [string]$fil.color_hex
  if (-not $hex -and $fil.multi_color_hexes) { $hex = ([string]$fil.multi_color_hexes).Split(',')[0] }
  $hex = $hex.Trim().TrimStart('#')
  if ($hex.Length -ge 6) {
    Set-Prop $p "default_filament_colour" @("#" + $hex.Substring(0, 6).ToUpperInvariant())
  }
  if ($fil.density) { Set-Prop $p "filament_density" @(Num $fil.density) }
  if ($fil.diameter) { Set-Prop $p "filament_diameter" @(Num $fil.diameter) }
  if ($fil.price -and $fil.weight) {
    # Spoolman: price per spool of 'weight' grams, Orca: price per kg
    Set-Prop $p "filament_cost" @(Num ([double]$fil.price / [double]$fil.weight * 1000.0))
  }
  if ($fil.spool_weight) { Set-Prop $p "filament_spool_weight" @(Num $fil.spool_weight) -OnlyIfExists }

  # Nozzle temperature: keep the first-layer offset and range from the template
  if ($fil.settings_extruder_temp) {
    $t = [int]$fil.settings_extruder_temp
    $t0 = [int](Get-First $p "nozzle_temperature")
    $ti = Get-First $p "nozzle_temperature_initial_layer"
    Set-Prop $p "nozzle_temperature" @("$t")
    if ($ti -ne $null) { Set-Prop $p "nozzle_temperature_initial_layer" @("$($t + ([int]$ti - $t0))") }
    $lo = Get-First $p "nozzle_temperature_range_low"; $hi = Get-First $p "nozzle_temperature_range_high"
    if ($lo -ne $null -and $t -lt [int]$lo) { Set-Prop $p "nozzle_temperature_range_low" @("$t") }
    if ($hi -ne $null -and $t -gt [int]$hi) { Set-Prop $p "nozzle_temperature_range_high" @("$t") }
  }
  # Bed temperature for all plate types the template knows
  if ($fil.settings_bed_temp) {
    $b = [int]$fil.settings_bed_temp
    foreach ($plate in "hot_plate", "textured_plate", "cool_plate", "eng_plate", "supertack_plate", "textured_cool_plate") {
      $k = "${plate}_temp"; $ki = "${plate}_temp_initial_layer"
      $old = Get-First $p $k
      if ($old -eq $null) { continue }
      $oldi = Get-First $p $ki
      Set-Prop $p $k @("$b")
      if ($oldi -ne $null) { Set-Prop $p $ki @("$($b + ([int]$oldi - [int]$old))") }
    }
  }

  # Extra fields from Spoolman: field name = Orca setting, optionally with a
  # nozzle suffix (_d025/_d04/_d06) that takes precedence for the matching variant.
  # pressure_advance (measured by the printer via the load cell) also turns on
  # enable_pressure_advance in Orca.
  $nz = Get-NozzleKey $tpl.Suffix
  $extraVals = Get-ExtraValues $fil.extra $nz
  if ($extraVals.ContainsKey("pressure_advance")) { $extraVals["enable_pressure_advance"] = "1" }
  # Orca stores shrinkage as percent text ("99.5%"); Spoolman holds the plain number.
  foreach ($k in "filament_shrink", "filament_shrinkage_compensation_z") {
    if ($extraVals.ContainsKey($k) -and $extraVals[$k] -notmatch '%$') { $extraVals[$k] = $extraVals[$k] + "%" }
  }
  foreach ($k in @($extraVals.Keys)) {
    if (-not $p.PSObject.Properties[$k]) {
      if (-not $warnedKeys.ContainsKey($k)) { Write-Warning "Extra field '$k' does not exist in the Orca template - ignored."; $warnedKeys[$k] = $true }
      continue
    }
    Set-Prop $p $k @($extraVals[$k])
  }

  $json = ($p | ConvertTo-Json -Depth 20)
  $base = Safe-FileName $name
  $jsonPath = Join-Path $OutDir "$base.json"
  $infoPath = Join-Path $OutDir "$base.info"
  $old = if (Test-Path $jsonPath) { [IO.File]::ReadAllText($jsonPath, $utf8) } else { $null }
  if ($old -eq $json) { $same++; continue }

  $verb = if ($old) { "updated" } else { "new" }
  Write-Host ("  {0,-12} {1}  [{2} -> {3}, #{4}]" -f $verb, $name, $fil.material, $tpl.Name, $hex)
  if (-not $WhatIf) {
    [IO.File]::WriteAllText($jsonPath, $json, $utf8)
    $now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    $info = "sync_info = `nuser_id = `nsetting_id = `nbase_id = `nupdated_time = $now`n"
    [IO.File]::WriteAllText($infoPath, $info, $utf8)
  }
  $written++
  }
}

$pruned = 0
if ($Prune -and (Test-Path $OutDir)) {
  foreach ($f in Get-ChildItem -Path $OutDir -Filter *.json) {
    try { $j = Read-Json $f.FullName } catch { continue }
    if ($j.filament_id -like "PSM*" -and -not $keepIds.ContainsKey($j.filament_id)) {
      Write-Host "  removed      $($j.name)"
      if (-not $WhatIf) {
        Remove-Item -LiteralPath $f.FullName
        $info = [IO.Path]::ChangeExtension($f.FullName, ".info")
        if (Test-Path -LiteralPath $info) { Remove-Item -LiteralPath $info }
      }
      $pruned++
    }
  }
}

$mode = if ($WhatIf) { " (DRY RUN, NOTHING WRITTEN - run without -WhatIf to write)" } else { "" }
Write-Host ("Done{0}: {1} new/changed, {2} unchanged, {3} without template, {4} removed. Target: {5}" -f $mode, $written, $same, $skipped, $pruned, $OutDir)
if ($written -and -not $WhatIf) { Write-Host "Restart OrcaSlicer so the profiles show up." }
