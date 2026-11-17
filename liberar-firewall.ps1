# Libera no firewall do Windows o que a gravação pelo Wi-Fi (OTA) precisa.
# Rodar uma vez, no PowerShell como administrador:
#
#   powershell -ExecutionPolicy Bypass -File .\liberar-firewall.ps1
#
# - 3233/TCP de entrada: o ESP32 se conecta de volta ao computador nesta
#   porta para baixar o firmware (o ota.sh fixa a porta com -P 3233).
# - 5353/UDP de entrada: respostas do mDNS, para achar a placa por
#   rsv-medidor-01.local e rsv-controlador-01.local.
#
# O hotspot do celular costuma entrar no Windows como rede "Pública", por
# isso as regras valem para todos os perfis. Para desfazer:
#   Remove-NetFirewallRule -DisplayName "AquaNivel*"

$regras = @(
    @{ Nome = "AquaNivel OTA (3233/TCP)"; Protocolo = "TCP"; Porta = 3233 },
    @{ Nome = "AquaNivel mDNS (5353/UDP)"; Protocolo = "UDP"; Porta = 5353 }
)

foreach ($r in $regras) {
    if (Get-NetFirewallRule -DisplayName $r.Nome -ErrorAction SilentlyContinue) {
        Write-Output "ja existe: $($r.Nome)"
        continue
    }
    New-NetFirewallRule -DisplayName $r.Nome -Direction Inbound -Action Allow `
        -Protocol $r.Protocolo -LocalPort $r.Porta -Profile Any | Out-Null
    Write-Output "criada: $($r.Nome)"
}
