class TelescopeModel {
  final String id;
  final String name;
  final String category;
  final String aperture;
  final String focalLength;
  final double price;
  final double rating;
  final String imageUrl;
  final String description;

  TelescopeModel({
    required this.id,
    required this.name,
    required this.category,
    required this.aperture,
    required this.focalLength,
    required this.price,
    required this.rating,
    required this.imageUrl,
    required this.description,
  });
}