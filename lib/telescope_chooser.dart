import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'dart:math';

// ********************************************************************
// MODÈLES DE DONNÉES
// ********************************************************************

/// Représente une option de réponse dans le quiz
class QuizOption {
  final String text;
  final Map<String, double> scores;

  QuizOption({required this.text, required this.scores});
}

/// Représente une question du quiz avec ses options
class QuizQuestion {
  final String question;
  final List<QuizOption> options;

  QuizQuestion({required this.question, required this.options});
}

/// Stocke une réponse utilisateur
class UserResponse {
  final String question;
  String selectedOption;
  int selectedIndex; // Index de l'option sélectionnée

  UserResponse({
    required this.question, 
    required this.selectedOption, 
    required this.selectedIndex
  });
}

/// Modèle de données d'un type de télescope
class TelescopeType {
  final String name;
  final String description;
  final String imageUrl;
  final List<String> advantages;
  final List<String> disadvantages;
  final String diameterRange;
  final String priceRange;

  TelescopeType({
    required this.name,
    required this.description,
    required this.imageUrl,
    required this.advantages,
    required this.disadvantages,
    required this.diameterRange,
    required this.priceRange,
  });
}

// ********************************************************************
// DONNÉES DU QUIZ (CONSTANTES)
// ********************************************************************

/// Liste de tous les types de télescopes disponibles
final List<TelescopeType> telescopeTypes = [
  TelescopeType(
    name: "Lunette achromatique",
    description: "Télescope à lentilles abordable, idéal pour les débutants et l'observation des planètes et de la Lune.",
    imageUrl: "assets/telescopes/achromatic.png",
    advantages: [
      "Simple d'utilisation et robuste",
      "Pas de collimation nécessaire",
      "Bon contraste sur les objets brillants",
      "Coût abordable",
      "Portable et polyvalent"
    ],
    disadvantages: [
      "Chromatisme résiduel (halos colorés)",
      "Limité pour l'astrophotographie du ciel profond",
      "Diamètre généralement limité (max 150mm)"
    ],
    diameterRange: "60-150mm",
    priceRange: "100€-1500€ selon le diamètre",
  ),
  TelescopeType(
    name: "Lunette apochromatique",
    description: "Télescope à lentilles haute performance sans aberration chromatique, idéal pour l'observation visuelle et l'astrophotographie.",
    imageUrl: "assets/telescopes/apochromatic.png",
    advantages: [
      "Excellente qualité d'image sans chromatisme",
      "Parfait pour l'astrophotographie du ciel profond",
      "Polyvalent (planètes et ciel profond)",
      "Pas de collimation nécessaire",
      "Contraste exceptionnel"
    ],
    disadvantages: [
      "Prix très élevé",
      "Diamètre limité par rapport au prix",
      "Nécessite souvent une bonne monture équatoriale"
    ],
    diameterRange: "70-150mm",
    priceRange: "1000€-15000€ selon le diamètre et la qualité",
  ),
  TelescopeType(
    name: "Newton/Dobson",
    description: "Télescope à miroir offrant le meilleur rapport diamètre/prix, idéal pour l'observation du ciel profond.",
    imageUrl: "assets/telescopes/dobsonian.png",
    advantages: [
      "Excellent rapport diamètre/prix",
      "Grand pouvoir collecteur de lumière",
      "Parfait pour le ciel profond visuel",
      "Version Dobson simple à utiliser",
      "Disponible en grands diamètres abordables"
    ],
    disadvantages: [
      "Nécessite des collimations régulières",
      "Encombrant, surtout en grand diamètre",
      "Moins compact qu'un catadioptrique",
      "Moins adapté à l'astrophotographie (sauf version équatoriale)"
    ],
    diameterRange: "114-500mm et plus",
    priceRange: "300€-3000€ selon le diamètre",
  ),
  TelescopeType(
    name: "Schmidt-Cassegrain",
    description: "Télescope polyvalent à miroirs et lame correctrice, compact et adapté à de nombreux usages.",
    imageUrl: "assets/telescopes/schmidt_cassegrain.png",
    advantages: [
      "Compact pour sa focale",
      "Polyvalent (planètes et ciel profond)",
      "Facile à transporter",
      "Compatible avec de nombreux accessoires",
      "Bon pour l'observation et la photo"
    ],
    disadvantages: [
      "Obstruction centrale importante (contraste réduit)",
      "La lame frontale peut se couvrir de buée",
      "Temps de mise en température assez long",
      "Prix moyen à élevé selon le diamètre"
    ],
    diameterRange: "5\"-14\" (125-355mm)",
    priceRange: "1000€-6000€ selon le diamètre",
  ),
  TelescopeType(
    name: "Maksutov-Cassegrain",
    description: "Télescope compact à hautes performances pour l'observation planétaire et lunaire.",
    imageUrl: "assets/telescopes/maksutov.png",
    advantages: [
      "Excellente qualité d'image sur les planètes",
      "Contraste élevé, bonne résolution",
      "Compact et portable",
      "Sans entretien (pas de collimation)",
      "Idéal en milieu urbain pour planètes/Lune"
    ],
    disadvantages: [
      "Champ visuel étroit (longue focale)",
      "Long temps de refroidissement",
      "Limité pour le ciel profond grand champ",
      "Diamètres limités (généralement ≤180mm)"
    ],
    diameterRange: "90-180mm typiquement",
    priceRange: "500€-2000€ selon le diamètre",
  ),
  TelescopeType(
    name: "Ritchey-Chrétien",
    description: "Télescope professionnel à miroirs hyperboliques, idéal pour l'astrophotographie avancée.",
    imageUrl: "assets/telescopes/ritchey_chretien.png",
    advantages: [
      "Image parfaitement nette sur tout le champ",
      "Pas de coma ni d'aberration chromatique",
      "Idéal pour l'astrophotographie de galaxies",
      "Qualité d'image professionnelle",
      "Grand champ corrigé pour capteurs photo"
    ],
    disadvantages: [
      "Prix élevé",
      "Collimation complexe",
      "Pas optimisé pour l'observation visuelle",
      "Nécessite une bonne monture équatoriale",
      "Pour astronomes expérimentés"
    ],
    diameterRange: "6\"-16\" (150-400mm)",
    priceRange: "1500€-8000€ selon le diamètre",
  ),
  TelescopeType(
    name: "Astrographe RASA",
    description: "Instrument ultra-rapide dédié à l'astrophotographie grand champ à courte pose.",
    imageUrl: "assets/telescopes/rasa.png",
    advantages: [
      "Optiques ultra-rapides (f/2)",
      "Images profondes en temps record",
      "Parfait pour les nébuleuses et grandes galaxies",
      "Excelle sur les objets étendus",
      "Idéal pour astrophotographie avancée"
    ],
    disadvantages: [
      "Uniquement photographique (pas d'observation visuelle)",
      "Prix élevé",
      "Nécessite des caméras spécifiques",
      "Obstruction par la caméra",
      "Pour astrophotographes expérimentés"
    ],
    diameterRange: "8\"-14\" (200-355mm)",
    priceRange: "1700€-8000€ selon le diamètre",
  ),
  TelescopeType(
    name: "Télescope intelligent",
    description: "Instrument automatisé tout-en-un combinant télescope, caméra et traitement d'image en temps réel.",
    imageUrl: "assets/telescopes/smart_telescope.png",
    advantages: [
      "Entièrement automatisé (pointe et image seul)",
      "Pas de courbe d'apprentissage technique",
      "Observation partagée sur smartphone/tablette",
      "Révèle les couleurs des objets en temps réel",
      "Très portable et design"
    ],
    disadvantages: [
      "Pas d'observation à l'oculaire traditionnelle",
      "Prix élevé pour le diamètre",
      "Fonctionnalités limitées et écosystème fermé",
      "Diamètre modeste (50-114mm typiquement)",
      "Image moins détaillée qu'en astrophoto classique"
    ],
    diameterRange: "50-114mm",
    priceRange: "1000€-4000€ selon le modèle",
  ),
  TelescopeType(
    name: "Télescope d'initiation",
    description: "Instrument simple et abordable pour débuter en astronomie, parfait pour les premiers pas dans l'observation.",
    imageUrl: "assets/telescopes/beginner_telescope.png",
    advantages: [
      "Prix très abordable",
      "Facilité d'utilisation",
      "Léger et portable",
      "Assemblage simple",
      "Idéal pour découvrir l'astronomie"
    ],
    disadvantages: [
      "Optiques de qualité modeste",
      "Capacités limitées pour le ciel profond",
      "Monture souvent instable",
      "Accessoires basiques",
      "Durabilité limitée"
    ],
    diameterRange: "60-114mm",
    priceRange: "50€-300€",
  ),
  TelescopeType(
    name: "Dobson",
    description: "Télescope de type Newton sur une monture altazimutale simple et robuste, excellent rapport diamètre/prix.",
    imageUrl: "assets/telescopes/dobson.png",
    advantages: [
      "Excellent rapport diamètre/prix",
      "Montage et utilisation simples",
      "Grande capacité collectrice de lumière",
      "Stable et robuste",
      "Idéal pour le ciel profond visuel"
    ],
    disadvantages: [
      "Encombrant et lourd en grand diamètre",
      "Pas de suivi automatique des astres",
      "Peu adapté à l'astrophotographie",
      "Mise en température nécessaire",
      "Nécessite une collimation régulière"
    ],
    diameterRange: "150-500mm et plus",
    priceRange: "350€-3000€ selon le diamètre",
  ),
  TelescopeType(
    name: "Dobson motorisé",
    description: "Télescope Dobson équipé de moteurs permettant le suivi des astres et le pointage automatique.",
    imageUrl: "assets/telescopes/motorized_dobson.png",
    advantages: [
      "Combine simplicité du Dobson et confort d'utilisation",
      "Suivi automatique des objets célestes",
      "Possibilité de pointage automatique (GoTo)",
      "Idéal pour l'observation prolongée",
      "Permet des sessions de dessins ou d'observation détaillée"
    ],
    disadvantages: [
      "Prix plus élevé qu'un Dobson classique",
      "Nécessite une alimentation électrique",
      "Plus lourd qu'un Dobson standard",
      "Configuration plus complexe",
      "Nécessite toujours une collimation régulière"
    ],
    diameterRange: "200-400mm",
    priceRange: "1200€-5000€ selon le diamètre et les options",
  ),
  TelescopeType(
    name: "Newton",
    description: "Télescope à miroir primaire parabolique sur monture équatoriale, adapté pour l'observation et l'astrophotographie.",
    imageUrl: "assets/telescopes/newtonian.png",
    advantages: [
      "Bon rapport ouverture/prix",
      "Polyvalence observation/photo",
      "Absence d'aberration chromatique",
      "Disponible en différentes focales",
      "Optiques performantes"
    ],
    disadvantages: [
      "Nécessite des collimations fréquentes",
      "Sensible aux turbulences thermiques",
      "Encombrement significatif",
      "Monture équatoriale à maîtriser",
      "Nécessite un bon équilibrage"
    ],
    diameterRange: "130-300mm",
    priceRange: "600€-3500€ selon le diamètre et la monture",
  ),
  TelescopeType(
    name: "Cassegrain",
    description: "Télescope catadioptrique à miroir sphérique et correcteur d'aberration, compact et polyvalent.",
    imageUrl: "assets/telescopes/cassegrain.png",
    advantages: [
      "Design optique compact",
      "Longue focale dans un tube court",
      "Bonne résolution pour planètes",
      "Système optique fermé (peu sensible à la poussière)",
      "Transportable facilement"
    ],
    disadvantages: [
      "Prix assez élevé",
      "Obstruction centrale importante",
      "Temps de mise en température long",
      "Moins lumineux que d'autres designs",
      "Champ de vision étroit"
    ],
    diameterRange: "90-250mm",
    priceRange: "1000€-4000€ selon le diamètre",
  ),
  TelescopeType(
    name: "Rowe-Ackermann-Schmidt (RASA)",
    description: "Variante de l'astrographe Schmidt avec conception optique optimisée pour l'astrophotographie grand champ.",
    imageUrl: "assets/telescopes/rasa.png",
    advantages: [
      "Optiques ultra-rapides (f/2.2)",
      "Parfaitement corrigé sur un grand champ",
      "Idéal pour l'imagerie à courte pose",
      "Excellente netteté de bord à bord",
      "Design compact et robuste"
    ],
    disadvantages: [
      "Exclusivement pour la photographie",
      "Investissement important",
      "Nécessite une monture très stable",
      "Courbe d'apprentissage technique",
      "Exige des caméras et filtres spécifiques"
    ],
    diameterRange: "8\"-14\" (200-355mm)",
    priceRange: "3500€-10000€ selon le diamètre",
  ),
];

