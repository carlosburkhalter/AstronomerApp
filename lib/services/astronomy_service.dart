// services/astronomy_service.dart
import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../models/celestial_object.dart';
import '../models/constellation.dart';
import '../models/star_position.dart';

/// Service class for astronomical calculations
class AstronomyService {
  /// Calculate local sidereal time
  /// 
  /// Returns the local sidereal time in degrees (0-360)
  static double calculateLocalSiderealTime(DateTime dateTime, double longitude) {
    // Get Julian Date
    final jd = calculateJulianDate(dateTime);
    final T = (jd - 2451545.0) / 36525.0;
    
    // Greenwich Sidereal Time (in degrees)
    double gst = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + 
                 0.000387933 * T * T - T * T * T / 38710000.0;
    
    // Normalize to 0-360 degrees
    gst = gst % 360.0;
    if (gst < 0) gst += 360.0;
    
    // Add longitude to get Local Sidereal Time
    double lst = (gst + longitude) % 360.0;
    
    return lst;
  }
  
  /// Calculate Julian Date from DateTime
  static double calculateJulianDate(DateTime date) {
    int y = date.year;
    int m = date.month;
    int d = date.day;
    
    if (m <= 2) {
      y--;
      m += 12;
    }
    
    int a = y ~/ 100;
    int b = 2 - a + (a ~/ 4);
    
    double jd = (365.25 * (y + 4716)).floor() + 
                (30.6001 * (m + 1)).floor() + 
                d + b - 1524.5;
    
    // Add time of day
    jd += date.hour / 24.0 + date.minute / 1440.0 + date.second / 86400.0;
    
    return jd;
  }
  
  /// Convert equatorial to horizontal coordinates
  /// 
  /// Takes right ascension and declination and converts to azimuth and altitude
  /// Returns a map with 'azimuth' and 'altitude' in degrees
  static Map<String, double> equatorialToHorizontal({
    required double rightAscension,
    required double declination,
    required double latitude,
    required double longitude,
    required DateTime dateTime,
  }) {
    // Apply precession correction
    final corrected = precessionCorrection(rightAscension, declination, dateTime);
    rightAscension = corrected['rightAscension']!;
    declination = corrected['declination']!;
    
    // Calculate local hour angle
    final siderealTime = calculateLocalSiderealTime(dateTime, longitude);
    final hourAngle = siderealTime - rightAscension * 15;
    
    // Convert to radians
    final latRad = latitude * math.pi / 180;
    final decRad = declination * math.pi / 180;
    final haRad = hourAngle * math.pi / 180;
    
    // Calculate altitude
    final sinAlt = math.sin(latRad) * math.sin(decRad) + 
                   math.cos(latRad) * math.cos(decRad) * math.cos(haRad);
    final altRad = math.asin(sinAlt);
    final alt = altRad * 180 / math.pi;
    
    // Calculate azimuth
    double az;
    final cosAz = (math.sin(decRad) - math.sin(latRad) * sinAlt) / 
                 (math.cos(latRad) * math.cos(altRad));
                 
    // Protect against domain errors in acos
    final cosAzClamped = cosAz.clamp(-1.0, 1.0);
    
    final sinAz = -math.cos(decRad) * math.sin(haRad) / math.cos(altRad);
    az = math.atan2(sinAz, cosAzClamped) * 180 / math.pi;
    
    // Normalize azimuth to 0-360 degrees
    if (az < 0) az += 360;
    
    return {
      'azimuth': az,
      'altitude': alt,
    };
  }
  
  /// Convert horizontal to screen coordinates
  /// 
  /// Takes azimuth and altitude and converts to x,y screen coordinates
  /// Returns a map with 'x', 'y', and 'isVisible' flag
  static Map<String, dynamic> horizontalToScreen({
    required double azimuth,
    required double altitude,
    required double viewAzimuth, // Center of view azimuth
    required Size size,
    required double centerX,
    required double centerY,
    required double zoomFactor,
    double offsetX = 0.0,
    double offsetY = 0.0,
  }) {
    bool isVisible = altitude > 0;
    
    // Adjust for map orientation
    final azimuthDiff = (azimuth - viewAzimuth + 360) % 360;
    
    // Calculate position on screen (azimuthal equidistant projection)
    final maxAltitude = 90.0;
    final radius = size.width * 0.4 * (maxAltitude - altitude) / maxAltitude * zoomFactor;
    final radians = azimuthDiff * math.pi / 180;
    
    final x = centerX + radius * math.sin(radians) + offsetX;
    final y = centerY - radius * math.cos(radians) + offsetY;
    
    // Check if object is visible and within the screen bounds
    isVisible = isVisible && radius < size.width * 1.5;
    
    return {
      'x': x,
      'y': y,
      'isVisible': isVisible,
      'radius': radius, // Useful for hit testing
    };
  }
  
