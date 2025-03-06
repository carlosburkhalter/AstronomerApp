// models/constellation.dart
import 'star_position.dart';

class Constellation {
  final String name;
  final String abbreviation;
  final List<StarPosition> stars;
  final List<List<int>> lines; // Pairs of indices for connecting lines
  
  const Constellation({
    required this.name,
    required this.abbreviation,
    required this.stars,
    required this.lines,
  });
}