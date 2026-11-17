<#
.SYNOPSIS
  Legt aus den Filamenten in Spoolman eigenstaendige OrcaSlicer-Filamentprofile an.

.DESCRIPTION
  Pro Spoolman-Filament entsteht ein Profil "<Hersteller> <Name> (SM<id>)" mit der
  Filament-ID "PSM<id>". Dieselbe ID schreibt der Drucker (orca_lanes.py) in
  Moonrakers lane_data, so dass Orca beim Filamentabgleich genau dieses Profil waehlt.

  Vorlagen: Pro Material legst du in Orca einmal ein eigenes Filament an
  ("Filament erstellen", kompatibel mit deinem Trident) und nennst es
  "SM-Vorlage <Material>", z.B. "SM-Vorlage PLA", "SM-Vorlage PETG".
  Alle Einstellungen der Vorlage werden uebernommen; aus Spoolman kommen Name,
  Hersteller, Farbe, Duesen- und Betttemperatur, Dichte, Durchmesser und Preis.
  Das Material einer Spoolman-Spule wird der Vorlage mit dem laengsten passenden
  Typ zugeordnet ("PLA+" -> "SM-Vorlage PLA", wenn es keine "PLA+"-Vorlage gibt).

  OrcaSlicer vor dem Lauf schliessen und danach neu starten.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\orca_spoolman_profiles.ps1 -WhatIf
  powershell -ExecutionPolicy Bypass -File .\orca_spoolman_profiles.ps1
  powershell -ExecutionPolicy Bypass -File .\orca_spoolman_profiles.ps1 -Prune
#>
[CmdletBinding()]
param(
  [string]$SpoolmanUrl = "http://spoolman.local:7912",
  # Orca-Ordner fuer eigenstaendige eigene Filamentprofile. Standard: der Ordner,
  # den Orca gerade benutzt (preset_folder in OrcaSlicer.conf; angemeldet =
  # user\<Konto-ID>, sonst user\default).
  [string]$OrcaDir = "",
  # Wo die Vorlagen liegen (Standard: derselbe Ordner)
  [string]$TemplateDir = "",
  # Wohin geschrieben wird (Standard: OrcaDir). Zum Testen einen leeren Ordner angeben.
  [string]$OutDir = "",
  [string]$TemplatePrefix = "SM-Vorlage",
  # Nur anzeigen, nichts schreiben
  [switch]$WhatIf,
  # Profile "PSM..." loeschen, deren Filament es in Spoolman nicht mehr gibt
  [switch]$Prune,
  # Auch archivierte Spoolman-Filamente bzw. solche ohne Spule anlegen
  [switch]$All
)

