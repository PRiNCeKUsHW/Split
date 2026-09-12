import 'category.dart';
import 'user.dart';

class ExpenseShare {
  final int? id;
  final User? user;
  final int? userId;
  final String? userName;
  final String amountOwed;
  final String basis;
  final int? presentDays;
  final int? shareUnits;
  final String? percent;

  ExpenseShare({
    this.id,
    this.user,
    this.userId,
    this.userName,
    required this.amountOwed,
    this.basis = '',
    this.presentDays,
    this.shareUnits,
    this.percent,
  });

  factory ExpenseShare.fromJson(Map<String, dynamic> json) {
    return ExpenseShare(
      id: json['id'] as int?,
      user: json['user'] != null ? User.fromJson(json['user']) : null,
      userId: json['user_id'] as int?,
      userName: json['user_name'] as String?,
      amountOwed: json['amount_owed']?.toString() ?? '0.00',
      basis: json['basis'] as String? ?? '',
      presentDays: json['present_days'] as int?,
      shareUnits: json['share_units'] as int?,
      percent: json['percent']?.toString(),
    );
  }
}

class Comment {
  final int id;
  final User author;
  final String body;
  final String createdAt;

  Comment({
    required this.id,
    required this.author,
    required this.body,
    required this.createdAt,
  });

  factory Comment.fromJson(Map<String, dynamic> json) {
    return Comment(
      id: json['id'] as int,
      author: User.fromJson(json['author']),
      body: json['body'] as String? ?? '',
      createdAt: json['created_at'] as String? ?? '',
    );
  }
}

class Expense {
  final int id;
  final String description;
  final String? amount;
  final String date;
  final String? periodStart;
  final String? periodEnd;
  final int? periodDays;
  final String splitType;
  final String? splitTypeLabel;
  final Category category;
  final User paidBy;
  final User? createdBy;
  final String? notes;
  final String? receiptUrl;
  final bool isDraft;
  final String? myShare;
  final int sharesCount;
  final List<ExpenseShare> shares;
  final List<Comment> comments;
  final bool isMonthClosed;

  Expense({
    required this.id,
    required this.description,
    this.amount,
    required this.date,
    this.periodStart,
    this.periodEnd,
    this.periodDays,
    required this.splitType,
    this.splitTypeLabel,
    required this.category,
    required this.paidBy,
    this.createdBy,
    this.notes,
    this.receiptUrl,
    required this.isDraft,
    this.myShare,
    this.sharesCount = 0,
    this.shares = const [],
    this.comments = const [],
    this.isMonthClosed = false,
  });

  factory Expense.fromJson(Map<String, dynamic> json) {
    var sharesList = <ExpenseShare>[];
    if (json['shares'] != null && json['shares'] is List) {
      sharesList = (json['shares'] as List)
          .map((s) => ExpenseShare.fromJson(s as Map<String, dynamic>))
          .toList();
    }

    var commentsList = <Comment>[];
    if (json['comments'] != null && json['comments'] is List) {
      commentsList = (json['comments'] as List)
          .map((c) => Comment.fromJson(c as Map<String, dynamic>))
          .toList();
    }

    return Expense(
      id: json['id'] as int,
      description: json['description'] as String? ?? '',
      amount: json['amount']?.toString(),
      date: json['date'] as String? ?? '',
      periodStart: json['period_start'] as String?,
      periodEnd: json['period_end'] as String?,
      periodDays: json['period_days'] as int?,
      splitType: json['split_type'] as String? ?? 'EQUAL',
      splitTypeLabel: json['split_type_label'] as String?,
      category: Category.fromJson(json['category'] as Map<String, dynamic>),
      paidBy: User.fromJson(json['paid_by'] as Map<String, dynamic>),
      createdBy: json['created_by'] != null
          ? User.fromJson(json['created_by'] as Map<String, dynamic>)
          : null,
      notes: json['notes'] as String?,
      receiptUrl: json['receipt_url'] as String?,
      isDraft: json['is_draft'] as bool? ?? false,
      myShare: json['my_share']?.toString(),
      sharesCount: json['shares_count'] as int? ?? sharesList.length,
      shares: sharesList,
      comments: commentsList,
      isMonthClosed: json['is_month_closed'] as bool? ?? false,
    );
  }
}
