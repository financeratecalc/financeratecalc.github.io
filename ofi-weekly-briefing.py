"""
OFI Weekly Briefing — Auto Email Newsletter
Runs every Monday via GitHub Actions
Sends OFI update to subscriber list
"""

import os, json, requests
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, To

# ─── OFI DATA ─────────────────────────────────────────────────────────────────
def get_current_ofi():
    try:
        url = "https://raw.githubusercontent.com/financeratecalc/financeratecalc.github.io/main/ofi-live-forecasts.json"
        r = requests.get(url, timeout=10)
        data = r.json()
        current = data.get("current_quarter", {})
        return {
            "value": current.get("ofi_actual", 47),
            "label": current.get("label", "MODERATE"),
            "quarter": current.get("quarter", "Q2 2026"),
            "prev": data.get("previous_quarter", {}).get("ofi_actual", 45)
        }
    except:
        return {"value": 47, "label": "MODERATE", "quarter": "Q2 2026", "prev": 45}

def get_lender_spotlight():
    lenders = [
        {"name": "loanDepot", "denial": 37.0, "trend": "↑ rising friction"},
        {"name": "Wells Fargo", "denial": 58.5, "trend": "⚠ very high overlay"},
        {"name": "UWM", "denial": 19.9, "trend": "✓ most accessible"},
        {"name": "PennyMac", "denial": 26.6, "trend": "↓ improving"},
        {"name": "Rocket", "denial": 28.4, "trend": "→ stable"},
    ]
    week = datetime.now().isocalendar()[1]
    return lenders[week % len(lenders)]

def get_state_spotlight():
    states = [
        {"name": "Florida", "ofi": 42, "note": "Re-tightening — SSDI + edge-case profiles squeezed"},
        {"name": "Texas", "ofi": 30, "note": "Lowest friction in nation — best environment for FHA"},
        {"name": "California", "ofi": 51, "note": "Above moderate — self-employed overlay heavy"},
        {"name": "New York", "ofi": 55, "note": "High friction — co-op board layer adds complexity"},
        {"name": "Georgia", "ofi": 38, "note": "Below moderate — improving lender mix"},
    ]
    week = datetime.now().isocalendar()[1]
    return states[week % len(states)]

