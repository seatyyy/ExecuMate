import asyncio

from browser_use.agent.service import Agent, Controller
from browser_use.browser.browser import Browser, BrowserConfig
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from typing_extensions import Callable, Awaitable


class MenuItem(BaseModel):
    item_name: str
    restaurant_name: str
    price: float
    url: str
    image_url: str


class MenuItems(BaseModel):
    menu_items: list[MenuItem]


browser = Browser(
    config=BrowserConfig(
        headless=True,
        cdp_url="http://localhost:9222"
        # chrome_instance_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',  # macOS path
    )
)

# llm = ChatAnthropic(model_name="claude-3-7-sonnet-20250219")
llm = ChatOpenAI(model="gpt-4o")

task_template = """
perform the following task
{task}
"""

async def find_ice_cream():
    query = "cherry ice cream"
    return await find_something(query=query)


async def find_something(query: str):
    task = f"""
        0. Start by going to: https://www.doordash.com/home
        1. Type "{query}" in the global search bar and press enter
        2. Go to the first search result (this is the most popular restaurant).
        3. When you can see the menu options for the resturant, we need to use the specific search input for the resturant located under the banner (identify it by the placeholder "Search [restaurant name]"
        4. Click the input field and type "{query}", then press enter
        5. Check for menu options related to "{query}"
        6. Get the name, url, price and image url of the top 3 items related to "{query}". URL is very important
        """

    result = await run_browser_agent(task)
    return result


async def find_2_lunch_options():
    task = f"""
    0. Start by going to: https://www.doordash.com/home
    1. Open the first option under 'Try something new' category on the same tab/page
    2. From the newly opened tab - extract the restaurant name
    3. From the newly opened page of restaurant - Extract the item name, item URL, item price, and item image URL for the top 3 items listed under the ‘Most Ordered’ section. The item URL is critical.   
    """
    result = await run_browser_agent(task)
    return result

async def run_browser_agent(task: str, on_step: Callable[[], Awaitable[None]] = None):
    """Run the browser-use agent with the specified task."""
    agent = Agent(
        task=task_template.format(task=task),
        browser=browser,
        llm=llm,
        register_new_step_callback=on_step,
        register_done_callback=on_step,
        controller=Controller(output_model=MenuItems)
    )

    result = await agent.run()
    await browser.close()
    result = result.final_result()
    if result:
        parsed: MenuItems = MenuItems.model_validate_json(result)
        return parsed
    return []


if __name__ == "__main__":
    asyncio.run(find_2_lunch_options())