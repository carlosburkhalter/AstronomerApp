// services/device_sensor_service.dart
import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:motion_sensors/motion_sensors.dart';
import 'package:vector_math/vector_math_64.dart';

class DeviceSensorService {
  // Singleton pattern
  static final DeviceSensorService _instance = DeviceSensorService._internal();
  factory DeviceSensorService() => _instance;
  DeviceSensorService._internal();

  // Sensor data
  double _azimuth = 0.0;
  double _altitude = 45.0;
  bool _isTracking = false;
  
  // Streams
  StreamSubscription<dynamic>? _rotationSubscription;
  final _orientationController = StreamController<Map<String, double>>.broadcast();
  Stream<Map<String, double>> get orientationStream => _orientationController.stream;

  // Start tracking device orientation
  void startTracking() {
    if (_isTracking) return;
    
    // Set sensor update interval (20ms = 50 updates per second)
    motionSensors.absoluteOrientationUpdateInterval = 20;
    
    // Start listening to sensor updates
    _rotationSubscription = motionSensors.absoluteOrientation.listen((AbsoluteOrientationEvent event) {
      // Convert quaternion to Euler angles
      final Vector3 orientation = quaternionToEuler(Quaternion(event.q[0], event.q[1], event.q[2], event.q[3]));
      
      // Convert to astronomical coordinates
      // Note: These calculations depend on how the phone is held
      // We assume the phone is held screen up toward the sky
      _azimuth = (((orientation.z * 180 / math.pi) + 360) % 360);
      _altitude = 90 - ((orientation.x * 180 / math.pi).abs());
      
      // Broadcast orientation change
      _orientationController.add({
        'azimuth': _azimuth,
        'altitude': _altitude,
      });
    });
    
    _isTracking = true;
  }

  // Stop tracking
  void stopTracking() {
    _rotationSubscription?.cancel();
    _isTracking = false;
  }

  // Get current values
  Map<String, double> getCurrentOrientation() {
    return {
      'azimuth': _azimuth,
      'altitude': _altitude,
    };
  }

  // Quaternion to Euler angles conversion
  Vector3 quaternionToEuler(Quaternion q) {
    // Roll (x-axis rotation)
    double sinr_cosp = 2 * (q.w * q.x + q.y * q.z);
    double cosr_cosp = 1 - 2 * (q.x * q.x + q.y * q.y);
    double roll = math.atan2(sinr_cosp, cosr_cosp);

    // Pitch (y-axis rotation)
    double sinp = 2 * (q.w * q.y - q.z * q.x);
    double pitch;
    if (sinp.abs() >= 1) {
      pitch = math.pi / 2 * sinp.sign; // Use 90 degrees if out of range
    } else {
      pitch = math.asin(sinp);
    }

    // Yaw (z-axis rotation)
    double siny_cosp = 2 * (q.w * q.z + q.x * q.y);
    double cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z);
    double yaw = math.atan2(siny_cosp, cosy_cosp);

    return Vector3(roll, pitch, yaw);
  }

  // Method to trigger a compass calibration request
  // Fix: Adding this method that was missing
  void calibrateCompass() {
    // On iOS, we can't directly trigger calibration,
    // but we can reset the sensor which often prompts iOS to recalibrate
    motionSensors.absoluteOrientationUpdateInterval = 100;
    
    // Stop and restart to encourage recalibration
    if (_isTracking) {
      stopTracking();
      Future.delayed(const Duration(milliseconds: 500), () {
        startTracking();
      });
    } else {
      // Just temporarily start and stop to trigger sensor reset
      startTracking();
      Future.delayed(const Duration(milliseconds: 500), () {
        stopTracking();
      });
    }
  }

  // Dispose resources
  void dispose() {
    stopTracking();
    _orientationController.close();
  }
}