$ErrorActionPreference = "Stop"
if (-not $WhatIf -and -not $OutDir -and (Get-Process -Name OrcaSlicer -ErrorAction SilentlyContinue)) {
  Write-Host "OrcaSlicer laeuft noch. Bitte Orca schliessen und das Skript erneut starten." -ForegroundColor Red
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
  Write-Host "Orca-Profilordner: user\$folder" -ForegroundColor Cyan
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
    # Orca 2.5 fuehrt manche Werte pro Extruder-Variante als Liste (z.B. 6 Eintraege).
    # Ein einzelner neuer Wert gilt dann fuer alle Eintraege der Vorlage.
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

# "@Voron Trident 350 0.4 nozzle" -> "d04", "0.25" -> "d025", ohne Angabe -> ""
function Get-NozzleKey([string]$suffix) {
  $m = [regex]::Match($suffix, '(\d+(?:\.\d+)?)\s*nozzle')
  if (-not $m.Success) { return "" }
  "d" + ([double]::Parse($m.Groups[1].Value, $inv).ToString("0.###", $inv) -replace '\.', '')
}

# Spoolman speichert Zusatzfelder als JSON-Text ("0.98"). Liefert key -> Wert als
# Orca-Text; ein Feld mit passender Duesen-Endung ueberschreibt das allgemeine.
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

# ---------------------------------------------------------------- Vorlagen
if (-not (Test-Path $TemplateDir)) { throw "Vorlagen-Ordner nicht gefunden: $TemplateDir" }
$templates = @{}
foreach ($f in Get-ChildItem -Path $TemplateDir -Filter *.json) {
  try { $j = Read-Json $f.FullName } catch { continue }
  if ($j.name -notlike "$TemplatePrefix *") { continue }
  if ($j.inherits) { Write-Warning "Vorlage '$($j.name)' erbt von '$($j.inherits)' - bitte als eigenes Filament anlegen. Uebersprungen."; continue }
  $type = [string](Get-First $j "filament_type")
  if (-not $type) { $type = $j.name.Substring($TemplatePrefix.Length).Trim() }
  $gc = (@($j.filament_start_gcode) -join "`n")
  if ($gc -match "SET_ACTIVE_SPOOL") { Write-Warning "Vorlage '$($j.name)' setzt SET_ACTIVE_SPOOL im Filament-Startcode. Das stoert die Spulenzuordnung pro Tool - bitte entfernen." }
  # Orca legt pro Duesen-Variante ein eigenes Profil an ("... @Voron Trident 350 0.4 nozzle").
  # Alle Varianten eines Typs werden gesammelt; jede bekommt ihr eigenes Spoolman-Profil.
  $suffix = ""
  $at = $j.name.LastIndexOf(" @")
  if ($at -ge 0) { $suffix = $j.name.Substring($at) }
  $key = $type.ToUpperInvariant()
  if (-not $templates.ContainsKey($key)) { $templates[$key] = @() }
  $templates[$key] += [pscustomobject]@{ Type = $type; Path = $f.FullName; Name = $j.name; Suffix = $suffix }
}
if ($templates.Count -eq 0) {
  throw "Keine Vorlage gefunden. In Orca pro Material ein eigenes Filament '$TemplatePrefix <Material>' anlegen (z.B. '$TemplatePrefix PLA'). Gesucht in: $TemplateDir"
}
Write-Host ("Vorlagen: " + (($templates.Values | ForEach-Object { $_ } | ForEach-Object { $_.Name }) -join ", "))

function Find-Template([string]$material) {
  $m = ($material + "").Trim().ToUpperInvariant()
  if ($templates.ContainsKey($m)) { return $templates[$m] }
  # laengster Vorlagen-Typ, mit dem das Material beginnt (PLA+ -> PLA, PETG-CF -> PETG)
  $best = $null
  foreach ($k in $templates.Keys) {
    if ($m.StartsWith($k) -and ($best -eq $null -or $k.Length -gt $best.Length)) { $best = $k }
  }
  if ($best) { return $templates[$best] }
  return $null
}

# ---------------------------------------------------------------- Spoolman
$api = $SpoolmanUrl.TrimEnd('/') + "/api/v1"
# PowerShell 5.1 gibt ein JSON-Array als ein Objekt zurueck: per Pipeline entpacken
$filaments = @(Invoke-RestMethod -Uri "$api/filament" -Method Get -TimeoutSec 15 | ForEach-Object { $_ })
$spools = @(Invoke-RestMethod -Uri "$api/spool" -Method Get -TimeoutSec 15 | ForEach-Object { $_ })
$activeFil = @{}
foreach ($s in $spools) { if (-not $s.archived -and $s.filament) { $activeFil[[int]$s.filament.id] = $true } }
Write-Host ("Spoolman: {0} Filamente, {1} davon mit nicht archivierter Spule" -f $filaments.Count, $activeFil.Count)

if (-not $WhatIf -and -not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }

$written = 0; $same = 0; $skipped = 0
$keepIds = @{}
foreach ($fil in $filaments) {
  $fid = [int]$fil.id
  if (-not $All -and -not $activeFil.ContainsKey($fid)) { continue }
  $id = "PSM$fid"
  $keepIds[$id] = $true
  $tplList = Find-Template $fil.material
  if (-not $tplList) { Write-Warning "SM$fid '$($fil.name)': keine Vorlage fuer Material '$($fil.material)'"; $skipped++; continue }

  $vendor = if ($fil.vendor -and $fil.vendor.name) { [string]$fil.vendor.name } else { "" }
  $label = (@($vendor, [string]$fil.name) | Where-Object { $_ }) -join " "
  if (-not $label) { $label = [string]$fil.material }

  # Ein Profil pro Duesen-Variante der Vorlage, alle mit derselben Filament-ID
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
    # Spoolman: Preis pro Spule mit 'weight' Gramm, Orca: Preis pro kg
    Set-Prop $p "filament_cost" @(Num ([double]$fil.price / [double]$fil.weight * 1000.0))
  }
  if ($fil.spool_weight) { Set-Prop $p "filament_spool_weight" @(Num $fil.spool_weight) -OnlyIfExists }

  # Duesentemperatur: Abstand zur ersten Schicht und Bereich aus der Vorlage erhalten
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
  # Betttemperatur fuer alle Plattentypen, die die Vorlage kennt
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

  # Zusatzfelder aus Spoolman: Feldname = Orca-Einstellung, optional mit
  # Duesen-Endung (_d025/_d04/_d06), die fuer die passende Variante Vorrang hat.
  # pressure_advance (vom Drucker per Load-Cell gemessen) schaltet in Orca
  # zusaetzlich enable_pressure_advance ein.
  $nz = Get-NozzleKey $tpl.Suffix
  $extraVals = Get-ExtraValues $fil.extra $nz
  if ($extraVals.ContainsKey("pressure_advance")) { $extraVals["enable_pressure_advance"] = "1" }
  foreach ($k in $extraVals.Keys) {
    if (-not $p.PSObject.Properties[$k]) {
      if (-not $warnedKeys.ContainsKey($k)) { Write-Warning "Zusatzfeld '$k' gibt es in der Orca-Vorlage nicht - ignoriert."; $warnedKeys[$k] = $true }
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

  $verb = if ($old) { "aktualisiert" } else { "neu" }
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
      Write-Host "  entfernt     $($j.name)"
      if (-not $WhatIf) {
        Remove-Item -LiteralPath $f.FullName
        $info = [IO.Path]::ChangeExtension($f.FullName, ".info")
        if (Test-Path -LiteralPath $info) { Remove-Item -LiteralPath $info }
      }
      $pruned++
    }
  }
}

$mode = if ($WhatIf) { " (PROBELAUF, NICHTS GESCHRIEBEN - zum Schreiben ohne -WhatIf starten)" } else { "" }
Write-Host ("Fertig{0}: {1} neu/geaendert, {2} unveraendert, {3} ohne Vorlage, {4} entfernt. Ziel: {5}" -f $mode, $written, $same, $skipped, $pruned, $OutDir)
if ($written -and -not $WhatIf) { Write-Host "OrcaSlicer neu starten, damit die Profile erscheinen." }
