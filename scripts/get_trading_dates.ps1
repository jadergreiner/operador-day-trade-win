# Script para calcular datas de trading (BDI date e TARGET date)
# Uso: powershell -NoProfile -File scripts\get_trading_dates.ps1

$CalendarFile = "data\calendario\feriados_b3.txt"
$holidays = @()

# Carrega feriados do arquivo se existir
if (Test-Path $CalendarFile) {
    $holidays = Get-Content $CalendarFile |
        ForEach-Object { $_.Trim() } |
        Where-Object { $_ -and -not $_.StartsWith('#') }
}

# Define função para verificar se é dia de trading
function IsBusinessDay($date) {
    if ($date.DayOfWeek -eq 'Saturday' -or $date.DayOfWeek -eq 'Sunday') {
        return $false
    }
    if ($holidays -contains $date.ToString('yyyy-MM-dd')) {
        return $false
    }
    return $true
}

# Encontra o dia de trading atual (pulando fins de semana e feriados)
$target = Get-Date
while (-not (IsBusinessDay $target)) {
    $target = $target.AddDays(-1)
}

# Encontra o dia anterior de trading (para BDI)
$bdi = $target.AddDays(-1)
while (-not (IsBusinessDay $bdi)) {
    $bdi = $bdi.AddDays(-1)
}

# Output em formato que o batch pode ler (uma linha com valores separados por vírgula)
Write-Output "$($bdi.ToString('yyyyMMdd')),$($target.ToString('yyyy-MM-dd'))"