/// Liste des questions du quiz avec leurs options
final List<QuizQuestion> quizQuestions = [
  QuizQuestion(
    question: "Quel est votre budget approximatif pour un télescope ?",
    options: [
      QuizOption(
        text: "Moins de 500€",
        scores: {
          "Lunette achromatique": 5, 
          "Lunette apochromatique": 1, 
          "Newton/Dobson": 4, 
          "Schmidt-Cassegrain": 0, 
          "Maksutov-Cassegrain": 1, 
          "Ritchey-Chrétien": 0, 
          "Astrographe RASA": 0, 
          "Télescope intelligent": 0, 
          "Télescope d'initiation": 5, 
          "Dobson": 3, 
          "Dobson motorisé": 0, 
          "Newton": 2, 
          "Cassegrain": 0,
          "Rowe-Ackermann-Schmidt (RASA)": 0
        },
      ),
      QuizOption(
        text: "500€ - 1000€",
        scores: {
          "Lunette achromatique": 4, 
          "Lunette apochromatique": 1, 
          "Newton/Dobson": 5, 
          "Schmidt-Cassegrain": 2, 
          "Maksutov-Cassegrain": 3, 
          "Ritchey-Chrétien": 0, 
          "Astrographe RASA": 0, 
          "Télescope intelligent": 2, 
          "Télescope d'initiation": 2, 
          "Dobson": 5, 
          "Dobson motorisé": 0, 
          "Newton": 4, 
          "Cassegrain": 2,
          "Rowe-Ackermann-Schmidt (RASA)": 0
        },
      ),
      QuizOption(
        text: "1000€ - 2000€",
        scores: {
          "Lunette achromatique": 2, 
          "Lunette apochromatique": 3, 
          "Newton/Dobson": 5, 
          "Schmidt-Cassegrain": 4, 
          "Maksutov-Cassegrain": 4, 
          "Ritchey-Chrétien": 1, 
          "Astrographe RASA": 0, 
          "Télescope intelligent": 4, 
          "Télescope d'initiation": 0, 
          "Dobson": 4, 
          "Dobson motorisé": 4, 
          "Newton": 5, 
          "Cassegrain": 3,
          "Rowe-Ackermann-Schmidt (RASA)": 0
        },
      ),
      QuizOption(
        text: "2000€ - 4000€",
        scores: {
          "Lunette achromatique": 0, 
          "Lunette apochromatique": 4, 
          "Newton/Dobson": 3, 
          "Schmidt-Cassegrain": 5, 
          "Maksutov-Cassegrain": 3, 
          "Ritchey-Chrétien": 3, 
          "Astrographe RASA": 3, 
          "Télescope intelligent": 4, 
          "Télescope d'initiation": 0, 
          "Dobson": 2, 
          "Dobson motorisé": 5, 
          "Newton": 3, 
          "Cassegrain": 4,
          "Rowe-Ackermann-Schmidt (RASA)": 4
        },
      ),
      QuizOption(
        text: "Plus de 4000€",
        scores: {
          "Lunette achromatique": 0, 
          "Lunette apochromatique": 5, 
          "Newton/Dobson": 2, 
          "Schmidt-Cassegrain": 4, 
          "Maksutov-Cassegrain": 2, 
          "Ritchey-Chrétien": 5, 
          "Astrographe RASA": 5, 
          "Télescope intelligent": 3, 
          "Télescope d'initiation": 0, 
          "Dobson": 1, 
          "Dobson motorisé": 3, 
          "Newton": 2, 
          "Cassegrain": 3,
          "Rowe-Ackermann-Schmidt (RASA)": 5
        },
      ),
    ],
  ),
  QuizQuestion(
    question: "Quel est votre niveau d'expérience en astronomie ?",
    options: [
      QuizOption(
        text: "Débutant complet",
        scores: {
          "Lunette achromatique": 5, 
          "Lunette apochromatique": 2, 
          "Newton/Dobson": 3, 
          "Schmidt-Cassegrain": 3, 
          "Maksutov-Cassegrain": 3, 
          "Ritchey-Chrétien": 0, 
          "Astrographe RASA": 0, 
          "Télescope intelligent": 5, 
          "Télescope d'initiation": 5, 
          "Dobson": 4, 
          "Dobson motorisé": 1, 
          "Newton": 2, 
          "Cassegrain": 2,
          "Rowe-Ackermann-Schmidt (RASA)": 0
        },
      ),
      QuizOption(
        text: "Quelques observations mais novice",
        scores: {
          "Lunette achromatique": 4, 
          "Lunette apochromatique": 2, 
          "Newton/Dobson": 4, 
          "Schmidt-Cassegrain": 3, 
          "Maksutov-Cassegrain": 4, 
          "Ritchey-Chrétien": 0, 
          "Astrographe RASA": 0, 
          "Télescope intelligent": 3, 
          "Télescope d'initiation": 2, 
          "Dobson": 5, 
          "Dobson motorisé": 2, 
          "Newton": 3, 
          "Cassegrain": 2,
          "Rowe-Ackermann-Schmidt (RASA)": 0
        },
      ),
      QuizOption(
        text: "Intermédiaire",
        scores: {
          "Lunette achromatique": 3, 
          "Lunette apochromatique": 4, 
          "Newton/Dobson": 5, 
          "Schmidt-Cassegrain": 5, 
          "Maksutov-Cassegrain": 4, 
          "Ritchey-Chrétien": 2, 
          "Astrographe RASA": 1, 
          "Télescope intelligent": 2, 
          "Télescope d'initiation": 0, 
          "Dobson": 4, 
          "Dobson motorisé": 4, 
          "Newton": 5, 
          "Cassegrain": 3,
          "Rowe-Ackermann-Schmidt (RASA)": 1
        },
      ),
      QuizOption(
        text: "Avancé",
        scores: {
          "Lunette achromatique": 1, 
          "Lunette apochromatique": 5, 
          "Newton/Dobson": 3, 
          "Schmidt-Cassegrain": 4, 
          "Maksutov-Cassegrain": 3, 
          "Ritchey-Chrétien": 4, 
          "Astrographe RASA": 4, 
          "Télescope intelligent": 2, 
          "Télescope d'initiation": 0, 
          "Dobson": 3, 
          "Dobson motorisé": 5, 
          "Newton": 4, 
          "Cassegrain": 4,
          "Rowe-Ackermann-Schmidt (RASA)": 5
        },
      ),
      QuizOption(
        text: "Expert en astrophotographie",
        scores: {
          "Lunette achromatique": 0, 
          "Lunette apochromatique": 5, 
          "Newton/Dobson": 1, 
          "Schmidt-Cassegrain": 3, 
          "Maksutov-Cassegrain": 1, 
          "Ritchey-Chrétien": 5, 
          "Astrographe RASA": 5, 
          "Télescope intelligent": 1, 
          "Télescope d'initiation": 0, 
          "Dobson": 0, 
          "Dobson motorisé": 2, 
          "Newton": 4, 
          "Cassegrain": 3,
          "Rowe-Ackermann-Schmidt (RASA)": 5
        },
      ),
    ],
  ),
  QuizQuestion(
    question: "Que voulez-vous observer principalement ?",
    options: [
      QuizOption(
        text: "Lune et planètes surtout",
        scores: {
          "Lunette achromatique": 4, 
          "Lunette apochromatique": 5, 
          "Newton/Dobson": 2, 
          "Schmidt-Cassegrain": 4, 
          "Maksutov-Cassegrain": 5, 
          "Ritchey-Chrétien": 2, 
          "Astrographe RASA": 0, 
          "Télescope intelligent": 3, 
          "Télescope d'initiation": 3, 
          "Dobson": 2, 
          "Dobson motorisé": 2, 
          "Newton": 3, 
          "Cassegrain": 5,
          "Rowe-Ackermann-Schmidt (RASA)": 0
        },
      ),
      QuizOption(
        text: "Galaxies et nébuleuses (ciel profond)",
        scores: {
          "Lunette achromatique": 2, 
          "Lunette apochromatique": 3, 
          "Newton/Dobson": 5, 
          "Schmidt-Cassegrain": 4, 
          "Maksutov-Cassegrain": 2, 
          "Ritchey-Chrétien": 3, 
          "Astrographe RASA": 3, 
          "Télescope intelligent": 3, 
          "Télescope d'initiation": 1, 
          "Dobson": 5, 
          "Dobson motorisé": 5, 
          "Newton": 4, 
          "Cassegrain": 2,
          "Rowe-Ackermann-Schmidt (RASA)": 5
        },
      ),
      QuizOption(
        text: "Grand champ (amas ouverts, grandes nébuleuses)",
        scores: {
          "Lunette achromatique": 3, 
          "Lunette apochromatique": 5, 
          "Newton/Dobson": 2, 
          "Schmidt-Cassegrain": 2, 
          "Maksutov-Cassegrain": 1, 
          "Ritchey-Chrétien": 2, 
          "Astrographe RASA": 4, 
          "Télescope intelligent": 2, 
          "Télescope d'initiation": 2, 
          "Dobson": 2, 
          "Dobson motorisé": 2, 
          "Newton": 3, 
          "Cassegrain": 1,
          "Rowe-Ackermann-Schmidt (RASA)": 5
        },
      ),
      QuizOption(
        text: "Un peu de tout (polyvalence)",
        scores: {
          "Lunette achromatique": 3, 
          "Lunette apochromatique": 4, 
          "Newton/Dobson": 4, 
          "Schmidt-Cassegrain": 5, 
          "Maksutov-Cassegrain": 3, 
          "Ritchey-Chrétien": 2, 
          "Astrographe RASA": 1, 
          "Télescope intelligent": 3, 
          "Télescope d'initiation": 2, 
          "Dobson": 3, 
          "Dobson motorisé": 4, 
          "Newton": 4, 
          "Cassegrain": 4,
          "Rowe-Ackermann-Schmidt (RASA)": 1
        },
      ),
      QuizOption(
        text: "Je ne sais pas encore, je veux découvrir",
        scores: {
          "Lunette achromatique": 4, 
          "Lunette apochromatique": 2, 
          "Newton/Dobson": 4, 
          "Schmidt-Cassegrain": 3, 
          "Maksutov-Cassegrain": 2, 
          "Ritchey-Chrétien": 0, 
          "Astrographe RASA": 0, 
          "Télescope intelligent": 5, 
          "Télescope d'initiation": 5, 
          "Dobson": 4, 
          "Dobson motorisé": 2, 
          "Newton": 2, 
          "Cassegrain": 1,
          "Rowe-Ackermann-Schmidt (RASA)": 0
        },
      ),
    ],
  ),
  QuizQuestion(
    question: "Où utiliserez-vous principalement votre télescope ?",
    options: [
      QuizOption(
        text: "En ville (pollution lumineuse forte)",
        scores: {
          "Lunette achromatique": 3, 
          "Lunette apochromatique": 3, 
          "Newton/Dobson": 2, 
          "Schmidt-Cassegrain": 4, 
          "Maksutov-Cassegrain": 5, 
          "Ritchey-Chrétien": 2, 
          "Astrographe RASA": 1, 
          "Télescope intelligent": 4, 
          "Télescope d'initiation": 3, 
          "Dobson": 2, 
          "Dobson motorisé": 2, 
          "Newton": 2, 
          "Cassegrain": 4,
          "Rowe-Ackermann-Schmidt (RASA)": 1
        },
      ),
      QuizOption(
        text: "En banlieue (pollution modérée)",
        scores: {
          "Lunette achromatique": 3, 
          "Lunette apochromatique": 4, 
          "Newton/Dobson": 4, 
          "Schmidt-Cassegrain": 4, 
          "Maksutov-Cassegrain": 4, 
          "Ritchey-Chrétien": 3, 
          "Astrographe RASA": 3, 
          "Télescope intelligent": 3, 
          "Télescope d'initiation": 3, 
          "Dobson": 4, 
          "Dobson motorisé": 4, 
          "Newton": 4, 
          "Cassegrain": 4,
          "Rowe-Ackermann-Schmidt (RASA)": 3
        },
      ),
      QuizOption(
        text: "À la campagne (ciel sombre)",
        scores: {
          "Lunette achromatique": 2, 
          "Lunette apochromatique": 4, 
          "Newton/Dobson": 5, 
          "Schmidt-Cassegrain": 3, 
          "Maksutov-Cassegrain": 2, 
          "Ritchey-Chrétien": 4, 
          "Astrographe RASA": 4, 
          "Télescope intelligent": 3, 
          "Télescope d'initiation": 1, 
          "Dobson": 5, 
          "Dobson motorisé": 5, 
          "Newton": 5, 
          "Cassegrain": 3,
          "Rowe-Ackermann-Schmidt (RASA)": 5
        },
      ),
      QuizOption(
        text: "En déplacement (nomade)",
        scores: {
          "Lunette achromatique": 4, 
          "Lunette apochromatique": 4, 
          "Newton/Dobson": 1, 
          "Schmidt-Cassegrain": 3, 
          "Maksutov-Cassegrain": 4, 
          "Ritchey-Chrétien": 1, 
          "Astrographe RASA": 2, 
          "Télescope intelligent": 5, 
          "Télescope d'initiation": 5, 
          "Dobson": 1, 
          "Dobson motorisé": 0, 
          "Newton": 2, 
          "Cassegrain": 3,
          "Rowe-Ackermann-Schmidt (RASA)": 2
        },
      ),
    ],
  ),
  QuizQuestion(
    question: "Quel type d'utilisation prévoyez-vous ?",
    options: [
      QuizOption(
        text: "Observation visuelle uniquement",
        scores: {
          "Lunette achromatique": 3, 
          "Lunette apochromatique": 3, 
          "Newton/Dobson": 5, 
          "Schmidt-Cassegrain": 4, 
          "Maksutov-Cassegrain": 4, 
          "Ritchey-Chrétien": 2, 
          "Astrographe RASA": 0, 
          "Télescope intelligent": 1, 
          "Télescope d'initiation": 4, 
          "Dobson": 5, 
          "Dobson motorisé": 4, 
          "Newton": 3, 
          "Cassegrain": 3,
          "Rowe-Ackermann-Schmidt (RASA)": 0
        },
      ),
      QuizOption(
        text: "Surtout visuel, un peu de photo",
        scores: {
          "Lunette achromatique": 2, 
          "Lunette apochromatique": 4, 
          "Newton/Dobson": 3, 
          "Schmidt-Cassegrain": 5, 
          "Maksutov-Cassegrain": 3, 
          "Ritchey-Chrétien": 2, 
          "Astrographe RASA": 1, 
          "Télescope intelligent": 2, 
          "Télescope d'initiation": 1, 
          "Dobson": 2, 
          "Dobson motorisé": 3, 
          "Newton": 4, 
          "Cassegrain": 3,
          "Rowe-Ackermann-Schmidt (RASA)": 1
        },
      ),
      QuizOption(
        text: "Principalement astrophotographie",
        scores: {
          "Lunette achromatique": 1, 
          "Lunette apochromatique": 5, 
          "Newton/Dobson": 1, 
          "Schmidt-Cassegrain": 3, 
          "Maksutov-Cassegrain": 2, 
          "Ritchey-Chrétien": 5, 
          "Astrographe RASA": 5, 
          "Télescope intelligent": 2, 
          "Télescope d'initiation": 0, 
          "Dobson": 0, 
          "Dobson motorisé": 1, 
          "Newton": 4, 
          "Cassegrain": 3,
          "Rowe-Ackermann-Schmidt (RASA)": 5
        },
      ),
      QuizOption(
        text: "Observation assistée/électronique",
        scores: {
          "Lunette achromatique": 1, 
          "Lunette apochromatique": 2, 
          "Newton/Dobson": 1, 
          "Schmidt-Cassegrain": 3, 
          "Maksutov-Cassegrain": 2, 
          "Ritchey-Chrétien": 2, 
          "Astrographe RASA": 3, 
          "Télescope intelligent": 5, 
          "Télescope d'initiation": 1, 
          "Dobson": 0, 
          "Dobson motorisé": 2, 
          "Newton": 1, 
          "Cassegrain": 2,
          "Rowe-Ackermann-Schmidt (RASA)": 3
        },
      ),
    ],
  ),
  QuizQuestion(
    question: "Quelle importance accordez-vous à la portabilité ?",
    options: [
      QuizOption(
        text: "Critique - je veux pouvoir le transporter facilement",
        scores: {
          "Lunette achromatique": 5, 
          "Lunette apochromatique": 4, 
          "Newton/Dobson": 1, 
          "Schmidt-Cassegrain": 3, 
          "Maksutov-Cassegrain": 5, 
          "Ritchey-Chrétien": 1, 
          "Astrographe RASA": 2, 
          "Télescope intelligent": 5, 
          "Télescope d'initiation": 5, 
          "Dobson": 0, 
          "Dobson motorisé": 0, 
          "Newton": 2, 
          "Cassegrain": 4,
          "Rowe-Ackermann-Schmidt (RASA)": 2
        },
      ),
      QuizOption(
        text: "Important, mais pas essentiel",
        scores: {
          "Lunette achromatique": 4, 
          "Lunette apochromatique": 4, 
          "Newton/Dobson": 2, 
          "Schmidt-Cassegrain": 4, 
          "Maksutov-Cassegrain": 4, 
          "Ritchey-Chrétien": 2, 
          "Astrographe RASA": 3, 
          "Télescope intelligent": 4, 
          "Télescope d'initiation": 4, 
          "Dobson": 2, 
          "Dobson motorisé": 1, 
          "Newton": 3, 
          "Cassegrain": 4,
          "Rowe-Ackermann-Schmidt (RASA)": 3
        },
      ),
      QuizOption(
        text: "Secondaire - je privilégie les performances",
        scores: {
          "Lunette achromatique": 2, 
          "Lunette apochromatique": 3, 
          "Newton/Dobson": 4, 
          "Schmidt-Cassegrain": 4, 
          "Maksutov-Cassegrain": 3, 
          "Ritchey-Chrétien": 3, 
          "Astrographe RASA": 4, 
          "Télescope intelligent": 2, 
          "Télescope d'initiation": 1, 
          "Dobson": 3, 
          "Dobson motorisé": 3, 
          "Newton": 4, 
          "Cassegrain": 3,
          "Rowe-Ackermann-Schmidt (RASA)": 4
        },
      ),
      QuizOption(
        text: "Pas important - je prévois une installation fixe",
        scores: {
          "Lunette achromatique": 1, 
          "Lunette apochromatique": 3, 
          "Newton/Dobson": 5, 
          "Schmidt-Cassegrain": 3, 
          "Maksutov-Cassegrain": 2, 
          "Ritchey-Chrétien": 5, 
          "Astrographe RASA": 4, 
          "Télescope intelligent": 2, 
          "Télescope d'initiation": 0, 
          "Dobson": 5, 
          "Dobson motorisé": 5, 
          "Newton": 5, 
          "Cassegrain": 3,
          "Rowe-Ackermann-Schmidt (RASA)": 5
        },
      ),
    ],
  ),
  QuizQuestion(
    question: "Acceptez-vous de faire de la maintenance régulière (collimation, ajustements) ?",
    options: [
      QuizOption(
        text: "Non, je veux un instrument sans entretien",
        scores: {
          "Lunette achromatique": 5, 
          "Lunette apochromatique": 5, 
          "Newton/Dobson": 0, 
          "Schmidt-Cassegrain": 3, 
          "Maksutov-Cassegrain": 5, 
          "Ritchey-Chrétien": 0, 
          "Astrographe RASA": 1, 
          "Télescope intelligent": 5, 
          "Télescope d'initiation": 4, 
          "Dobson": 0, 
          "Dobson motorisé": 0, 
          "Newton": 0, 
          "Cassegrain": 4,
          "Rowe-Ackermann-Schmidt (RASA)": 1
        },
      ),
      QuizOption(
        text: "Un minimum, mais pas trop compliqué",
        scores: {
          "Lunette achromatique": 3, 
          "Lunette apochromatique": 3, 
          "Newton/Dobson": 2, 
          "Schmidt-Cassegrain": 5, 
          "Maksutov-Cassegrain": 4, 
          "Ritchey-Chrétien": 2, 
          "Astrographe RASA": 3, 
          "Télescope intelligent": 3, 
          "Télescope d'initiation": 2, 
          "Dobson": 2, 
          "Dobson motorisé": 3, 
          "Newton": 2, 
          "Cassegrain": 4,
          "Rowe-Ackermann-Schmidt (RASA)": 3
        },
      ),
      QuizOption(
        text: "Oui, ça ne me dérange pas",
        scores: {
          "Lunette achromatique": 2, 
          "Lunette apochromatique": 2, 
          "Newton/Dobson": 5, 
          "Schmidt-Cassegrain": 3, 
          "Maksutov-Cassegrain": 2, 
          "Ritchey-Chrétien": 4, 
          "Astrographe RASA": 4, 
          "Télescope intelligent": 1, 
          "Télescope d'initiation": 1, 
          "Dobson": 5, 
          "Dobson motorisé": 4, 
          "Newton": 5, 
          "Cassegrain": 2,
          "Rowe-Ackermann-Schmidt (RASA)": 4
        },
      ),
    ],
  ),
  QuizQuestion(
    question: "Quelle est votre priorité concernant la simplicité d'utilisation ?",
    options: [
      QuizOption(
        text: "Je veux quelque chose de très simple, même automatisé",
        scores: {
          "Lunette achromatique": 4, 
          "Lunette apochromatique": 2, 
          "Newton/Dobson": 2, 
          "Schmidt-Cassegrain": 2, 
          "Maksutov-Cassegrain": 3, 
          "Ritchey-Chrétien": 0, 
          "Astrographe RASA": 0, 
          "Télescope intelligent": 5, 
          "Télescope d'initiation": 5, 
          "Dobson": 3, 
          "Dobson motorisé": 2, 
          "Newton": 1, 
          "Cassegrain": 2,
          "Rowe-Ackermann-Schmidt (RASA)": 0
        },
      ),
      QuizOption(
        text: "Je préfère un bon équilibre simplicité/performance",
        scores: {
          "Lunette achromatique": 3, 
          "Lunette apochromatique": 4, 
          "Newton/Dobson": 3, 
          "Schmidt-Cassegrain": 5, 
          "Maksutov-Cassegrain": 4, 
          "Ritchey-Chrétien": 2, 
          "Astrographe RASA": 2, 
          "Télescope intelligent": 3, 
          "Télescope d'initiation": 2, 
          "Dobson": 3, 
          "Dobson motorisé": 4, 
          "Newton": 3, 
          "Cassegrain": 4,
          "Rowe-Ackermann-Schmidt (RASA)": 2
        },
      ),
      QuizOption(
        text: "Je suis prêt à gérer la complexité pour les performances",
        scores: {
          "Lunette achromatique": 1, 
          "Lunette apochromatique": 3, 
          "Newton/Dobson": 4, 
          "Schmidt-Cassegrain": 3, 
          "Maksutov-Cassegrain": 2, 
          "Ritchey-Chrétien": 5, 
          "Astrographe RASA": 5, 
          "Télescope intelligent": 1, 
          "Télescope d'initiation": 0, 
          "Dobson": 3, 
          "Dobson motorisé": 4, 
          "Newton": 5, 
          "Cassegrain": 3,
          "Rowe-Ackermann-Schmidt (RASA)": 5
        },
      ),
    ],
  ),
  QuizQuestion(
    question: "Préférez-vous un télescope manuel ou automatisé?",
    options: [
      QuizOption(
        text: "Manuel - j'aime chercher les objets moi-même",
        scores: {
          "Lunette achromatique": 4,
          "Lunette apochromatique": 4,
          "Newton/Dobson": 5,
          "Schmidt-Cassegrain": 2,
          "Maksutov-Cassegrain": 3,
          "Ritchey-Chrétien": 1,
          "Astrographe RASA": 0,
          "Télescope intelligent": 0,
          "Télescope d'initiation": 4,
          "Dobson": 5,
          "Dobson motorisé": 0,
          "Newton": 4,
          "Cassegrain": 2,
          "Rowe-Ackermann-Schmidt (RASA)": 0
        },
      ),
      QuizOption(
        text: "Automatisé avec GoTo - je veux que le télescope pointe les objets",
        scores: {
          "Lunette achromatique": 1,
          "Lunette apochromatique": 3,
          "Newton/Dobson": 1,
          "Schmidt-Cassegrain": 5,
          "Maksutov-Cassegrain": 4,
          "Ritchey-Chrétien": 3,
          "Astrographe RASA": 2,
          "Télescope intelligent": 2,
          "Télescope d'initiation": 0,
          "Dobson": 1,
          "Dobson motorisé": 5,
          "Newton": 2,
          "Cassegrain": 4,
          "Rowe-Ackermann-Schmidt (RASA)": 2
        },
      ),
      QuizOption(
        text: "Entièrement automatisé - je veux observation et imagerie assistées",
        scores: {
          "Lunette achromatique": 0,
          "Lunette apochromatique": 2,
          "Newton/Dobson": 0,
          "Schmidt-Cassegrain": 3,
          "Maksutov-Cassegrain": 2,
          "Ritchey-Chrétien": 3,
          "Astrographe RASA": 3,
          "Télescope intelligent": 5,
          "Télescope d'initiation": 0,
          "Dobson": 0,
          "Dobson motorisé": 3,
          "Newton": 1,
          "Cassegrain": 2,
          "Rowe-Ackermann-Schmidt (RASA)": 3
        },
      ),
    ],
  ),
];

