// ui/widgets/sky_map_app_bar.dart
import 'package:flutter/material.dart';

/// Custom app bar for the sky map screen
class SkyMapAppBar extends StatelessWidget {
  final String locationName;
  final String currentTime;
  final TextEditingController searchController;
  final Function(String) onSearch;
  final VoidCallback onMenuToggle;

  const SkyMapAppBar({
    super.key,
    required this.locationName,
    required this.currentTime,
    required this.searchController,
    required this.onSearch,
    required this.onMenuToggle,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 56,
      color: const Color(0xFF0A1525).withOpacity(0.8),
      child: Row(
        children: [
          const SizedBox(width: 16),
          Icon(Icons.explore, color: Colors.lightBlue.shade200),
          const SizedBox(width: 8),
          Text(
            'SkyMap for Beginners',
            style: TextStyle(
              color: Colors.lightBlue.shade100,
              fontSize: 18,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(width: 16),
          Text(
            '$locationName - $currentTime',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 14,
            ),
          ),
          const Spacer(),
          // Search bar
          Container(
            width: 200,
            height: 36,
            decoration: BoxDecoration(
              color: const Color(0xFF162632),
              borderRadius: BorderRadius.circular(4),
              border: Border.all(color: Colors.grey.shade800),
            ),
            child: TextField(
              controller: searchController,
              style: const TextStyle(color: Colors.white, fontSize: 14),
              decoration: const InputDecoration(
                hintText: 'Search object...',
                hintStyle: TextStyle(color: Colors.white38, fontSize: 13),
                border: InputBorder.none,
                contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                suffixIcon: Icon(Icons.search, color: Colors.white54, size: 18),
              ),
              onSubmitted: onSearch,
            ),
          ),
          IconButton(
            icon: const Icon(Icons.menu, color: Colors.white70),
            onPressed: onMenuToggle,
            tooltip: 'Settings',
          ),
        ],
      ),
    );
  }
}