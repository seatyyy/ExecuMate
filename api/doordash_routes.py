from flask import Blueprint, jsonify
from api.browser import find_2_lunch_options
from logging import getLogger
from traceback import format_exc


logger = getLogger(__name__)

# Create a Blueprint for DoorDash routes
doordash_bp = Blueprint('doordash_bp', __name__, url_prefix='/doordash')

@doordash_bp.route('/', methods=['GET'])
async def index():
    try:
        result = await find_2_lunch_options()
    except Exception as e:
        logger.error("Cannot find 2 lunch options", exc_info=e)
        result = {"error": "Cannot find 2 lunch options"}

    return jsonify(result)

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