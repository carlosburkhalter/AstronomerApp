import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'dart:ui';
import 'dart:math';
import 'telescope_model.dart'; // Assurez-vous que ce fichier existe et contient la classe TelescopeModel

class TelescopeBrowserScreen extends StatefulWidget {
  const TelescopeBrowserScreen({Key? key}) : super(key: key);

  @override
  State<TelescopeBrowserScreen> createState() => _TelescopeBrowserScreenState();
}

class _TelescopeBrowserScreenState extends State<TelescopeBrowserScreen> {
  final PageController _pageController = PageController(viewportFraction: 0.85);
  int _currentPage = 0;
  
  // Exemple de liste de télescopes
  final List<TelescopeModel> _telescopes = [
    TelescopeModel(
      id: '1',
      name: 'Celestron NexStar 8SE',
      category: 'Schmidt-Cassegrain',
      aperture: '203mm (8")',
      focalLength: '2032mm',
      price: 1199.99,
      rating: 4.7,
      imageUrl: 'assets/telescopes/celestron_nexstar_8se.png',
      description: 'Parfait pour débutants et confirmés grâce à son grand diamètre pour des images claires.',
    ),
    TelescopeModel(
      id: '2',
      name: 'Orion SkyQuest XT10i',
      category: 'Dobsonian',
      aperture: '254mm (10")',
      focalLength: '1200mm',
      price: 899.99,
      rating: 4.8,
      imageUrl: 'assets/telescopes/orion_skyquest_xt10i.png',
      description: 'L’IntelliScope facilite la localisation des objets célestes.',
    ),
    TelescopeModel(
      id: '3',
      name: 'Meade ETX90 Observer',
      category: 'Maksutov-Cassegrain',
      aperture: '90mm (3.5")',
      focalLength: '1250mm',
      price: 649.99,
      rating: 4.5,
      imageUrl: 'assets/telescopes/meade_etx90.png',
      description: 'Design compact et portable offrant un excellent contraste pour l’observation lunaire et planétaire.',
    ),
  ];
  
  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        // Fond animé (nébuleuse)
        const AnimatedStarBackground(),
        SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // En-tête de l'app
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Stellar Scope',
                      style: Theme.of(context).textTheme.headlineMedium,
                    ),
                    CircleAvatar(
                      radius: 20,
                      backgroundColor: Theme.of(context).colorScheme.primary.withOpacity(0.2),
                      child: IconButton(
                        icon: const Icon(CupertinoIcons.profile_circled, color: Colors.white),
                        onPressed: () {},
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                Text(
                  'Find Your Perfect Telescope',
                  style: Theme.of(context).textTheme.headlineLarge,
                ),
                const SizedBox(height: 8),
                Text(
                  'Explore the cosmos with equipment matched to your needs',
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
                const SizedBox(height: 30),
                // Chips de filtre
                SizedBox(
                  height: 44,
                  child: ListView(
                    scrollDirection: Axis.horizontal,
                    children: [
                      _buildFilterChip('All', isSelected: true),
                      _buildFilterChip('Refractor'),
                      _buildFilterChip('Reflector'),
                      _buildFilterChip('Cassegrain'),
                      _buildFilterChip('Dobsonian'),
                    ],
                  ),
                ),
                const SizedBox(height: 30),
                // Affichage des cartes de télescopes via PageView
                Expanded(
                  child: PageView.builder(
                    controller: _pageController,
                    itemCount: _telescopes.length,
                    onPageChanged: (int page) {
                      setState(() {
                        _currentPage = page;
                      });
                    },
                    itemBuilder: (context, index) {
                      final telescope = _telescopes[index];
                      final isActive = index == _currentPage;
                      return AnimatedScale(
                        scale: isActive ? 1.0 : 0.9,
                        duration: const Duration(milliseconds: 300),
                        child: TelescopeCard(telescope: telescope),
                      );
                    },
                  ),
                ),
                const SizedBox(height: 30),
                // Indicateur de page
                Center(
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: List.generate(
                      _telescopes.length,
                      (index) => _buildPageIndicator(index == _currentPage),
                    ),
                  ),
                ),
                const SizedBox(height: 30),
              ],
            ),
          ),
        ),
      ],
    );
  }
  
  Widget _buildFilterChip(String label, {bool isSelected = false}) {
    return Padding(
      padding: const EdgeInsets.only(right: 10),
      child: GestureDetector(
        onTap: () {},
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: isSelected 
                ? Theme.of(context).colorScheme.primary 
                : Theme.of(context).colorScheme.surface,
            borderRadius: BorderRadius.circular(20),
            border: isSelected ? null : Border.all(color: Colors.white24),
          ),
          child: Text(
            label,
            style: TextStyle(
              color: isSelected ? Colors.white : Colors.white70,
              fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
            ),
          ),
        ),
      ),
    );
  }
  
  Widget _buildPageIndicator(bool isActive) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      margin: const EdgeInsets.symmetric(horizontal: 4),
      height: 8,
      width: isActive ? 24 : 8,
      decoration: BoxDecoration(
        color: isActive ? Theme.of(context).colorScheme.primary : Colors.white24,
        borderRadius: BorderRadius.circular(4),
      ),
    );
  }
}

