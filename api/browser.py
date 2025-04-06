import asyncio
import json
import os
from distutils.util import strtobool

from browser_use.agent.service import Agent, Controller
from browser_use.browser.browser import Browser, BrowserConfig
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from typing_extensions import Callable, Awaitable


MOCK_BROWSER_AGENT = strtobool(os.environ.get("MOCK_BROWSER_AGENT", "True"))

MOCK_ITEMS = {
  "menu_items": [
    {
      "item_name": "Chicken Kebab",
      "restaurant_name": "Hummus Mediterranean Kitchen",
      "price": 20.25,
      "restaurant_url": "https://www.doordash.com/store/902?cursor=eyJzdG9yZV9wcmltYXJ5X3ZlcnRpY2FsX2lkcyI6WzEsNCwxMDAzMzIsMTc1LDE3NiwxNzcsMTc5LDE5MywxOTVdfQ==&pickup=false",
      "image_url": "https://img.cdn4dd.com/cdn-cgi/image/fit=contain,format=auto,width=800,quality=50/https://doordash-static.s3.amazonaws.com/media/photos/240ebad9-dce0-4a06-874b-7126c9694208-retina-large.jpg",
      "delivery_time": "25 min"
    },
    {
      "item_name": "Chips & Salsa",
      "restaurant_name": "Hummus Mediterranean Kitchen",
      "price": 3.5,
      "restaurant_url": "https://www.doordash.com/store/902?cursor=eyJzdG9yZV9wcmltYXJ5X3ZlcnRpY2FsX2lkcyI6WzEsNCwxMDAzMzIsMTc1LDE3NiwxNzcsMTc5LDE5MywxOTVdfQ==&pickup=false",
      "image_url": "https://img.cdn4dd.com/p/fit=cover,width=1200,format=auto,quality=50/media/yelp/9b23282a-01f7-4169-bbd2-8a5ee8bdea67.jpg",
      "delivery_time": "25 min"
    },
    {
      "item_name": "Crepevine Club",
      "restaurant_name": "Hummus Mediterranean Kitchen",
      "price": 22.95,
      "restaurant_url": "https://www.doordash.com/store/34196?cursor=eyJzdG9yZV9wcmltYXJ5X3ZlcnRpY2FsX2lkcyI6WzEsNCwxNzddfQ==&pickup=false",
      "image_url": "https://img.cdn4dd.com/p/fit=cover,width=1200,format=auto,quality=50/media/photos/137616b9-2018-46ae-8e8a-07d0860926a8-retina-large-jpeg",
      "delivery_time": "25 min"
    }
  ]
}


class MenuItem(BaseModel):
    item_name: str
    restaurant_name: str
    price: float
    restaurant_url: str
    image_url: str
    delivery_time: str


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

    controller = Controller(output_model=MenuItems)
    result = await run_browser_agent(task, controller)
    return result


async def find_2_lunch_options():

    if MOCK_BROWSER_AGENT:
        return MOCK_ITEMS

    task = f"""
    1. Start by going to: https://www.doordash.com/home
    2. Open the first option under 'Fastest near you' category on the same tab/page
    3. From the newly opened tab - extract the restaurant name, restaurant url, delivery time 
    4. From the newly opened page of restaurant - Extract the item name, item price, and item image URL for the top 3 items listed under the ‘Most Ordered’ section. The item URL is critical.   
    """
    controller = Controller(output_model=MenuItems)
    result = await run_browser_agent(task, controller)
    return result.model_dump()


async def run_browser_agent(task: str, controller: Controller):
    """Run the browser-use agent with the specified task."""
    agent = Agent(
        task=task_template.format(task=task),
        browser=browser,
        llm=llm,
        controller=controller
    )

    result = await agent.run()
    await browser.close()
    result = result.final_result()
    if result:
        parsed: MenuItems = MenuItems.model_validate_json(result)
        return parsed
    return None


async def order_food(restaurant_url: str, item_name: str) -> str:
    """Order food from a restaurant.

    Args:
        restaurant_url: URL of the restaurant
        item_name: Name of the item to order
    """

    if MOCK_BROWSER_AGENT:
        return f"Order for '{item_name}' started. Your order is being processed."

    task = f"""
1. Go to {restaurant_url}
2. Put into search field the name of the item: {item_name}
3. Click on {item_name} and wait 2 seconds
4. Click "Add to cart"
5. Wait 3 seconds
6. Click "Cart" button on the top right corner
7. Click on "Continue" in the cart
8. If there are upsell modals, click "Skip"
9. Click "Place order"
"""

    # Start the background task for ordering
    await perform_order(task)

    # Return a message immediately
    return f"Order for '{item_name}' started. Your order is being processed."


async def perform_order(task: str):
    """Perform the actual food ordering in the background."""
    try:
        controller = Controller()
        result = await run_browser_agent(task=task, controller=controller)
        return result
    except Exception as e:
        return "Error when doing the order"

# if __name__ == "__main__":
    # asyncio.run(find_2_lunch_options())

    # asyncio.run(order_food(
    #     restaurant_url=MOCK_ITEMS["menu_items"][0]["restaurant_url"],
    #     item_name=MOCK_ITEMS["menu_items"][0]["item_name"]
    # ))

    # asyncio.run(order_food(restaurant_url="https://www.doordash.com/store/paris-baguette-san-mateo-27651459/39908751/?cursor=eyJzZWFyY2hfaXRlbV9jYXJvdXNlbF9jdXJzb3IiOnsicXVlcnkiOiJjaGVlc2UgY2FrZSIsIml0ZW1faWRzIjpbMTcyODU3NTUyNjAsMTcyODU3NTUyNjIsMjQ0MDE0OTEyMTVdLCJzZWFyY2hfdGVybSI6ImNoZWVzZWNha2UiLCJ2ZXJ0aWNhbF9pZCI6LTk5OSwidmVydGljYWxfbmFtZSI6ImFsbCJ9LCJzdG9yZV9wcmltYXJ5X3ZlcnRpY2FsX2lkcyI6WzEsNCwxNDQsMTc2LDE3NywxOTMsMTk1LDI4NF19&pickup=false",
    #                         item_name="NY Style Cheesecake Slice"))