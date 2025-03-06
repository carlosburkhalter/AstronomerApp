// ui/widgets/object_info_dialog.dart
import 'package:flutter/material.dart';
import '../../models/celestial_object.dart';
import '../../services/astronomy_service.dart';

/// Dialog showing detailed information about celestial objects
class ObjectInfoDialog extends StatelessWidget {
  final CelestialObject object;
  final VoidCallback onCenter;

  const ObjectInfoDialog({
    super.key,
    required this.object,
    required this.onCenter,
  });

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: const Color(0xFF102030),
      title: Text(
        object.name,
        style: const TextStyle(color: Colors.white),
      ),
      content: SizedBox(
        width: 300,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildInfoRow('Type:', object.type.toUpperCase()),
            _buildInfoRow('Catalog ID:', object.catalogId),
            _buildInfoRow('Magnitude:', object.magnitude.toStringAsFixed(2)),
            _buildInfoRow('Right Ascension:', AstronomyService.formatRA(object.rightAscension)),
            _buildInfoRow('Declination:', AstronomyService.formatDEC(object.declination)),
            const Divider(color: Colors.white24),
            if (object.description != null)
              Text(
                object.description!,
                style: const TextStyle(color: Colors.white70, fontStyle: FontStyle.italic),
              ),
          ],
        ),
      ),
      actions: [
        TextButton(
          child: const Text('Close', style: TextStyle(color: Colors.white)),
          onPressed: () => Navigator.of(context).pop(),
        ),
        TextButton(
          child: const Text('Center View', style: TextStyle(color: Colors.lightBlue)),
          onPressed: () {
            Navigator.of(context).pop();
            onCenter();
          },
        ),
      ],
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        children: [
          Text(
            label,
            style: const TextStyle(color: Colors.white70, fontWeight: FontWeight.bold),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(color: Colors.white),
            ),
          ),
        ],
      ),
    );
  }
}