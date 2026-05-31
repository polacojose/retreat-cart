from urllib.parse import quote_plus, urlparse

import httpx
from playwright.async_api import async_playwright
from playwright_stealth.stealth import Stealth
from pydantic import SecretStr

_CLUBPLUS_LOGIN_URL = (
    "https://login.clubplus.co.nz/?banner=PNS&channel=WEB&callback_url={}"
)


async def clubplus_authenticate(
    callback_page: str, username: str, password: SecretStr
) -> httpx.AsyncClient:
    async with Stealth().use_async(async_playwright()) as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Navigate to the login page
        await page.goto(_CLUBPLUS_LOGIN_URL.format(quote_plus(callback_page)))

        # Enter the username
        await page.get_by_role("textbox", name="email").fill(username)
        await page.get_by_role("button", name="Continue").click()

        # Wait for password input
        await page.wait_for_selector('input[name="password"]', timeout=5000)

        # Enter password
        async with page.expect_navigation():
            await page.get_by_role("textbox", name="password").fill(
                password.get_secret_value()
            )
            await page.get_by_role("button", name="Continue").click()
            await page.wait_for_url(
                "**{}**".format(urlparse(callback_page).hostname), timeout=10000
            )

        playwright_cookies = await context.cookies()
        user_agent = await page.evaluate("navigator.userAgent")

        await browser.close()

    cookies = {cookie["name"]: cookie["value"] for cookie in playwright_cookies}

    headers = {
        "user-agent": user_agent,
    }

    return httpx.AsyncClient(cookies=cookies, headers=headers)
