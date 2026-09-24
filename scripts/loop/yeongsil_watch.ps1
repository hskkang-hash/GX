# GuardianX 영실 감시기 v1.0 — LOOP_STATE.json 을 5분마다 읽어 wo_ready 면 Claude Code 를 헤드리스로 띄운다.
# 등록: schtasks /Create /TN "GuardianX-Yeongsil" /TR "powershell -NoProfile -ExecutionPolicy Bypass -File C:\GuardianX\guardianx-source\scripts\loop\yeongsil_watch.ps1" /SC ONLOGON /RL HIGHEST /F
# 멈춤: LOOP_STATE.json 의 "pause": true  또는  schtasks /End /TN "GuardianX-Yeongsil"
$ErrorActionPreference = 'Continue'
$Repo      = 'C:\GuardianX\guardianx-source'
$State     = Join-Path $Repo 'docs\agent\loop\LOOP_STATE.json'
$Inbox     = Join-Path $Repo 'docs\agent\loop\CEO_INBOX.md'
$Prompt    = Join-Path $Repo 'scripts\loop\yeongsil_prompt.txt'
$Settings  = Join-Path $Repo 'scripts\loop\headless.settings.json'
$LogDir    = Join-Path $Repo 'docs\agent\loop\logs'
$PollSec   = 300          # 5분
$WorkStart = 8            # 08:00 KST 부터
$WorkEnd   = 22           # 22:00 KST 까지 (착수 기준)
$MaxTurnsPerDay = 3
$MaxTurnsClaude = 400     # claude -p --max-turns (도구 호출 상한 · 4.5시간 턴에 여유)
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Read-State { try { Get-Content $State -Raw -Encoding UTF8 | ConvertFrom-Json } catch { $null } }
function Write-State($s, $phase, $by, $extra) {
  $s.phase = $phase; $s.updated_by = $by; $s.updated_at = (Get-Date).ToString('yyyy-MM-ddTHH:mm:sszzz')
  if ($extra) { foreach ($k in $extra.Keys) { $s | Add-Member -NotePropertyName $k -NotePropertyValue $extra[$k] -Force } }
  $s | ConvertTo-Json -Depth 5 | Set-Content $State -Encoding UTF8
}
function Log($msg) { $line = "[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg; Write-Host $line; Add-Content (Join-Path $LogDir 'watch.log') $line -Encoding UTF8 }
function PushPending { try { (git -C $Repo log --oneline origin/turn-q..turn-q 2>$null | Measure-Object -Line).Lines } catch { -1 } }
function InboxAnswered($since) { try { (Get-Item $Inbox).LastWriteTime -gt $since } catch { $false } }

Log "감시기 시작 · repo=$Repo · poll=${PollSec}s · 창 ${WorkStart}~${WorkEnd}시 · 하루 ${MaxTurnsPerDay}턴"
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) { Log "claude CLI 가 없다 — npm i -g @anthropic-ai/claude-code 뒤 다시 시작"; exit 1 }

while ($true) {
  $s = Read-State
  if (-not $s) { Log "LOOP_STATE.json 을 읽지 못함"; Start-Sleep $PollSec; continue }
  if ($s.pause -eq $true) { Start-Sleep $PollSec; continue }
  $now = Get-Date
  $pending = PushPending
  if ($pending -ge 3) { Log "push 대기 $pending 커밋 — 대표 손(따라하기 ②)" }

  switch ($s.phase) {
    'wo_ready' {
      if ($now.Hour -lt $WorkStart -or $now.Hour -ge $WorkEnd) { break }
      $today = $now.ToString('yyyy-MM-dd')
      if ($s.turns_day -ne $today) { $s | Add-Member -NotePropertyName turns_day -NotePropertyValue $today -Force; $s.turns_today = 0 }
      if ([int]$s.turns_today -ge $MaxTurnsPerDay) { Log "오늘 턴 상한 $MaxTurnsPerDay 도달 — 내일"; Start-Sleep 3600; break }
      $turn = $s.next_turn; if (-not $turn) { $turn = $s.turn }
      $log = Join-Path $LogDir ("{0}_{1}.log" -f $turn, $now.ToString('yyyyMMdd_HHmm'))
      Log "착수 · 턴 $turn · wo=$($s.wo) · 로그=$log"
      $s.turn = $turn; $s.turns_today = [int]$s.turns_today + 1
      Write-State $s 'code_running' 'watcher' @{ started_at = $now.ToString('s') }
      $p = Get-Content $Prompt -Raw -Encoding UTF8
      Push-Location $Repo
      try {
        & claude -p $p --settings $Settings --permission-mode acceptEdits --max-turns $MaxTurnsClaude --output-format text 2>&1 | Tee-Object -FilePath $log
      } finally { Pop-Location }
      $tail = (Get-Content $log -Tail 40 -ErrorAction SilentlyContinue) -join "`n"
      $s2 = Read-State
      if ($tail -match '429|rate limit|usage limit|한도') {
        Write-State $s2 'rate_limited' 'watcher' @{ retry_after = $now.AddHours(1).ToString('s') }; Log "한도 감지 → rate_limited"
      } elseif ($s2.phase -eq 'code_running') {
        # 영실이 상태를 못 바꾸고 끝났다 — 보고서가 있으면 report_ready, 없으면 대표에게
        $rep = Get-ChildItem (Join-Path $Repo 'docs\workorders') -Filter '*_report*.md' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($rep -and $rep.LastWriteTime -gt $now) { Write-State $s2 'report_ready' 'watcher' @{ report = ('docs/workorders/' + $rep.Name) }; Log "보고서 발견 → report_ready" }
        else { Write-State $s2 'waiting_ceo' 'watcher' @{ ceo_question = '영실 헤드리스가 보고서 없이 끝남 — 로그 확인 필요' }; Log "보고서 없이 종료 → waiting_ceo" }
      }
      Log "종료 · phase=$((Read-State).phase)"
    }
    'waiting_ceo' {
      $since = [datetime]$s.updated_at
      if (InboxAnswered $since) {
        Log "CEO_INBOX 갱신 감지 → 이어서 착수"
        Write-State $s 'wo_ready' 'watcher' @{ notes = '대표 답 뒤 재착수' }
      }
    }
    'rate_limited' {
      if ($s.retry_after -and $now -gt [datetime]$s.retry_after) { Write-State $s 'wo_ready' 'watcher' @{ retry_after = $null }; Log "한도 해제 시각 지남 → wo_ready" }
    }
    default { }   # code_running(대화형 진행 중) · report_ready(세종 차례) · paused → 기다린다
  }
  Start-Sleep $PollSec
}
