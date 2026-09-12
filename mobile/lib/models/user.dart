class User {
  final int id;
  final String username;
  final String name;
  final String displayName;
  final String phone;
  final String upiId;
  final String initials;
  final bool isActiveMember;
  final bool isStaff;
  final String? joinedOn;
  final String? leftOn;

  User({
    required this.id,
    required this.username,
    required this.name,
    required this.displayName,
    this.phone = '',
    required this.upiId,
    required this.initials,
    required this.isActiveMember,
    this.isStaff = false,
    this.joinedOn,
    this.leftOn,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'] as int,
      username: json['username'] as String? ?? '',
      name: json['name'] as String? ?? '',
      displayName: json['display_name'] as String? ?? '',
      phone: json['phone'] as String? ?? '',
      upiId: json['upi_id'] as String? ?? '',
      initials: json['initials'] as String? ?? '?',
      isActiveMember: json['is_active_member'] as bool? ?? true,
      isStaff: json['is_staff'] as bool? ?? false,
      joinedOn: json['joined_on'] as String?,
      leftOn: json['left_on'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'username': username,
      'name': name,
      'display_name': displayName,
      'phone': phone,
      'upi_id': upiId,
      'initials': initials,
      'is_active_member': isActiveMember,
      'is_staff': isStaff,
      'joined_on': joinedOn,
      'left_on': leftOn,
    };
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is User && runtimeType == other.runtimeType && id == other.id);

  @override
  int get hashCode => id.hashCode;
}