class TelescopeCard extends StatelessWidget {
  final TelescopeModel telescope;
  
  const TelescopeCard({Key? key, required this.telescope}) : super(key: key);
  
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 10),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFF1A1B2E),
            Color(0xFF0A0A1A),
          ],
        ),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: Colors.white54,
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Theme.of(context).colorScheme.primary.withOpacity(0.1),
            blurRadius: 20,
            spreadRadius: 5,
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 5, sigmaY: 5),
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Catégorie et note
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      decoration: BoxDecoration(
                        color: Theme.of(context).colorScheme.primary.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        telescope.category,
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.primary,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    Row(
                      children: [
                        const Icon(Icons.star, color: Colors.amber, size: 18),
                        const SizedBox(width: 4),
                        Text(
                          telescope.rating.toString(),
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                // Image du télescope
                Expanded(
                  child: Center(
                    child: Image.asset(
                      telescope.imageUrl,
                      fit: BoxFit.contain,
                    ),
                  ),
                ),
                const SizedBox(height: 20),
                Text(
                  telescope.name,
                  style: Theme.of(context).textTheme.headlineMedium,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 8),
                Text(
                  telescope.description,
                  style: Theme.of(context).textTheme.bodyMedium,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 20),
                // Spécifications avec appel à _buildSpecItem
                Row(
                  children: [
                    _buildSpecItem(context, 'Aperture', telescope.aperture),
                    const SizedBox(width: 20),
                    _buildSpecItem(context, 'Focal Length', telescope.focalLength),
                  ],
                ),
                const SizedBox(height: 20),
                // Prix et bouton d'action
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Price',
                          style: TextStyle(color: Colors.white54, fontSize: 12),
                        ),
                        Text(
                          '\$${telescope.price}',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 22,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                    ElevatedButton(
                      onPressed: () {},
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Theme.of(context).colorScheme.primary,
                        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        elevation: 0,
                      ),
                      child: const Text(
                        'View Details',
                        style: TextStyle(fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // Méthode privée pour afficher une spécification
  Widget _buildSpecItem(BuildContext context, String label, String value) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.05),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.white.withOpacity(0.1)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: const TextStyle(color: Colors.white54, fontSize: 12),
            ),
            const SizedBox(height: 4),
            Text(
              value,
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w600,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }
}

/// Fond animé de type nébuleuse
class AnimatedStarBackground extends StatefulWidget {
  const AnimatedStarBackground({Key? key}) : super(key: key);
  
  @override
  State<AnimatedStarBackground> createState() => _AnimatedStarBackgroundState();
}

class _AnimatedStarBackgroundState extends State<AnimatedStarBackground> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  
  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 20),
    )..repeat();
  }
  
  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    return SizedBox.expand(
      child: AnimatedBuilder(
        animation: _controller,
        builder: (context, child) {
          return CustomPaint(
            painter: NebulaPainter(_controller.value),
            child: Container(
              decoration: BoxDecoration(
                gradient: RadialGradient(
                  center: const Alignment(0.2, -0.7),
                  radius: 1.5,
                  colors: [
                    const Color(0xFF1F1039).withOpacity(0.6),
                    const Color(0xFF0A0A1A),
                  ],
                  stops: const [0.1, 1.0],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

class NebulaPainter extends CustomPainter {
  final double animationValue;
  
  NebulaPainter(this.animationValue);
  
  @override
  void paint(Canvas canvas, Size size) {
    _paintNebulaClouds(canvas, size, 0.7, const Color(0xFF6E8DFB), const Color(0xFF3B4D8C), animationValue);
    _paintNebulaClouds(canvas, size, 0.5, const Color(0xFFB388FF), const Color(0xFF594080), animationValue + 0.4);
    _paintConstellations(canvas, size);
    _paintBrightStars(canvas, size, animationValue);
  }
  
  void _paintNebulaClouds(Canvas canvas, Size size, double opacity, Color color1, Color color2, double offset) {
    final paint = Paint()
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 30)
      ..style = PaintingStyle.fill;
    
    for (int i = 0; i < 3; i++) {
      final path = Path();
      path.moveTo(0, size.height * 0.3 + sin(offset * 2 * pi + i) * 30);
      for (double x = 0; x < size.width; x += size.width / 20) {
        final xProgress = x / size.width;
        final wave1 = sin((xProgress + offset) * 2 * pi) * 20;
        final wave2 = sin((xProgress * 2 + offset * 1.5) * 2 * pi) * 15;
        final wave3 = sin((xProgress * 3 + i + offset * 0.8) * 2 * pi) * 25;
        final y = size.height * (0.4 + i * 0.15) + wave1 + wave2 + wave3;
        path.lineTo(x, y);
      }
      path.lineTo(size.width, size.height);
      path.lineTo(0, size.height);
      path.close();
      
      final gradientOffset = offset * 0.2;
      final gradient = LinearGradient(
        begin: Alignment(gradientOffset, 0),
        end: Alignment(gradientOffset + 1, 1),
        colors: [
          color1.withOpacity(opacity * 0.1),
          color2.withOpacity(opacity * 0.3),
          Colors.transparent,
        ],
        stops: const [0.0, 0.5, 1.0],
      );
      
      paint.shader = gradient.createShader(Rect.fromLTWH(0, 0, size.width, size.height));
      canvas.drawPath(path, paint);
    }
  }
  
  void _paintConstellations(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.white.withOpacity(0.3)
      ..strokeWidth = 0.5
      ..style = PaintingStyle.stroke;
    
    final constellations = [
      [
        Offset(size.width * 0.2, size.height * 0.2),
        Offset(size.width * 0.25, size.height * 0.25),
        Offset(size.width * 0.3, size.height * 0.2),
        Offset(size.width * 0.35, size.height * 0.15),
      ],
      [
        Offset(size.width * 0.7, size.height * 0.3),
        Offset(size.width * 0.75, size.height * 0.25),
        Offset(size.width * 0.8, size.height * 0.28),
        Offset(size.width * 0.78, size.height * 0.35),
        Offset(size.width * 0.73, size.height * 0.32),
        Offset(size.width * 0.7, size.height * 0.3),
      ],
    ];
    
    for (final points in constellations) {
      final path = Path()..moveTo(points[0].dx, points[0].dy);
      for (int i = 1; i < points.length; i++) {
        path.lineTo(points[i].dx, points[i].dy);
      }
      canvas.drawPath(path, paint);
      for (final point in points) {
        canvas.drawCircle(point, 1.5, Paint()..color = Colors.white.withOpacity(0.7));
      }
    }
  }
  
  void _paintBrightStars(Canvas canvas, Size size, double animValue) {
    final brightStars = [
      Offset(size.width * 0.15, size.height * 0.12),
      Offset(size.width * 0.8, size.height * 0.18),
      Offset(size.width * 0.65, size.height * 0.35),
    ];
    
    for (int i = 0; i < brightStars.length; i++) {
      final point = brightStars[i];
      final pulseFactor = 0.8 + sin(animValue * 2 * pi + i) * 0.2;
      canvas.drawCircle(point, 2 * pulseFactor, Paint()..color = Colors.white);
      canvas.drawCircle(
        point,
        8 * pulseFactor,
        Paint()
          ..color = Colors.white.withOpacity(0.2)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 5),
      );
      canvas.drawLine(
        Offset(point.dx - 10 * pulseFactor, point.dy),
        Offset(point.dx + 10 * pulseFactor, point.dy),
        Paint()
          ..color = Colors.white.withOpacity(0.15)
          ..strokeWidth = 1
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 2),
      );
      canvas.drawLine(
        Offset(point.dx, point.dy - 10 * pulseFactor),
        Offset(point.dx, point.dy + 10 * pulseFactor),
        Paint()
          ..color = Colors.white.withOpacity(0.15)
          ..strokeWidth = 1
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 2),
      );
    }
  }
  
  @override
  bool shouldRepaint(NebulaPainter oldDelegate) {
    return oldDelegate.animationValue != animationValue;
  }
}