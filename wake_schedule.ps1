param([ValidateSet('agendar', 'cancelar', 'consultar')][string]$Acao)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$taskName = 'Yuna.app - Despertar'
$marker = 'Projeto Yuna: despertar local autorizado pelo usuario.'
try {
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($task -and $task.Description -ne $marker) {
        throw 'Ja existe uma tarefa de outra origem com esse nome.'
    }
    switch ($Acao) {
        'agendar' {
            $at = [datetime]::ParseExact($env:YUNA_WAKE_TIME, 'yyyy-MM-ddTHH:mm:ss', [cultureinfo]::InvariantCulture)
            if ($at -le (Get-Date) -or $at -gt (Get-Date).AddDays(7)) { throw 'Horario invalido.' }
            $rootPath = $env:YUNA_WAKE_ROOT
            $launcher = Join-Path $rootPath 'wake_yuna.py'
            if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) { throw 'Launcher ausente.' }
            if (-not (Test-Path -LiteralPath $env:YUNA_WAKE_PYTHON -PathType Leaf)) { throw 'Python ausente.' }
            $action = New-ScheduledTaskAction -Execute $env:YUNA_WAKE_PYTHON -Argument ('"' + $launcher + '"') -WorkingDirectory $rootPath
            $trigger = New-ScheduledTaskTrigger -Once -At $at
            $settings = New-ScheduledTaskSettingsSet -WakeToRun -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 1)
            $account = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
            $principal = New-ScheduledTaskPrincipal -UserId $account -LogonType Interactive -RunLevel Limited
            $definition = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $marker
            Register-ScheduledTask -TaskName $taskName -InputObject $definition -Force | Out-Null
            @{exists=$true} | ConvertTo-Json -Compress
        }
        'cancelar' {
            if ($task) { Unregister-ScheduledTask -TaskName $taskName -Confirm:$false }
            @{removed=[bool]$task} | ConvertTo-Json -Compress
        }
        'consultar' {
            if ($task) {
                $info = Get-ScheduledTaskInfo -TaskName $taskName
                @{exists=$true;state=[string]$task.State;next_run=$info.NextRunTime.ToString('dd/MM/yyyy HH:mm')} | ConvertTo-Json -Compress
            } else { @{exists=$false} | ConvertTo-Json -Compress }
        }
    }
} catch {
    Write-Error 'Nao foi possivel gerenciar a tarefa de despertar da Yuna.'
    exit 1
}
