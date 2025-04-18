from flask import Blueprint, jsonify, request
from pydantic import BaseModel

from api.browser import find_2_lunch_options, order_food
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

@doordash_bp.route('/order', methods=['POST'])
async def make_order():
    try:
        data = request.get_json()
        result = await order_food(data.get("restaurant_url"), data.get("item_name"))
    except Exception as e:
        logger.error("Cannot order food", exc_info=e)
        result = {"error": "Cannot order food"}

    return jsonify(result)
