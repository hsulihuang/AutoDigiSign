[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [ValidatePattern('^[^\\/:*?"<>|\[\]]+$')]
    [string]$TaskName = 'AutoDigiSign',

    [ValidateNotNullOrEmpty()]
    [string]$DailyTimes = '06:30,13:00,16:50,20:00,23:30',

    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($env:OS -ne 'Windows_NT') {
    throw 'This script can only register tasks on Windows.'
}

Import-Module ScheduledTasks -ErrorAction Stop

$ProjectRoot = (Resolve-Path -LiteralPath (
    Join-Path $PSScriptRoot '..\..'
)).Path
$LauncherPath = Join-Path $ProjectRoot 'launcher_win64.bat'
$PythonPath = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$PackageEntryPath = Join-Path $ProjectRoot 'src\autodigisign\__main__.py'

foreach ($RequiredFile in @($LauncherPath, $PythonPath, $PackageEntryPath)) {
    if (-not (Test-Path -LiteralPath $RequiredFile -PathType Leaf)) {
        throw "Required file not found: $RequiredFile"
    }
}

$TimeTokens = @(
    $DailyTimes -split '[,;\s]+' |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
)
if ($TimeTokens.Count -eq 0) {
    throw 'At least one daily time is required.'
}

$NormalizedTimes = @(
    foreach ($TimeToken in $TimeTokens) {
        try {
            $ParsedTime = [DateTime]::ParseExact(
                $TimeToken,
                'HH:mm',
                [Globalization.CultureInfo]::InvariantCulture,
                [Globalization.DateTimeStyles]::None
            )
        }
        catch [FormatException] {
            throw (
                "Invalid daily time '$TimeToken'. " +
                'Use 24-hour HH:mm format, for example 06:30 or 13:00.'
            )
        }
        $ParsedTime.ToString(
            'HH:mm',
            [Globalization.CultureInfo]::InvariantCulture
        )
    }
) | Sort-Object -Unique

$CurrentUser = [Security.Principal.WindowsIdentity]::GetCurrent().Name
if ([string]::IsNullOrWhiteSpace($CurrentUser)) {
    throw 'The current Windows user could not be determined.'
}

$Triggers = @(
    foreach ($TimeText in $NormalizedTimes) {
        $ParsedTime = [DateTime]::ParseExact(
            $TimeText,
            'HH:mm',
            [Globalization.CultureInfo]::InvariantCulture,
            [Globalization.DateTimeStyles]::None
        )
        $StartAt = [DateTime]::Today.Add($ParsedTime.TimeOfDay)
        New-ScheduledTaskTrigger -Daily -At $StartAt
    }
)

$CmdPath = Join-Path $env:SystemRoot 'System32\cmd.exe'
$ActionArguments = '/d /c ""{0}" --scheduled"' -f $LauncherPath
$Action = New-ScheduledTaskAction `
    -Execute $CmdPath `
    -Argument $ActionArguments `
    -WorkingDirectory $ProjectRoot
$Principal = New-ScheduledTaskPrincipal `
    -UserId $CurrentUser `
    -LogonType Interactive `
    -RunLevel Limited
$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 4) `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries
$Description = (
    'Runs AutoDigiSign for the signed-in user every day at {0}. ' +
    'The card, PCSC reader, HCAServiSign, and interactive desktop must be ready.'
) -f ($NormalizedTimes -join ', ')
$Task = New-ScheduledTask `
    -Action $Action `
    -Trigger $Triggers `
    -Principal $Principal `
    -Settings $Settings `
    -Description $Description

$ExistingTask = Get-ScheduledTask `
    -TaskPath '\' `
    -TaskName $TaskName `
    -ErrorAction SilentlyContinue
if ($null -ne $ExistingTask -and -not $Force) {
    throw (
        "Scheduled task '$TaskName' already exists. " +
        'Run this script again with -Force to replace it.'
    )
}

$Operation = if ($null -eq $ExistingTask) {
    'Register Windows scheduled task'
}
else {
    'Replace Windows scheduled task'
}

if ($PSCmdlet.ShouldProcess($TaskName, $Operation)) {
    $RegisterParameters = @{
        TaskName = $TaskName
        TaskPath = '\'
        InputObject = $Task
    }
    if ($null -ne $ExistingTask) {
        $RegisterParameters['Force'] = $true
    }
    Register-ScheduledTask @RegisterParameters | Out-Null

    Write-Host "Scheduled task '$TaskName' was registered for $CurrentUser."
    Write-Host "Daily trigger times: $($NormalizedTimes -join ', ')"
    Write-Host 'The task runs only while this user is logged on.'
}
