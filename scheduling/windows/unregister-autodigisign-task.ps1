[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [ValidatePattern('^[^\\/:*?"<>|\[\]]+$')]
    [string]$TaskName = 'AutoDigiSign',

    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($env:OS -ne 'Windows_NT') {
    throw 'This script can only unregister tasks on Windows.'
}

Import-Module ScheduledTasks -ErrorAction Stop

$ExistingTask = Get-ScheduledTask `
    -TaskPath '\' `
    -TaskName $TaskName `
    -ErrorAction SilentlyContinue
if ($null -eq $ExistingTask) {
    Write-Host "Scheduled task '$TaskName' does not exist; nothing was removed."
    return
}

if ($Force) {
    $ConfirmPreference = 'None'
}

if ($PSCmdlet.ShouldProcess($TaskName, 'Unregister Windows scheduled task')) {
    Unregister-ScheduledTask `
        -TaskPath '\' `
        -TaskName $TaskName `
        -Confirm:$false
    Write-Host "Scheduled task '$TaskName' was removed."
    Write-Host 'Project files, configuration, rosters, and logs were not changed.'
}