  /// Convert equatorial to screen coordinates directly
  static Map<String, dynamic> equatorialToScreen({
    required double rightAscension,
    required double declination,
    required double latitude,
    required double longitude,
    required DateTime dateTime,
    required double viewAzimuth,
    required Size size,
    required double centerX,
    required double centerY,
    required double zoomFactor,
    double offsetX = 0.0,
    double offsetY = 0.0,
    required int projectionMode, // 0 = azimuthal, 1 = equatorial
  }) {
    if (projectionMode == 0) {
      // Azimuthal projection - convert to horizontal first
      final horizontal = equatorialToHorizontal(
        rightAscension: rightAscension,
        declination: declination,
        latitude: latitude,
        longitude: longitude,
        dateTime: dateTime,
      );
      
      return horizontalToScreen(
        azimuth: horizontal['azimuth']!,
        altitude: horizontal['altitude']!,
        viewAzimuth: viewAzimuth,
        size: size,
        centerX: centerX,
        centerY: centerY,
        zoomFactor: zoomFactor,
        offsetX: offsetX,
        offsetY: offsetY,
      );
    } else {
      // Equatorial projection
      // Apply precession correction first
      final corrected = precessionCorrection(rightAscension, declination, dateTime);
      rightAscension = corrected['rightAscension']!;
      declination = corrected['declination']!;
      
      // Distance from the north celestial pole
      final polarDistance = (90 - declination) * zoomFactor;
      final radius = size.width * 0.4 * polarDistance / 90;
      
      // Hour angle relative to east
      final angle = (rightAscension * 15 - viewAzimuth + 360) % 360;
      final radians = angle * math.pi / 180;
      
      final x = centerX + radius * math.sin(radians) + offsetX;
      final y = centerY - radius * math.cos(radians) + offsetY;
      
      // Check if object is visible
      final isVisible = radius < size.width * 1.5;
      
      return {
        'x': x,
        'y': y,
        'isVisible': isVisible,
        'radius': radius,
      };
    }
  }

  /// Apply precession correction to coordinates
  /// 
  /// Adjusts star positions for Earth's precession since J2000 epoch
  static Map<String, double> precessionCorrection(double ra, double dec, DateTime date) {
    // J2000 epoch (January 1, 2000, 12:00 UTC)
    final DateTime j2000 = DateTime.utc(2000, 1, 1, 12);
    
    // Calculate years since J2000
    final double yearsFromJ2000 = date.difference(j2000).inDays / 365.25;
    
    // Precession correction factors
    // These are simplified approximations
    final double m = (3.07234 + 0.00186 * yearsFromJ2000) * yearsFromJ2000; // in degrees
    final double n = (20.0468 - 0.0085 * yearsFromJ2000) * yearsFromJ2000; // in arcseconds
    
    // Convert to radians for calculations
    final double raRad = ra * 15 * math.pi / 180; // RA in hours to radians
    final double decRad = dec * math.pi / 180;
    final double mRad = m * math.pi / 180;
    final double nRad = n * math.pi / (180 * 3600); // arcseconds to radians
    
    // Apply precession formulae
    final double newRaRad = raRad + (mRad + nRad * math.sin(raRad) * math.tan(decRad)) / math.cos(decRad);
    final double newDecRad = decRad + nRad * math.cos(raRad);
    
    // Convert back to degrees and hours
    double newRa = (newRaRad * 180 / math.pi) / 15; // back to hours
    double newDec = newDecRad * 180 / math.pi;
    
    // Normalize RA to 0-24 range
    newRa = newRa % 24;
    if (newRa < 0) newRa += 24;
    
    return {
      'rightAscension': newRa,
      'declination': newDec,
    };
  }

  /// Format Right Ascension for display
  static String formatRA(double ra) {
    int hours = ra.floor();
    int minutes = ((ra - hours) * 60).floor();
    int seconds = ((((ra - hours) * 60) - minutes) * 60).round();
    
    return '${hours.toString().padLeft(2, '0')}h${minutes.toString().padLeft(2, '0')}m${seconds.toString().padLeft(2, '0')}s';
  }

  /// Format Declination for display
  static String formatDEC(double dec) {
    String sign = dec >= 0 ? '+' : '';
    dec = dec.abs();
    int degrees = dec.floor();
    int minutes = ((dec - degrees) * 60).floor();
    int seconds = ((((dec - degrees) * 60) - minutes) * 60).round();
    
    return '$sign${degrees.toString().padLeft(2, "0")}°${minutes.toString().padLeft(2, "0")}\'${seconds.toString().padLeft(2, "0")}"';
  }
  
  /// Apply atmospheric refraction correction to altitude
  static double applyRefraction(double altitude) {
    // Skip corrections for objects high in the sky
    if (altitude > 30.0) return altitude;
    
    // Simplified refraction formula
    // Approximately accurate for normal atmospheric conditions
    final double refraction = 1.02 / math.tan((altitude + 10.3 / (altitude + 5.11)) * math.pi / 180.0) / 60.0;
    
    // Return corrected altitude
    return altitude + refraction;
  }
}