from flask import Blueprint, jsonify
from langchain_openai import ChatOpenAI
from browser_use import Agent, Browser, BrowserConfig, Controller
from pydantic import BaseModel
import os


llm = ChatOpenAI(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

browser = Browser(
    config=BrowserConfig(
        chrome_instance_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',  # macOS path
    )
)

# Create a Blueprint for DoorDash routes
doordash_bp = Blueprint('doordash_bp', __name__, url_prefix='/doordash')


class MenuItem(BaseModel):
    item_name: str
    restaurant_name: str
    price: float
    url: str
    image_url: str

class MenuItems(BaseModel):
    menu_items: list[MenuItem]




@doordash_bp.route('/', methods=['GET'])
async def index():
    controller = Controller(output_model=MenuItems)
    agent = Agent(
        task="""
        1. Go to ubereats.com
        2. Open the first restaurant option and extract info on the first liked / recommended item on their menu
        3. Go back to the home page, open the second restaurant, and extract info about the first item on the menu
        """,
        llm=llm,
        browser=browser,
        controller=controller
    )
    history = await agent.run()

    result = history.final_result()
    if result:
        parsed: MenuItems = MenuItems.model_validate_json(result)

        for item in parsed.menu_items:
            print('\n--------------------------------')
            print(f'Item Name:        {item.item_name}')
            print(f'Restaurant Name:  {item.restaurant_name}')
            print(f'Price:            {item.price}')
            print(f'URL:              {item.url}')
            print(f'Image URL:        {item.image_url}')
    else:
        print('No result')
    return result

# Add other DoorDash specific routes here later
# e.g., @doordash_bp.route('/orders', methods=['GET'])
# def get_orders():
#     # Logic to get DoorDash orders
#     return jsonify({"orders": []})


# """
#         1. Go to ubereats.com
#         2. Click the hamburger menu on the left, then "Orders"
#         3. Tell me the last restaurant I ordered from
#         """,