// models/celestial_object.dart
import 'package:flutter/material.dart';

/// CelestialObject represents a celestial body in the sky map
/// This class is immutable and optimized for rendering
class CelestialObject {
  final String name;
  final String type; // star, planet, galaxy, nebula, etc.
  final String catalogId; // Catalog designation (e.g., M31, Alpha CMa)
  final double rightAscension; // in hours (0-24)
  final double declination; // in degrees (-90 to +90)
  final double magnitude; // brightness (lower is brighter)
  final String? description;
  final Color color;

  // Computed fields for rendering optimization
  final double _renderSize; // Cached size for rendering

  const CelestialObject._({
    required this.name,
    required this.type,
    required this.catalogId,
    required this.rightAscension,
    required this.declination,
    required this.magnitude,
    this.description,
    required this.color,
    required double renderSize,
  }) : _renderSize = renderSize;

  /// Factory constructor for creating a star
  factory CelestialObject.star({
    required String name,
    required String catalogId,
    required double rightAscension,
    required double declination,
    required double magnitude,
    String? description,
    required Color color,
  }) {
    // Calculate render size based on magnitude
    final renderSize = _calculateStarSize(magnitude);
    
    return CelestialObject._(
      name: name,
      type: 'star',
      catalogId: catalogId,
      rightAscension: rightAscension,
      declination: declination,
      magnitude: magnitude,
      description: description,
      color: color,
      renderSize: renderSize,
    );
  }

  /// Factory constructor for creating a planet
  factory CelestialObject.planet({
    required String name,
    required String catalogId,
    required double rightAscension,
    required double declination,
    required double magnitude,
    String? description,
    required Color color,
  }) {
    // Set render size based on planet type
    double renderSize;
    
    switch (name) {
      case "Jupiter": renderSize = 7.0; break;
      case "Saturn": renderSize = 6.5; break;
      case "Mars": renderSize = 5.0; break;
      case "Venus": renderSize = 6.0; break;
      case "Mercury": renderSize = 4.0; break;
      case "Uranus": case "Neptune": renderSize = 5.0; break;
      case "Moon": renderSize = 8.0; break;
      default: renderSize = 5.0;
    }
    
    return CelestialObject._(
      name: name,
      type: 'planet',
      catalogId: catalogId,
      rightAscension: rightAscension,
      declination: declination,
      magnitude: magnitude,
      description: description,
      color: color,
      renderSize: renderSize,
    );
  }

  /// Factory constructor for creating a deep sky object (DSO)
  factory CelestialObject.deepSky({
    required String name,
    required String type, // galaxy, nebula, planetary, globular, open
    required String catalogId,
    required double rightAscension,
    required double declination,
    required double magnitude,
    String? description,
    Color? color,
  }) {
    // Set color based on type if not provided
    color ??= _getDeepSkyObjectColor(type);
    
    // Size based on magnitude and type
    double renderSize = (10.0 - magnitude / 2).clamp(3.0, 12.0);
    
    return CelestialObject._(
      name: name,
      type: type,
      catalogId: catalogId,
      rightAscension: rightAscension,
      declination: declination,
      magnitude: magnitude,
      description: description,
      color: color,
      renderSize: renderSize,
    );
  }

  /// Get the pre-calculated rendering size
  double get renderSize => _renderSize;

  /// Check if this object should be visible based on the zoom factor
  bool isVisibleWithZoom(double zoomFactor) {
    double visibleMagnitude = 6.0;
    if (zoomFactor >= 1.5) visibleMagnitude = 9.0;
    if (zoomFactor >= 2.0) visibleMagnitude = 12.0;
    
    return magnitude <= visibleMagnitude;
  }

  /// Calculate star size based on magnitude
  static double _calculateStarSize(double magnitude) {
    // Brighter stars (lower magnitude) appear larger
    if (magnitude < 0) {
      return 3.0 - magnitude * 0.3; // Negative magnitudes make stars larger
    } else if (magnitude < 1.0) {
      return 3.0;
    } else if (magnitude < 2.0) {
      return 2.5;
    } else if (magnitude < 3.0) {
      return 2.0;
    } else if (magnitude < 4.0) {
      return 1.5;
    } else if (magnitude < 5.0) {
      return 1.2;
    } else {
      return 0.8;
    }
  }

  /// Get color for deep sky objects based on their type
  static Color _getDeepSkyObjectColor(String type) {
    switch (type) {
      case "galaxy": return Colors.blue.shade200;
      case "nebula": return Colors.pink.shade200;
      case "planetary": return Colors.purple.shade200;
      case "globular": return Colors.amber.shade200;
      case "open": return Colors.lightBlue.shade200;
      default: return Colors.white;
    }
  }
}