# run_validation.ps1 - Quick Task 261120-2u1: PostgreSQL 16 Isolated Validation (v4 com parsing XML SelectSingleNode)

$ErrorActionPreference = "SilentlyContinue"

# Task 1: Garantir que o Docker Desktop esteja em execução
$dockerProc = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
if (-not $dockerProc) {
    Write-Host "[1/5] Invocando inicialização do Docker Desktop..."
    Start-Process "C:\Users\Windows Lite BR\AppData\Local\Programs\DockerDesktop\Docker Desktop.exe" -WorkingDirectory "C:\Users\Windows Lite BR\AppData\Local\Programs\DockerDesktop"
} else {
    Write-Host "[1/5] Processo Docker Desktop já está em execução."
}

Write-Host "[1/5] Aguardando prontidão do daemon Docker (até 120s)..."
$dockerReady = $false
for ($i = 0; $i -lt 60; $i++) {
    $null = docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        $dockerReady = $true
        break
    }
    Start-Sleep -Seconds 2
}
if (-not $dockerReady) {
    throw "DOCKER READINESS FAILURE: Daemon Docker não respondeu no tempo limite de 120s."
}
Write-Host "[1/5] Daemon Docker ativo e pronto."

# Task 2, 3 & 4: Ciclo de Vida do Teste e Auditoria
$junitXmlPath = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "viralpanel_pg16_junit_$([System.Guid]::NewGuid().ToString('N')).xml")
$containerStarted = $false
$containerId = $null
$executionError = $null
$cleanupErrors = @()
$testPassed = $false
$junitReportXmlContent = $null

# Snapshot inicial de volumes com validação estrita de exit code
$volumesOutput = docker volume ls -q 2>&1
$lastCode = $LASTEXITCODE
if ($lastCode -ne 0) {
    throw "INITIALIZATION FAILURE: docker volume ls falhou com exit code $lastCode."
}
$volumesBefore = if ($volumesOutput) { @($volumesOutput) } else { @() }
Write-Host "[2/5] Baseline de volumes capturado com sucesso: $($volumesBefore.Count) volume(s) preexistente(s)."

