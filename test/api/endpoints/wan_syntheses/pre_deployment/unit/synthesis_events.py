from typing import Any, Callable, Dict

Served = Callable[[Dict[str, Any]], Any]
MISSING = "No such wan synthesis"
NO_WAN = "The synthesis has no wan"
ASHBURN = {"id": 1, "name": "Ashburn, VA", "municipality": "Ashburn", "state": "VA",
           "country": "US", "latitude": 39.0438, "longitude": -77.4874, "carrier": "zayo"}
CHEYENNE = {"id": 2, "name": "Cheyenne, WY", "municipality": "Cheyenne", "state": "WY",
            "country": "US", "latitude": 41.14, "longitude": -104.8202, "carrier": "lumen"}
WARREN = {"id": 1, "name": "F.E. Warren AFB", "municipality": "Cheyenne", "state": "WY",
          "country": "United States", "latitude": 41.1517, "longitude": -104.8678,
          "exempt_from_distance_constraint": False}
HILL = {"id": 2, "name": "Hill AFB", "municipality": "Layton", "state": "UT",
        "country": "United States", "latitude": 41.124, "longitude": -111.9731,
        "exempt_from_distance_constraint": False}
PROVIDER_A = {"id": 1, "name": "Provider A", "municipality": "Columbus", "state": "OH",
              "country": "United States", "latitude": 39.9612, "longitude": -82.9988}
PROVIDER_B = {"id": 2, "name": "Provider B", "municipality": "Boardman", "state": "OR",
              "country": "United States", "latitude": 45.8396, "longitude": -119.7006}


def get(resource: str = "/wan-syntheses") -> Dict[str, Any]:
    return {"resource": resource, "httpMethod": "GET"}


def under(resource: str, synthesis: str, **member: str) -> Dict[str, Any]:
    parameters = {"id": synthesis, **member}
    return {"resource": resource, "httpMethod": "GET", "pathParameters": parameters}
