import os
import re

# Sky Blue affiliate block to inject
SKYBLUE_BLOCK = '''
<!-- Sky Blue Credit Affiliate Block -->
<div style="background:linear-gradient(135deg,rgba(255,68,68,0.06),rgba(255,204,0,0.04));border:1px solid rgba(255,204,0,0.2);border-radius:16px;padding:24px;margin:24px 0;">
  <div style="font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:rgba(255,204,0,0.7);margin-bottom:10px;">Credit Score Holding You Back?</div>
  <div style="font-size:20px;font-weight:700;color:#f0ede8;margin-bottom:8px;">FIX YOUR CREDIT BEFORE YOU APPLY</div>
  <div style="font-size:13px;color:rgba(240,237,232,0.5);margin-bottom:18px;line-height:1.6;">A low credit score is often the only thing standing between you and loan approval. Professional credit repair can remove incorrect negative items and move your score faster than doing it alone.</div>
  <a href="https://financeratecalc.com/go/credit-repair" target="_blank" rel="noopener sponsored"
     style="display:inline-block;background:linear-gradient(135deg,#1a6644,#44dd88);color:#080810;padding:13px 26px;border-radius:10px;text-decoration:none;font-weight:700;font-size:14px;letter-spacing:0.5px;">
    🔧 Start Credit Repair with Sky Blue →
  </a>
  <div style="font-size:10px;color:rgba(240,237,232,0.2);margin-top:12px;">Sponsored. Commission may be earned. <a href="affiliate-disclosure.html" style="color:rgba(240,237,232,0.2);text-decoration:underline;">Disclosure →</a></div>
</div>
<!-- End Sky Blue Block -->
'''

# Light version for salary/down-payment/refinance pages (lighter styling)
SKYBLUE_BLOCK_LIGHT = '''
<!-- Sky Blue Credit Affiliate Block -->
<div style="background:#f8f4ef;border:1px solid #e0d8cc;border-radius:12px;padding:20px;margin:24px 0;">
  <div style="font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#b8860b;margin-bottom:8px;">Credit Score Too Low?</div>
  <div style="font-size:18px;font-weight:700;color:#2c2a26;margin-bottom:6px;">Fix Your Credit Before You Apply</div>
  <div style="font-size:13px;color:#8a8070;margin-bottom:16px;line-height:1.6;">If your credit score is holding you back from qualifying, professional credit repair can remove incorrect negative items faster than doing it alone.</div>
  <a href="https://financeratecalc.com/go/credit-repair" target="_blank" rel="noopener sponsored"
     style="display:inline-block;background:#2a6b4a;color:#fff;padding:11px 22px;border-radius:8px;text-decoration:none;font-weight:700;font-size:13px;">
    🔧 Start Credit Repair with Sky Blue →
  </a>
  <div style="font-size:10px;color:#c0b8a8;margin-top:10px;">Sponsored. Commission may be earned. <a href="affiliate-disclosure.html" style="color:#c0b8a8;text-decoration:underline;">Disclosure →</a></div>
</div>
<!-- End Sky Blue Block -->
'''

# Priority pages (dark theme) - inject before </body>
PRIORITY_PAGES = [
    'bank-approval-simulator.html',
    'mortgage-readiness-quiz.html',
    'loan-offer-analyzer.html',
    'debt-consolidation-calculator.html',
    'credit-card-payoff-calculator.html',
    'foreclosure-clock.html',
]

# Secondary pages (light theme) - mortgage cities, salary, down-payment, refinance
def is_secondary_page(filename):
    return (
        filename.startswith('mortgage-') and filename != 'mortgage-calculator.html'
        and filename != 'mortgage-glossary.html'
        and filename != 'mortgage-auditor.html'
        and filename != 'mortgage-readiness-quiz.html'
        and filename != 'mortgage-crisis-map.html'
        and filename != 'mortgage-iq.html'
    ) or filename.startswith('can-i-afford-a-house-on-') \
      or filename.startswith('down-payment-for-') \
      or filename.startswith('should-i-refinance') \
      or filename.startswith('salary-to-afford-') \
      or filename.startswith('how-much-house-can-i-afford-')

def already_has_skyblue(content):
    return 'Sky Blue Credit Affiliate Block' in content or 'credit-repair' in content

def inject_block(content, block):
    # Try to inject just before </footer> first
    if '</footer>' in content:
        return content.replace('</footer>', block + '</footer>', 1)
    # Fallback: inject before </body>
    if '</body>' in content:
        return content.replace('</body>', block + '</body>', 1)
    # Last resort: append
    return content + block

def process_file(filepath, block):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if already_has_skyblue(content):
        print(f'  SKIP (already has Sky Blue): {os.path.basename(filepath)}')
        return False
    
    new_content = inject_block(content, block)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f'  OK: {os.path.basename(filepath)}')
    return True

def main():
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    print(f'Working directory: {script_dir}')
    print('=' * 50)
    
    updated = 0
    skipped = 0
    
    # Process priority pages (dark theme block)
    print('\n--- Priority Pages (dark theme) ---')
    for filename in PRIORITY_PAGES:
        filepath = os.path.join(script_dir, filename)
        if os.path.exists(filepath):
            if process_file(filepath, SKYBLUE_BLOCK):
                updated += 1
            else:
                skipped += 1
        else:
            print(f'  NOT FOUND: {filename}')
    
    # Process secondary pages (light theme block)
    print('\n--- Secondary Pages (light theme) ---')
    all_files = [f for f in os.listdir(script_dir) if f.endswith('.html')]
    
    for filename in sorted(all_files):
        if is_secondary_page(filename):
            filepath = os.path.join(script_dir, filename)
            if process_file(filepath, SKYBLUE_BLOCK_LIGHT):
                updated += 1
            else:
                skipped += 1
    
    print('\n' + '=' * 50)
    print(f'Done! Updated: {updated} files | Skipped: {skipped} files')

if __name__ == '__main__':
    main()