// ********************************************************************
// WIDGET PRINCIPAL
// ********************************************************************

/// Widget principal du sélecteur de télescope
class TelescopeChooser extends StatefulWidget {
  final Function(String) onTelescopeSelected;

  const TelescopeChooser({Key? key, required this.onTelescopeSelected}) : super(key: key);

  @override
  State<TelescopeChooser> createState() => _TelescopeChooserState();
}

class _TelescopeChooserState extends State<TelescopeChooser> {
  // Variables d'état
  int _currentQuestionIndex = 0;
  Map<String, double> _telescopeScores = {};
  List<UserResponse> _userResponses = [];
  bool _showResults = false;
  bool _showCopiedMessage = false;
  int _selectedTabIndex = 0;
  bool _recommendationsUpdated = false;
  final GlobalKey _recommendationsKey = GlobalKey();
  
  @override
  void initState() {
    super.initState();
    _initializeScores();
  }
  
  // Initialise les scores à zéro pour tous les types de télescopes
  void _initializeScores() {
    for (var telescope in telescopeTypes) {
      _telescopeScores[telescope.name] = 0.0;
    }
  }
  
  // Appelé lorsque l'utilisateur sélectionne une option
  void _selectOption(int optionIndex) {
    final currentQuestion = quizQuestions[_currentQuestionIndex];
    final selectedOption = currentQuestion.options[optionIndex];
    
    // Stocke la réponse de l'utilisateur
    _userResponses.add(UserResponse(
      question: currentQuestion.question,
      selectedOption: selectedOption.text,
      selectedIndex: optionIndex,
    ));
    
    // Met à jour les scores
    _updateScores(optionIndex, currentQuestion);
    
    setState(() {
      if (_currentQuestionIndex < quizQuestions.length - 1) {
        _currentQuestionIndex++;
      } else {
        _showResults = true;
      }
    });
  }
  