# ─── EMAIL HTML ───────────────────────────────────────────────────────────────
def build_email(ofi, lender, state, date_str):
    change = ofi["value"] - ofi["prev"]
    change_str = f"+{change}" if change > 0 else str(change)
    change_color = "#e8845a" if change > 0 else "#6bffb8" if change < 0 else "#c8a44a"

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background:#08090c;font-family:'Helvetica Neue',Arial,sans-serif;">
<div style="max-width:580px;margin:0 auto;padding:32px 24px;">

  <!-- Header -->
  <div style="border-bottom:2px solid #c8a44a;padding-bottom:16px;margin-bottom:24px;">
    <div style="font-size:11px;color:#888;letter-spacing:0.1em;text-transform:uppercase;">FinanceRateCalc</div>
    <div style="font-size:22px;font-weight:900;color:#fff;margin-top:4px;">OFI Weekly Briefing</div>
    <div style="font-size:12px;color:#888;margin-top:4px;">{date_str}</div>
  </div>

  <!-- OFI Score -->
  <div style="background:rgba(200,164,74,0.06);border:1px solid rgba(200,164,74,0.2);border-radius:10px;padding:20px;margin-bottom:20px;text-align:center;">
    <div style="font-size:11px;color:#888;text-transform:uppercase;letter-spacing:0.1em;">Overlay Friction Index — {ofi['quarter']}</div>
    <div style="font-size:64px;font-weight:900;color:#c8a44a;line-height:1.1;margin:8px 0;">{ofi['value']}</div>
    <div style="font-size:16px;color:#fff;font-weight:700;">{ofi['label']}</div>
    <div style="font-size:13px;color:{change_color};margin-top:6px;">{change_str} from last period</div>
  </div>

  <!-- What This Means -->
  <div style="margin-bottom:20px;">
    <div style="font-size:11px;color:#c8a44a;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">What This Means</div>
    <div style="font-size:14px;color:#aaa;line-height:1.8;">
      OFI {ofi['value']} signals <strong style="color:#fff;">{ofi['label'].lower()} underwriting friction</strong> in the US mortgage market.
      When OFI rises above 50, lender overlay behavior tightens — the gap between agency guidelines and real-world approvals widens.
      Edge-case profiles (580-620 FICO, SSDI income, self-employed) feel this first.
    </div>
  </div>

  <!-- Lender Spotlight -->
  <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:16px;margin-bottom:16px;">
    <div style="font-size:11px;color:#888;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">Lender Spotlight</div>
    <div style="font-size:15px;font-weight:700;color:#fff;">{lender['name']}</div>
    <div style="font-size:13px;color:#aaa;margin-top:4px;">2024 FHA denial rate: {lender['denial']}% — {lender['trend']}</div>
  </div>

  <!-- State Spotlight -->
  <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:16px;margin-bottom:24px;">
    <div style="font-size:11px;color:#888;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">State Spotlight</div>
    <div style="font-size:15px;font-weight:700;color:#fff;">{state['name']} — OFI {state['ofi']}</div>
    <div style="font-size:13px;color:#aaa;margin-top:4px;">{state['note']}</div>
  </div>

  <!-- CTA -->
  <div style="text-align:center;margin-bottom:24px;">
    <a href="https://financeratecalc.com/ofi.html" 
       style="background:#c8a44a;color:#000;padding:12px 24px;border-radius:7px;font-weight:700;font-size:14px;text-decoration:none;display:inline-block;">
      View Full OFI Dashboard →
    </a>
    &nbsp;
    <a href="https://financeratecalc.com/zai-for-brokers.html"
       style="background:rgba(107,191,146,0.15);color:#6bffb8;padding:12px 24px;border-radius:7px;font-weight:700;font-size:14px;text-decoration:none;display:inline-block;border:1px solid rgba(107,191,146,0.3);">
      Zai for Brokers →
    </a>
  </div>

  <!-- Share -->
  <div style="background:rgba(200,164,74,0.04);border:1px solid rgba(200,164,74,0.1);border-radius:8px;padding:14px;text-align:center;margin-bottom:24px;">
    <div style="font-size:12px;color:#888;">Know a broker or underwriter who'd find this useful?</div>
    <div style="font-size:12px;color:#c8a44a;margin-top:4px;">Forward this email — subscription is free at financeratecalc.com</div>
  </div>

  <!-- Footer -->
  <div style="border-top:1px solid rgba(255,255,255,0.07);padding-top:16px;text-align:center;">
    <div style="font-size:11px;color:#555;line-height:1.8;">
      FinanceRateCalc Research Division · OFI = Overlay Friction Index<br>
      Data: CFPB HMDA 2024 federal public data · Not financial advice<br>
      <a href="https://financeratecalc.com/ofi-methodology.html" style="color:#666;">Methodology</a> · 
      <a href="https://financeratecalc.com/ofi-validation.html" style="color:#666;">AI Validation</a> ·
      <a href="mailto:unsubscribe@financeratecalc.com" style="color:#666;">Unsubscribe</a>
    </div>
  </div>

</div>
</body>
</html>
"""

# ─── SEND ─────────────────────────────────────────────────────────────────────
def send_briefing():
    ofi = get_current_ofi()
    lender = get_lender_spotlight()
    state = get_state_spotlight()
    date_str = datetime.now().strftime("%B %d, %Y")

    html = build_email(ofi, lender, state, date_str)

    # Subscriber listesi — başlangıçta sen + test
    subscribers = [
        "ziya@financeratecalc.com",  # Sen
    ]

    # SendGrid API key env'den
    api_key = os.environ.get("SENDGRID_API_KEY", "")
    if not api_key:
        print("⚠️ SENDGRID_API_KEY not set — saving HTML preview only")
        with open("/tmp/ofi-weekly-preview.html", "w") as f:
            f.write(html)
        print("✅ Preview saved: /tmp/ofi-weekly-preview.html")
        return

    sg = SendGridAPIClient(api_key)
    for email in subscribers:
        message = Mail(
            from_email="ofi@financeratecalc.com",
            to_emails=email,
            subject=f"OFI Weekly — {date_str} | OFI {ofi['value']} ({ofi['label']})",
            html_content=html
        )
        try:
            response = sg.send(message)
            print(f"✅ Sent to {email}: {response.status_code}")
        except Exception as e:
            print(f"❌ Failed {email}: {e}")

if __name__ == "__main__":
    send_briefing()
