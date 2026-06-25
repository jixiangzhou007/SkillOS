"""SkillOS E2E test — Playwright automated testing."""
import sys, os, time
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:8765'
SCREENSHOTS = os.path.join(os.path.dirname(__file__), 'e2e_screenshots')
os.makedirs(SCREENSHOTS, exist_ok=True)

def screenshot(page, name):
    path = os.path.join(SCREENSHOTS, name)
    page.screenshot(path=path, full_page=True)
    print(f'  [SCREENSHOT] {name}')

errors = []
def log_error(msg):
    errors.append(msg)
    try:
        print(f'  [ERROR] {msg}')
    except UnicodeEncodeError:
        print(f'  [ERROR] {msg.encode("ascii", "replace").decode("ascii")}')

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        headless=True
    )
    context = browser.new_context(viewport={'width': 1440, 'height': 900})
    page = context.new_page()

    # Capture all console output for debugging
    page.on('console', lambda msg: print(f'  [CONSOLE {msg.type}] {msg.text[:150]}') if msg.type in ('error','warning') else None)
    page.on('pageerror', lambda err: print(f'  [PAGE ERROR] {err.message[:200]}'))
    page.on('requestfailed', lambda req: print(f'  [REQ FAIL] {req.url[:100]}'))

    # ════════════════════════════════════════════════════
    # 1. LOGIN PAGE
    # ════════════════════════════════════════════════════
    print('\n=== 1. LOGIN PAGE ===')
    page.goto(f'{BASE}/login.html', wait_until='domcontentloaded')
    page.wait_for_timeout(500)
    screenshot(page, '01-login.png')

    # Check form elements
    if page.locator('#user').is_visible():
        print('  [OK] Login form visible')
    else:
        log_error('Login form not visible')

    if page.locator('#pass').is_visible():
        print('  [OK] Password field visible')
    else:
        log_error('Password field not visible')

    btn_primary = page.locator('.btn-primary')
    btn_secondary = page.locator('.btn-secondary')
    print(f'  [OK] Login button: {btn_primary.is_visible()}, Register button: {btn_secondary.is_visible()}')

    # Register test user
    test_user = f'test_{int(time.time()) % 10000}'
    test_pass = 'test1234'
    page.fill('#user', test_user)
    page.fill('#pass', test_pass)
    btn_secondary.click()
    page.wait_for_timeout(2000)

    # Check redirect or error
    if 'login' not in page.url:
        print(f'  [OK] Registered & redirected to: {page.url[:60]}')
    else:
        # Check error message
        error_el = page.locator('#error')
        if error_el.text_content():
            print(f'  [WARN] Register/lLogin returned: {error_el.text_content()[:80]}')
            # Try login instead
            page.fill('#user', test_user)
            page.fill('#pass', test_pass)
            btn_primary.click()
            page.wait_for_timeout(2000)

    # ════════════════════════════════════════════════════
    # 2. MAIN PAGE / WELCOME SCREEN
    # ════════════════════════════════════════════════════
    print('\n=== 2. MAIN PAGE ===')
    page.goto(f'{BASE}/', wait_until='domcontentloaded')
    page.wait_for_timeout(3000)
    screenshot(page, '02-main.png')

    # Check welcome screen
    welcome = page.locator('.welcome')
    if welcome.is_visible():
        title = page.locator('.welcome-title').text_content()
        try: print(f'  [OK] Welcome visible: "{title}"')
        except: print(f'  [OK] Welcome visible (unicode title)')
    else:
        log_error('Welcome screen not visible')

    # Check sidebar sections
    sidebar = page.locator('#sidebar')
    if sidebar.is_visible():
        print('  [OK] Sidebar visible')
    else:
        log_error('Sidebar not visible')

    # Check sidebar sections exist
    sections = page.locator('#sidebar .sb-section-header').all()
    print(f'  [OK] Sidebar sections: {len(sections)}')
    for s in sections:
        txt = s.text_content()[:30]
        try: print(f'     - {txt}')
        except: print(f'     - [unicode]')

    # Check recent skills
    recent = page.locator('#welcome-recent-skills')
    recent_skills = page.locator('.welcome-skill-chip').all()
    print(f'  [OK] Recent skill chips: {len(recent_skills)}')

    # Check chat input
    inp = page.locator('#input')
    if inp.is_visible():
        print('  [OK] Chat input visible')
    else:
        log_error('Chat input not visible')

    # ════════════════════════════════════════════════════
    # 3. CHAT / EXTRACTION
    # ════════════════════════════════════════════════════
    print('\n=== 3. CHAT ===')
    page.fill('#input', '你好')
    page.click('#send-btn')
    page.wait_for_timeout(3000)
    screenshot(page, '03-chat-hello.png')

    msgs = page.locator('.msg').all()
    print(f'  [OK] Messages in chat: {len(msgs)}')
    for m in msgs[-3:]:
        role = 'user' if 'user' in (m.get_attribute('class') or '') else 'ai' if 'ai' in (m.get_attribute('class') or '') else 'sys'
        text = m.text_content()[:60]
        print(f'     [{role}] {text}')

    # Check extraction
    if page.locator('#workspace-phase').is_visible():
        phase_text = page.locator('#wp-badge').text_content()
        print(f'  [OK] Extraction phase bar visible: "{phase_text}"')
    else:
        print('  [INFO] Extraction phase bar not shown (may need specific message)')

    # ════════════════════════════════════════════════════
    # 4. SETTINGS PAGE
    # ════════════════════════════════════════════════════
    print('\n=== 4. SETTINGS ===')
    # Click settings in sidebar tools
    settings_btn = page.locator('#sidebar .sb-nav-item:has-text("设置")')
    if settings_btn.count() > 0:
        settings_btn.first.click()
        page.wait_for_timeout(1000)
    else:
        # Try from nav or direct navigation
        page.evaluate("showSettings()")
        page.wait_for_timeout(1000)

    screenshot(page, '04-settings-model.png')

    # Model tab
    model_cards = page.locator('.model-card, [x-for*="models"] > div').all()
    if len(model_cards) == 0:
        # Try finding model cards by looking for labels
        model_cards = page.locator('#settings-view').locator('text=DeepSeek').all()
    print(f'  [OK] Model cards found: {len(model_cards)}')

    # Wait for model list to render (now uses native JS, not Alpine)
    page.wait_for_selector('#model-list-container .model-card', timeout=5000)
    page.wait_for_timeout(500)
    # Click edit button - find the first nav-sm button with "编辑"
    edit_btn = page.locator('#model-list-container button:has-text("编辑")').first
    if edit_btn.count() > 0:
        print(f'  [INFO] Edit button found, clicking...')
        edit_btn.click()
        page.wait_for_timeout(800)
        screenshot(page, '04b-model-modal.png')

        # Check modal
        modal = page.locator('.modal-overlay[style*="flex"], .modal-overlay.open, .modal-box')
        if modal.count() > 0:
            print('  [OK] Model edit modal opened')
            # Click cancel
            cancel = page.locator('.modal-btn-cancel').first
            if cancel.is_visible():
                cancel.click()
                page.wait_for_timeout(500)
                print('  [OK] Modal closed')
        else:
            log_error('Model edit modal did not open')
    else:
        log_error('Edit button not found on model cards')

    # Test other tabs
    for tab_name in ['用量', '技能', '语音']:
        tab = page.locator(f'.tab:has-text("{tab_name}")')
        if tab.count() > 0:
            tab.first.click()
            page.wait_for_timeout(500)
            print(f'  [OK] Switched to tab: {tab_name}')

    screenshot(page, '04c-settings-voice.png')

    # ════════════════════════════════════════════════════
    # 5. SKILL DETAIL
    # ════════════════════════════════════════════════════
    print('\n=== 5. SKILL DETAIL ===')
    # Go back to chat, then click a skill from sidebar
    page.evaluate("showChat()")
    page.wait_for_timeout(500)

    # Find skill names in sidebar
    skill_items = page.locator('#skill-list .tree-name, #skill-list .skill-card .name').all()
    if len(skill_items) > 0:
        skill_name = skill_items[0].text_content()
        print(f'  [INFO] Clicking skill: {skill_name[:30]}')
        skill_items[0].click()
        page.wait_for_timeout(1000)

        # Check detail view
        detail_view = page.locator('#detail-view')
        if detail_view.is_visible() or page.locator('#d-name').is_visible():
            dname = page.locator('#d-name').text_content()
            print(f'  [OK] Detail view opened: "{dname}"')
            screenshot(page, '05-skill-detail.png')

            # Check tabs
            tabs = page.locator('#detail-tabs .dt').all()
            print(f'  [OK] Detail tabs: {len(tabs)}')
            for t in tabs[:5]:
                print(f'     - {t.text_content()[:20]}')

            # Check quality strip
            qstrip = page.locator('#quality-strip-container')
            if qstrip.is_visible() or qstrip.inner_text():
                print(f'  [OK] Quality strip: {qstrip.inner_text()[:60]}')
        else:
            log_error('Detail view did not open')
    else:
        print('  [INFO] No skills in sidebar to click')

    # ════════════════════════════════════════════════════
    # 6. KNOWLEDGE VIEW
    # ════════════════════════════════════════════════════
    print('\n=== 6. KNOWLEDGE VIEW ===')
    # Click knowledge in sidebar
    kb_btn = page.locator('#sidebar .sb-nav-item:has-text("仪表盘")')
    if kb_btn.count() > 0:
        kb_btn.first.click()
    else:
        page.evaluate("showUnifiedKnowledge('dashboard')")
    page.wait_for_timeout(1500)
    screenshot(page, '06-knowledge-dashboard.png')

    kb_tabs = page.locator('#knowledge-tabs .kt').all()
    print(f'  [OK] Knowledge tabs: {len(kb_tabs)}')

    # Try switching to knowledge tab
    kb_tab = page.locator('#knowledge-tabs .kt:has-text("知识库")')
    if kb_tab.count() > 0:
        kb_tab.first.click()
        page.wait_for_timeout(1000)
        print('  [OK] Switched to knowledge browser')

    # ════════════════════════════════════════════════════
    # 7. GLOBAL SEARCH
    # ════════════════════════════════════════════════════
    print('\n=== 7. GLOBAL SEARCH ===')
    page.evaluate("showChat()")
    page.wait_for_timeout(300)
    search = page.locator('#global-search')
    if search.is_visible():
        search.fill('test')
        page.wait_for_timeout(1000)
        panel = page.locator('#global-search-panel')
        if panel.is_visible():
            print('  [OK] Search panel opened')
        else:
            print('  [INFO] Search panel not visible (may need results)')
        search.fill('')
        page.keyboard.press('Escape')

    # ════════════════════════════════════════════════════
    # FINAL REPORT
    # ════════════════════════════════════════════════════
    print('\n═══════════════════════════════════════')
    print(f'  ERRORS: {len(errors)}')
    for e in errors:
        print(f'    {e[:120]}')
    print(f'  Screenshots: {SCREENSHOTS}')
    print('═══════════════════════════════════════')

    browser.close()

sys.exit(1 if errors else 0)
