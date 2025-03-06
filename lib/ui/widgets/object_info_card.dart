// ui/widgets/object_info_card.dart
import 'package:flutter/material.dart';
import '../../models/celestial_object.dart';
import '../../services/astronomy_service.dart';

/// Widget for displaying selected celestial object information
class ObjectInfoCard extends StatelessWidget {
  final CelestialObject object;
  final VoidCallback onClose;
  final VoidCallback onMoreInfo;

  const ObjectInfoCard({
    super.key,
    required this.object,
    required this.onClose,
    required this.onMoreInfo,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      width: 250,
      decoration: BoxDecoration(
        color: Colors.black87,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.lightBlue.shade900),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Container(
                width: 12,
                height: 12,
                decoration: BoxDecoration(
                  color: object.color,
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  object.name,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              GestureDetector(
                onTap: onClose,
                child: const Icon(Icons.close, color: Colors.white70, size: 16),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              Text(
                'Type: ${object.type[0].toUpperCase() + object.type.substring(1)}',
                style: const TextStyle(
                  color: Colors.white70,
                  fontSize: 12,
                ),
              ),
              const Spacer(),
              Text(
                object.catalogId,
                style: TextStyle(
                  color: Colors.amber.shade400,
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            'Magnitude: ${object.magnitude.toStringAsFixed(2)}',
            style: const TextStyle(
              color: Colors.white70,
              fontSize: 12,
            ),
          ),
          Text(
            'RA: ${AstronomyService.formatRA(object.rightAscension)}',
            style: const TextStyle(
              color: Colors.white70,
              fontSize: 12,
            ),
          ),
          Text(
            'Dec: ${AstronomyService.formatDEC(object.declination)}',
            style: const TextStyle(
              color: Colors.white70,
              fontSize: 12,
            ),
          ),
          if (object.description != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                object.description!,
                style: const TextStyle(
                  color: Colors.white70,
                  fontSize: 11,
                  fontStyle: FontStyle.italic,
                ),
              ),
            ),
          const SizedBox(height: 8),
          TextButton(
            child: const Text('More Info'),
            onPressed: onMoreInfo,
            style: TextButton.styleFrom(
              foregroundColor: Colors.lightBlue,
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              minimumSize: Size.zero,
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
            ),
          ),
        ],
      ),
    );
  }
}