  // Met à jour les scores en fonction de l'option sélectionnée
  void _updateScores(int optionIndex, QuizQuestion question) {
    final selectedOption = question.options[optionIndex];
    
    selectedOption.scores.forEach((telescopeName, score) {
      if (_telescopeScores.containsKey(telescopeName)) {
        _telescopeScores[telescopeName] = _telescopeScores[telescopeName]! + score;
      }
    });
  }
  
  // Réinitialise le quiz
  void _restartQuiz() {
    setState(() {
      _currentQuestionIndex = 0;
      _userResponses = [];
      _initializeScores();
      _showResults = false;
    });
  }
  
  // Permet de changer une réponse existante
  void _changeAnswer(int questionIndex, int newOptionIndex) {
    final question = quizQuestions[questionIndex];
    final oldOptionIndex = _userResponses[questionIndex].selectedIndex;
    final newOption = question.options[newOptionIndex];
    
    setState(() {
      _userResponses[questionIndex].selectedOption = newOption.text;
      _userResponses[questionIndex].selectedIndex = newOptionIndex;
      
      // Recalcule tous les scores depuis le début
      _initializeScores();
      for (int i = 0; i < _userResponses.length; i++) {
        final response = _userResponses[i];
        final currentQuestion = quizQuestions[i];
        _updateScores(response.selectedIndex, currentQuestion);
      }
      
      // Active l'indicateur de mise à jour
      _recommendationsUpdated = true;
      
      // Si l'utilisateur est dans l'onglet des réponses, on bascule vers l'onglet des recommandations
      if (_selectedTabIndex == 1) {
        _selectedTabIndex = 0;
      }
    });
    
    // Désactiver l'indicateur après un délai
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) {
        setState(() {
          _recommendationsUpdated = false;
        });
      }
    });
  }
  
  // Obtient les trois meilleures recommandations
  List<TelescopeType> _getTopRecommendations() {
    var sortedTelescopes = telescopeTypes.toList()
      ..sort((a, b) => _telescopeScores[b.name]!.compareTo(_telescopeScores[a.name]!));
    return sortedTelescopes.take(3).toList();
  }
  
  // Obtient tous les scores triés
  List<MapEntry<String, double>> _getAllScoresSorted() {
    var scoreEntries = _telescopeScores.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    return scoreEntries;
  }
  
  // Copie les résultats dans le presse-papiers
  Future<void> _copyResultsToClipboard() async {
    final recommendations = _getTopRecommendations();
    final allScores = _getAllScoresSorted();
    
    String content = "📊 RÉSULTATS DU QUIZ TÉLESCOPES 📊\n\n";
    
    // Section 1: Réponses de l'utilisateur
    content += "🔍 VOS RÉPONSES:\n";
    content += "==================\n\n";
    
    for (var i = 0; i < _userResponses.length; i++) {
      content += "${i+1}. ${_userResponses[i].question}\n";
      content += "   Réponse: ${_userResponses[i].selectedOption}\n\n";
    }
    
    // Section 2: Tableau des scores
    content += "📈 TABLEAU DES SCORES:\n";
    content += "=====================\n\n";
    
    for (var i = 0; i < allScores.length; i++) {
      final entry = allScores[i];
      content += "${i+1}. ${entry.key}: ${entry.value.toStringAsFixed(1)} points\n";
    }
    
    content += "\n";
    
    // Section 3: Top recommandations détaillées
    content += "🏆 RECOMMANDATIONS DÉTAILLÉES:\n";
    content += "============================\n\n";
    
    for (var i = 0; i < recommendations.length; i++) {
      final telescope = recommendations[i];
      content += "🔭 #${i+1} - ${telescope.name}\n";
      content += "Score: ${_telescopeScores[telescope.name]!.toStringAsFixed(1)} points\n\n";
      content += "Description: ${telescope.description}\n\n";
      content += "Diamètre: ${telescope.diameterRange}\n";
      content += "Prix: ${telescope.priceRange}\n\n";
      
      content += "✅ Avantages:\n";
      telescope.advantages.forEach((advantage) => content += "• $advantage\n");
      
      content += "\n❌ Inconvénients:\n";
      telescope.disadvantages.forEach((disadvantage) => content += "• $disadvantage\n");
      
      content += "\n-------------------------------------\n\n";
    }
    
    content += "Ces résultats sont basés sur vos réponses et peuvent servir de point de départ pour discuter avec un spécialiste en astronomie.";
    
    await Clipboard.setData(ClipboardData(text: content));
    
    setState(() {
      _showCopiedMessage = true;
    });
    
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) {
        setState(() {
          _showCopiedMessage = false;
        });
      }
    });
  }
  
  @override
  Widget build(BuildContext context) {
    if (_showResults) {
      return _buildResultsScreen();
    } else {
      return _buildQuestionScreen();
    }
  }
  
  // ********************************************************************
  // ÉCRAN DES QUESTIONS
  // ********************************************************************
  
  Widget _buildQuestionScreen() {
    QuizQuestion currentQuestion = quizQuestions[_currentQuestionIndex];
    
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            const Color(0xFF1F1039).withOpacity(0.8),
            const Color(0xFF0A0A1A),
          ],
        ),
      ),
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Indicateur de progression
              Column(
                children: [
                  SizedBox(
                    width: double.infinity,
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: LinearProgressIndicator(
                        value: (_currentQuestionIndex + 1) / quizQuestions.length,
                        backgroundColor: Colors.white12,
                        valueColor: AlwaysStoppedAnimation<Color>(Theme.of(context).colorScheme.primary),
                        minHeight: 8,
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    "Question ${_currentQuestionIndex + 1}/${quizQuestions.length}",
                    style: const TextStyle(color: Colors.white70),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
              
              const SizedBox(height: 32),
              
              // Affichage de la question
              Text(
                currentQuestion.question,
                style: const TextStyle(
                  fontSize: 24, 
                  fontWeight: FontWeight.bold, 
                  color: Colors.white,
                  height: 1.3,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 40),
              
              // Options du quiz
              Expanded(
                child: ListView.builder(
                  itemCount: currentQuestion.options.length,
                  physics: const BouncingScrollPhysics(),
                  itemBuilder: (context, index) {
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 16),
                      child: AnimatedOpacity(
                        opacity: 1.0,
                        duration: Duration(milliseconds: 200 + (index * 50)),
                        child: ElevatedButton(
                          onPressed: () => _selectOption(index),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Theme.of(context).colorScheme.surface.withOpacity(0.7),
                            padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 20),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(16),
                              side: BorderSide(color: Theme.of(context).colorScheme.primary.withOpacity(0.3)),
                            ),
                            elevation: 4,
                          ),
                          child: Text(
                            currentQuestion.options[index].text,
                            style: const TextStyle(fontSize: 16, color: Colors.white, height: 1.3),
                            textAlign: TextAlign.center,
                          ),
                        ),
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ********************************************************************
  // ÉCRAN DES RÉSULTATS
  // ********************************************************************
  
  Widget _buildResultsScreen() {
    List<TelescopeType> recommendations = _getTopRecommendations();
    List<MapEntry<String, double>> allScores = _getAllScoresSorted();
    
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            const Color(0xFF1F1039).withOpacity(0.8),
            const Color(0xFF0A0A1A),
          ],
        ),
      ),
      child: CupertinoPageScaffold(
        backgroundColor: Colors.transparent,
        navigationBar: CupertinoNavigationBar(
          middle: const Text(
            "Votre télescope idéal",
            style: TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 18,
              color: Colors.white,
            ),
          ),
          backgroundColor: const Color(0xFF1F1039).withOpacity(0.7),
          border: Border(
            bottom: BorderSide(
              color: Colors.white.withOpacity(0.1),
              width: 0.5,
            ),
          ),
        ),
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 8),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20.0),
                child: Text(
                  "Basé sur vos préférences",
                  style: TextStyle(
                    fontSize: 16,
                    color: Colors.white.withOpacity(0.7),
                    fontWeight: FontWeight.normal,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
              const SizedBox(height: 16),
              
              // Contrôle de segment pour les onglets
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20.0),
                child: Container(
                  width: double.infinity,
                  decoration: BoxDecoration(
                    color: Colors.black.withOpacity(0.3),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: Colors.white.withOpacity(0.1),
                      width: 0.5,
                    ),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: GestureDetector(
                          onTap: () => setState(() => _selectedTabIndex = 0),
                          child: Container(
                            padding: const EdgeInsets.symmetric(vertical: 12),
                            decoration: BoxDecoration(
                              color: _selectedTabIndex == 0 
                                  ? Theme.of(context).colorScheme.primary.withOpacity(0.5)
                                  : Colors.transparent,
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Center(
                              child: Text(
                                "Recommandations",
                                style: TextStyle(
                                  color: Colors.white,
                                  fontWeight: _selectedTabIndex == 0 
                                      ? FontWeight.bold 
                                      : FontWeight.normal,
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                      Expanded(
                        child: GestureDetector(
                          onTap: () => setState(() => _selectedTabIndex = 1),
                          child: Container(
                            padding: const EdgeInsets.symmetric(vertical: 12),
                            decoration: BoxDecoration(
                              color: _selectedTabIndex == 1 
                                  ? Theme.of(context).colorScheme.primary.withOpacity(0.5)
                                  : Colors.transparent,
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Center(
                              child: Text(
                                "Vos réponses",
                                style: TextStyle(
                                  color: Colors.white,
                                  fontWeight: _selectedTabIndex == 1 
                                      ? FontWeight.bold 
                                      : FontWeight.normal,
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              
              const SizedBox(height: 16),
              
              // Contenu de l'onglet
              Expanded(
                child: _selectedTabIndex == 0 
                    ? _buildRecommendationsTab(recommendations, allScores)
                    : _buildUserResponsesTab(),
              ),
              
              // Boutons d'action en bas
              Padding(
                padding: const EdgeInsets.all(16.0),
                child: Row(
                  children: [
                    Expanded(
                      child: CupertinoButton(
                        padding: EdgeInsets.zero,
                        color: Colors.white.withOpacity(0.1),
                        child: Text(
                          "Recommencer",
                          style: TextStyle(
                            color: CupertinoColors.white,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        onPressed: _restartQuiz,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: CupertinoButton(
                        padding: EdgeInsets.zero,
                        color: Theme.of(context).colorScheme.primary,
                        child: Text(
                          "Partager les réponses",
                          style: TextStyle(
                            color: CupertinoColors.white,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        onPressed: _copyResultsToClipboard,
                      ),
                    ),
                  ],
                ),
              ),
              
              // Message de confirmation de copie
              if (_showCopiedMessage)
                Container(
                  margin: const EdgeInsets.only(bottom: 16, left: 16, right: 16),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      color: const Color(0xFF1E3A29), // Fond vert foncé
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            CupertinoIcons.check_mark_circled, 
                            color: CupertinoColors.activeGreen,
                            size: 18,
                          ),
                          const SizedBox(width: 8),
                          Text(
                            "Résultats copiés dans le presse-papiers",
                            style: TextStyle(
                              color: CupertinoColors.activeGreen,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  // Onglet des recommandations
  Widget _buildRecommendationsTab(List<TelescopeType> recommendations, List<MapEntry<String, double>> allScores) {
    return Stack(
      children: [
        // Le contenu original
        ListView(
          key: _recommendationsKey,
          physics: const BouncingScrollPhysics(),
          padding: const EdgeInsets.symmetric(horizontal: 20),
          children: [
            // Animation conditionnelle pour la carte des scores
            AnimatedContainer(
              duration: const Duration(milliseconds: 500),
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.3),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: _recommendationsUpdated 
                      ? Theme.of(context).colorScheme.primary.withOpacity(0.8) 
                      : Colors.white.withOpacity(0.1),
                ),
                boxShadow: _recommendationsUpdated 
                    ? [BoxShadow(
                        color: Theme.of(context).colorScheme.primary.withOpacity(0.3),
                        blurRadius: 8,
                        spreadRadius: 1,
                      )] 
                    : null,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.all(16),
                    child: Text(
                      "Scores de correspondance",
                      style: TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.only(left: 16, right: 16, bottom: 16),
                    child: ListView.builder(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: min(6, allScores.length),
                      itemBuilder: (context, index) {
                        final entry = allScores[index];
                        final double percentage = entry.value / allScores.first.value;
                        
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Text(
                                    entry.key,
                                    style: TextStyle(
                                      fontSize: 15,
                                      color: index < 3 
                                          ? Colors.white 
                                          : Colors.white.withOpacity(0.6),
                                      fontWeight: index < 3 ? FontWeight.bold : FontWeight.normal,
                                    ),
                                  ),
                                  Text(
                                    entry.value.toStringAsFixed(1),
                                    style: TextStyle(
                                      fontSize: 15,
                                      fontWeight: index < 3 ? FontWeight.bold : FontWeight.normal,
                                      color: index < 3 
                                          ? Colors.white 
                                          : Colors.white.withOpacity(0.6),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 6),
                              Stack(
                                children: [
                                  Container(
                                    height: 8,
                                    width: double.infinity,
                                    decoration: BoxDecoration(
                                      borderRadius: BorderRadius.circular(4),
                                      color: Colors.white.withOpacity(0.1),
                                    ),
                                  ),
                                  FractionallySizedBox(
                                    widthFactor: percentage,
                                    child: Container(
                                      height: 8,
                                      decoration: BoxDecoration(
                                        borderRadius: BorderRadius.circular(4),
                                        color: index == 0
                                            ? Theme.of(context).colorScheme.primary
                                            : index == 1
                                                ? Colors.amber
                                                : index == 2
                                                    ? Colors.orange
                                                    : Colors.white.withOpacity(0.4),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        );
                      },
                    ),
                  ),
                ],
              ),
            ),
            
            const SizedBox(height: 24),
            
            // Meilleures recommandations
            ..._buildDetailedRecommendations(recommendations),
          ],
        ),
        
        // Indicateur de mise à jour
        if (_recommendationsUpdated)
          Positioned(
            top: 8,
            right: 20,
            child: TweenAnimationBuilder(
              tween: Tween<double>(begin: 0.0, end: 1.0),
              duration: const Duration(milliseconds: 400),
              builder: (context, double value, child) {
                return Opacity(
                  opacity: value,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.primary.withOpacity(0.9),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          CupertinoIcons.arrow_clockwise,
                          color: Colors.white,
                          size: 14,
                        ),
                        const SizedBox(width: 6),
                        Text(
                          "Mis à jour",
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
      ],
    );
  }

  // Onglet des réponses de l'utilisateur
  Widget _buildUserResponsesTab() {
    return ListView.builder(
      itemCount: _userResponses.length,
      physics: const BouncingScrollPhysics(),
      padding: const EdgeInsets.symmetric(horizontal: 20),
      itemBuilder: (context, index) {
        final response = _userResponses[index];
        final question = quizQuestions[index];
        
        return Padding(
          padding: const EdgeInsets.only(bottom: 16),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: Container(
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.3),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.white.withOpacity(0.1)),
              ),
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          width: 32,
                          height: 32,
                          decoration: BoxDecoration(
                            color: Theme.of(context).colorScheme.primary.withOpacity(0.3),
                            shape: BoxShape.circle,
                          ),
                          child: Center(
                            child: Text(
                              "${index + 1}",
                              style: TextStyle(
                                fontWeight: FontWeight.bold,
                                color: Theme.of(context).colorScheme.primary,
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            question.question,
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                              color: Colors.white,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    
                    // Affichage de la réponse actuelle
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Theme.of(context).colorScheme.primary.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: Theme.of(context).colorScheme.primary.withOpacity(0.3),
                        ),
                      ),
                      child: Text(
                        response.selectedOption,
                        style: TextStyle(
                          fontSize: 15,
                          color: Colors.white,
                        ),
                      ),
                    ),
                    
                    const SizedBox(height: 12),
                    
                    // Bouton pour modifier la réponse
                    CupertinoButton(
                      padding: EdgeInsets.zero,
                      onPressed: () => _showChangeAnswerDialog(index, question),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: Colors.white.withOpacity(0.2),
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              CupertinoIcons.pencil,
                              size: 16,
                              color: Colors.white,
                            ),
                            const SizedBox(width: 8),
                            Text(
                              "Modifier la réponse",
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 14,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  // Affiche un dialogue pour changer la réponse
  void _showChangeAnswerDialog(int questionIndex, QuizQuestion question) {
    showDialog(
      context: context,
      builder: (context) {
        return Dialog(
          backgroundColor: const Color(0xFF1A1039),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
          ),
          child: Padding(
            padding: const EdgeInsets.all(20.0),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  "Modifier votre réponse",
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  question.question,
                  style: TextStyle(
                    fontSize: 15,
                    color: Colors.white.withOpacity(0.8),
                  ),
                ),
                const SizedBox(height: 20),
                
                // Liste des options
                Container(
                  constraints: BoxConstraints(
                    maxHeight: MediaQuery.of(context).size.height * 0.4,
                  ),
                  child: SingleChildScrollView(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: List.generate(
                        question.options.length,
                        (index) => Padding(
                          padding: const EdgeInsets.only(bottom: 8.0),
                          child: ListTile(
                            title: Text(
                              question.options[index].text,
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 14,
                              ),
                            ),
                            leading: Radio<int>(
                              value: index,
                              groupValue: _userResponses[questionIndex].selectedIndex,
                              onChanged: (value) {
                                Navigator.of(context).pop();
                                if (value != null) {
                                  _changeAnswer(questionIndex, value);
                                }
                              },
                              activeColor: Theme.of(context).colorScheme.primary,
                            ),
                            onTap: () {
                              Navigator.of(context).pop();
                              _changeAnswer(questionIndex, index);
                            },
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(8),
                            ),
                            tileColor: _userResponses[questionIndex].selectedIndex == index
                                ? Theme.of(context).colorScheme.primary.withOpacity(0.2)
                                : Colors.transparent,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
                
                const SizedBox(height: 16),
                
                // Bouton pour fermer
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    TextButton(
                      onPressed: () => Navigator.of(context).pop(),
                      child: Text(
                        "Annuler",
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.8),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  // Construit les recommandations détaillées
  List<Widget> _buildDetailedRecommendations(List<TelescopeType> recommendations) {
    List<Widget> widgets = [];
    
    for (var index = 0; index < recommendations.length; index++) {
      TelescopeType telescope = recommendations[index];
      widgets.add(
        Padding(
          padding: const EdgeInsets.only(bottom: 20),
          child: GestureDetector(
            onTap: () {
              widget.onTelescopeSelected(telescope.name);
            },
            child: ClipRRect(
              borderRadius: BorderRadius.circular(14),
              child: Container(
                decoration: BoxDecoration(
                  color: Colors.black.withOpacity(0.3),
                  borderRadius: BorderRadius.circular(14),
                  border: index == 0 
                      ? Border.all(color: Theme.of(context).colorScheme.primary, width: 2)
                      : Border.all(color: Colors.white.withOpacity(0.1)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              if (index == 0)
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                                  decoration: BoxDecoration(
                                    color: Theme.of(context).colorScheme.primary,
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(
                                        CupertinoIcons.check_mark_circled_solid, 
                                        size: 14, 
                                        color: Colors.white
                                      ),
                                      const SizedBox(width: 4),
                                      const Text(
                                        "MEILLEUR MATCH",
                                        style: TextStyle(
                                          color: Colors.white,
                                          fontWeight: FontWeight.bold,
                                          fontSize: 11,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              const Spacer(),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                decoration: BoxDecoration(
                                  color: Colors.white.withOpacity(0.1),
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: Row(
                                  children: [
                                    Icon(
                                      CupertinoIcons.graph_circle_fill, 
                                      size: 12, 
                                      color: index == 0 
                                          ? Theme.of(context).colorScheme.primary
                                          : Colors.white.withOpacity(0.5)
                                    ),
                                    const SizedBox(width: 4),
                                    Text(
                                      "${_telescopeScores[telescope.name]!.toStringAsFixed(1)} pts",
                                      style: TextStyle(
                                        color: index == 0 
                                            ? Theme.of(context).colorScheme.primary
                                            : Colors.white.withOpacity(0.7),
                                        fontWeight: FontWeight.bold,
                                        fontSize: 12,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          Text(
                            telescope.name,
                            style: TextStyle(
                              fontSize: 20, 
                              fontWeight: FontWeight.bold, 
                              color: Colors.white
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            telescope.description,
                            style: TextStyle(
                              fontSize: 15, 
                              color: Colors.white.withOpacity(0.7), 
                              height: 1.4
                            ),
                          ),
                          const SizedBox(height: 16),
                          Row(
                            children: [
                              Expanded(
                                child: _buildSpecItem(
                                  "Diamètre", 
                                  telescope.diameterRange,
                                  CupertinoIcons.circle_lefthalf_fill,
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: _buildSpecItem(
                                  "Gamme de prix", 
                                  telescope.priceRange,
                                  CupertinoIcons.money_euro_circle,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 16),
                        ],
                      ),
                    ),
                    
                    // Section Avantages et Inconvénients
                    _buildExpandableSection(
                      title: "Avantages et Inconvénients",
                      initiallyExpanded: index == 0,
                      children: [
                        const SizedBox(height: 4),
                        
                        // Section Avantages
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Padding(
                              padding: const EdgeInsets.only(left: 16),
                              child: Text(
                                "Avantages",
                                style: TextStyle(
                                  fontWeight: FontWeight.bold, 
                                  color: Colors.white,
                                  fontSize: 15,
                                ),
                              ),
                            ),
                            const SizedBox(height: 8),
                            ...telescope.advantages.map((advantage) => Padding(
                              padding: const EdgeInsets.only(bottom: 8, left: 16, right: 16),
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Icon(
                                    CupertinoIcons.check_mark_circled, 
                                    size: 16, 
                                    color: Colors.green
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      advantage,
                                      style: TextStyle(
                                        color: Colors.white, 
                                        height: 1.3,
                                        fontSize: 15,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            )),
                          ],
                        ),
                        
                        const SizedBox(height: 16),
                        
                        // Section Inconvénients
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Padding(
                              padding: const EdgeInsets.only(left: 16),
                              child: Text(
                                "Inconvénients",
                                style: TextStyle(
                                  fontWeight: FontWeight.bold, 
                                  color: Colors.white,
                                  fontSize: 15,
                                ),
                              ),
                            ),
                            const SizedBox(height: 8),
                            ...telescope.disadvantages.map((disadvantage) => Padding(
                              padding: const EdgeInsets.only(bottom: 8, left: 16, right: 16),
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Icon(
                                    CupertinoIcons.minus_circle, 
                                    size: 16, 
                                    color: Colors.red
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      disadvantage,
                                      style: TextStyle(
                                        color: Colors.white, 
                                        height: 1.3,
                                        fontSize: 15,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            )),
                          ],
                        ),
                        const SizedBox(height: 16),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
    }
    
    return widgets;
  }

  // Construit un élément de spécification (diamètre, prix, etc.)
  Widget _buildSpecItem(String title, String value, IconData icon) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 14, color: Colors.white.withOpacity(0.5)),
              const SizedBox(width: 6),
              Text(
                title,
                style: TextStyle(
                  fontSize: 13, 
                  color: Colors.white.withOpacity(0.5)
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: TextStyle(
              fontSize: 14, 
              fontWeight: FontWeight.bold, 
              color: Colors.white
            ),
          ),
        ],
      ),
    );
  }

  // Construit une section extensible
  Widget _buildExpandableSection({
    required String title,
    required List<Widget> children,
    bool initiallyExpanded = false,
  }) {
    return CustomExpandableSection(
      title: Text(
        title,
        style: TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.bold,
          fontSize: 16,
        ),
      ),
      trailing: Icon(
        CupertinoIcons.chevron_down,
        size: 14,
        color: Colors.white.withOpacity(0.5),
      ),
      initiallyExpanded: initiallyExpanded,
      children: children,
    );
  }
}

// ********************************************************************
// WIDGETS UTILITAIRES
// ********************************************************************

/// Section extensible avec style iOS pour la compatibilité
class CustomExpandableSection extends StatefulWidget {
  final Widget title;
  final Widget trailing;
  final List<Widget> children;
  final bool initiallyExpanded;
  
  const CustomExpandableSection({
    Key? key,
    required this.title,
    required this.trailing,
    required this.children,
    this.initiallyExpanded = false,
  }) : super(key: key);
  
  @override
  _CustomExpandableSectionState createState() => _CustomExpandableSectionState();
}

class _CustomExpandableSectionState extends State<CustomExpandableSection> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _iconTurns;
  late Animation<double> _heightFactor;
  bool _isExpanded = false;
  
  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 200),
      vsync: this,
    );
    _heightFactor = _controller.drive(CurveTween(curve: Curves.easeInOut));
    _iconTurns = _controller.drive(Tween<double>(begin: 0.0, end: 0.5)
        .chain(CurveTween(curve: Curves.easeIn)));
    _isExpanded = widget.initiallyExpanded;
    if (_isExpanded) {
      _controller.value = 1.0;
    }
  }
  
  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }
  
  void _handleTap() {
    setState(() {
      _isExpanded = !_isExpanded;
      if (_isExpanded) {
        _controller.forward();
      } else {
        _controller.reverse();
      }
    });
  }
  
  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        GestureDetector(
          onTap: _handleTap,
          behavior: HitTestBehavior.opaque,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              border: Border(
                top: BorderSide(
                  color: Colors.white.withOpacity(0.1),
                  width: 0.5,
                ),
              ),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: <Widget>[
                widget.title,
                RotationTransition(
                  turns: _iconTurns,
                  child: widget.trailing,
                ),
              ],
            ),
          ),
        ),
        ClipRect(
          child: AnimatedBuilder(
            animation: _controller,
            builder: (context, child) {
              return SizeTransition(
                sizeFactor: _heightFactor,
                child: child,
              );
            },
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: widget.children,
            ),
          ),
        ),
      ],
    );
  }
}