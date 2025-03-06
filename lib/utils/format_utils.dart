// utils/format_utils.dart
import 'package:intl/intl.dart';

/// Utility class for formatting data
class FormatUtils {
  /// Format time as HH:MM:SS
  static String formatTime(DateTime time) {
    return DateFormat('HH:mm:ss').format(time);
  }
  
  /// Format date as YYYY-MM-DD
  static String formatDate(DateTime date) {
    return DateFormat('yyyy-MM-dd').format(date);
  }
  
  /// Format date and time
  static String formatDateTime(DateTime dateTime) {
    return DateFormat('yyyy-MM-dd HH:mm').format(dateTime);
  }
  
  /// Format degrees as DD° MM' SS"
  static String formatDegrees(double degrees) {
    final sign = degrees >= 0 ? '+' : '-';
    degrees = degrees.abs();
    
    final int deg = degrees.floor();
    final int min = ((degrees - deg) * 60).floor();
    final int sec = ((((degrees - deg) * 60) - min) * 60).round();
    
    return '$sign${deg.toString().padLeft(2, "0")}°${min.toString().padLeft(2, "0")}\'${sec.toString().padLeft(2, "0")}"';
  }
  
  /// Format hours as HH:MM:SS
  static String formatHours(double hours) {
    final int hrs = hours.floor();
    final int min = ((hours - hrs) * 60).floor();
    final int sec = ((((hours - hrs) * 60) - min) * 60).round();
    
    return '${hrs.toString().padLeft(2, "0")}h${min.toString().padLeft(2, "0")}m${sec.toString().padLeft(2, "0")}s';
  }
  
  /// Format decimal value to specified precision
  static String formatDecimal(double value, {int precision = 2}) {
    return value.toStringAsFixed(precision);
  }
  
  /// Format magnitude (star brightness)
  static String formatMagnitude(double magnitude) {
    final prefix = magnitude < 0 ? '' : '+';
    return '$prefix${magnitude.toStringAsFixed(2)}';
  }
  
  /// Format distance in light years
  static String formatLightYears(double lightYears) {
    if (lightYears >= 1000000) {
      return '${(lightYears / 1000000).toStringAsFixed(2)} million ly';
    } else if (lightYears >= 1000) {
      return '${(lightYears / 1000).toStringAsFixed(1)}k ly';
    } else {
      return '${lightYears.toStringAsFixed(1)} ly';
    }
  }
  
  // Make constructor private to prevent instantiation
  FormatUtils._();
}