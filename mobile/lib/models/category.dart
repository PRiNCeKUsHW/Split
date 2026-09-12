import 'package:flutter/material.dart';

class Category {
  final int id;
  final String name;
  final String icon;
  final String colorHex;
  final String behaviour;
  final String behaviourLabel;
  final bool prorateByTenancy;
  final bool prorateByPresence;

  Category({
    required this.id,
    required this.name,
    required this.icon,
    required this.colorHex,
    required this.behaviour,
    required this.behaviourLabel,
    required this.prorateByTenancy,
    required this.prorateByPresence,
  });

  factory Category.fromJson(Map<String, dynamic> json) {
    return Category(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      icon: json['icon'] as String? ?? '',
      colorHex: json['color'] as String? ?? '#3a34c9',
      behaviour: json['behaviour'] as String? ?? 'EVEN',
      behaviourLabel: json['behaviour_label'] as String? ?? 'Split evenly',
      prorateByTenancy: json['prorate_by_tenancy'] as bool? ?? false,
      prorateByPresence: json['prorate_by_presence'] as bool? ?? false,
    );
  }

  Color get color {
    try {
      String hex = colorHex.replaceAll('#', '');
      if (hex.length == 6) {
        hex = 'FF$hex';
      }
      return Color(int.parse(hex, radix: 16));
    } catch (_) {
      return const Color(0xFF3A34C9);
    }
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is Category && runtimeType == other.runtimeType && id == other.id);

  @override
  int get hashCode => id.hashCode;
}
