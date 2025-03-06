// sky_map_screen.dart
import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'models/celestial_object.dart';
import 'models/constellation.dart';
import 'services/astronomy_service.dart';
import 'services/location_service.dart';
import 'services/celestial_data_provider.dart';
import 'services/device_sensor_service.dart';
import 'ui/painters/sky_map_painter.dart';
import 'ui/widgets/object_info_card.dart';
import 'ui/widgets/sky_map_app_bar.dart';
import 'ui/widgets/bottom_toolbar.dart';
import 'ui/widgets/settings_panel.dart';
import 'ui/widgets/object_info_dialog.dart';
import 'utils/constants.dart';
import 'utils/format_utils.dart';

class SkyMapScreen extends StatefulWidget {
  const SkyMapScreen({Key? key}) : super(key: key);

  @override
  State<SkyMapScreen> createState() => _SkyMapScreenState();
}

class _SkyMapScreenState extends State<SkyMapScreen> with SingleTickerProviderStateMixin {
  // Celestial data manager
  final _dataProvider = CelestialDataProvider();
  
  // Sensor manager
  final _sensorService = DeviceSensorService();
  
  // Celestial objects
  List<CelestialObject> _stars = [];
  List<CelestialObject> _planets = [];
  List<CelestialObject> _deepSkyObjects = [];
  List<Constellation> _constellations = [];
  
  // View state
  double _azimuth = 0.0; // North = 0°
  double _elevation = 45.0;
  DateTime _currentTime = DateTime.now();
  double _zoomFactor = AppConstants.defaultZoomFactor;
  double _offsetX = 0.0;
  double _offsetY = 0.0;
  int _projectionMode = AppConstants.projectionAzimuthal;
  String _projectionName = "Azimuthal";
  
  // Display options
  bool _showStars = true;
  bool _showPlanets = true;
  bool _showConstellations = true;
  bool _showDeepSkyObjects = true;
  bool _showGrid = true;
  bool _showHorizon = true;
  bool _showObjectNames = true;
  bool _nightModeEnabled = false;
  
  // Location
  double _latitude = AppConstants.defaultLatitude;
  double _longitude = AppConstants.defaultLongitude;
  double _altitude = AppConstants.defaultAltitude;
  String _locationName = "Determining location...";
  bool _isLoading = true;
  
  // UI state
  bool _menuVisible = false;
  late AnimationController _animationController;
  final TextEditingController _searchController = TextEditingController();
  CelestialObject? _selectedObject;
  double _previousScale = 1.0;
  
  // Sensor tracking
  bool _sensorTrackingEnabled = false;
  StreamSubscription? _sensorSubscription;
  
  // Time control
  bool _useRealTime = true;
  Timer? _timer;
  Timer? _timeControlTimer;
  
  // Smooth motion
  double _targetAzimuth = 0.0;
  double _targetElevation = 45.0;
  double _azimuthVelocity = 0.0;
  double _elevationVelocity = 0.0;
  
