from typing import Dict, Any

class DataNormalizer:
    def normalize(self, provider_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Takes raw provider outputs and normalizes them for the Feature Engineer.
        """
        normalized = {}
        
        # Safely extract routing data
        routing_data = provider_results.get("RoutingAgent", {})
        normalized["distance_km"] = 2.1  # Extracted from routing_data in a real implementation
        normalized["eta_mins"] = 14
        
        # Safely extract weather data
        weather_data = provider_results.get("WeatherAgent", {})
        normalized["weather_condition"] = weather_data.get("condition", "Clear")
        normalized["temperature_c"] = weather_data.get("temperature_c", 24)
        
        # Safely extract community data
        community_data = provider_results.get("CommunityAgent", {})
        normalized["total_community_reports"] = community_data.get("total_reports", 0)
        
        return normalized
