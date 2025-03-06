// services/celestial_data_provider.dart
import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../models/celestial_object.dart';
import '../models/constellation.dart';
import '../models/star_position.dart';

/// Service for providing celestial data
class CelestialDataProvider {
  // Singleton instance
  static final CelestialDataProvider _instance = CelestialDataProvider._internal();
  
  // Factory constructor
  factory CelestialDataProvider() => _instance;
  
  // Private constructor
  CelestialDataProvider._internal();
  
  // Cache for celestial data
  List<CelestialObject>? _starsCache;
  List<CelestialObject>? _planetsCache;
  List<CelestialObject>? _deepSkyObjectsCache;
  List<Constellation>? _constellationsCache;
  
  /// Get stars data
  Future<List<CelestialObject>> getStars() async {
    if (_starsCache != null) {
      return _starsCache!;
    }
    
    // Load and cache stars data
    final stars = await _loadStarsData();
    _starsCache = stars;
    return stars;
  }
  
  /// Get planets data with current positions
  Future<List<CelestialObject>> getPlanets({DateTime? dateTime}) async {
    // Always recalculate planet positions if date is provided
    if (dateTime != null || _planetsCache == null) {
      final planets = _calculatePlanetPositions(dateTime ?? DateTime.now());
      _planetsCache = planets;
      return planets;
    }
    
    return _planetsCache!;
  }
  
  /// Get deep sky objects data
  Future<List<CelestialObject>> getDeepSkyObjects() async {
    if (_deepSkyObjectsCache != null) {
      return _deepSkyObjectsCache!;
    }
    
    // Load and cache deep sky objects data
    final dsos = await _loadDeepSkyObjects();
    _deepSkyObjectsCache = dsos;
    return dsos;
  }
  
  /// Get constellation data
  Future<List<Constellation>> getConstellations() async {
    if (_constellationsCache != null) {
      return _constellationsCache!;
    }
    
    // Load and cache constellation data
    final constellations = await _loadConstellationData();
    _constellationsCache = constellations;
    return constellations;
  }
  
  /// Clear all data caches
  void clearCaches() {
    _starsCache = null;
    _planetsCache = null;
    _deepSkyObjectsCache = null;
    _constellationsCache = null;
  }
  
  /// Search for celestial objects by name or catalog ID
  Future<List<CelestialObject>> searchObjects(String query) async {
    if (query.isEmpty) {
      return [];
    }
    
    final queryLower = query.toLowerCase();
    final result = <CelestialObject>[];
    
    // Get all celestial objects
    final stars = await getStars();
    final planets = await getPlanets();
    final dsos = await getDeepSkyObjects();
    
    final allObjects = [...stars, ...planets, ...dsos];
    
    // Exact matches first (highest priority)
    for (var obj in allObjects) {
      if (obj.name.toLowerCase() == queryLower || 
          obj.catalogId.toLowerCase() == queryLower) {
        result.add(obj);
      }
    }
    
    // Then partial matches in name
    if (result.isEmpty) {
      for (var obj in allObjects) {
        if (obj.name.toLowerCase().contains(queryLower)) {
          result.add(obj);
        }
      }
    }
    
    // Then partial matches in catalog ID
    if (result.isEmpty) {
      for (var obj in allObjects) {
        if (obj.catalogId.toLowerCase().contains(queryLower)) {
          result.add(obj);
        }
      }
    }
    
    return result;
  }
  
  /// Find the brightest object near given coordinates
  Future<CelestialObject?> findObjectNearCoordinates(
    double rightAscension, 
    double declination,
    double toleranceDegrees,
  ) async {
    // Get all celestial objects
    final stars = await getStars();
    final planets = await getPlanets();
    final dsos = await getDeepSkyObjects();
    
    // Combine and sort by brightness (magnitude)
    final List<CelestialObject> allObjects = [...stars, ...planets, ...dsos]
      ..sort((a, b) => a.magnitude.compareTo(b.magnitude));
    
    // Check distance to the coordinates
    for (var obj in allObjects) {
      // Simple spherical distance calculation
      final double dRA = (obj.rightAscension - rightAscension) * 15 * math.cos(declination * math.pi / 180);
      final double dDec = obj.declination - declination;
      final double distance = math.sqrt(dRA * dRA + dDec * dDec);
      
      if (distance <= toleranceDegrees) {
        return obj;
      }
    }
    
    return null;
  }
  