try {
    Write-Host "[2/5] Provisionando contêiner PostgreSQL 16 efêmero em 127.0.0.1:5433..."
    $runOutput = docker run --rm -d --name viralpanel-test-postgres16 `
      -e POSTGRES_USER=postgres `
      -e POSTGRES_PASSWORD=postgres `
      -e POSTGRES_DB=viralpanel_test `
      -p 127.0.0.1:5433:5432 `
      postgres:16 2>&1

    $lastCode = $LASTEXITCODE
    if ($lastCode -ne 0 -or [string]::IsNullOrWhiteSpace($runOutput)) {
        throw "docker run falhou com exit code $lastCode : $runOutput"
    }

    $containerId = $runOutput.Trim()
    $containerStarted = $true
    Write-Host "[2/5] Contêiner iniciado com ID: $containerId"

    Write-Host "[2/5] Aguardando readiness interno do PostgreSQL (pg_isready)..."
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        $res = docker exec viralpanel-test-postgres16 pg_isready -U postgres 2>&1
        if ($LASTEXITCODE -eq 0 -and $res -match "accepting connections") { $ready = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw "PostgreSQL 16 falhou no readiness check interno em 30s." }
    Write-Host "[2/5] PostgreSQL 16 pronto e aceitando conexões internamente."

    Write-Host "[2/5] Consultando versão oficial do PostgreSQL no catálogo..."
    $versionOutput = (docker exec viralpanel-test-postgres16 psql -U postgres -d viralpanel_test -t -c "SELECT version();" 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw "psql falhou ao consultar version() com exit code $LASTEXITCODE : $versionOutput"
    }
    $versionOutput = $versionOutput.Trim()
    Write-Host "[2/5] Versão confirmada: $versionOutput"
    if ($versionOutput -notmatch "PostgreSQL 16") { throw "Versão não é PostgreSQL 16.x" }

    Write-Host "[2/5] Sondando prontidão da porta 127.0.0.1:5433 e autenticação pelo host Windows com driver psycopg2..."
    $env:TEST_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@127.0.0.1:5433/viralpanel_test"
    $env:ALLOW_DESTRUCTIVE_TEST_DATABASE = "true"

    $hostReady = $false
    $lastProbeDiag = ""
    for ($i = 0; $i -lt 30; $i++) {
        $probeDiag = & .venv\Scripts\python.exe -c "
import socket, traceback
from urllib.parse import urlparse
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from tests.test_migrations import get_verified_test_db_url, is_postgres_available
url = get_verified_test_db_url()
parsed = make_url(url)
host = urlparse(url).hostname or parsed.host or '127.0.0.1'
port = parsed.port or 5432
try:
    with socket.create_connection((host, port), timeout=1.0):
        pass
    eng = create_engine(url, connect_args={'connect_timeout': 2})
    with eng.connect() as conn:
        db = conn.execute(text('SELECT current_database()')).scalar()
        if db == 'viralpanel_test':
            print('SUCCESS:viralpanel_test')
        else:
            print('WRONG_DB:' + str(db))
except Exception as e:
    print('PROBE_ERROR:' + repr(e))
" 2>&1
        $lastProbeDiag = ($probeDiag -join " ").Trim()
        if ($lastProbeDiag -match "SUCCESS:viralpanel_test") {
            $hostReady = $true
            break
        }
        Write-Host "[2/5] Aguardando relay de rede do host Windows ($i/30): $lastProbeDiag"
        Start-Sleep -Seconds 1
    }

    if (-not $hostReady) {
        throw "PostgreSQL 16 falhou na conectividade pelo host Windows em 30s. Último diagnóstico: $lastProbeDiag"
    }
    Write-Host "[2/5] Conectividade pelo host Windows comprovada com sucesso!"

    Write-Host "[3/5] Executando pytest com garantias e relatório JUnit XML..."
    & .venv\Scripts\pytest.exe -vv -k "test_postgres_real_migration_and_strict_zero_drift" --junitxml="$junitXmlPath" tests/test_migrations.py
    $pytestExitCode = $LASTEXITCODE

    Write-Host "[3/5] pytest exit code: $pytestExitCode"
    if ($pytestExitCode -ne 0) {
        throw "Teste pytest falhou com exit code $pytestExitCode"
    }

    if (-not (Test-Path $junitXmlPath)) {
        throw "Relatório JUnit XML não foi gerado em $junitXmlPath"
    }

    $junitReportXmlContent = Get-Content $junitXmlPath -Raw
    [xml]$parsedXml = $junitReportXmlContent
    $suite = $parsedXml.SelectSingleNode("//testsuite")
    if (-not $suite) {
        throw "Nenhum elemento <testsuite> encontrado no XML de relatório."
    }

    $totalTests = [int]$suite.GetAttribute("tests")
    $totalFailures = [int]$suite.GetAttribute("failures")
    $totalErrors = [int]$suite.GetAttribute("errors")
    $totalSkipped = [int]$suite.GetAttribute("skipped")

    Write-Host "[3/5] Métricas JUnit XML: tests=$totalTests, failures=$totalFailures, errors=$totalErrors, skipped=$totalSkipped"

    if ($totalTests -ne 1 -or $totalFailures -ne 0 -or $totalErrors -ne 0 -or $totalSkipped -ne 0) {
        throw "Validação JUnit XML falhou! Esperado: tests=1, failures=0, errors=0, skipped=0. Obtido: tests=$totalTests, failures=$totalFailures, errors=$totalErrors, skipped=$totalSkipped"
    }

    $testPassed = $true

} catch {
    $executionError = $_
    Write-Error "[EXECUTION ERROR] $($executionError.Exception.Message)"
} finally {
    Write-Host "[4/5] Executando descarte e limpeza compulsória..."
    $env:TEST_DATABASE_URL = $null
    $env:ALLOW_DESTRUCTIVE_TEST_DATABASE = $null

    if ($containerStarted) {
        Write-Host "[4/5] Parando e removendo contêiner $containerId..."
        if ($containerId) { $null = docker stop $containerId 2>&1 }
        $null = docker stop viralpanel-test-postgres16 2>&1
        $null = docker rm -f viralpanel-test-postgres16 2>&1
    }

    Write-Host "[4/5] Executando auditoria incondicional de descarte..."
    if ($containerId) {
        $remById = docker ps -a --filter "id=$containerId" -q 2>&1
        $code = $LASTEXITCODE
        if ($code -ne 0) {
            $cleanupErrors += "DOCKER AUDIT FAILURE: docker ps (por ID) falhou com exit code $code."
        } elseif ($remById) {
            $cleanupErrors += "Contêiner ainda existe no Docker por ID: $remById"
        }
    }

    $remByName = docker ps -a --filter "name=viralpanel-test-postgres16" -q 2>&1
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        $cleanupErrors += "DOCKER AUDIT FAILURE: docker ps (por Nome) falhou com exit code $code."
    } elseif ($remByName) {
        $cleanupErrors += "Contêiner ainda existe no Docker por Nome: $remByName"
    }

    $volumesAfter = @(docker volume ls -q 2>&1)
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        $cleanupErrors += "DOCKER AUDIT FAILURE: docker volume ls falhou com exit code $code."
    } else {
        $newVolumes = Compare-Object -ReferenceObject $volumesBefore -DifferenceObject $volumesAfter | Where-Object { $_.SideIndicator -eq "=>" }
        if ($newVolumes) {
            $cleanupErrors += "Novo(s) volume(s) órfão(s) criado(s): $($newVolumes.InputObject -join ', ')"
        }
    }

    $listener = Get-NetTCPConnection -LocalPort 5433 -State Listen -ErrorAction SilentlyContinue
    if ($listener) {
        $cleanupErrors += "Porta 5433 ainda possui listener ativo em State Listen!"
    }

    if ($env:TEST_DATABASE_URL -ne $null -or $env:ALLOW_DESTRUCTIVE_TEST_DATABASE -ne $null) {
        $cleanupErrors += "Variáveis de ambiente não foram anuladas!"
    }

    if ($junitXmlPath -and (Test-Path $junitXmlPath)) {
        Remove-Item -Path $junitXmlPath -Force -ErrorAction SilentlyContinue
    }

    Write-Host "`n================ EXECUTION REPORT ================"
    Write-Host "Status da Execução do Teste: $(if ($testPassed) { 'PASSED' } else { 'FAILED' })"
    if ($executionError) {
        Write-Host "Detalhe do Erro de Execução: $($executionError.Exception.Message)"
    }

    Write-Host "`n================ CLEANUP AUDIT REPORT ================"
    if ($cleanupErrors.Count -eq 0) {
        Write-Host "Status da Auditoria de Limpeza: CLEAN (Todos os recursos liberados, 0 vazamentos, estado do Docker comprovado)"
    } else {
        Write-Error "OPERATIONAL SECURITY FAILURE: Auditoria de limpeza falhou!`n$($cleanupErrors -join "`n")"
    }
    Write-Host "=====================================================`n"

    if ($executionError) {
        throw $executionError
    }
    if ($cleanupErrors.Count -gt 0) {
        throw "OPERATIONAL SECURITY FAILURE: Falha na verificação de limpeza."
    }
}
