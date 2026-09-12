import 'user.dart';

class Transfer {
  final User fromUser;
  final User toUser;
  final String amount;
  final bool involvesMe;
  final bool iPay;

  Transfer({
    required this.fromUser,
    required this.toUser,
    required this.amount,
    required this.involvesMe,
    required this.iPay,
  });

  factory Transfer.fromJson(Map<String, dynamic> json) {
    return Transfer(
      fromUser: User.fromJson(json['from_user'] as Map<String, dynamic>),
      toUser: User.fromJson(json['to_user'] as Map<String, dynamic>),
      amount: json['amount']?.toString() ?? '0.00',
      involvesMe: json['involves_me'] as bool? ?? false,
      iPay: json['i_pay'] as bool? ?? false,
    );
  }
}

class BalanceSummary {
  final User user;
  final String net;
  final bool isMe;

  BalanceSummary({
    required this.user,
    required this.net,
    required this.isMe,
  });

  factory BalanceSummary.fromJson(Map<String, dynamic> json) {
    return BalanceSummary(
      user: User.fromJson(json['user'] as Map<String, dynamic>),
      net: json['net']?.toString() ?? '0.00',
      isMe: json['is_me'] as bool? ?? false,
    );
  }
}

class SettlementItem {
  final int id;
  final User? fromUser;
  final User? toUser;
  final String amount;
  final String date;
  final String method;
  final String note;
  final String? status;
  final String? statusLabel;
  final String? confirmedAt;
  final String? createdAt;

  SettlementItem({
    required this.id,
    this.fromUser,
    this.toUser,
    required this.amount,
    required this.date,
    required this.method,
    this.note = '',
    this.status,
    this.statusLabel,
    this.confirmedAt,
    this.createdAt,
  });

  factory SettlementItem.fromJson(Map<String, dynamic> json) {
    return SettlementItem(
      id: json['id'] as int,
      fromUser: json['from_user'] != null
          ? User.fromJson(json['from_user'] as Map<String, dynamic>)
          : null,
      toUser: json['to_user'] != null
          ? User.fromJson(json['to_user'] as Map<String, dynamic>)
          : null,
      amount: json['amount']?.toString() ?? '0.00',
      date: json['date'] as String? ?? '',
      method: json['method'] as String? ?? 'UPI',
      note: json['note'] as String? ?? '',
      status: json['status'] as String?,
      statusLabel: json['status_label'] as String?,
      confirmedAt: json['confirmed_at'] as String?,
      createdAt: json['created_at'] as String?,
    );
  }
}
