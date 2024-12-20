import pandas as pd
import openrouteservice
from django.http import JsonResponse
from django.views import View
from shapely.geometry import LineString, Point

# Load fuel price data
fuel_data = pd.read_csv(r'D:\fuel_route_api\routes\fuel-prices-for-be-assessment.csv')

# Constants
MAX_RANGE = 500  # miles
MPG = 10         # miles per gallon
MAX_DISTANCE_FROM_ROUTE = 5  # miles

# OpenRouteService API Key
ORS_API_KEY = 'Y5b3ce3597851110001cf6248630e4e1cb3ae4a28bb9f50137a4b32e6'

class RouteView(View):
    def get(self, request):
        # Parse inputs
        start = request.GET.get('start')  # Start location (e.g., "Big Cabin, OK")
        end = request.GET.get('end')      # End location (e.g., "Seymour, IN")
        
        if not start or not end:
            return JsonResponse({'error': 'Start and End locations are required'}, status=400)
        
        try:
            # Initialize ORS client
            client = openrouteservice.Client(key=ORS_API_KEY)
            
            # Get coordinates for start and end locations
            start_coords = self.get_coordinates(client, start)
            end_coords = self.get_coordinates(client, end)
            
            # Get route between start and end
            routes = client.directions(
                coordinates=[start_coords, end_coords],
                profile='driving-car',
                format='geojson'
            )
            
            # Route details
            route_coords = routes['features'][0]['geometry']['coordinates']
            total_distance = routes['features'][0]['properties']['segments'][0]['distance'] / 1609  # meters to miles
            
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
    
    def get_coordinates(self, client, location):
        """Get coordinates of a location using ORS Geocoding API."""
        geocode = client.pelias_search(text=location)
        if geocode['features']:
            return geocode['features'][0]['geometry']['coordinates']
        raise ValueError(f"Unable to fetch coordinates for {location}")
    
    def find_optimal_stops(self, route_coords, fuel_data, total_distance):
        """
        Calculate fuel stops and total cost along the route.
        """
        stops = []
        remaining_distance = total_distance
        total_cost = 0

        # Create a LineString object representing the route
        route_line = LineString(route_coords)
    
        # Filter fuel stops that are close to the route
        def is_within_range(row):
            stop_point = Point(row['Longitude'], row['Latitude'])
            # Convert the distance from degrees to approximate miles
            distance_from_route = route_line.distance(stop_point) * 69  # 1 degree ~ 69 miles
            return distance_from_route <= MAX_DISTANCE_FROM_ROUTE

        filtered_stops = fuel_data[fuel_data.apply(is_within_range, axis=1)]

        if filtered_stops.empty:
            raise ValueError("No fuel stops found within the specified route proximity.")
    
        while remaining_distance > 0:
            # Sort fuel stops by Retail Price and get the cheapest stop
            eligible_stops = filtered_stops.sort_values(by='Retail Price')
            cheapest_stop = eligible_stops.iloc[0]
        
            # Fuel calculations
            fuel_needed = min(MAX_RANGE, remaining_distance) / MPG
            cost = fuel_needed * cheapest_stop['Retail Price']
        
            # Add the stop to the list
            stops.append({
                'truckstop_name': cheapest_stop['Truckstop Name'],
                'city': cheapest_stop['City'],
                'state': cheapest_stop['State'],
                'fuel_price_per_gallon': cheapest_stop['Retail Price'],
                'cost': round(cost, 2)
            })
        
            # Update totals
            total_cost += cost
            remaining_distance -= MAX_RANGE

        return stops, total_cost
