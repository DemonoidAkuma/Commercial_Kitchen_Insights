from config import FOOD_COST_THRESHOLD, WASTE_PERCENT_THRESHOLD

def calculate_waste_percent(waste, revenue):
    if revenue == 0:
        return 0
    return (waste / revenue) * 100

def risk_rating(food_percent, waste_percent, food_target, waste_target):
    food_diff = food_percent - food_target
    waste_diff = waste_percent - waste_target

    if food_diff <= 0 and waste_diff <= 0:
        return "GREEN"

    if (0 < food_diff <= 1) or (0 < waste_diff <= 0.5):
        return "AMBER"

    return "RED"