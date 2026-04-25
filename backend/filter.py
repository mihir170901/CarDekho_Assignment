import json
from pathlib import Path


def load_cars():
    path = Path(__file__).parent.parent / "data" / "cars.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def filter_cars(cars: list, params: dict) -> list:
    """
    Hard-filter cars by user params. Returns candidates for AI ranking.
    params keys: budget, use_case, seats, fuel, transmission, priority
    """
    budget = params.get("budget")
    seats = params.get("seats")
    fuel = params.get("fuel", "Any")
    transmission = params.get("transmission", "Any")

    results = []
    for car in cars:
        # Budget: allow 10% stretch above stated budget
        if budget:
            limit = float(budget) * 1.10
            if car["price_lakhs"] > limit:
                continue

        # Seating
        if seats:
            required = int(seats)
            if car["seating_capacity"] < required:
                continue

        # Fuel type
        if fuel and fuel.lower() not in ("any", "no preference", ""):
            fuel_norm = fuel.lower().strip()
            car_fuel = car["fuel_type"].lower()
            # Map user shorthand
            mapping = {
                "electric": "electric", "ev": "electric",
                "cng": "cng", "diesel": "diesel",
                "petrol": "petrol", "hybrid": "hybrid",
            }
            target = mapping.get(fuel_norm, fuel_norm)
            if target not in car_fuel:
                continue

        # Transmission
        if transmission and transmission.lower() not in ("any", "no preference", ""):
            trans_norm = transmission.lower().strip()
            car_trans = [t.lower() for t in car.get("transmission", [])]
            if trans_norm == "automatic":
                auto_types = {"at", "amt", "cvt", "dct", "ivt", "ecvt", "dsg", "automatic"}
                if not any(t in auto_types for t in car_trans):
                    continue
            elif trans_norm == "manual":
                if "manual" not in car_trans:
                    continue

        results.append(car)

    # Sort by relevance heuristic before sending to AI
    priority = params.get("priority", "")
    results = _sort_candidates(results, priority)

    # Return top 15 to keep AI prompt manageable
    return results[:15]


def _sort_candidates(cars: list, priority: str) -> list:
    priority = priority.lower() if priority else ""

    def score(car):
        if "mileage" in priority:
            return -(car.get("mileage_kmpl") or car.get("range_km", 0) or 0)
        elif "safety" in priority:
            return -car.get("safety_rating_ncap", 0)
        elif "maintenance" in priority or "low maintenance" in priority:
            cost_map = {"Low": 0, "Medium": 1, "High": 2}
            return cost_map.get(car.get("maintenance_cost", "Medium"), 1)
        elif "resale" in priority:
            resale_map = {"High": 0, "Medium": 1, "Low": 2}
            return resale_map.get(car.get("resale_value", "Medium"), 1)
        elif "boot" in priority or "space" in priority:
            return -(car.get("boot_space_litres") or 0)
        else:
            # Default: balance safety + reliability
            return -(car.get("safety_rating_ncap", 0) * 2 + car.get("reliability_score", 0))

    return sorted(cars, key=score)
