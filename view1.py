import pandas as pd
import requests
from django.http import JsonResponse
from django.views import View
from shapely.geometry import LineString, Point

# Load fuel price data
fuel_data = pd.read_csv(r'D:\fuel_route_api\routes\fuel-prices-for-be-assessment.csv')

# Constants
MAX_RANGE = 500  # miles
MPG = 10         # miles per gallon
MAX_DISTANCE_FROM_ROUTE = 5  # miles

# MapQuest API Key
MAPQUEST_API_KEY = 'YOUR_MAPQUEST_API_KEY'

class RouteView(View):
    def get(self, request):
        # Parse inputs
        start = request.GET.get('start')  # Start location (e.g., "Big Cabin, OK")
        end = request.GET.get('end')      # End location (e.g., "Seymour, IN")
        
        if not start or not end:
            return JsonResponse({'error': 'Start and End locations are required'}, status=400)
        
        try:
            # Get coordinates for start and end locations
            start_coords = self.get_coordinates(start)
            end_coords = self.get_coordinates(end)
            
            # Get route between start and end
            route_coords, total_distance = self.get_route(start_coords, end_coords)
            
            # Find optimal fuel stops
            fuel_stops, total_cost = self.find_optimal_stops(route_coords, fuel_data, total_distance)
            
            # API Response
            return JsonResponse({
                'route': route_coords,
                'total_distance_miles': round(total_distance, 2),
                'optimal_fuel_stops': fuel_stops,
                'total_fuel_cost_usd': round(total_cost, 2)
            })
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def get_coordinates(self, location):
        """Get coordinates of a location using MapQuest Geocoding API."""
        url = f"http://www.mapquestapi.com/geocoding/v1/address?key={MAPQUEST_API_KEY}&location={location}"
        response = requests.get(url)
        data = response.json()
        
        if response.status_code == 200 and data['results']:
            location_data = data['results'][0]['locations'][0]['latLng']
            return [location_data['lng'], location_data['lat']]
        raise ValueError(f"Unable to fetch coordinates for {location}")
    
    def get_route(self, start_coords, end_coords):
        """Get route details using MapQuest Directions API."""
