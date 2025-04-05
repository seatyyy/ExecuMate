from flask import Blueprint, jsonify
from langchain_openai import ChatOpenAI
from browser_use import Agent, Browser, BrowserConfig

from dotenv import load_dotenv
import os

import asyncio
# print(os.getenv("OPENAI_API_KEY"))

llm = ChatOpenAI(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

browser = Browser(
    config=BrowserConfig(
        # Specify the path to your Chrome executable
        chrome_instance_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',  # macOS path
        # For Windows, typically: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
        # For Linux, typically: '/usr/bin/google-chrome'
    )
)


# Create a Blueprint for DoorDash routes
doordash_bp = Blueprint('doordash_bp', __name__, url_prefix='/doordash')

@doordash_bp.route('/', methods=['GET'])
async def index():
    agent = Agent(
        task="""
        1. Go to doordash.com
        """,
        # 2. Click on "Orders" in the left sidebar
        # 3. Tell me the last restaurant I ordered from
        llm=llm,
        browser=browser
    )
    result = await agent.run()
    print(result)
    return jsonify({"result": "success"})

# Add other DoorDash specific routes here later
# e.g., @doordash_bp.route('/orders', methods=['GET'])
# def get_orders():
#     # Logic to get DoorDash orders
#     return jsonify({"orders": []})
