// ui/widgets/bottom_toolbar.dart
import 'package:flutter/material.dart';

/// Bottom toolbar with common controls
class BottomToolbar extends StatelessWidget {
  final VoidCallback onNorth;
  final VoidCallback onZoomIn;
  final VoidCallback onZoomOut;
  final VoidCallback onToggleProjection;
  final VoidCallback onShowGuide;
  final VoidCallback onToggleTracking;
  final bool trackingEnabled;

  const BottomToolbar({
    super.key,
    required this.onNorth,
    required this.onZoomIn,
    required this.onZoomOut,
    required this.onToggleProjection,
    required this.onShowGuide,
    required this.onToggleTracking,
    required this.trackingEnabled,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 56,
      color: const Color(0xFF102030),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          IconButton(
            icon: const Icon(Icons.north, color: Colors.white70),
            tooltip: 'North',
            onPressed: onNorth,
          ),
          IconButton(
            icon: const Icon(Icons.zoom_in, color: Colors.white70),
            tooltip: 'Zoom In',
            onPressed: onZoomIn,
          ),
          IconButton(
            icon: const Icon(Icons.zoom_out, color: Colors.white70),
            tooltip: 'Zoom Out',
            onPressed: onZoomOut,
          ),
          IconButton(
            icon: Icon(
              trackingEnabled ? Icons.sensors : Icons.sensors_off,
              color: trackingEnabled ? Colors.green : Colors.white70,
            ),
            tooltip: trackingEnabled ? 'Disable Tracking' : 'Enable Tracking',
            onPressed: onToggleTracking,
          ),
          IconButton(
            icon: const Icon(Icons.swap_horiz, color: Colors.white70),
            tooltip: 'Change Projection',
            onPressed: onToggleProjection,
          ),
          IconButton(
            icon: const Icon(Icons.help_outline, color: Colors.white70),
            tooltip: 'Beginner Guide',
            onPressed: onShowGuide,
          ),
        ],
      ),
    );
  }
}