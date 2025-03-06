// ui/widgets/settings_panel.dart
import 'package:flutter/material.dart';

/// Side panel with app settings
class SettingsPanel extends StatelessWidget {
  final bool showStars;
  final bool showPlanets;
  final bool showConstellations;
  final bool showDeepSkyObjects;
  final bool showGrid;
  final bool showHorizon;
  final bool showObjectNames;
  final int projectionMode;
  final bool useRealTime;
  final bool nightModeEnabled;
  final Function(bool) onShowStarsChanged;
  final Function(bool) onShowPlanetsChanged;
  final Function(bool) onShowConstellationsChanged;
  final Function(bool) onShowDeepSkyObjectsChanged;
  final Function(bool) onShowGridChanged;
  final Function(bool) onShowHorizonChanged;
  final Function(bool) onShowObjectNamesChanged;
  final Function(int?) onProjectionModeChanged;
  final Function(bool) onUseRealTimeChanged;
  final Function(bool) onNightModeChanged;
  final VoidCallback onSetCurrentTime;
  final VoidCallback onShowTechnicalInfo;
  final VoidCallback onResetView;
  final VoidCallback onResetToRealTime;
  final VoidCallback onCalibrateCompass;

  const SettingsPanel({
    super.key,
    required this.showStars,
    required this.showPlanets,
    required this.showConstellations,
    required this.showDeepSkyObjects,
    required this.showGrid,
    required this.showHorizon,
    required this.showObjectNames,
    required this.projectionMode,
    required this.useRealTime,
    required this.nightModeEnabled,
    required this.onShowStarsChanged,
    required this.onShowPlanetsChanged,
    required this.onShowConstellationsChanged,
    required this.onShowDeepSkyObjectsChanged,
    required this.onShowGridChanged,
    required this.onShowHorizonChanged,
    required this.onShowObjectNamesChanged,
    required this.onProjectionModeChanged,
    required this.onUseRealTimeChanged,
    required this.onNightModeChanged,
    required this.onSetCurrentTime,
    required this.onShowTechnicalInfo,
    required this.onResetView,
    required this.onResetToRealTime,
    required this.onCalibrateCompass,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      color: nightModeEnabled ? const Color(0xFF110000) : const Color(0xFF0E1821),
      child: ListView(
        padding: EdgeInsets.zero,
        children: [
          // Display settings
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: Text(
              'DISPLAY',
              style: TextStyle(
                color: nightModeEnabled ? Colors.red.shade300 : Colors.lightBlue,
                fontSize: 12,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          SwitchListTile(
            title: Text('Stars', 
              style: TextStyle(color: nightModeEnabled ? Colors.red.shade200 : Colors.white)
            ),
            value: showStars,
            activeColor: nightModeEnabled ? Colors.red : Colors.blue,
            onChanged: onShowStarsChanged,
          ),
          SwitchListTile(
            title: Text('Planets', 
              style: TextStyle(color: nightModeEnabled ? Colors.red.shade200 : Colors.white)
            ),
            value: showPlanets,
            activeColor: nightModeEnabled ? Colors.red : Colors.blue,
            onChanged: onShowPlanetsChanged,
          ),
          SwitchListTile(
            title: Text('Constellations', 
              style: TextStyle(color: nightModeEnabled ? Colors.red.shade200 : Colors.white)
            ),
            value: showConstellations,
            activeColor: nightModeEnabled ? Colors.red : Colors.blue,
            onChanged: onShowConstellationsChanged,
          ),
          SwitchListTile(
            title: Text('Deep Sky Objects', 
              style: TextStyle(color: nightModeEnabled ? Colors.red.shade200 : Colors.white)
            ),
            value: showDeepSkyObjects,
            activeColor: nightModeEnabled ? Colors.red : Colors.blue,
            onChanged: onShowDeepSkyObjectsChanged,
          ),
          SwitchListTile(
            title: Text('Grid', 
              style: TextStyle(color: nightModeEnabled ? Colors.red.shade200 : Colors.white)
            ),
            value: showGrid,
            activeColor: nightModeEnabled ? Colors.red : Colors.blue,
            onChanged: onShowGridChanged,
          ),
          SwitchListTile(
            title: Text('Horizon', 
              style: TextStyle(color: nightModeEnabled ? Colors.red.shade200 : Colors.white)
            ),
            value: showHorizon,
            activeColor: nightModeEnabled ? Colors.red : Colors.blue,
            onChanged: onShowHorizonChanged,
          ),
          SwitchListTile(
            title: Text('Object Names', 
              style: TextStyle(color: nightModeEnabled ? Colors.red.shade200 : Colors.white)
            ),
            value: showObjectNames,
            activeColor: nightModeEnabled ? Colors.red : Colors.blue,
            onChanged: onShowObjectNamesChanged,
          ),
          
          // View settings
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: Text(
              'VIEW',
              style: TextStyle(
                color: nightModeEnabled ? Colors.red.shade300 : Colors.lightBlue,
                fontSize: 12,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          SwitchListTile(
            title: Text('Night Mode', 
              style: TextStyle(color: nightModeEnabled ? Colors.red.shade200 : Colors.white)
            ),
            subtitle: Text(
              'Red light to preserve night vision', 
              style: TextStyle(
                color: nightModeEnabled ? Colors.red.shade100.withOpacity(0.7) : Colors.white54, 
                fontSize: 12
              )
            ),
            value: nightModeEnabled,
            activeColor: Colors.red.shade300,
            onChanged: onNightModeChanged,
          ),
          ListTile(
            title: Text('Calibrate Compass', 
              style: TextStyle(color: nightModeEnabled ? Colors.red.shade200 : Colors.white)
            ),
            trailing: Icon(Icons.compass_calibration, 
              color: nightModeEnabled ? Colors.red.shade300 : Colors.white70
            ),
            onTap: onCalibrateCompass,
          ),
          
          // Projection settings
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: Text(
              'PROJECTION',
              style: TextStyle(
                color: nightModeEnabled ? Colors.red.shade300 : Colors.lightBlue,
                fontSize: 12,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          RadioListTile<int>(
            title: Text('Azimuthal', 
              style: TextStyle(color: nightModeEnabled ? Colors.red.shade200 : Colors.white)
            ),
            value: 0,
            groupValue: projectionMode,
            activeColor: nightModeEnabled ? Colors.red : Colors.blue,
            onChanged: onProjectionModeChanged,
          ),
          RadioListTile<int>(
            title: Text('Equatorial', 
              style: TextStyle(color: nightModeEnabled ? Colors.red.shade200 : Colors.white)
            ),
            value: 1,
            groupValue: projectionMode,
            activeColor: nightModeEnabled ? Colors.red : Colors.blue,
            onChanged: onProjectionModeChanged,
          ),
          
          // Date and time settings
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: Text(
              'TIME',
              style: TextStyle(
                color: nightModeEnabled ? Colors.red.shade300 : Colors.lightBlue,
                fontSize: 12,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          SwitchListTile(
            title: Text(
              useRealTime ? 'Real Time' : 'Simulated Time',
              style: TextStyle(color: nightModeEnabled ? Colors.red.shade200 : Colors.white),
            ),
            value: useRealTime,
            activeColor: nightModeEnabled ? Colors.red : Colors.green,
            onChanged: onUseRealTimeChanged,
          ),
          if (!useRealTime)
            ListTile(
              title: Text('Set Current Time', 
                style: TextStyle(color: nightModeEnabled ? Colors.red.shade200 : Colors.white)
              ),
              trailing: Icon(Icons.access_time, 
                color: nightModeEnabled ? Colors.red.shade300 : Colors.white70
              ),
              onTap: onSetCurrentTime,
            ),
            
          // Information
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: Text(
              'INFORMATION',
              style: TextStyle(
                color: nightModeEnabled ? Colors.red.shade300 : Colors.lightBlue,
                fontSize: 12,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          ListTile(
            title: Text('Technical Details', 
              style: TextStyle(color: nightModeEnabled ? Colors.red.shade200 : Colors.white)
            ),
            trailing: Icon(Icons.info_outline, 
              color: nightModeEnabled ? Colors.red.shade300 : Colors.white70
            ),
            onTap: onShowTechnicalInfo,
          ),
          ListTile(
            title: Text('Reset View', 
              style: TextStyle(color: nightModeEnabled ? Colors.red.shade200 : Colors.white)
            ),
            trailing: Icon(Icons.refresh, 
              color: nightModeEnabled ? Colors.red.shade300 : Colors.white70
            ),
            onTap: onResetView,
          ),
          ListTile(
            title: Text('Reset to Real Time', 
              style: TextStyle(color: nightModeEnabled ? Colors.red.shade200 : Colors.white)
            ),
            trailing: Icon(Icons.restart_alt, 
              color: nightModeEnabled ? Colors.red.shade300 : Colors.white70
            ),
            onTap: onResetToRealTime,
          ),
        ],
      ),
    );
  }
}