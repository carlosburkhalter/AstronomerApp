// ui/painters/sky_map_painter.dart
import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../../models/celestial_object.dart';
import '../../models/constellation.dart';
import '../../services/astronomy_service.dart';

/// Main painter class for the sky map
class SkyMapPainter extends CustomPainter {
  final List<CelestialObject> stars;
  final List<CelestialObject> planets;
  final List<CelestialObject> deepSkyObjects;
  final List<Constellation> constellations;
  final double azimuth;
  final double elevation;
  final double latitude;
  final double longitude;
  final DateTime dateTime;
  final double zoomFactor;
  final double offsetX;
  final double offsetY;
  final int projectionMode;
  final bool showGrid;
  final bool showHorizon;
  final bool showObjectNames;
  final CelestialObject? selectedObject;
  final bool nightMode;
  
  // Cache for performance
  final Map<String, Map<String, dynamic>> _screenCoordinatesCache = {};

  SkyMapPainter({
    required this.stars,
    required this.planets,
    required this.deepSkyObjects,
    required this.constellations,
    required this.azimuth,
    required this.elevation,
    required this.latitude,
    required this.longitude,
    required this.dateTime,
    required this.zoomFactor,
    required this.offsetX,
    required this.offsetY,
    required this.projectionMode,
    required this.showGrid,
    required this.showHorizon,
    required this.showObjectNames,
    required this.selectedObject,
    this.nightMode = false,
  });

  @override
  void paint(Canvas canvas, Size size) {
    // Clear the coordinate cache when starting a new paint
    _screenCoordinatesCache.clear();
    
    // Center of the screen
    final centerX = size.width / 2;
    final centerY = size.height / 2;
    
    // Draw in layers from back to front
    _drawSkyBackground(canvas, size);
    
    if (showHorizon) {
      _drawHorizon(canvas, size, centerX, centerY);
    }
    
    if (showGrid) {
      _drawCoordinateGrid(canvas, size, centerX, centerY);
    }
    
    // Draw constellations (lines connecting stars)
    if (constellations.isNotEmpty) {
      for (var constellation in constellations) {
        _drawConstellation(canvas, size, constellation, centerX, centerY);
      }
    }
    
    // Draw deep sky objects
    if (deepSkyObjects.isNotEmpty) {
      for (var dso in deepSkyObjects) {
        _drawDeepSkyObject(canvas, size, dso, centerX, centerY);
      }
    }
    
    // Draw stars
    if (stars.isNotEmpty) {
      for (var star in stars) {
        _drawStar(canvas, size, star, centerX, centerY);
      }
    }
    
    // Draw planets
    if (planets.isNotEmpty) {
      for (var planet in planets) {
        _drawPlanet(canvas, size, planet, centerX, centerY);
      }
    }
    
    // Draw cardinal points
    _drawCardinalPoints(canvas, size, centerX, centerY);
    
    // Draw projection info
    _drawProjectionInfo(canvas, size);
    
    // If an object is selected, highlight it
    if (selectedObject != null) {
      _highlightSelectedObject(canvas, size, selectedObject!, centerX, centerY);
    }
  }
  
  // Draw sky background with stars
  void _drawSkyBackground(Canvas canvas, Size size) {
    // Realistic sky gradient based on elevation
    final Paint skyPaint = Paint();
    
    if (nightMode) {
      // Night mode - use a dark red background
      skyPaint.color = const Color(0xFF110000);
      canvas.drawRect(Rect.fromLTWH(0, 0, size.width, size.height), skyPaint);
    } else {
      // Normal mode - use blue gradient
      skyPaint.shader = RadialGradient(
        center: Alignment.center,
        radius: 1.0,
        colors: const [
          Color(0xFF050A15), // Very dark blue at center
          Color(0xFF071525), // Dark blue
          Color(0xFF0A1A35), // Medium blue
          Color(0xFF0F1A40), // Slightly lighter blue/violet at edge
        ],
        stops: const [0.0, 0.3, 0.7, 1.0],
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height));
      
      canvas.drawRect(Rect.fromLTWH(0, 0, size.width, size.height), skyPaint);
      
      // Add Milky Way effect
      _drawMilkyWayEffect(canvas, size);
    }
    