  /// Load stars data from assets/database
  Future<List<CelestialObject>> _loadStarsData() async {
    // This would normally load from a file or database
    // For now, we'll use hardcoded data
    final List<CelestialObject> stars = [];
    
    // Add bright stars
    stars.add(CelestialObject.star(
      name: "Sirius",
      catalogId: "α CMa",
      rightAscension: 6.7525,
      declination: -16.7161,
      magnitude: -1.46,
      description: "The brightest star in the night sky.",
      color: Colors.white,
    ));
    
    stars.add(CelestialObject.star(
      name: "Canopus",
      catalogId: "α Car",
      rightAscension: 6.3992,
      declination: -52.6956,
      magnitude: -0.74,
      description: "The second brightest star in the night sky.",
      color: Colors.white.withBlue(220),
    ));
    
    stars.add(CelestialObject.star(
      name: "Alpha Centauri",
      catalogId: "α Cen",
      rightAscension: 14.6598,
      declination: -60.8331,
      magnitude: -0.27,
      description: "The closest star system to the Solar System.",
      color: Colors.yellowAccent,
    ));
    
    stars.add(CelestialObject.star(
      name: "Arcturus",
      catalogId: "α Boo",
      rightAscension: 14.2612,
      declination: 19.1825,
      magnitude: -0.05,
      description: "The brightest star in the northern celestial hemisphere.",
      color: Colors.orange,
    ));
    
    stars.add(CelestialObject.star(
      name: "Vega",
      catalogId: "α Lyr",
      rightAscension: 18.6157,
      declination: 38.7836,
      magnitude: 0.03,
      description: "The fifth brightest star in the night sky.",
      color: Colors.lightBlueAccent,
    ));
    
    // Add more stars...
    
    // Add background stars
    const int backgroundStarsCount = 200;
    final random = math.Random(42); // Fixed seed for consistency
    
    for (int i = 0; i < backgroundStarsCount; i++) {
      double mag = 3.0 + random.nextDouble() * 3.0;
      double ra = random.nextDouble() * 24;
      double decBias = (random.nextDouble() * 2 - 1) * (random.nextDouble() * 2 - 1);
      double dec = decBias * 90;
      
      // Simple color distribution
      Color starColor;
      int colorType = random.nextInt(10);
      
      if (colorType < 1) {
        starColor = Colors.blue.shade100; // O, B stars - rare
      } else if (colorType < 3) {
        starColor = Colors.white; // A stars
      } else if (colorType < 5) {
        starColor = Colors.yellow.shade100; // F, G stars
      } else if (colorType < 7) {
        starColor = Colors.orange.shade100; // K stars
      } else {
        starColor = Colors.red.shade100; // M stars - common
      }
      
      stars.add(CelestialObject.star(
        name: "HD ${100000 + i}",
        catalogId: "HD ${100000 + i}",
        rightAscension: ra,
        declination: dec,
        magnitude: mag,
        color: starColor,
      ));
    }
    
    return stars;
  }
  
  /// Calculate planet positions for a given date
  List<CelestialObject> _calculatePlanetPositions(DateTime dateTime) {
    // In a real app, we would use proper astronomical calculations
    // Based on orbital elements and the date
    // For now, we'll use simplified approximate positions
    
    // Get a random offset based on the date to simulate movement
    final dateKey = dateTime.year * 10000 + dateTime.month * 100 + dateTime.day;
    final random = math.Random(dateKey);
    
    final List<CelestialObject> planets = [];
    
    planets.add(CelestialObject.planet(
      name: "Mercury",
      catalogId: "Mercury",
      rightAscension: 7.0 + _getRandomOffset(random),
      declination: 20.0 + _getRandomOffset(random),
      magnitude: -0.5,
      description: "The smallest and innermost planet in the Solar System.",
      color: Colors.grey.shade300,
    ));
    
    planets.add(CelestialObject.planet(
      name: "Venus",
      catalogId: "Venus",
      rightAscension: 8.0 + _getRandomOffset(random),
      declination: 15.0 + _getRandomOffset(random),
      magnitude: -4.3,
      description: "The second planet from the Sun and the brightest natural object in the night sky.",
      color: Colors.yellow.shade100,
    ));
    
    planets.add(CelestialObject.planet(
      name: "Mars",
      catalogId: "Mars",
      rightAscension: 10.0 + _getRandomOffset(random),
      declination: 5.0 + _getRandomOffset(random),
      magnitude: 1.0,
      description: "The fourth planet from the Sun, often called the 'Red Planet'.",
      color: Colors.red.shade300,
    ));
    
    planets.add(CelestialObject.planet(
      name: "Jupiter",
      catalogId: "Jupiter",
      rightAscension: 12.0 + _getRandomOffset(random),
      declination: 0.0 + _getRandomOffset(random),
      magnitude: -2.2,
      description: "The largest planet in the Solar System.",
      color: Colors.amber.shade200,
    ));
    
    planets.add(CelestialObject.planet(
      name: "Saturn",
      catalogId: "Saturn",
      rightAscension: 14.0 + _getRandomOffset(random),
      declination: -10.0 + _getRandomOffset(random),
      magnitude: 0.5,
      description: "The sixth planet from the Sun, known for its rings.",
      color: Colors.yellow.shade400,
    ));
    
    planets.add(CelestialObject.planet(
      name: "Uranus",
      catalogId: "Uranus",
      rightAscension: 16.0 + _getRandomOffset(random),
      declination: -20.0 + _getRandomOffset(random),
      magnitude: 5.6,
      description: "The seventh planet from the Sun.",
      color: Colors.cyan.shade200,
    ));
    
    planets.add(CelestialObject.planet(
      name: "Neptune",
      catalogId: "Neptune",
      rightAscension: 18.0 + _getRandomOffset(random),
      declination: -25.0 + _getRandomOffset(random),
      magnitude: 7.8,
      description: "The eighth and farthest planet from the Sun.",
      color: Colors.blue.shade300,
    ));
    
    planets.add(CelestialObject.planet(
      name: "Moon",
      catalogId: "Moon",
      rightAscension: 6.0 + _getRandomOffset(random),
      declination: 25.0 + _getRandomOffset(random),
      magnitude: -12.6,
      description: "Earth's only natural satellite.",
      color: Colors.grey.shade200,
    ));
    
    return planets;
  }
  
