import 'package:flutter/material.dart';

class AppColors {
  // Light Theme Palette
  static const Color ink = Color(0xFF0A0A0A);
  static const Color paper = Color(0xFFFAFAF9); // bone, never pure white
  static const Color surface = Color(0xFFFFFFFF);
  static const Color muted = Color(0xFF44403C); // Dark stone for crystal clear readability (>9:1 contrast)

  // Flat Saturated Fills (Text on any of these is ALWAYS black)
  static const Color topbar = Color(0xFFA78BFA); // FlatSplit violet topbar
  static const Color action = Color(0xFFA78BFA); // Violet (buttons, active tabs)
  static const Color creditFill = Color(0xFFBEF264); // Lime (you are owed)
  static const Color debitFill = Color(0xFFFB7185); // Rose (you owe)
  static const Color infoFill = Color(0xFF67E8F9); // Cyan (neutral / drafts)

  // Semantic text colors, only ever on paper or surface
  static const Color creditText = Color(0xFF15803D); // Deep forest green
  static const Color debitText = Color(0xFFBE123C); // Deep crimson

  // Dark Theme Palette
  static const Color darkInk = Color(0xFFF4F2EE);
  static const Color darkPaper = Color(0xFF14131A);
  static const Color darkSurface = Color(0xFF1E1C26);
  static const Color darkMuted = Color(0xFFA8A29E);
  static const Color darkCreditText = Color(0xFF86EFAC);
  static const Color darkDebitText = Color(0xFFFDA4AF);

  // Neobrutal Metrics
  static const double borderWidth = 3.0;
  static const double thinBorderWidth = 2.0;
  static const double shadowOffset = 4.0;
  static const double smallShadowOffset = 2.0;
  static const double largeShadowOffset = 6.0;
}