    // Add background stars
    _drawBackgroundStarField(canvas, size);
  }
  
  // Draw a subtle Milky Way band
  void _drawMilkyWayEffect(Canvas canvas, Size size) {
    final centerX = size.width / 2;
    final centerY = size.height / 2;
    final milkyWayWidth = size.width * 0.6;
    final milkyWayHeight = size.height * 1.5;
    
    // Rotation based on time 
    final milkyWayAngle = (dateTime.hour / 24.0) * 2 * math.pi + math.pi / 6;
    
    canvas.save();
    canvas.translate(centerX, centerY);
    canvas.rotate(milkyWayAngle);
    
    // Draw the Milky Way band with a radial gradient
    final milkyWayPaint = Paint()
      ..shader = RadialGradient(
        center: const Alignment(0.0, 0.0),
        radius: 1.0,
        colors: [
          Colors.white.withOpacity(0.05),
          Colors.white.withOpacity(0.03),
          Colors.white.withOpacity(0.01),
          Colors.white.withOpacity(0.0),
        ],
        stops: const [0.1, 0.3, 0.6, 1.0],
      ).createShader(Rect.fromCenter(
        center: Offset.zero,
        width: milkyWayWidth,
        height: milkyWayHeight,
      ));
    
    canvas.drawOval(
      Rect.fromCenter(
        center: Offset.zero,
        width: milkyWayWidth,
        height: milkyWayHeight,
      ),
      milkyWayPaint
    );
    
    canvas.restore();
  }
  
  // Draw background star field
  void _drawBackgroundStarField(Canvas canvas, Size size) {
    // Add a field of very faint stars for background
    final random = math.Random(42); // Fixed seed for consistency
    
    for (int i = 0; i < 500; i++) {
      final x = random.nextDouble() * size.width;
      final y = random.nextDouble() * size.height;
      final starSize = 0.1 + random.nextDouble() * 0.4;
      final opacity = 0.1 + random.nextDouble() * 0.3;
      
      // In night mode, stars are red-tinted
      final starColor = nightMode 
          ? Colors.red.withOpacity(opacity) 
          : Colors.white.withOpacity(opacity);
      
      canvas.drawCircle(
        Offset(x, y),
        starSize,
        Paint()..color = starColor,
      );
    }
  }
  
  // Draw horizon and ground
  void _drawHorizon(Canvas canvas, Size size, double centerX, double centerY) {
    // Draw horizon line and ground
    final Color horizonColor = nightMode 
        ? Colors.red.withOpacity(0.5) 
        : Colors.green.withOpacity(0.5);
        
    final Paint horizonPaint = Paint()
      ..color = horizonColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;
    
    final radius = size.width * 0.4 * zoomFactor;
    
    // Draw horizon circle
    canvas.drawCircle(
      Offset(centerX, centerY),
      radius,
      horizonPaint,
    );
    
    // Draw ground with gradient
    final Paint groundPaint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: nightMode 
            ? [
                Colors.red.shade900.withOpacity(0.3),
                Colors.red.shade900.withOpacity(0.5),
              ]
            : [
                Colors.green.shade900.withOpacity(0.3),
                Colors.brown.shade800.withOpacity(0.5),
              ],
      ).createShader(Rect.fromLTRB(
        centerX - radius,
        centerY,
        centerX + radius,
        centerY + radius * 2
      ))
      ..style = PaintingStyle.fill;
    
    // Create a path for ground with terrain silhouette
    final groundPath = Path();
    groundPath.moveTo(centerX - radius, centerY);
    
    // Create a simple terrain silhouette
    final terrain = 40; // Number of points
    final terrainRandom = math.Random(42);
    
    for (int i = 0; i <= terrain; i++) {
      double x = centerX - radius + (2 * radius / terrain) * i;
      
      // Random height for terrain profile
      double height = 0;
      
      // Add some "mountains"
      if (i % 7 == 0) {
        height = -radius * 0.1 * (0.3 + terrainRandom.nextDouble() * 0.7);
      } else if (i % 3 == 0) {
        height = -radius * 0.05 * terrainRandom.nextDouble();
      } else {
        height = -radius * 0.02 * terrainRandom.nextDouble();
      }
      
      groundPath.lineTo(x, centerY + height);
    }
    
    // Close the path
    groundPath.lineTo(centerX + radius, centerY);
    groundPath.arcTo(
      Rect.fromCircle(center: Offset(centerX, centerY), radius: radius),
      0,
      math.pi,
      false
    );
    groundPath.close();
    
    canvas.drawPath(groundPath, groundPaint);
    
    // Add some trees or buildings
    _drawTerrainDetails(canvas, centerX, centerY, radius);
  }
  
  // Draw trees and buildings on horizon
  void _drawTerrainDetails(Canvas canvas, double centerX, double centerY, double radius) {
    final random = math.Random(42);
    
    // Draw some trees and buildings
    for (int i = 0; i < 8; i++) {
      double x = centerX - radius * 0.8 + radius * 1.6 * random.nextDouble();
      double height = radius * 0.06 + radius * 0.04 * random.nextDouble();
      
      if (random.nextBool()) {
        // Draw a tree
        Paint trunkPaint = Paint()
          ..color = nightMode 
              ? Colors.red.shade900.withOpacity(0.7)
              : Colors.brown.shade900.withOpacity(0.7)
          ..style = PaintingStyle.fill;
          
        canvas.drawRect(
          Rect.fromLTWH(x - 1, centerY - height * 0.4, 2, height * 0.5),
          trunkPaint
        );
        
        Paint foliagePaint = Paint()
          ..color = nightMode 
              ? Colors.red.shade900.withOpacity(0.6)
              : Colors.green.shade900.withOpacity(0.6)
          ..style = PaintingStyle.fill;
          
        // Draw foliage as a simple triangle
        Path treePath = Path();
        treePath.moveTo(x, centerY - height);
        treePath.lineTo(x - height * 0.4, centerY - height * 0.6);
        treePath.lineTo(x + height * 0.4, centerY - height * 0.6);
        treePath.close();
        
        canvas.drawPath(treePath, foliagePaint);
        
        // Second part of foliage
        Path treePath2 = Path();
        treePath2.moveTo(x, centerY - height * 0.7);
        treePath2.lineTo(x - height * 0.5, centerY - height * 0.3);
        treePath2.lineTo(x + height * 0.5, centerY - height * 0.3);
        treePath2.close();
        
        canvas.drawPath(treePath2, foliagePaint);
      } else {
        // Draw a small building
        Paint buildingPaint = Paint()
          ..color = nightMode 
              ? Colors.red.shade900.withOpacity(0.7)
              : Colors.grey.shade900.withOpacity(0.7)
          ..style = PaintingStyle.fill;
        
        canvas.drawRect(
          Rect.fromLTWH(x - height * 0.3, centerY - height * 0.6, height * 0.6, height * 0.6),
          buildingPaint
        );
        
        // Roof
        Path roofPath = Path();
        roofPath.moveTo(x - height * 0.4, centerY - height * 0.6);
        roofPath.lineTo(x + height * 0.4, centerY - height * 0.6);
        roofPath.lineTo(x, centerY - height * 0.9);
        roofPath.close();
        
        canvas.drawPath(roofPath, Paint()
          ..color = nightMode 
              ? Colors.red.shade800.withOpacity(0.7)
              : Colors.brown.shade800.withOpacity(0.7)
        );
      }
    }
  }
  
  // Draw coordinate grid (azimuthal or equatorial)
  void _drawCoordinateGrid(Canvas canvas, Size size, double centerX, double centerY) {
    // Draw coordinate grid based on projection mode
    final Paint gridPaint = Paint()
      ..color = nightMode ? const Color(0xFF441111) : const Color(0xFF30507A)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 0.5;
      
    final Paint gridMainPaint = Paint()
      ..color = nightMode ? const Color(0xFF881111) : const Color(0xFF4070AA)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 0.8;
    
    final TextStyle gridLabelStyle = TextStyle(
      color: nightMode 
          ? Colors.red.shade200.withOpacity(0.7)
          : Colors.lightBlue.shade200.withOpacity(0.7),
      fontSize: 10,
    );
    
    if (projectionMode == 0) {
      // Azimuthal projection (altitude-azimuth)
      
      // Altitude circles
      for (int alt = 10; alt <= 80; alt += 10) {
        final radius = size.width * 0.4 * (90 - alt) / 90 * zoomFactor;
        final isMainLine = alt % 30 == 0;
        
        canvas.drawCircle(
          Offset(centerX, centerY),
          radius,
          isMainLine ? gridMainPaint : gridPaint,
        );
        
        // Labels for main altitude circles
        if (isMainLine) {
          final textSpan = TextSpan(
            text: '$alt°',
            style: gridLabelStyle,
          );
          final textPainter = TextPainter(
            text: textSpan,
            textDirection: TextDirection.ltr,
          );
          textPainter.layout();

          textPainter.paint(
            canvas,
            Offset(centerX + 5, centerY - radius - 15),
          );
        }
      }
      
      // Azimuth lines
      for (int az = 0; az < 360; az += 15) {
        final isMainLine = az % 90 == 0;
        final radians = (az - azimuth) * math.pi / 180;
        final maxRadius = size.width * 0.5 * zoomFactor;
        
        canvas.drawLine(
          Offset(centerX, centerY),
          Offset(
            centerX + maxRadius * math.sin(radians),
            centerY - maxRadius * math.cos(radians),
          ),
          isMainLine ? gridMainPaint : gridPaint,
        );
        
        // Labels for main azimuth lines
        if (isMainLine) {
          String azLabel = '$az°';
          if (az == 0) azLabel = 'N';
          if (az == 90) azLabel = 'E';
          if (az == 180) azLabel = 'S';
          if (az == 270) azLabel = 'W';
          
          final textSpan = TextSpan(
            text: azLabel,
            style: gridLabelStyle.copyWith(
              fontWeight: isMainLine ? FontWeight.bold : FontWeight.normal,
            ),
          );
          
          final textPainter = TextPainter(
            text: textSpan,
            textDirection: TextDirection.ltr,
          );
          
          textPainter.layout();
          
          final labelRadius = maxRadius - 30;
          textPainter.paint(
            canvas,
            Offset(
              centerX + labelRadius * math.sin(radians) - textPainter.width / 2,
              centerY - labelRadius * math.cos(radians) - textPainter.height / 2,
            ),
          );
        }
      }
    } else {
      // Equatorial projection
      
      // Declination circles
      for (int dec = -80; dec <= 80; dec += 20) {
        final isMainLine = dec % 40 == 0 || dec == 0;
        final radius = size.width * 0.4 * (90 - dec) / 180 * zoomFactor;
        
        canvas.drawCircle(
          Offset(centerX, centerY),
          radius,
          isMainLine ? gridMainPaint : gridPaint,
        );
        
        // Labels for declination
        if (isMainLine) {
          final textSpan = TextSpan(
            text: '${dec > 0 ? '+' : ''}${dec}°',
            style: gridLabelStyle,
          );
          
          final textPainter = TextPainter(
            text: textSpan,
            textDirection: TextDirection.ltr,
          );
          
          textPainter.layout();
          textPainter.paint(
            canvas,
            Offset(centerX + 5, centerY - radius - 15),
          );
        }
      }
      
      // Right ascension lines
      for (int ra = 0; ra < 24; ra += 1) {
        final isMainLine = ra % 6 == 0;
        final radians = (ra * 15 - azimuth) * math.pi / 180;
        final maxRadius = size.width * 0.5 * zoomFactor;
        
        canvas.drawLine(
          Offset(centerX, centerY),
          Offset(
            centerX + maxRadius * math.sin(radians),
            centerY - maxRadius * math.cos(radians),
          ),
          isMainLine ? gridMainPaint : gridPaint,
        );
        
        // Labels for right ascension
        if (isMainLine) {
          final textSpan = TextSpan(
            text: '${ra}h',
            style: gridLabelStyle,
          );
          
          final textPainter = TextPainter(
            text: textSpan,
            textDirection: TextDirection.ltr,
          );
          
          textPainter.layout();
          
          final labelRadius = maxRadius - 30;
          textPainter.paint(
            canvas,
            Offset(
              centerX + labelRadius * math.sin(radians) - textPainter.width / 2,
              centerY - labelRadius * math.cos(radians) - textPainter.height / 2,
            ),
          );
        }
      }
      
      // Celestial equator
      canvas.drawCircle(
        Offset(centerX, centerY),
        size.width * 0.4 * (90) / 180 * zoomFactor,
        Paint()
          ..color = nightMode ? const Color(0xFF881111) : const Color(0xFF4488CC)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.2,
      );
    }
  }
  
  // Draw a constellation's lines and name
  void _drawConstellation(Canvas canvas, Size size, Constellation constellation, double centerX, double centerY) {
    // Paint for constellation lines
    final Paint linePaint = Paint()
      ..color = nightMode ? const Color(0xFF551111) : const Color(0xFF3A5F8A)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.0;
    
    // Paint for constellation points
    final Paint starPointPaint = Paint()
      ..color = nightMode ? Colors.red.withOpacity(0.6) : Colors.white.withOpacity(0.6)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 0.8;
    
    // Convert star positions and draw lines
    final List<Offset> starPositions = [];
    
    for (var star in constellation.stars) {
      final screenCoords = _getScreenCoordinates(
        star.rightAscension,
        star.declination,
        size,
        centerX,
        centerY,
      );
      
      if (screenCoords['isVisible'] == true) {
        final position = Offset(screenCoords['x']!, screenCoords['y']!);
        starPositions.add(position);
        
        // Draw a small circle at each constellation star
        canvas.drawCircle(position, 2.0, starPointPaint);
      } else {
        // Position off screen
        starPositions.add(const Offset(-1000, -1000));
      }
    }
    
    // Draw lines between stars
    for (var line in constellation.lines) {
      if (line[0] < starPositions.length && line[1] < starPositions.length) {
        if (starPositions[line[0]].dx > -999 && starPositions[line[1]].dx > -999) {
          canvas.drawLine(
            starPositions[line[0]],
            starPositions[line[1]],
            linePaint,
          );
        }
      }
    }
    
    // Draw constellation name
    if (starPositions.isNotEmpty && showObjectNames) {
      double sumX = 0;
      double sumY = 0;
      int visibleStars = 0;
      
      for (var pos in starPositions) {
        if (pos.dx > -999) {
          sumX += pos.dx;
          sumY += pos.dy;
          visibleStars++;
        }
      }
      
      if (visibleStars > 1) {
        final centerOfConstellation = Offset(sumX / visibleStars, sumY / visibleStars);
        
        final TextSpan textSpan = TextSpan(
          text: constellation.name,
          style: TextStyle(
            color: nightMode ? Colors.red.shade200.withOpacity(0.7) : Colors.lightBlue.shade200.withOpacity(0.7),
            fontSize: 14,
            fontStyle: FontStyle.italic,
          ),
        );
        
        final TextPainter textPainter = TextPainter(
          text: textSpan,
          textDirection: TextDirection.ltr,
        );
        
        textPainter.layout();
        
        // Background for text
        canvas.drawRect(
          Rect.fromCenter(
            center: centerOfConstellation,
            width: textPainter.width + 12,
            height: textPainter.height + 6,
          ),
          Paint()
            ..color = Colors.black.withOpacity(0.7)
            ..style = PaintingStyle.fill,
        );
        
        textPainter.paint(
          canvas,
          Offset(
            centerOfConstellation.dx - textPainter.width / 2,
            centerOfConstellation.dy - textPainter.height / 2,
          ),
        );
      }
    }
  }
  
  // Draw deep sky object (galaxy, nebula, etc)
  void _drawDeepSkyObject(Canvas canvas, Size size, CelestialObject dso, double centerX, double centerY) {
    final screenCoords = _getScreenCoordinates(
      dso.rightAscension,
      dso.declination,
      size,
      centerX,
      centerY,
    );
    
    if (screenCoords['isVisible'] != true) {
      return;
    }
    
    // Check if this is the selected object
    final bool isSelected = dso == selectedObject;
    
    // Determine if object should be displayed based on magnitude and zoom
    if (!isSelected && !dso.isVisibleWithZoom(zoomFactor)) {
      return;
    }
    
    // Adjust color for night mode
    Color dsoColor = dso.color;
    if (nightMode) {
      // Convert to red tones for night mode
      final brightness = (0.299 * dso.color.red + 0.587 * dso.color.green + 0.114 * dso.color.blue) / 255;
      dsoColor = Color.fromARGB(
        dso.color.alpha,
        (brightness * 255).round(),  // Use brightness for red channel
        0,                           // No green
        0                            // No blue
      );
    }
    
    final Paint dsoPaint = Paint()
      ..color = dsoColor.withOpacity(isSelected ? 1.0 : 0.8)
      ..style = PaintingStyle.fill;
    
    final x = screenCoords['x']!;
    final y = screenCoords['y']!;
    
    // Size based on magnitude and type
    double dsoSize = dso.renderSize;
    
    // Increase size for selected objects
    if (isSelected) {
      dsoSize *= 1.5;
    }
    
    // Draw based on object type
    switch (dso.type) {
      case 'galaxy':
        // Galaxy = ellipse
        canvas.drawOval(
          Rect.fromCenter(
            center: Offset(x, y),
            width: dsoSize * 1.5,
            height: dsoSize * 0.8,
          ),
          dsoPaint,
        );
        break;
        
      case 'nebula':
        // Nebula = diffuse cloud
        final nebulaPaint = Paint()
          ..shader = RadialGradient(
            colors: [
              dsoColor.withOpacity(0.8),
              dsoColor.withOpacity(0.3),
              dsoColor.withOpacity(0.1),
            ],
            stops: const [0.2, 0.7, 1.0],
          ).createShader(Rect.fromCircle(center: Offset(x, y), radius: dsoSize * 1.2));
          
        canvas.drawCircle(
          Offset(x, y),
          dsoSize * 1.2,
          nebulaPaint,
        );
        break;
        
      case 'planetary':
        // Planetary nebula = ring
        canvas.drawCircle(
          Offset(x, y),
          dsoSize * 0.7,
          dsoPaint,
        );
        
        canvas.drawCircle(
          Offset(x, y),
          dsoSize * 0.9,
          Paint()
            ..color = dsoColor.withOpacity(0.3)
            ..style = PaintingStyle.stroke
            ..strokeWidth = dsoSize * 0.4,
        );
        break;
        
      case 'globular':
        // Globular cluster = dense star cluster
        canvas.drawCircle(
          Offset(x, y),
          dsoSize * 0.7,
          dsoPaint,
        );
        
        // Outer circle
        canvas.drawCircle(
          Offset(x, y),
          dsoSize,
          Paint()
            ..color = dsoColor.withOpacity(0.3)
            ..style = PaintingStyle.stroke
            ..strokeWidth = 1.0,
        );
        
        // Add star points
        final random = math.Random(dso.catalogId.hashCode);
        for (int i = 0; i < 8; i++) {
          final dist = random.nextDouble() * dsoSize * 0.6;
          final angle = random.nextDouble() * 2 * math.pi;
          final starX = x + dist * math.cos(angle);
          final starY = y + dist * math.sin(angle);
          
          canvas.drawCircle(
            Offset(starX, starY),
            0.8,
            Paint()..color = nightMode ? Colors.red.withOpacity(0.7) : Colors.white.withOpacity(0.7),
          );
        }
        break;
        
      case 'open':
        // Open cluster = loose group of stars
        final random = math.Random(dso.catalogId.hashCode);
        
        for (int i = 0; i < 10; i++) {
          final offsetX = (random.nextDouble() - 0.5) * dsoSize * 2;
          final offsetY = (random.nextDouble() - 0.5) * dsoSize * 2;
          
          canvas.drawCircle(
            Offset(x + offsetX, y + offsetY),
            0.8,
            dsoPaint,
          );
        }
        
        // Circle to indicate region
        canvas.drawCircle(
          Offset(x, y),
          dsoSize * 0.9,
          Paint()
            ..color = dsoColor.withOpacity(0.2)
            ..style = PaintingStyle.stroke
            ..strokeWidth = 0.5,
        );
        break;
        
      default:
        // Default = simple circle
        canvas.drawCircle(
          Offset(x, y),
          dsoSize * 0.5,
          dsoPaint,
        );
        break;
    }
    
    // Add highlight for selected object
    if (isSelected) {
      canvas.drawCircle(
        Offset(x, y),
        dsoSize * 1.5,
        Paint()
          ..color = (nightMode ? Colors.red : Colors.white).withOpacity(0.3)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2.0,
      );
    }
    
    // Draw name label if enabled or if object is selected
    if ((showObjectNames && dso.magnitude < 8.0) || isSelected) {
      final textSpan = TextSpan(
        text: isSelected ? "${dso.name} (${dso.catalogId})" : dso.catalogId,
        style: TextStyle(
          color: dsoColor,
          fontSize: isSelected ? 14 : 12,
          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
          shadows: [
            const Shadow(
              offset: Offset(1, 1),
              blurRadius: 2,
              color: Colors.black,
            ),
          ],
        ),
      );
      
      final textPainter = TextPainter(
        text: textSpan,
        textDirection: TextDirection.ltr,
      );
      
      textPainter.layout();
      textPainter.paint(
        canvas,
        Offset(x + dsoSize + 2, y - textPainter.height / 2),
      );
    }
  }
  
  // Draw a star with diffraction spikes for bright stars
  void _drawStar(Canvas canvas, Size size, CelestialObject star, double centerX, double centerY) {
    final screenCoords = _getScreenCoordinates(
      star.rightAscension,
      star.declination,
      size,
      centerX,
      centerY,
    );
    
    if (screenCoords['isVisible'] == true) {
      // Check if this is the selected object
      final bool isSelected = star == selectedObject;
      
      // Adjust color for night mode
      Color starColor = star.color;
      if (nightMode) {
        // For stars in night mode, use red with varying brightness
        final brightness = (0.299 * star.color.red + 0.587 * star.color.green + 0.114 * star.color.blue) / 255;
        starColor = Color.fromARGB(
          star.color.alpha,
          (brightness * 255).round(),  // Use brightness for red channel
          0,                           // No green
          0                            // No blue
        );
      }
      
      final Paint starPaint = Paint()
        ..color = starColor
        ..style = PaintingStyle.fill;
      
      // Use pre-calculated size for efficiency
      double starSize = star.renderSize;
      
      // Increase size for selected stars
      if (isSelected) {
        starSize *= 1.5;
      }
      
      canvas.drawCircle(
        Offset(screenCoords['x']!, screenCoords['y']!),
        starSize,
        starPaint,
      );
      
      // Add diffraction spikes for bright stars
      if (star.magnitude < 1.5 || isSelected) {
        _drawDiffractionSpikes(
          canvas, 
          Offset(screenCoords['x']!, screenCoords['y']!), 
          starSize * 3.0, 
          starColor,
        );
      }
      
      // Draw name label if enabled or if star is selected
      if ((showObjectNames && star.magnitude < 3.0) || isSelected || zoomFactor > 2.0) {
        // Draw catalog ID
        TextSpan catalogSpan = TextSpan(
          text: star.catalogId,
          style: TextStyle(
            color: starColor.withOpacity(0.7),
            fontSize: isSelected ? 12 : 10,
            fontStyle: FontStyle.italic,
            shadows: [
              const Shadow(
                offset: Offset(1, 1),
                blurRadius: 1,
                color: Colors.black,
              ),
            ],
          ),
        );
        
        TextPainter catalogPainter = TextPainter(
          text: catalogSpan,
          textDirection: TextDirection.ltr,
        );
        
        catalogPainter.layout();
        catalogPainter.paint(
          canvas,
          Offset(
            screenCoords['x']! + starSize + 4,
            screenCoords['y']! - catalogPainter.height - 2,
          ),
        );
        
        // Draw star name
        TextSpan nameSpan = TextSpan(
          text: star.name,
          style: TextStyle(
            color: starColor,
            fontSize: isSelected ? 14 : 12,
            fontWeight: star.magnitude < 1.0 || isSelected ? FontWeight.bold : FontWeight.normal,
            shadows: [
              const Shadow(
                offset: Offset(1, 1),
                blurRadius: 2,
                color: Colors.black,
              ),
            ],
          ),
        );
        
        TextPainter namePainter = TextPainter(
          text: nameSpan,
          textDirection: TextDirection.ltr,
        );
        
        namePainter.layout();
        namePainter.paint(
          canvas,
          Offset(
            screenCoords['x']! + starSize + 4,
            screenCoords['y']!,
          ),
        );
        
        // Add magnitude for selected stars
        if (isSelected) {
          TextSpan magnitudeSpan = TextSpan(
            text: "mag: ${star.magnitude.toStringAsFixed(2)}",
            style: TextStyle(
              color: starColor.withOpacity(0.7),
              fontSize: 10,
              fontStyle: FontStyle.italic,
              shadows: [
                const Shadow(
                  offset: Offset(1, 1),
                  blurRadius: 1,
                  color: Colors.black,
                ),
              ],
            ),
          );
          
          TextPainter magnitudePainter = TextPainter(
            text: magnitudeSpan,
            textDirection: TextDirection.ltr,
          );
          
          magnitudePainter.layout();
          magnitudePainter.paint(
            canvas,
            Offset(
              screenCoords['x']! + starSize + 4,
              screenCoords['y']! + namePainter.height + 2,
            ),
          );
        }
      }
    }
  }
  
  // Draw diffraction spikes for bright stars
  void _drawDiffractionSpikes(Canvas canvas, Offset center, double length, Color color) {
    final Paint spikePaint = Paint()
      ..color = color.withOpacity(0.3)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 0.8;
    
    // Draw 4 rays in a cross pattern
    canvas.drawLine(
      Offset(center.dx - length, center.dy),
      Offset(center.dx + length, center.dy),
      spikePaint,
    );
    
    canvas.drawLine(
      Offset(center.dx, center.dy - length),
      Offset(center.dx, center.dy + length),
      spikePaint,
    );
  }
  
  // Draw a planet with special features for some planets
  void _drawPlanet(Canvas canvas, Size size, CelestialObject planet, double centerX, double centerY) {
    final screenCoords = _getScreenCoordinates(
      planet.rightAscension,
      planet.declination,
      size,
      centerX,
      centerY,
    );
    
    if (screenCoords['isVisible'] == true) {
      // Check if this is the selected object
      final bool isSelected = planet == selectedObject;
      
      // Adjust color for night mode
      Color planetColor = planet.color;
      if (nightMode) {
        // For planets in night mode, use red with varying brightness
        final brightness = (0.299 * planet.color.red + 0.587 * planet.color.green + 0.114 * planet.color.blue) / 255;
        planetColor = Color.fromARGB(
          planet.color.alpha,
          (brightness * 255).round(),  // Use brightness for red channel
          0,                           // No green
          0                            // No blue
        );
      }
      
      final Paint planetPaint = Paint()
        ..color = planetColor
        ..style = PaintingStyle.fill;
      
      // Use pre-calculated size for efficiency
      double planetSize = planet.renderSize;
      
      // Increase size for selected planets
      if (isSelected) {
        planetSize *= 1.5;
      }
      
      // Draw planet (simplified as circle)
      canvas.drawCircle(
        Offset(screenCoords['x']!, screenCoords['y']!),
        planetSize,
        planetPaint,
      );
      
      // Add special features for planets
      if (planet.name == "Saturn") {
        // Add rings for Saturn
        canvas.drawOval(
          Rect.fromCenter(
            center: Offset(screenCoords['x']!, screenCoords['y']!),
            width: planetSize * 2.4,
            height: planetSize * 0.8,
          ),
          Paint()
            ..color = planetColor
            ..style = PaintingStyle.stroke
            ..strokeWidth = 1.5,
        );
      }
      
      // Highlight selected planet
      if (isSelected) {
        canvas.drawCircle(
          Offset(screenCoords['x']!, screenCoords['y']!),
          planetSize * 1.5,
          Paint()
            ..color = (nightMode ? Colors.red : Colors.white).withOpacity(0.3)
            ..style = PaintingStyle.stroke
            ..strokeWidth = 2.0,
        );
      }
      
      // Always show planet names
      TextSpan planetSpan = TextSpan(
        text: planet.name,
        style: TextStyle(
          color: planetColor,
          fontSize: isSelected ? 16 : 14,
          fontWeight: FontWeight.bold,
          shadows: [
            const Shadow(
              offset: Offset(1, 1),
              blurRadius: 2,
              color: Colors.black,
            ),
          ],
        ),
      );
      
      TextPainter planetPainter = TextPainter(
        text: planetSpan,
        textDirection: TextDirection.ltr,
      );
      
      planetPainter.layout();
      planetPainter.paint(
        canvas,
        Offset(
          screenCoords['x']! + planetSize + 4,
          screenCoords['y']! - planetPainter.height / 2,
        ),
      );
      
      // Add magnitude for selected planets
      if (isSelected) {
        TextSpan magnitudeSpan = TextSpan(
          text: "mag: ${planet.magnitude.toStringAsFixed(1)}",
          style: TextStyle(
            color: planetColor.withOpacity(0.7),
            fontSize: 12,
            fontStyle: FontStyle.italic,
            shadows: [
              const Shadow(
                offset: Offset(1, 1),
                blurRadius: 1,
                color: Colors.black,
              ),
            ],
          ),
        );
        
        TextPainter magnitudePainter = TextPainter(
          text: magnitudeSpan,
          textDirection: TextDirection.ltr,
        );
        
        magnitudePainter.layout();
        magnitudePainter.paint(
          canvas,
          Offset(
            screenCoords['x']! + planetSize + 4,
            screenCoords['y']! + planetPainter.height + 2,
          ),
        );
      }
    }
  }
  
  // Draw N, E, S, W markers at the horizon
  void _drawCardinalPoints(Canvas canvas, Size size, double centerX, double centerY) {
    final radius = size.width * 0.45;
    
    final cardinalPoints = [
      {'label': 'N', 'angle': (0 - azimuth + 360) % 360},
      {'label': 'E', 'angle': (90 - azimuth + 360) % 360},
      {'label': 'S', 'angle': (180 - azimuth + 360) % 360},
      {'label': 'W', 'angle': (270 - azimuth + 360) % 360},
    ];
    
    for (var point in cardinalPoints) {
      final angle = point['angle'] as double;
      final radians = angle * math.pi / 180;
      
      final x = centerX + radius * math.sin(radians);
      final y = centerY - radius * math.cos(radians);
      
      // Draw the point
      canvas.drawCircle(
        Offset(x, y),
        5.0,
        Paint()
          ..color = nightMode ? const Color(0xFF991111) : const Color(0xFF4070AA)
          ..style = PaintingStyle.fill,
      );
      
      // Draw the label
      final textSpan = TextSpan(
        text: point['label'] as String,
        style: TextStyle(
          color: nightMode ? Colors.red.shade100 : Colors.white,
          fontSize: 16,
          fontWeight: FontWeight.bold,
          shadows: [
            const Shadow(
              offset: Offset(1, 1),
              blurRadius: 2,
              color: Colors.black,
            ),
          ],
        ),
      );
      
      final textPainter = TextPainter(
        text: textSpan,
        textDirection: TextDirection.ltr,
      );
      
      textPainter.layout();
      textPainter.paint(
        canvas,
        Offset(
          x - textPainter.width / 2,
          y - textPainter.height / 2,
        ),
      );
    }
  }
  
  // Show current projection mode in the corner
  void _drawProjectionInfo(Canvas canvas, Size size) {
    final textSpan = TextSpan(
      text: projectionMode == 0 ? "Azimuthal Projection" : "Equatorial Projection",
      style: TextStyle(
        color: nightMode ? Colors.red.shade300.withOpacity(0.7) : Colors.white70,
        fontSize: 12,
      ),
    );
    
    final textPainter = TextPainter(
      text: textSpan,
      textDirection: TextDirection.ltr,
    );
    
    textPainter.layout();
    textPainter.paint(
      canvas,
      Offset(
        size.width - textPainter.width - 10,
        size.height - textPainter.height - 70,
      ),
    );
  }
  
  // Highlight selected object with pulsing circle
  void _highlightSelectedObject(Canvas canvas, Size size, CelestialObject object, double centerX, double centerY) {
    final screenCoords = _getScreenCoordinates(
      object.rightAscension,
      object.declination,
      size,
      centerX,
      centerY,
    );
    
    if (screenCoords['isVisible'] == true) {
      // Draw a pulsing circle around the selected object
      final now = DateTime.now().millisecondsSinceEpoch / 1000;
      final pulseFactor = 0.7 + 0.3 * math.sin(now * 3);
      
      canvas.drawCircle(
        Offset(screenCoords['x']!, screenCoords['y']!),
        15.0 * pulseFactor,
        Paint()
          ..color = nightMode ? Colors.red.withOpacity(0.3) : Colors.amber.withOpacity(0.3)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2.0,
      );
    }
  }
  
  // Get screen coordinates for a celestial object, using cache if available
  Map<String, dynamic> _getScreenCoordinates(
    double rightAscension,
    double declination,
    Size size,
    double centerX,
    double centerY,
  ) {
    // Create a cache key
    final String cacheKey = '$rightAscension:$declination';
    
    // Return from cache if available
    if (_screenCoordinatesCache.containsKey(cacheKey)) {
      return _screenCoordinatesCache[cacheKey]!;
    }
    
    // Calculate coordinates
    final screenCoords = AstronomyService.equatorialToScreen(
      rightAscension: rightAscension,
      declination: declination,
      latitude: latitude,
      longitude: longitude,
      dateTime: dateTime,
      viewAzimuth: azimuth,
      size: size,
      centerX: centerX,
      centerY: centerY,
      zoomFactor: zoomFactor,
      offsetX: offsetX,
      offsetY: offsetY,
      projectionMode: projectionMode,
    );
    
    // Store in cache
    _screenCoordinatesCache[cacheKey] = screenCoords;
    
    return screenCoords;
  }

  @override
  bool shouldRepaint(SkyMapPainter oldDelegate) {
    // Only repaint if necessary
    return oldDelegate.azimuth != azimuth ||
           oldDelegate.elevation != elevation ||
           oldDelegate.dateTime != dateTime ||
           oldDelegate.zoomFactor != zoomFactor ||
           oldDelegate.offsetX != offsetX ||
           oldDelegate.offsetY != offsetY ||
           oldDelegate.projectionMode != projectionMode ||
           oldDelegate.showGrid != showGrid ||
           oldDelegate.showHorizon != showHorizon ||
           oldDelegate.showObjectNames != showObjectNames ||
           oldDelegate.selectedObject != selectedObject ||
           oldDelegate.nightMode != nightMode;
  }
}