  double _getRandomOffset(math.Random random) {
    return (random.nextDouble() - 0.5) * 2.0;
  }
  
  /// Load deep sky objects data
  Future<List<CelestialObject>> _loadDeepSkyObjects() async {
    final List<CelestialObject> dsos = [];
    
    // Selected Messier objects for beginners
    final messierObjects = [
      ["Andromeda Galaxy", "galaxy", "M31", 0.7126, 41.2686, 3.4, "The nearest major galaxy to the Milky Way."],
      ["Triangulum Galaxy", "galaxy", "M33", 1.5633, 30.6583, 5.7, "A spiral galaxy in the constellation Triangulum."],
      ["Pleiades", "open", "M45", 3.7833, 24.1167, 1.6, "An open star cluster also known as the Seven Sisters."],
      ["Orion Nebula", "nebula", "M42", 5.5833, -5.3833, 4.0, "A diffuse nebula situated in the Milky Way."],
      ["Crab Nebula", "nebula", "M1", 5.5756, 22.0145, 8.4, "A supernova remnant in the constellation of Taurus."],
      ["Beehive Cluster", "open", "M44", 8.7, 19.9833, 3.7, "An open cluster in the constellation Cancer."],
      ["Whirlpool Galaxy", "galaxy", "M51", 13.5, 47.2, 8.4, "A grand-design spiral galaxy interacting with NGC 5195."],
      ["Ring Nebula", "planetary", "M57", 18.8833, 33.0333, 8.8, "A planetary nebula in the constellation of Lyra."],
      ["Swan Nebula", "nebula", "M17", 18.3458, -16.1833, 6.0, "An H II region in the constellation Sagittarius."],
      ["Dumbbell Nebula", "planetary", "M27", 19.9833, 22.7167, 7.5, "A planetary nebula in the constellation Vulpecula."],
    ];
    
    for (var obj in messierObjects) {
      dsos.add(CelestialObject.deepSky(
        name: obj[0] as String,
        type: obj[1] as String,
        catalogId: obj[2] as String,
        rightAscension: obj[3] as double,
        declination: obj[4] as double,
        magnitude: obj[5] as double,
        description: obj[6] as String,
      ));
    }
    
    return dsos;
  }
  
  /// Load constellation data
  Future<List<Constellation>> _loadConstellationData() async {
    final List<Constellation> constellations = [];
    
    // Ursa Major (Great Bear/Big Dipper)
    final ursaMajorStars = [
      StarPosition("Dubhe", 11.0622, 61.7511),
      StarPosition("Merak", 11.0306, 56.3825),
      StarPosition("Phecda", 11.8968, 53.6948),
      StarPosition("Megrez", 12.2573, 57.0325),
      StarPosition("Alioth", 12.9004, 55.9592),
      StarPosition("Mizar", 13.3988, 54.9254),
      StarPosition("Alkaid", 13.7923, 49.3133),
    ];
    
    final ursaMajorLines = [
      [0, 1], // Dubhe - Merak
      [1, 2], // Merak - Phecda
      [2, 3], // Phecda - Megrez
      [3, 4], // Megrez - Alioth
      [4, 5], // Alioth - Mizar
      [5, 6], // Mizar - Alkaid
    ];
    
    constellations.add(Constellation(
      name: "Ursa Major",
      abbreviation: "UMa",
      stars: ursaMajorStars,
      lines: ursaMajorLines,
    ));
    
    // Orion (The Hunter)
    final orionStars = [
      StarPosition("Betelgeuse", 5.9195, 7.4071),
      StarPosition("Rigel", 5.2425, -8.2016),
      StarPosition("Bellatrix", 5.4186, 6.3498),
      StarPosition("Mintaka", 5.5334, -0.2991),
      StarPosition("Alnilam", 5.6034, -1.2019),
      StarPosition("Alnitak", 5.6795, -1.9426),
      StarPosition("Saiph", 5.7959, -9.6697),
    ];
    
    final orionLines = [
      [0, 2], // Betelgeuse - Bellatrix
      [2, 3], // Bellatrix - Mintaka
      [3, 4], // Mintaka - Alnilam
      [4, 5], // Alnilam - Alnitak
      [5, 6], // Alnitak - Saiph
      [6, 1], // Saiph - Rigel
      [1, 3], // Rigel - Mintaka
      [0, 6], // Betelgeuse - Saiph
    ];
    
    constellations.add(Constellation(
      name: "Orion",
      abbreviation: "Ori",
      stars: orionStars,
      lines: orionLines,
    ));
    
    // Add more constellations...
    
    return constellations;
  }
}