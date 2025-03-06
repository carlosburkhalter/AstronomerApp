// utils/constants.dart
/// Application constants
class AppConstants {
  // Default location (London)
  static const double defaultLatitude = 51.5074;
  static const double defaultLongitude = -0.1278;
  static const double defaultAltitude = 25.0;
  static const String defaultLocationName = "London, UK (Default)";
  
  // UI constants
  static const double minZoomFactor = 0.5;
  static const double maxZoomFactor = 5.0;
  static const double defaultZoomFactor = 1.0;
  
  // Celestial visibility thresholds
  static const double baseVisibleMagnitude = 6.0;
  static const double midZoomVisibleMagnitude = 9.0;
  static const double highZoomVisibleMagnitude = 12.0;
  
  // Color constants
  static const int skyBackgroundDark = 0xFF050A15;
  static const int skyBackgroundMedium = 0xFF0A1A35;
  static const int appBarBackground = 0xFF0A1525;
  static const int menuPanelBackground = 0xFF0E1821;
  static const int bottomBarBackground = 0xFF102030;
  
  // Night mode colors
  static const int nightModeRed = 0xFF550000;
  static const int nightModeBackground = 0xFF110000;
  static const int nightModeText = 0xFF770000;
  
  // Projection modes
  static const int projectionAzimuthal = 0;
  static const int projectionEquatorial = 1;
  
  // Update intervals
  static const int skyUpdateIntervalMs = 100;
  static const int timeSimulationIntervalSec = 1;
  static const int timeSimulationStepMin = 1;
  
  // Location settings
  static const int locationTimeoutSec = 10;
  static const int geocodingTimeoutSec = 5;
  
  // Sensor settings
  static const double sensorSmoothingFactor = 0.1; // Lower for smoother transitions, higher for more responsiveness
  static const int sensorUpdateIntervalMs = 20;
  
  // Private constructor to prevent instantiation
  AppConstants._();
}