@echo off
REM Round 10 order-flow recorder, started by Windows Task Scheduler (task "IndiaEquity_OrderFlowRecorder", weekdays 09:05).
REM Read-only market data (Angel One SnapQuote). Never places orders. Stops itself at 15:31 IST.
REM Credentials come from the user's environment variables (ANGEL_API_KEY, ANGEL_CLIENT_CODE, ANGEL_PIN, ANGEL_TOTP_SECRET).
cd /d "C:\Users\jeeva\claude-projects\india-equity-intraday-skill"
if not exist trader\ticks_r10 mkdir trader\ticks_r10
echo %date% %time% task start >> trader\ticks_r10\_task.log
"C:\Python314\python.exe" trader-flows\angel_recorder.py record RELIANCE HDFCBANK ICICIBANK SBIN AXISBANK KOTAKBANK INFY TCS HCLTECH LT "M&M" MARUTI BHARTIARTL ITC HINDUNILVR SUNPHARMA TATASTEEL BAJFINANCE BEL MCX ADANIENT NTPC TITAN ETERNAL BSE --out trader\ticks_r10 >> trader\ticks_r10\_task.log 2>&1
echo %date% %time% task end (exit %errorlevel%) >> trader\ticks_r10\_task.log