  @override
  void initState() {
    super.initState();
    
    // Initialize animation controller for menu
    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 250),
    );
    
    // Initialize location and data
    _initializeApp();
    
    // Set up sensor listener
    _sensorSubscription = _sensorService.orientationStream.listen((orientation) {
      if (_sensorTrackingEnabled && mounted) {
        setState(() {
          // Update target values - actual values will be smoothly interpolated
          _targetAzimuth = orientation['azimuth']!;
          _targetElevation = orientation['altitude']!;
        });
      }
    });
  }
  
  Future<void> _initializeApp() async {
    await _initializeLocation();
    await _loadCelestialData();
    _startUpdateTimers();
    
    setState(() {
      _isLoading = false;
    });
  }
  
  Future<void> _initializeLocation() async {
    final locationData = await LocationService.getCurrentLocation();
    
    setState(() {
      _latitude = locationData['latitude'];
      _longitude = locationData['longitude'];
      _altitude = locationData['altitude'] ?? AppConstants.defaultAltitude;
      
      if (locationData['success'] == true) {
        _getLocationName();
      } else {
        _locationName = AppConstants.defaultLocationName;
      }
    });
  }
  
  Future<void> _getLocationName() async {
    try {
      final name = await LocationService.getLocationName(_latitude, _longitude);
      
      if (mounted) {
        setState(() {
          _locationName = name;
        });
      }
    } catch (e) {
      // Keep existing location name if error occurs
    }
  }
  
  Future<void> _loadCelestialData() async {
    final stars = await _dataProvider.getStars();
    final planets = await _dataProvider.getPlanets();
    final dsos = await _dataProvider.getDeepSkyObjects();
    final constellations = await _dataProvider.getConstellations();
    
    if (mounted) {
      setState(() {
        _stars = stars;
        _planets = planets;
        _deepSkyObjects = dsos;
        _constellations = constellations;
      });
    }
  }
  
  void _startUpdateTimers() {
    // Timer for regular UI updates
    _timer = Timer.periodic(const Duration(milliseconds: AppConstants.skyUpdateIntervalMs), (timer) {
      if (mounted) {
        setState(() {
          if (_useRealTime) {
            _currentTime = DateTime.now();
          }
          
          // Smooth motion for sensor-based movement
          if (_sensorTrackingEnabled) {
            _smoothlyUpdateOrientation();
          }
          
          // Update planet positions periodically when observing real time
          if (_useRealTime && _currentTime.second % 30 == 0) {
            _updatePlanetPositions();
          }
        });
      }
    });
    
    // Timer for time simulation
    _timeControlTimer = Timer.periodic(
      const Duration(seconds: AppConstants.timeSimulationIntervalSec), 
      (timer) {
        if (!_useRealTime && mounted) {
          setState(() {
            _currentTime = _currentTime.add(
              const Duration(minutes: AppConstants.timeSimulationStepMin)
            );
          });
        }
      }
    );
  }
  
  void _smoothlyUpdateOrientation() {
    // Calculate differences
    double azimuthDiff = _targetAzimuth - _azimuth;
    double elevationDiff = _targetElevation - _elevation;
    
    // Handle azimuth wrap-around (0-360 degrees)
    if (azimuthDiff > 180) azimuthDiff -= 360;
    if (azimuthDiff < -180) azimuthDiff += 360;
    
    // Apply smooth movement with exponential smoothing
    _azimuth += azimuthDiff * AppConstants.sensorSmoothingFactor;
    _elevation += elevationDiff * AppConstants.sensorSmoothingFactor;
    
    // Normalize azimuth to 0-360 range
    _azimuth = _azimuth % 360;
    if (_azimuth < 0) _azimuth += 360;
    
    // Clamp elevation to 0-90 range
    _elevation = _elevation.clamp(0.0, 90.0);
  }
  
  void _updatePlanetPositions() async {
    final updatedPlanets = await _dataProvider.getPlanets(dateTime: _currentTime);
    
    if (mounted) {
      setState(() {
        _planets = updatedPlanets;
      });
    }
  }
  
  void _resetToRealTime() {
    setState(() {
      _useRealTime = true;
      _currentTime = DateTime.now();
      _updatePlanetPositions();
    });
  }
  
  void _toggleSensorTracking() {
    setState(() {
      _sensorTrackingEnabled = !_sensorTrackingEnabled;
      
      if (_sensorTrackingEnabled) {
        _sensorService.startTracking();
        
        // Initialize target values
        final orientation = _sensorService.getCurrentOrientation();
        _targetAzimuth = orientation['azimuth']!;
        _targetElevation = orientation['altitude']!;
        
        // Show a toast or snackbar
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Sensor tracking enabled. Point your device at the sky.'),
            duration: Duration(seconds: 2),
          ),
        );
      } else {
        // Don't stop tracking service - just disable updates to the view
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Sensor tracking disabled. Manual control enabled.'),
            duration: Duration(seconds: 2),
          ),
        );
      }
    });
  }
  
  void _calibrateCompass() {
    _sensorService.calibrateCompass();
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Calibrating compass. Move your device in a figure-8 pattern.'),
        duration: Duration(seconds: 3),
      ),
    );
  }
  
  void _searchObject(String query) async {
    if (query.isEmpty) return;
    
    final results = await _dataProvider.searchObjects(query);
    
    if (results.isNotEmpty) {
      _selectObject(results.first);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('No object found with that name.'),
          backgroundColor: Colors.red,
          duration: Duration(seconds: 2),
        ),
      );
    }
  }
  
  void _selectObject(CelestialObject object) {
    setState(() {
      _selectedObject = object;
      
      // Center view on the object
      _centerOnObject(object);
      
      // Close menu if open
      if (_menuVisible) {
        _toggleMenu();
      }
      
      // Show confirmation
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Selected: ${object.name} (${object.catalogId})'),
          backgroundColor: _nightModeEnabled ? Colors.red.shade800 : Colors.green,
          duration: const Duration(seconds: 2),
        ),
      );
    });
  }
  
  void _centerOnObject(CelestialObject object) {
    // Disable sensor tracking when manually centering
    if (_sensorTrackingEnabled) {
      _toggleSensorTracking();
    }
    
    // Calculate horizontal coordinates
    final horizontalCoords = AstronomyService.equatorialToHorizontal(
      rightAscension: object.rightAscension,
      declination: object.declination,
      latitude: _latitude,
      longitude: _longitude,
      dateTime: _currentTime,
    );
    
    setState(() {
      _azimuth = horizontalCoords['azimuth']!;
      _elevation = math.max(0, math.min(90, horizontalCoords['altitude']!));
      _zoomFactor = 1.5; // Zoom in a bit when selecting an object
    });
  }
  
  void _toggleMenu() {
    setState(() {
      _menuVisible = !_menuVisible;
      if (_menuVisible) {
        _animationController.forward();
      } else {
        _animationController.reverse();
      }
    });
  }
  
  void _toggleNightMode() {
    setState(() {
      _nightModeEnabled = !_nightModeEnabled;
    });
  }
  
  // Show object info dialog
  void _showObjectInfo(CelestialObject object) {
    showDialog(
      context: context,
      builder: (context) => ObjectInfoDialog(
        object: object,
        onCenter: () => _selectObject(object),
      ),
    );
  }
  
  // Show technical information dialog
  void _showTechnicalInfo() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: _nightModeEnabled 
            ? const Color(AppConstants.nightModeBackground) 
            : const Color(AppConstants.bottomBarBackground),
        title: Text(
          'Technical Information',
          style: TextStyle(
            color: _nightModeEnabled ? Colors.red.shade300 : Colors.white
          ),
        ),
        content: SizedBox(
          width: 300,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildInfoRow('Location:', _locationName),
              _buildInfoRow('Coordinates:', 'Lat: ${_latitude.toStringAsFixed(4)}°, Lon: ${_longitude.toStringAsFixed(4)}°'),
              _buildInfoRow('Local Time:', FormatUtils.formatTime(_currentTime)),
              _buildInfoRow('Local Date:', FormatUtils.formatDate(_currentTime)),
              _buildInfoRow('Sidereal Time:', '${(AstronomyService.calculateLocalSiderealTime(_currentTime, _longitude) / 15).toStringAsFixed(2)} hours'),
              _buildInfoRow('Azimuth:', '${_azimuth.toStringAsFixed(2)}°'),
              _buildInfoRow('Elevation:', '${_elevation.toStringAsFixed(2)}°'),
              _buildInfoRow('Projection:', _projectionName),
              _buildInfoRow('Zoom:', '${_zoomFactor.toStringAsFixed(2)}×'),
              _buildInfoRow('Tracking:', _sensorTrackingEnabled ? 'Enabled' : 'Disabled'),
              _buildInfoRow('Night Mode:', _nightModeEnabled ? 'Enabled' : 'Disabled'),
            ],
          ),
        ),
        actions: [
          TextButton(
            child: Text('Close', 
              style: TextStyle(
                color: _nightModeEnabled ? Colors.red.shade300 : Colors.white
              )
            ),
            onPressed: () => Navigator.of(context).pop(),
          ),
        ],
      ),
    );
  }
  
  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        children: [
          Text(
            label,
            style: TextStyle(
              color: _nightModeEnabled ? Colors.red.shade200.withOpacity(0.7) : Colors.white70, 
              fontWeight: FontWeight.bold
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                color: _nightModeEnabled ? Colors.red.shade100 : Colors.white
              ),
            ),
          ),
        ],
      ),
    );
  }
  
  // Find object at tap position
  CelestialObject? _findObjectAtPosition(Offset position) {
    final Size size = MediaQuery.of(context).size;
    final double centerX = size.width / 2;
    final double centerY = size.height / 2;
    
    // Check all visible objects
    final allObjects = [
      ..._showStars ? _stars : [],
      ..._showPlanets ? _planets : [],
      ..._showDeepSkyObjects ? _deepSkyObjects : [],
    ];
    
    // Find the object closest to the tap position
    CelestialObject? closestObject;
    double closestDistance = double.infinity;
    
    for (var obj in allObjects) {
      final screenCoords = AstronomyService.equatorialToScreen(
        rightAscension: obj.rightAscension,
        declination: obj.declination,
        latitude: _latitude,
        longitude: _longitude,
        dateTime: _currentTime,
        viewAzimuth: _azimuth,
        size: size,
        centerX: centerX,
        centerY: centerY,
        zoomFactor: _zoomFactor,
        offsetX: _offsetX,
        offsetY: _offsetY,
        projectionMode: _projectionMode,
      );
      
      if (screenCoords['isVisible'] == true) {
        final objPos = Offset(screenCoords['x']!, screenCoords['y']!);
        
        // Calculate tap radius based on object type and magnitude
        double tapRadius = 15.0;
        if (obj.type == 'star') {
          tapRadius = 15.0 - obj.magnitude * 0.5;
          tapRadius = math.max(10.0, tapRadius);
        } else if (obj.type == 'planet') {
          tapRadius = 20.0;
        } else {
          tapRadius = 25.0;
        }
        
        // Check if tap is within object radius
        final distance = (objPos - position).distance;
        if (distance < tapRadius && distance < closestDistance) {
          closestObject = obj;
          closestDistance = distance;
        }
      }
    }
    
    return closestObject;
  }
  
  // Show beginner guide dialog
  void _showBeginnerGuide() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: _nightModeEnabled 
            ? const Color(AppConstants.nightModeBackground) 
            : const Color(AppConstants.bottomBarBackground),
        title: Text(
          'Beginner\'s Guide to Stargazing',
          style: TextStyle(
            color: _nightModeEnabled ? Colors.red.shade300 : Colors.white
          ),
        ),
        content: SizedBox(
          width: 350,
          height: 400,
          child: ListView(
            children: [
              Text(
                'Welcome to SkyMap for Beginners! This app will help you identify stars, planets, and other celestial objects in the night sky.',
                style: TextStyle(
                  color: _nightModeEnabled ? Colors.red.shade100 : Colors.white70
                ),
              ),
              const SizedBox(height: 16),
              
              Text(
                'How to Use This App:',
                style: TextStyle(
                  color: _nightModeEnabled ? Colors.red.shade200 : Colors.white, 
                  fontWeight: FontWeight.bold
                ),
              ),
              const SizedBox(height: 8),
              
              Text(
                '1. Hold your device up to the sky with the screen facing you.',
                style: TextStyle(
                  color: _nightModeEnabled ? Colors.red.shade100 : Colors.white70
                ),
              ),
              Text(
                '2. Enable sensor tracking with the tracking button to match the sky.',
                style: TextStyle(
                  color: _nightModeEnabled ? Colors.red.shade100 : Colors.white70
                ),
              ),
              Text(
                '3. Tap on any object to get more information about it.',
                style: TextStyle(
                  color: _nightModeEnabled ? Colors.red.shade100 : Colors.white70
                ),
              ),
              Text(
                '4. Use the search bar to find specific objects.',
                style: TextStyle(
                  color: _nightModeEnabled ? Colors.red.shade100 : Colors.white70
                ),
              ),
              Text(
                '5. Enable night mode to protect your night vision.',
                style: TextStyle(
                  color: _nightModeEnabled ? Colors.red.shade100 : Colors.white70
                ),
              ),
              const SizedBox(height: 16),
              
              Text(
                'Understanding the Sky:',
                style: TextStyle(
                  color: _nightModeEnabled ? Colors.red.shade200 : Colors.white, 
                  fontWeight: FontWeight.bold
                ),
              ),
              const SizedBox(height: 8),
              
              _buildGuideItem(
                'Stars',
                'Stars appear as points of light with different colors. The color indicates the star\'s temperature: blue stars are hottest, followed by white, yellow, orange, and red.',
                Icons.star,
                _nightModeEnabled ? Colors.red.shade200 : Colors.white,
              ),
              
              _buildGuideItem(
                'Planets',
                'Planets generally don\'t twinkle like stars and often appear brighter. Venus, Mars, Jupiter, and Saturn are easily visible to the naked eye.',
                Icons.public,
                _nightModeEnabled ? Colors.red.shade200 : Colors.amber.shade200,
              ),
              
              _buildGuideItem(
                'Constellations',
                'Constellations are patterns of stars that form recognizable shapes. They help navigate the night sky and locate other objects.',
                Icons.connect_without_contact,
                _nightModeEnabled ? Colors.red.shade200 : Colors.lightBlue.shade200,
              ),
              
              _buildGuideItem(
                'Deep Sky Objects',
                'These include galaxies, nebulae, and star clusters. Most require binoculars or a telescope to view, but some like the Andromeda Galaxy and Pleiades can be seen with the naked eye.',
                Icons.blur_circular,
                _nightModeEnabled ? Colors.red.shade200 : Colors.pink.shade200,
              ),
              
              const SizedBox(height: 16),
              
              Text(
                'Tips for Beginners:',
                style: TextStyle(
                  color: _nightModeEnabled ? Colors.red.shade200 : Colors.white, 
                  fontWeight: FontWeight.bold
                ),
              ),
              const SizedBox(height: 8),
              
              Text(
                '• Allow your eyes at least 20 minutes to adjust to darkness for better viewing.',
                style: TextStyle(
                  color: _nightModeEnabled ? Colors.red.shade100 : Colors.white70
                ),
              ),
              Text(
                '• Use night mode to preserve your night vision.',
                style: TextStyle(
                  color: _nightModeEnabled ? Colors.red.shade100 : Colors.white70
                ),
              ),
              Text(
                '• Start by learning major constellations like Ursa Major (Big Dipper), Orion, and Cassiopeia.',
                style: TextStyle(
                  color: _nightModeEnabled ? Colors.red.shade100 : Colors.white70
                ),
              ),
              Text(
                '• The planets follow a path called the ecliptic across the sky.',
                style: TextStyle(
                  color: _nightModeEnabled ? Colors.red.shade100 : Colors.white70
                ),
              ),
              Text(
                '• Full moon nights are not ideal for stargazing as the bright light makes it harder to see fainter objects.',
                style: TextStyle(
                  color: _nightModeEnabled ? Colors.red.shade100 : Colors.white70
                ),
              ),
              Text(
                '• If the compass seems inaccurate, use the calibration option in the settings menu.',
                style: TextStyle(
                  color: _nightModeEnabled ? Colors.red.shade100 : Colors.white70
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            child: Text('Close', 
              style: TextStyle(
                color: _nightModeEnabled ? Colors.red.shade300 : Colors.white
              )
            ),
            onPressed: () => Navigator.of(context).pop(),
          ),
        ],
      ),
    );
  }
  
  Widget _buildGuideItem(String title, String description, IconData icon, Color color) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(color: color, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 4),
                Text(
                  description,
                  style: TextStyle(
                    color: _nightModeEnabled ? Colors.red.shade100 : Colors.white70, 
                    fontSize: 12
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
  
  void _showDateTimePicker() async {
    final selectedDate = await showDatePicker(
      context: context,
      initialDate: _currentTime,
      firstDate: DateTime(2000),
      lastDate: DateTime(2050),
      builder: (context, child) {
        return Theme(
          data: ThemeData.dark(),
          child: child!,
        );
      },
    );
    
    if (selectedDate != null) {
      final selectedTime = await showTimePicker(
        context: context,
        initialTime: TimeOfDay.fromDateTime(_currentTime),
        builder: (context, child) {
          return Theme(
            data: ThemeData.dark(),
            child: child!,
          );
        },
      );
      
      if (selectedTime != null) {
        setState(() {
          _currentTime = DateTime(
            selectedDate.year,
            selectedDate.month,
            selectedDate.day,
            selectedTime.hour,
            selectedTime.minute,
          );
          _updatePlanetPositions();
        });
      }
    }
  }
  
  void _resetView() {
    setState(() {
      _azimuth = 0.0;
      _elevation = 45.0;
      _zoomFactor = AppConstants.defaultZoomFactor;
      _offsetX = 0.0;
      _offsetY = 0.0;
      _selectedObject = null;
    });
  }
  
  void _toggleProjection() {
    setState(() {
      _projectionMode = (_projectionMode + 1) % 2;
      _projectionName = _projectionMode == AppConstants.projectionAzimuthal
          ? "Azimuthal"
          : "Equatorial";
    });
  }
  
  @override
  void dispose() {
    _timer?.cancel();
    _timeControlTimer?.cancel();
    _sensorSubscription?.cancel();
    _sensorService.dispose();
    _animationController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _nightModeEnabled 
          ? const Color(AppConstants.nightModeBackground) 
          : const Color(AppConstants.skyBackgroundDark),
      body: Stack(
        children: [
          // Sky map main canvas
          _isLoading
              ? Center(
                  child: CircularProgressIndicator(
                    color: _nightModeEnabled ? Colors.red : Colors.lightBlue,
                  ),
                )
              : GestureDetector(
                  onScaleStart: (ScaleStartDetails details) {
                    _previousScale = _zoomFactor;
                    
                    // Disable sensor tracking during manual interaction
                    if (_sensorTrackingEnabled) {
                      _toggleSensorTracking();
                    }
                  },
                  onScaleUpdate: (ScaleUpdateDetails details) {
                    setState(() {
                      // Handle zooming
                      if (details.scale != 1.0) {
                        _zoomFactor = math.max(
                          AppConstants.minZoomFactor, 
                          math.min(_previousScale * details.scale, AppConstants.maxZoomFactor)
                        );
                      }
                      
                      // Handle panning
                      if (details.scale == 1.0) {
                        _azimuth = (_azimuth - details.focalPointDelta.dx * 0.3) % 360;
                        _elevation = math.max(0, math.min(90, _elevation + details.focalPointDelta.dy * 0.3));
                      }
                    });
                  },
                  onTapDown: (TapDownDetails details) {
                    // Check if an object was tapped
                    final tapPosition = details.localPosition;
                    final tappedObject = _findObjectAtPosition(tapPosition);
                    if (tappedObject != null) {
                      _showObjectInfo(tappedObject);
                    }
                  },
                  child: CustomPaint(
                    painter: SkyMapPainter(
                      stars: _showStars ? _stars : [],
                      planets: _showPlanets ? _planets : [],
                      deepSkyObjects: _showDeepSkyObjects ? _deepSkyObjects : [],
                      constellations: _showConstellations ? _constellations : [],
                      azimuth: _azimuth,
                      elevation: _elevation,
                      latitude: _latitude,
                      longitude: _longitude,
                      dateTime: _currentTime,
                      zoomFactor: _zoomFactor,
                      offsetX: _offsetX,
                      offsetY: _offsetY,
                      projectionMode: _projectionMode,
                      showGrid: _showGrid,
                      showHorizon: _showHorizon,
                      showObjectNames: _showObjectNames,
                      selectedObject: _selectedObject,
                      nightMode: _nightModeEnabled,
                    ),
                    size: MediaQuery.of(context).size,
                  ),
                ),
                
          // App bar overlay
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: SkyMapAppBar(
              locationName: _locationName,
              currentTime: FormatUtils.formatTime(_currentTime),
              searchController: _searchController,
              onSearch: _searchObject,
              onMenuToggle: _toggleMenu,
              nightMode: _nightModeEnabled,
            ),
          ),
          
          // Menu panel (sliding from right)
          AnimatedPositioned(
            duration: const Duration(milliseconds: 250),
            curve: Curves.easeInOut,
            top: 56,
            bottom: 56,
            right: _menuVisible ? 0 : -250,
            width: 250,
            child: SettingsPanel(
              showStars: _showStars,
              showPlanets: _showPlanets,
              showConstellations: _showConstellations,
              showDeepSkyObjects: _showDeepSkyObjects,
              showGrid: _showGrid,
              showHorizon: _showHorizon,
              showObjectNames: _showObjectNames,
              projectionMode: _projectionMode,
              useRealTime: _useRealTime,
              nightModeEnabled: _nightModeEnabled,
              onShowStarsChanged: (val) => setState(() => _showStars = val),
              onShowPlanetsChanged: (val) => setState(() => _showPlanets = val),
              onShowConstellationsChanged: (val) => setState(() => _showConstellations = val),
              onShowDeepSkyObjectsChanged: (val) => setState(() => _showDeepSkyObjects = val),
              onShowGridChanged: (val) => setState(() => _showGrid = val),
              onShowHorizonChanged: (val) => setState(() => _showHorizon = val),
              onShowObjectNamesChanged: (val) => setState(() => _showObjectNames = val),
              onProjectionModeChanged: (val) => setState(() {
                if (val != null) {
                  _projectionMode = val;
                  _projectionName = val == 0 ? "Azimuthal" : "Equatorial";
                }
              }),
              onUseRealTimeChanged: (val) => setState(() => _useRealTime = val),
              onNightModeChanged: (val) => setState(() => _nightModeEnabled = val),
              onSetCurrentTime: _showDateTimePicker,
              onShowTechnicalInfo: _showTechnicalInfo,
              onResetView: _resetView,
              onResetToRealTime: _resetToRealTime,
              onCalibrateCompass: _calibrateCompass,
            ),
          ),
          
          // Bottom toolbar
          Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: BottomToolbar(
              onNorth: () => setState(() => _azimuth = 0.0),
              onZoomIn: () => setState(() => _zoomFactor = math.min(_zoomFactor * 1.2, AppConstants.maxZoomFactor)),
              onZoomOut: () => setState(() => _zoomFactor = math.max(_zoomFactor / 1.2, AppConstants.minZoomFactor)),
              onToggleProjection: _toggleProjection,
              onShowGuide: _showBeginnerGuide,
              onToggleTracking: _toggleSensorTracking,
              trackingEnabled: _sensorTrackingEnabled,
            ),
          ),
          
          // Selected object info
          if (_selectedObject != null)
            Positioned(
              top: 70,
              right: _menuVisible ? 260 : 10,
              child: ObjectInfoCard(
                object: _selectedObject!,
                onClose: () => setState(() => _selectedObject = null),
                onMoreInfo: () => _showObjectInfo(_selectedObject!),
              ),
            ),
            
          // Current view information overlay
          Positioned(
            bottom: 65,
            left: 10,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: _nightModeEnabled ? Colors.red.shade900.withOpacity(0.5) : Colors.black54,
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(
                'Az: ${_azimuth.toStringAsFixed(1)}° Alt: ${_elevation.toStringAsFixed(1)}° Zoom: ${_zoomFactor.toStringAsFixed(1)}×',
                style: TextStyle(
                  color: _nightModeEnabled ? Colors.red.shade100 : Colors.white,
                  fontSize: 12,
                ),
              ),
            ),
          ),
          
          // Tracking indicator
          if (_sensorTrackingEnabled)
            Positioned(
              top: 70,
              left: 10,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: _nightModeEnabled ? Colors.red.shade900.withOpacity(0.5) : Colors.green.withOpacity(0.7),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Row(
                  children: [
                    Icon(
                      Icons.sensors,
                      color: _nightModeEnabled ? Colors.red.shade100 : Colors.white,
                      size: 16,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      'Tracking Active',
                      style: TextStyle(
                        color: _nightModeEnabled ? Colors.red.shade100 : Colors.white,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}