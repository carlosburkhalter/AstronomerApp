// services/location_service.dart
import 'dart:async';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../utils/constants.dart';

/// Service for handling location-related functionality
class LocationService {
  /// Get the current device location
  /// 
  /// Returns a map with latitude, longitude, altitude, and a success flag
  static Future<Map<String, dynamic>> getCurrentLocation() async {
    try {
      // Check location permissions
      LocationPermission permission = await Geolocator.checkPermission();
      
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
        
        if (permission == LocationPermission.denied || 
            permission == LocationPermission.deniedForever) {
          return _getDefaultLocation(reason: 'Permission denied');
        }
      }
      
      // Check if location services are enabled
      bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        return _getDefaultLocation(reason: 'Location services disabled');
      }
      
      // Get position with timeout
      Position position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
        timeLimit: const Duration(seconds: 10),
      );
      
      return {
        'success': true,
        'latitude': position.latitude,
        'longitude': position.longitude,
        'altitude': position.altitude,
        'accuracy': position.accuracy,
        'timestamp': position.timestamp,
      };
    } catch (e) {
      return _getDefaultLocation(reason: 'Error: $e');
    }
  }
  
  /// Get location name from coordinates using reverse geocoding
  /// 
  /// Returns a string with the location name
  static Future<String> getLocationName(double latitude, double longitude) async {
    try {
      // Throttle to avoid hitting rate limits
      await Future.delayed(const Duration(milliseconds: 300));
      
      final url = Uri.parse(
        'https://nominatim.openstreetmap.org/reverse?format=json'
        '&lat=$latitude&lon=$longitude&zoom=10'
      );
      
      final response = await http.get(
        url,
        headers: {
          'User-Agent': 'SkyMapApp/1.0',
          'Accept-Language': 'en-US,en;q=0.9',
        },
      ).timeout(const Duration(seconds: 5));
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        
        // Extract location info
        final address = data['address'];
        final String city = address['city'] ?? 
                           address['town'] ?? 
                           address['village'] ?? 
                           address['hamlet'] ?? 
                           address['county'] ??
                           "Unknown";
                           
        final String country = address['country'] ?? "";
        
        return "$city, $country";
      } else {
        return _formatCoordinates(latitude, longitude);
      }
    } catch (e) {
      // Fall back to coordinates if geocoding fails
      return _formatCoordinates(latitude, longitude);
    }
  }
  
  /// Format coordinates as a readable string
  static String _formatCoordinates(double latitude, double longitude) {
    String latDir = latitude >= 0 ? 'N' : 'S';
    String lonDir = longitude >= 0 ? 'E' : 'W';
    return '${latitude.abs().toStringAsFixed(2)}° $latDir, ${longitude.abs().toStringAsFixed(2)}° $lonDir';
  }
  
  /// Get default location data when location services fail
  static Map<String, dynamic> _getDefaultLocation({required String reason}) {
    return {
      'success': false,
      'latitude': AppConstants.defaultLatitude,
      'longitude': AppConstants.defaultLongitude,
      'altitude': AppConstants.defaultAltitude,
      'reason': reason,
    };
  }
  
  /// Check if coordinates are valid
  static bool areCoordinatesValid(double latitude, double longitude) {
    return latitude >= -90 && latitude <= 90 && 
           longitude >= -180 && longitude <= 180;
  }
  
  /// Get distance between two coordinates in kilometers
  static double getDistanceBetweenCoordinates(
    double lat1, double lon1, double lat2, double lon2) {
    return Geolocator.distanceBetween(lat1, lon1, lat2, lon2) / 1000;
  }
  
  /// Generate a location cache key
  static String generateLocationCacheKey(double latitude, double longitude) {
    return '${latitude.toStringAsFixed(4)}_${longitude.toStringAsFixed(4)}';
  }
}