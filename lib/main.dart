// main.dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'telescope_browser_screen.dart';
import 'telescope_chooser.dart';
import 'sky_map_screen.dart';
import 'utils/constants.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Force portrait orientation
  SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);
  
  // Set system UI overlay style
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
    systemNavigationBarColor: Color(AppConstants.bottomBarBackground),
    systemNavigationBarIconBrightness: Brightness.light,
  ));
  
  runApp(const StellarScopeApp());
}

class StellarScopeApp extends StatelessWidget {
  const StellarScopeApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Stellar Scope',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        primaryColor: const Color(0xFF1A1B2E),
        scaffoldBackgroundColor: const Color(0xFF0A0A1A),
        fontFamily: 'SF Pro Display',
        textTheme: const TextTheme(
          headlineLarge: TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: Colors.white),
          headlineMedium: TextStyle(fontSize: 22, fontWeight: FontWeight.w600, color: Colors.white),
          bodyLarge: TextStyle(fontSize: 16, color: Colors.white70),
          bodyMedium: TextStyle(fontSize: 14, color: Colors.white70),
        ),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF6E8DFB),
          secondary: Color(0xFFB388FF),
          tertiary: Color(0xFF4ECDC4),
          background: Color(0xFF0A0A1A),
          surface: Color(0xFF1A1B2E),
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFF1A1B2E),
          elevation: 0,
        ),
      ),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({Key? key}) : super(key: key);
  
  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int _currentIndex = 0;
  
  final List<Widget> _pages = [
    const TelescopeBrowserScreen(),
    TelescopeChooser(
      onTelescopeSelected: (selectedTelescopeName) {
        // You can perform an action when a user selects a telescope via the quiz
        // For example, show a SnackBar or navigate to details
      },
    ),
    const SkyMapScreen(), // Our sky map screen
  ];
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _pages[_currentIndex],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        selectedItemColor: Theme.of(context).colorScheme.primary,
        unselectedItemColor: Colors.white54,
        backgroundColor: const Color(0xFF0A0A1A),
        onTap: (index) {
          setState(() {
            _currentIndex = index;
          });
        },
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.home),
            label: 'Explorer',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.question_answer),
            label: 'Quiz',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.stars),
            label: 'Ciel',
          ),
        ],
      ),
    );
  }
}